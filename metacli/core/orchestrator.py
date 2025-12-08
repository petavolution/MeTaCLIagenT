"""
Orchestration Engine - Coordinate AI agents with iterative sequences

Supports:
- Iterative sequences: audit → load → refactor → genplan → continue → meta-refactor
- Sub-agent decision points (process output, decide next action)
- Sequential and parallel execution
- Template-based routing
- Database persistence for entire workflow
- Error recovery and retry logic

Example:
    orchestrator = Orchestrator(db_path="workflow.db")

    # Define iterative workflow
    workflow = orchestrator.create_workflow("audit-refactor-cycle")
    workflow.add_step("audit", "claude-code", "audit {target}")
    workflow.add_decision("check_issues", decide_next_from_audit)
    workflow.add_step("load_context", "claude-code", "load context about {issues}")
    workflow.add_step("refactor", "codex", "fix {issues}")
    workflow.add_step("verify", "claude-code", "verify changes")

    # Execute
    result = orchestrator.execute(workflow, context={"target": "src/api.py"})
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Union
from enum import Enum

from .executor import UnifiedExecutor, ExecutionResult, ExecutionMode
from ..testing.realistic_parser import KeywordRouter, create_audit_refactor_router
from ..testing.database import TestDatabase


class StepType(Enum):
    """Type of workflow step."""
    EXECUTE = "execute"      # Execute CLI tool
    DECIDE = "decide"        # Make decision based on previous output
    LOOP = "loop"            # Loop back to earlier step
    PARALLEL = "parallel"    # Execute multiple steps in parallel
    SUB_WORKFLOW = "sub_workflow"  # Execute sub-workflow


@dataclass
class WorkflowStep:
    """
    Single step in workflow.

    Attributes:
        name: Step name
        step_type: Type of step
        tool: Tool to execute (for EXECUTE steps)
        prompt_template: Prompt template with {variables}
        decision_func: Decision function (for DECIDE steps)
        parallel_steps: Sub-steps for parallel execution
        condition: Optional condition to execute step
        retry_on_error: Retry if step fails
        max_retries: Maximum retry attempts
    """
    name: str
    step_type: StepType = StepType.EXECUTE
    tool: Optional[str] = None
    prompt_template: Optional[str] = None
    decision_func: Optional[Callable] = None
    parallel_steps: List[WorkflowStep] = field(default_factory=list)
    condition: Optional[Callable] = None
    retry_on_error: bool = False
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowContext:
    """
    Context passed through workflow execution.

    Attributes:
        variables: Variables available to steps
        results: Results from previous steps
        current_step: Current step index
        iteration_count: Number of iterations (for loops)
    """
    variables: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, ExecutionResult] = field(default_factory=dict)
    current_step: int = 0
    iteration_count: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get variable from context."""
        return self.variables.get(key, default)

    def set(self, key: str, value: Any):
        """Set variable in context."""
        self.variables[key] = value

    def get_last_result(self) -> Optional[ExecutionResult]:
        """Get result from last executed step."""
        if self.results:
            return list(self.results.values())[-1]
        return None


