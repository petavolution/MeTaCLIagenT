"""
Workflow Engine - Unified Orchestration API

The Workflow class is the unified API for all orchestration needs:
- Simple sequences (like CLISequence)
- Advanced workflows with conditionals, loops, sub-agents
- Declarative workflows from YAML/JSON
- Pre-built patterns
- Registry-based workflows

Multiple Construction Methods:
    # Direct instantiation
    workflow = Workflow("my-task")
    workflow.add_step("step1", "python", "print('hi')")

    # From YAML/JSON
    workflow = Workflow.from_yaml("workflow.yaml")

    # From pattern
    workflow = Workflow.from_pattern(audit_refactor_cycle("src/"))

    # From registry
    workflow = Workflow.from_registry("audit-refactor")

Advanced Features:
- Conditional branching (if/else)
- Loops (repeat until condition)
- Sub-agent delegation
- Dynamic prompt generation
- Context passing

Example:
    from metacli.core import Workflow

    # Simple workflow
    workflow = Workflow("code-review")
    workflow.add_step("generate", "claude-code", "Write API")
    workflow.add_step("review", "gemini", "Review code", use_previous=True)
    result = workflow.run()

    # Advanced workflow
    workflow = Workflow.from_yaml("workflows/audit-refactor.yaml", target="src/")
    result = workflow.run()
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from ..kernel import Process, Security, SecurityError
from .sequence import CLIToolConfig, get_tool_config, OutputParser
from .persistence import get_persistence
from .decision import (
    Decision, DecisionType, DecisionEngine,
    DecisionFunc, ConditionFunc, Condition, PromptTemplate,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Step
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class WorkflowStep:
    """A step in a workflow with conditional/loop support."""
    name: str                                    # Step name
    tool_name: str                               # CLI tool to use
    prompt: str | PromptTemplate                 # Prompt or template
    use_previous: bool = False                   # Use previous output
    condition: Optional[str | ConditionFunc] = None  # Execution condition
    decision: Optional[DecisionFunc] = None      # Decision function
    loop_to: Optional[str] = None                # Loop forward to step
    loop_back_to: Optional[str] = None           # Loop back to step
    max_iterations: Optional[int] = None         # Max loop iterations
    timeout: float = 60.0

    # Results (populated after execution)
    raw_output: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None
    duration: float = 0.0
    iterations: int = 0
    decision_result: Optional[Decision] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Workflow:
    """
    Advanced workflow engine with conditionals, loops, and sub-agents.

    Features:
    - Conditional execution
    - Loop support (forward and backward)
    - Sub-agent delegation
    - Context tracking
    - Dynamic prompt generation
    - Auto-persistence

    Example:
        workflow = Workflow("my-workflow")
        workflow.add_step("generate", "claude-code", "Write code")
        workflow.add_step("test", "python", "pytest", condition="has_code")
        result = workflow.run()
    """

    def __init__(self, name: str = "workflow", auto_save: bool = True):
        """
        Initialize workflow.

        Args:
            name: Workflow name
            auto_save: Auto-save results to persistence layer
        """
        self.name = name
        self.steps: List[WorkflowStep] = []
        self.step_map: Dict[str, int] = {}  # name -> index
        self.processes: Dict[str, Process] = {}
        self.parser = OutputParser()
        self.security = Security()
        self.auto_save = auto_save
        self.workflow_id: Optional[str] = None
        self.started_at: Optional[float] = None

        # Execution context
        self.context: Dict[str, Any] = {
            "iteration": 0,
            "all_outputs": [],
        }

    @classmethod
    def from_pattern(cls, pattern: Dict[str, Any]) -> Workflow:
        """
        Create workflow from pattern definition.

        Args:
            pattern: Pattern dict from patterns.py

        Returns:
            Workflow instance

        Example:
            from metacli.core.patterns import audit_refactor_cycle
            pattern = audit_refactor_cycle("src/api.py")
            workflow = Workflow.from_pattern(pattern)
        """
        workflow = cls(pattern["name"], auto_save=True)

        # Initialize context from pattern
        workflow.context.update(pattern.get("context", {}))

        # Add steps
        for step_def in pattern["steps"]:
            workflow.add_step(
                name=step_def["name"],
                tool_name=step_def["tool"],
                prompt=step_def["prompt"],
                use_previous=step_def.get("use_previous", False),
                condition=step_def.get("condition"),
                decision=step_def.get("decision"),
                loop_to=step_def.get("loop_to"),
                loop_back_to=step_def.get("loop_back_to"),
                max_iterations=step_def.get("max_iterations"),
                timeout=step_def.get("timeout", 60.0),
            )

        return workflow

    @classmethod
    def from_yaml(cls, filepath: str, **context) -> Workflow:
        """
        Create workflow from YAML file.

        Args:
            filepath: Path to YAML workflow file
            **context: Context variables to override

        Returns:
            Workflow instance

        Example:
            workflow = Workflow.from_yaml("workflows/audit-refactor.yaml", target="src/")
        """
        # Import here to avoid circular dependency
        try:
            from ..meta import WorkflowLoader
            return WorkflowLoader.from_yaml(filepath, **context)
        except ImportError:
            raise ImportError("Meta layer not available. Install: pip install pyyaml")

    @classmethod
    def from_json(cls, filepath: str, **context) -> Workflow:
        """
        Create workflow from JSON file.

        Args:
            filepath: Path to JSON workflow file
            **context: Context variables to override

        Returns:
            Workflow instance

        Example:
            workflow = Workflow.from_json("workflows/audit.json")
        """
        # Import here to avoid circular dependency
        try:
            from ..meta import WorkflowLoader
            return WorkflowLoader.from_json(filepath, **context)
        except ImportError:
            raise ImportError("Meta layer not available. Install: pip install pyyaml")

    @classmethod
    def from_registry(cls, name: str, **context) -> Workflow:
        """
        Load workflow from registry by name.

        Args:
            name: Registered workflow name
            **context: Context variables to override

        Returns:
            Workflow instance

        Example:
            workflow = Workflow.from_registry("audit-refactor", target="src/")
        """
        # Import here to avoid circular dependency
        try:
            from ..meta import get_registry
            registry = get_registry()
            return registry.get(name, **context)
        except ImportError:
            raise ImportError("Meta layer not available. Install: pip install pyyaml")

    def add_step(
        self,
        name: str,
        tool_name: str,
        prompt: str | PromptTemplate,
        use_previous: bool = False,
        condition: Optional[str | ConditionFunc] = None,
        decision: Optional[DecisionFunc] = None,
        loop_to: Optional[str] = None,
        loop_back_to: Optional[str] = None,
        max_iterations: Optional[int] = None,
        timeout: float = 60.0,
    ) -> WorkflowStep:
        """
        Add a step to the workflow.

        Args:
            name: Step name (unique identifier)
            tool_name: CLI tool to use
            prompt: Prompt string or PromptTemplate
            use_previous: Include previous step output
            condition: Condition for execution (name or function)
            decision: Decision function for routing
            loop_to: Step name to loop forward to
            loop_back_to: Step name to loop back to
            max_iterations: Max loop iterations
            timeout: Step timeout

        Returns:
            Created WorkflowStep

        Example:
            workflow.add_step(
                "fix",
                "aider",
                PromptTemplate("Fix {{error_count}} errors"),
                decision=has_errors_decision,
                loop_back_to="test",
                max_iterations=3
            )
        """
        step = WorkflowStep(
            name=name,
            tool_name=tool_name,
            prompt=prompt,
            use_previous=use_previous,
            condition=condition,
            decision=decision,
            loop_to=loop_to,
            loop_back_to=loop_back_to,
            max_iterations=max_iterations,
            timeout=timeout,
        )
        self.steps.append(step)
        self.step_map[name] = len(self.steps) - 1
        return step

    def run(self) -> Dict[str, Any]:
        """
        Execute the workflow.

        Returns:
            Result dictionary with all steps, outputs, decisions

        Example:
            result = workflow.run()
            print(f"Status: {result['status']}")
            print(f"Steps executed: {result['total_steps']}")
        """
        start_time = time.time()
        self.started_at = start_time
        self.workflow_id = f"workflow-{int(start_time * 1000):x}"

        previous_output = ""
        current_index = 0

        while current_index < len(self.steps):
            step = self.steps[current_index]

            # Check condition
            if step.condition:
                condition_met = Condition.evaluate(
                    step.condition,
                    previous_output,
                    self.context
                )
                if not condition_met:
                    # Skip this step
                    current_index += 1
                    continue

            # Build prompt
            if isinstance(step.prompt, PromptTemplate):
                full_prompt = step.prompt.render({
                    **self.context,
                    "previous_output": previous_output,
                })
            elif step.use_previous and previous_output:
                full_prompt = f"{step.prompt}\n\nPrevious output:\n{previous_output}"
            else:
                full_prompt = step.prompt

            # Execute step
            try:
                output = self._execute_step(step, full_prompt)
                step.raw_output = output
                step.success = True
                step.iterations += 1

                # Parse output
                step.parsed_data = self._parse_step_output(output)

                # Update context
                self.context["all_outputs"].append(output)
                self.context["last_output"] = output
                self.context[f"{step.name}_output"] = output

                # Make decision
                if step.decision:
                    decision = DecisionEngine.analyze(
                        output,
                        self.context,
                        step.decision
                    )
                    step.decision_result = decision
                    self.context.update(decision.context)

                    # Handle decision routing
                    if decision.type == DecisionType.LOOP and step.loop_back_to:
                        # Check max iterations
                        if step.max_iterations and step.iterations >= step.max_iterations:
                            # Max iterations reached, continue forward
                            previous_output = self.parser.summarize_output(output)
                            current_index += 1
                        else:
                            # Loop back
                            loop_index = self.step_map.get(step.loop_back_to)
                            if loop_index is not None:
                                current_index = loop_index
                                previous_output = decision.next_prompt or output
                            else:
                                # Invalid loop target, continue
                                previous_output = self.parser.summarize_output(output)
                                current_index += 1
                    elif decision.type == DecisionType.STOP:
                        # Stop execution
                        break
                    elif decision.next_step and decision.next_step in self.step_map:
                        # Branch to specific step
                        current_index = self.step_map[decision.next_step]
                        previous_output = decision.next_prompt or output
                    else:
                        # Continue to next step
                        previous_output = self.parser.summarize_output(output)
                        current_index += 1
                else:
                    # No decision, continue
                    previous_output = self.parser.summarize_output(output)
                    current_index += 1

            except Exception as e:
                step.success = False
                step.error = str(e)
                # Stop on error
                break

        total_duration = time.time() - start_time
        result = self._build_result(total_duration)

        # Auto-save
        if self.auto_save:
            self._save_result(result)

        return result

    def _execute_step(self, step: WorkflowStep, prompt: str) -> str:
        """Execute a single step."""
        start = time.time()

        # Get tool config
        tool_config = get_tool_config(step.tool_name)
        if not tool_config:
            raise SecurityError(f"Unknown tool: {step.tool_name}")

        # Validate command
        self.security.validate_command(tool_config.cmd)

        # Get or create process
        if step.tool_name not in self.processes:
            proc = Process.spawn(
                cmd=tool_config.cmd,
                interactive=tool_config.requires_pty,
                name=tool_config.name,
            )
            proc.start()
            self.processes[step.tool_name] = proc

        proc = self.processes[step.tool_name]

        # Send prompt and get response
        try:
            proc.write(prompt + "\n")
            response = proc.read(timeout=step.timeout)
            step.duration = time.time() - start
            return response
        except Exception as e:
            step.duration = time.time() - start
            raise

    def _parse_step_output(self, output: str) -> Dict[str, Any]:
        """Parse step output."""
        return {
            "code_blocks": self.parser.extract_code_blocks(output),
            "has_errors": self.parser.has_errors(output),
            "file_paths": self.parser.extract_file_paths(output),
            "test_results": self.parser.parse_test_results(output),
            "summary": self.parser.summarize_output(output, max_length=200),
        }

    def _build_result(self, total_duration: float) -> Dict[str, Any]:
        """Build final result summary."""
        successful_steps = sum(1 for s in self.steps if s.success)
        has_error = any(not s.success for s in self.steps)

        return {
            "id": self.workflow_id,
            "name": self.name,
            "status": "failed" if has_error else "completed",
            "started_at": self.started_at,
            "completed_at": time.time(),
            "total_steps": len(self.steps),
            "successful_steps": successful_steps,
            "duration": total_duration,
            "error_message": next((s.error for s in self.steps if not s.success), None),
            "context": self.context,
            "steps": [
                {
                    "name": s.name,
                    "tool_name": s.tool_name,
                    "prompt": str(s.prompt),
                    "raw_output": s.raw_output or "",
                    "success": s.success,
                    "duration": s.duration,
                    "iterations": s.iterations,
                    "parsed_data": s.parsed_data,
                    "error_message": s.error,
                    "decision": {
                        "type": s.decision_result.type.value if s.decision_result else None,
                        "reason": s.decision_result.reason if s.decision_result else None,
                    } if s.decision_result else None,
                }
                for s in self.steps
            ],
            "final_output": self.steps[-1].raw_output if self.steps and self.steps[-1].success else None,
        }

    def _save_result(self, result: Dict[str, Any]) -> None:
        """Save result to persistence layer."""
        try:
            persistence = get_persistence()
            persistence.save(result)
        except Exception:
            pass

    def cleanup(self):
        """Stop all processes."""
        for tool_name, proc in self.processes.items():
            proc.terminate()
        self.processes.clear()