@dataclass
class Workflow:
    """
    Workflow definition with steps and decision points.

    Example:
        workflow = Workflow("audit-refactor")
        workflow.add_step("audit", "claude-code", "audit {target}")
        workflow.add_decision("route", lambda ctx: route_based_on_audit(ctx))
        workflow.add_step("refactor", "codex", "fix {issues}")
    """
    name: str
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    router: Optional[KeywordRouter] = None
    max_iterations: int = 10  # Prevent infinite loops

    def add_step(
        self,
        name: str,
        tool: str,
        prompt_template: str,
        condition: Optional[Callable] = None,
        retry_on_error: bool = False
    ) -> Workflow:
        """
        Add execution step.

        Args:
            name: Step name
            tool: Tool to execute
            prompt_template: Prompt template with {variables}
            condition: Optional condition to execute
            retry_on_error: Retry on failure

        Returns:
            Self for chaining
        """
        step = WorkflowStep(
            name=name,
            step_type=StepType.EXECUTE,
            tool=tool,
            prompt_template=prompt_template,
            condition=condition,
            retry_on_error=retry_on_error
        )
        self.steps.append(step)
        return self

    def add_decision(
        self,
        name: str,
        decision_func: Callable[[WorkflowContext], str]
    ) -> Workflow:
        """
        Add decision point.

        Args:
            name: Decision name
            decision_func: Function that returns next step name

        Returns:
            Self for chaining
        """
        step = WorkflowStep(
            name=name,
            step_type=StepType.DECIDE,
            decision_func=decision_func
        )
        self.steps.append(step)
        return self

    def add_loop(
        self,
        name: str,
        target_step: str,
        condition: Callable[[WorkflowContext], bool]
    ) -> Workflow:
        """
        Add loop back to earlier step.

        Args:
            name: Loop name
            target_step: Step name to loop back to
            condition: Condition to continue looping

        Returns:
            Self for chaining
        """
        step = WorkflowStep(
            name=name,
            step_type=StepType.LOOP,
            condition=condition,
            metadata={"target": target_step}
        )
        self.steps.append(step)
        return self

    def add_parallel(
        self,
        name: str,
        sub_steps: List[WorkflowStep]
    ) -> Workflow:
        """
        Add parallel execution of multiple steps.

        Args:
            name: Parallel block name
            sub_steps: Steps to execute in parallel

        Returns:
            Self for chaining
        """
        step = WorkflowStep(
            name=name,
            step_type=StepType.PARALLEL,
            parallel_steps=sub_steps
        )
        self.steps.append(step)
        return self

    def set_router(self, router: KeywordRouter) -> Workflow:
        """Set keyword router for automatic routing."""
        self.router = router
        return self


class Orchestrator:
    """
    Orchestration engine for AI agent workflows.

    Features:
    - Execute workflows with iterative sequences
    - Sub-agent decision points
    - Sequential and parallel execution
    - Template-based routing
    - Error recovery and retry
    - Database persistence

    Example:
        orchestrator = Orchestrator()

        # Create workflow
        workflow = orchestrator.create_workflow("audit-refactor")
        workflow.add_step("audit", "claude-code", "audit {target}")
        workflow.add_decision("route", decide_next_action)
        workflow.add_step("refactor", "codex", "fix {issues}")

        # Execute
        result = orchestrator.execute(workflow, {"target": "src/"})
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        executor: Optional[UnifiedExecutor] = None
    ):
        """
        Initialize orchestrator.

        Args:
            db_path: Path to database for persistence
            executor: Custom executor (or create default)
        """
        self.db_path = db_path
        self.executor = executor or UnifiedExecutor(db_path=db_path)
        self.db = TestDatabase(db_path) if db_path else None

        # Workflow registry
        self.workflows: Dict[str, Workflow] = {}

        # Execution history
        self.execution_history: List[Dict[str, Any]] = []

    def create_workflow(
        self,
        name: str,
        description: str = ""
    ) -> Workflow:
        """
        Create new workflow.

        Args:
            name: Workflow name
            description: Workflow description

        Returns:
            Workflow object
        """
        workflow = Workflow(name=name, description=description)
        self.workflows[name] = workflow
        return workflow

    def execute(
        self,
        workflow: Union[str, Workflow],
        context: Optional[Dict[str, Any]] = None,
        save_to_db: bool = True
    ) -> WorkflowContext:
        """
        Execute workflow.

        Args:
            workflow: Workflow object or name
            context: Initial context variables
            save_to_db: Save execution to database

        Returns:
            Final workflow context
        """
        # Get workflow object
        if isinstance(workflow, str):
            if workflow not in self.workflows:
                raise ValueError(f"Workflow '{workflow}' not found")
            workflow = self.workflows[workflow]

        # Initialize context
        ctx = WorkflowContext(variables=context or {})

        # Record start time
        start_time = time.time()

        # Execute steps
        step_idx = 0
        while step_idx < len(workflow.steps):
            step = workflow.steps[step_idx]

            # Check iteration limit
            if ctx.iteration_count >= workflow.max_iterations:
                print(f"Warning: Max iterations ({workflow.max_iterations}) reached")
                break

            # Execute step based on type
            if step.step_type == StepType.EXECUTE:
                result = self._execute_step(workflow, step, ctx)
                if result:
                    ctx.results[step.name] = result
                step_idx += 1

            elif step.step_type == StepType.DECIDE:
                next_step_name = self._execute_decision(workflow, step, ctx)
                # Find next step by name
                step_idx = self._find_step_index(workflow, next_step_name)
                if step_idx < 0:
                    step_idx = len(workflow.steps)  # End workflow

            elif step.step_type == StepType.LOOP:
                should_loop = self._execute_loop(workflow, step, ctx)
                if should_loop:
                    target_name = step.metadata.get("target")
                    step_idx = self._find_step_index(workflow, target_name)
                    ctx.iteration_count += 1
                else:
                    step_idx += 1

            elif step.step_type == StepType.PARALLEL:
                results = self._execute_parallel(workflow, step, ctx)
                for name, result in results.items():
                    ctx.results[name] = result
                step_idx += 1

            else:
                step_idx += 1

        # Record execution
        duration = time.time() - start_time
        execution_record = {
            "workflow": workflow.name,
            "duration": duration,
            "steps_executed": len(ctx.results),
            "timestamp": start_time,
            "context": ctx.variables,
        }
        self.execution_history.append(execution_record)

        # Save to database
        if save_to_db and self.db:
            self._save_workflow_to_db(workflow, ctx, duration)

        return ctx

    def _execute_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        ctx: WorkflowContext
    ) -> Optional[ExecutionResult]:
        """Execute single workflow step."""
        # Check condition
        if step.condition and not step.condition(ctx):
            return None

        # Render prompt template
        prompt = self._render_template(step.prompt_template, ctx)

        # Execute with retry
        for attempt in range(step.max_retries + 1):
            result = self.executor.execute(
                tool=step.tool,
                prompt=prompt,
                save_to_db=False  # We'll save the whole workflow
            )

            # Check if successful
            if result.success or not step.retry_on_error:
                return result

            # Retry if needed
            if attempt < step.max_retries:
                print(f"Retry {attempt + 1}/{step.max_retries} for step {step.name}")
                time.sleep(1)  # Brief delay before retry

        return result

    def _execute_decision(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        ctx: WorkflowContext
    ) -> str:
        """Execute decision step."""
        if not step.decision_func:
            return ""

        # Get last result
        last_result = ctx.get_last_result()

        # Use router if available
        if workflow.router and last_result and last_result.parsed_output:
            next_action = workflow.router.route(last_result.parsed_output)
            ctx.set("next_action", next_action)

        # Call decision function
        next_step_name = step.decision_func(ctx)

        return next_step_name

    def _execute_loop(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        ctx: WorkflowContext
    ) -> bool:
        """Execute loop step."""
        if not step.condition:
            return False

        return step.condition(ctx)

    def _execute_parallel(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        ctx: WorkflowContext
    ) -> Dict[str, ExecutionResult]:
        """Execute parallel steps using ThreadPoolExecutor."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import copy

        results = {}

        # Determine number of workers
        max_workers = min(len(step.parallel_steps), 10)  # Cap at 10 concurrent

        # Execute in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            # Submit all tasks
            future_to_step = {}
            for sub_step in step.parallel_steps:
                if sub_step.step_type == StepType.EXECUTE:
                    # Create copy of context for thread safety
                    ctx_copy = copy.deepcopy(ctx)
                    future = pool.submit(
                        self._execute_step,
                        workflow,
                        sub_step,
                        ctx_copy
                    )
                    future_to_step[future] = sub_step

            # Collect results as they complete
            for future in as_completed(future_to_step):
                sub_step = future_to_step[future]
                try:
                    result = future.result()
                    if result:
                        results[sub_step.name] = result
                except Exception as e:
                    print(f"Error in parallel step {sub_step.name}: {e}")

        return results

    def _render_template(
        self,
        template: Optional[str],
        ctx: WorkflowContext
    ) -> str:
        """Render prompt template with context variables."""
        if not template:
            return ""

        # Simple variable substitution
        rendered = template
        for key, value in ctx.variables.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))

        return rendered

    def _find_step_index(
        self,
        workflow: Workflow,
        step_name: str
    ) -> int:
        """Find step index by name."""
        for i, step in enumerate(workflow.steps):
            if step.name == step_name:
                return i
        return -1

    def _save_workflow_to_db(
        self,
        workflow: Workflow,
        ctx: WorkflowContext,
        duration: float
    ):
        """Save workflow execution to database."""
        if not self.db:
            return

        from ..testing.database import TestScenario

        # Create scenario from workflow
        steps = []
        for name, result in ctx.results.items():
            steps.append({
                "name": name,
                "tool": result.tool,
                "prompt": result.prompt,
                "output": result.raw_output[:500],  # Truncate
                "duration": result.duration,
                "success": result.success,
            })

        scenario = TestScenario(
            name=f"{workflow.name}_{int(time.time())}",
            description=workflow.description,
            steps=steps,
            tags=[workflow.name, "orchestration"],
            category="workflow"
        )

        self.db.save_scenario(scenario)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-built Workflows
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_audit_refactor_workflow(
    orchestrator: Orchestrator,
    target: str = "src/"
) -> Workflow:
    """
    Create audit-refactor workflow.

    Sequence: audit → load → refactor → verify → meta

    Args:
        orchestrator: Orchestrator instance
        target: Target directory to audit

    Returns:
        Configured workflow
    """
    workflow = orchestrator.create_workflow(
        "audit-refactor",
        "Complete audit-refactor cycle"
    )

    # Set router
    workflow.set_router(create_audit_refactor_router())

    # Step 1: Audit
    workflow.add_step(
        "audit",
        "claude-code",
        "audit {target} for security and quality issues"
    )

    # Decision: Check if issues found
    def decide_after_audit(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if last and last.parsed_output:
            if last.parsed_output.has_identified_issues:
                return "load_context"
        return "done"

    workflow.add_decision("check_issues", decide_after_audit)

    # Step 2: Load context
    workflow.add_step(
        "load_context",
        "claude-code",
        "load context about the identified issues in {target}"
    )

    # Step 3: Refactor
    workflow.add_step(
        "refactor",
        "codex",
        "fix the identified issues in {target}"
    )

    # Step 4: Verify
    workflow.add_step(
        "verify",
        "claude-code",
        "verify that all issues in {target} have been fixed"
    )

    # Step 5: Meta-analyze
    workflow.add_step(
        "meta",
        "gemini",
        "meta-analyze the refactoring approach for {target}"
    )

    return workflow


def create_iterative_refactor_workflow(
    orchestrator: Orchestrator,
    max_iterations: int = 3
) -> Workflow:
    """
    Create iterative refactor workflow with continue loop.

    Sequence: audit → refactor → genplan → continue → genplan → continue

    Args:
        orchestrator: Orchestrator instance
        max_iterations: Maximum iterations

    Returns:
        Configured workflow
    """
    workflow = orchestrator.create_workflow(
        "iterative-refactor",
        "Iterative refactor with continue loop"
    )
    workflow.max_iterations = max_iterations

    # Step 1: Initial audit
    workflow.add_step(
        "audit",
        "claude-code",
        "audit {target} and create refactoring plan"
    )

    # Step 2: Apply refactoring
    workflow.add_step(
        "refactor",
        "codex",
        "apply refactoring phase {iteration} to {target}"
    )

    # Step 3: Generate plan for next iteration
    workflow.add_step(
        "genplan",
        "codex",
        "generate plan for next refactoring iteration on {target}"
    )

    # Decision: Continue or finish?
    def decide_continue(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if last and last.is_complete:
            return "done"
        if ctx.iteration_count < max_iterations:
            return "continue"
        return "done"

    workflow.add_decision("check_continue", decide_continue)

    # Step 4: Continue with next phase
    workflow.add_step(
        "continue",
        "codex",
        "continue with next refactoring phase for {target}"
    )

    # Loop back to genplan
    def should_loop(ctx: WorkflowContext) -> bool:
        return ctx.iteration_count < max_iterations

    workflow.add_loop("loop_back", "genplan", should_loop)

    return workflow
