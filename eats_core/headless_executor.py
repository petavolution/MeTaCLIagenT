# headless_executor.py - Non-Interactive Execution Engine
"""
Headless Executor for MeTaCLIagenT.

Enables non-interactive, scriptable execution of AI tool workflows.
Inspired by Codex CLI's `exec` command, enhanced with EATS's
universal orchestration capabilities.

Key Features:
- One-shot execution (single prompt → result)
- Multi-step playbook automation (5-step pattern)
- JSONL event streaming (machine-parseable monitoring)
- Session persistence & resume (long-running tasks)
- Stdin prompt ingestion (safe from shell escaping)
- Structured output validation (JSON schemas)

Usage:
    # One-shot execution
    executor = HeadlessExecutor(orchestrator, session_manager)
    result = await executor.execute_one_shot(
        prompt="Scan repo and identify bugs",
        tools=[claude_tool, aider_tool],
    )

    # Playbook execution
    playbook = Playbook.from_file("workflow.yaml")
    result = await executor.execute_playbook(playbook, variables={})

    # Resume session
    result = await executor.resume_session("session-abc123")

Command Line:
    eats exec "prompt"
    eats exec - < prompt.md
    eats exec --playbook workflow.yaml
    eats exec resume abc123
    eats exec --last
"""

from __future__ import annotations
import asyncio
import time
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import json

from .universal_orchestrator import (
    UniversalOrchestrator,
    OrchestrationResult,
    ExecutionConfig,
    ExecutionStrategy,
)
from .universal_tool import UniversalTool, ToolResult, ExecutionStatus
from .event_logger import JSONLEventLogger, NullEventLogger


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class HeadlessResult:
    """
    Result of headless execution.

    Contains all outputs, events, and session metadata.
    """
    # Session metadata
    session_id: str
    session_name: str
    workflow_type: str  # "one-shot", "playbook", "resume"

    # Execution result
    orchestration_result: OrchestrationResult
    final_output: str = ""

    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration: float = 0.0

    # Artifacts
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.orchestration_result.is_success()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "workflow_type": self.workflow_type,
            "status": self.orchestration_result.status.value,
            "success": self.is_success(),
            "total_duration": self.total_duration,
            "final_output": self.final_output,
            "artifacts": self.artifacts,
        }


@dataclass
class PromptSource:
    """Source of prompt for headless execution."""
    type: str  # "arg", "stdin", "file"
    content: str
    filepath: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Headless Executor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class HeadlessExecutor:
    """
    Non-interactive execution engine for EATS.

    Inspired by Codex CLI's `exec` command, this enables:
    - One-shot workflow execution
    - Multi-step playbook automation
    - JSONL event streaming
    - Session persistence & resume
    """

    def __init__(
        self,
        orchestrator: UniversalOrchestrator,
        session_manager: Optional[Any] = None,  # SessionManager from Phase 7
        event_logger: Optional[JSONLEventLogger] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        """
        Initialize headless executor.

        Args:
            orchestrator: UniversalOrchestrator instance
            session_manager: Optional SessionManager for persistence
            event_logger: Optional EventLogger for JSONL streaming
            config: Execution configuration
        """
        self.orchestrator = orchestrator
        self.session_manager = session_manager
        self.event_logger = event_logger or NullEventLogger()
        self.config = config or ExecutionConfig()

        # State
        self._current_session: Optional[Any] = None

    # ─────────────────────────────────────────────────────
    # One-Shot Execution
    # ─────────────────────────────────────────────────────

    async def execute_one_shot(
        self,
        prompt: str,
        tools: List[UniversalTool],
        context: Optional[Dict[str, Any]] = None,
    ) -> HeadlessResult:
        """
        Execute a single prompt through a tool chain.

        This is the simplest execution mode:
        - Takes a prompt string
        - Runs it through a list of tools
        - Returns aggregated result

        Args:
            prompt: User prompt (from stdin/arg/file)
            tools: Tools to execute
            context: Execution context

        Returns:
            HeadlessResult with outputs and events
        """
        start_time = time.time()
        context = context or {}

        # Generate session ID
        session_id = f"headless-{int(start_time)}"
        session_name = "one-shot"

        # Emit session start
        self.event_logger.session_start(
            session_id=session_id,
            workflow="one-shot",
            variables={"prompt": prompt[:100]},
        )

        try:
            # Create session if manager available
            if self.session_manager:
                self._current_session = await self.session_manager.create_session(
                    name=session_name,
                    workflow="one-shot",
                    variables={"prompt": prompt},
                )
                session_id = self._current_session.id
                context["session_id"] = session_id

            # Execute orchestration
            orchestration_result = await self._execute_with_events(
                tools=tools,
                inputs=[prompt],
                context=context,
            )

            # Build headless result
            result = HeadlessResult(
                session_id=session_id,
                session_name=session_name,
                workflow_type="one-shot",
                orchestration_result=orchestration_result,
                final_output=orchestration_result.get_output(),
                start_time=start_time,
                end_time=time.time(),
                total_duration=time.time() - start_time,
            )

            # Save session if manager available
            if self.session_manager and self._current_session:
                self._current_session.orchestration_results = [orchestration_result]
                self._current_session.status = orchestration_result.status
                await self.session_manager.save_session(self._current_session)

            # Emit completion
            self.event_logger.session_complete(
                session_id=session_id,
                status=orchestration_result.status.value,
                total_duration=result.total_duration,
            )

            return result

        except Exception as e:
            # Emit error event
            self.event_logger.session_error(
                session_id=session_id,
                error=str(e),
            )
            raise

    # ─────────────────────────────────────────────────────
    # Multi-Step Playbook Execution
    # ─────────────────────────────────────────────────────

    async def execute_playbook(
        self,
        playbook: Any,  # Playbook from Phase 6
        initial_vars: Optional[Dict[str, str]] = None,
    ) -> HeadlessResult:
        """
        Execute a multi-step playbook (5-step automation pattern).

        Playbooks support:
        - Sequential step execution
        - Conditional branching (IF/THEN)
        - Variable substitution
        - Checkpointing for resume

        Args:
            playbook: Playbook definition (YAML/JSON)
            initial_vars: Initial variables for template substitution

        Returns:
            HeadlessResult with all step outputs
        """
        start_time = time.time()
        initial_vars = initial_vars or {}

        # Generate session ID
        session_id = f"playbook-{playbook.name}-{int(start_time)}"

        # Emit session start
        self.event_logger.session_start(
            session_id=session_id,
            workflow="playbook",
            variables=initial_vars,
        )

        try:
            # Create session if manager available
            if self.session_manager:
                self._current_session = await self.session_manager.create_session(
                    name=playbook.name,
                    workflow="playbook",
                    variables=initial_vars,
                )
                session_id = self._current_session.id

            # Execute each step
            step_results = []
            total_steps = len(playbook.steps)

            for i, step in enumerate(playbook.steps):
                step_num = i + 1

                # Emit step start
                self.event_logger.step_start(
                    session_id=session_id,
                    step=step_num,
                    total_steps=total_steps,
                    name=step.get("name", f"step-{step_num}"),
                )

                # Execute step (placeholder - needs Phase 6 TemplateExecutor)
                step_result = await self._execute_playbook_step(
                    step=step,
                    variables=initial_vars,
                    context={"session_id": session_id},
                )

                step_results.append(step_result)

                # Save checkpoint if manager available
                if self.session_manager and self._current_session:
                    await self.session_manager.save_checkpoint(
                        session_id=session_id,
                        step=step_num,
                        result=step_result,
                    )
                    self.event_logger.checkpoint_save(session_id, step_num)

                # Emit step complete
                self.event_logger.step_complete(
                    step=step_num,
                    status=step_result.status.value if hasattr(step_result, 'status') else "completed",
                    duration=step_result.duration_seconds if hasattr(step_result, 'duration_seconds') else 0.0,
                )

            # Aggregate results
            aggregated_result = OrchestrationResult(
                strategy=ExecutionStrategy.SEQUENTIAL,
                status=ExecutionStatus.COMPLETED,
                total_duration=time.time() - start_time,
                tool_results=step_results,
                total_tools=len(step_results),
                successful_tools=sum(1 for r in step_results if r.is_success()),
                failed_tools=sum(1 for r in step_results if r.is_failure()),
            )

            # Build headless result
            result = HeadlessResult(
                session_id=session_id,
                session_name=playbook.name,
                workflow_type="playbook",
                orchestration_result=aggregated_result,
                final_output=self._aggregate_playbook_output(step_results),
                start_time=start_time,
                end_time=time.time(),
                total_duration=time.time() - start_time,
            )

            # Save session
            if self.session_manager and self._current_session:
                self._current_session.orchestration_results = [aggregated_result]
                self._current_session.status = aggregated_result.status
                await self.session_manager.save_session(self._current_session)

            # Emit completion
            self.event_logger.session_complete(
                session_id=session_id,
                status=aggregated_result.status.value,
                total_duration=result.total_duration,
            )

            return result

        except Exception as e:
            self.event_logger.session_error(session_id=session_id, error=str(e))
            raise

    async def _execute_playbook_step(
        self,
        step: Dict[str, Any],
        variables: Dict[str, str],
        context: Dict[str, Any],
    ) -> ToolResult:
        """
        Execute a single playbook step.

        This is a placeholder - will be enhanced with Phase 6 TemplateExecutor.
        """
        # For now, just execute the tool directly
        # Phase 6 will add: variable substitution, pattern matching, conditional logic

        tool_name = step.get("tool", "unknown")
        input_text = step.get("input", "")

        # Simple variable substitution
        for var_name, var_value in variables.items():
            input_text = input_text.replace(f"{{{{{var_name}}}}}", var_value)

        # Create a dummy tool (placeholder)
        # In real implementation, this would resolve to actual UniversalTool
        from .universal_tool import POSIXTool, ToolCapabilities

        tool = POSIXTool(
            name=tool_name,
            command=["echo"],  # Placeholder
            capabilities=ToolCapabilities(),
        )

        # Execute
        result = await tool.execute(input_text=input_text, context=context)
        return result

    # ─────────────────────────────────────────────────────
    # Session Resume
    # ─────────────────────────────────────────────────────

    async def resume_session(
        self,
        session_id: str,
        additional_prompt: Optional[str] = None,
    ) -> HeadlessResult:
        """
        Resume a previous session and continue execution.

        Args:
            session_id: Session ID to resume (or "last" for most recent)
            additional_prompt: Optional new prompt to append

        Returns:
            HeadlessResult with continued execution
        """
        if not self.session_manager:
            raise RuntimeError("SessionManager required for resume capability")

        # Load session
        if session_id == "last":
            session = await self.session_manager.get_last_session()
            if not session:
                raise ValueError("No previous session found")
        else:
            session = await self.session_manager.resume_session(session_id)

        # Emit resume event
        self.event_logger.session_resume(
            session_id=session.id,
            from_step=session.current_step,
        )

        # TODO: Implement resume logic
        # This requires Phase 7 SessionManager with checkpoint support

        # Placeholder: Just return existing session
        result = HeadlessResult(
            session_id=session.id,
            session_name=session.name,
            workflow_type="resume",
            orchestration_result=session.orchestration_results[0] if session.orchestration_results else None,
            final_output="",
            total_duration=0.0,
        )

        return result

    # ─────────────────────────────────────────────────────
    # Prompt Parsing
    # ─────────────────────────────────────────────────────

    @staticmethod
    def parse_prompt(
        prompt_arg: Optional[str] = None,
        read_stdin: bool = False,
        filepath: Optional[str] = None,
    ) -> PromptSource:
        """
        Parse prompt from various sources.

        Priority:
        1. File path (if provided)
        2. Stdin (if prompt_arg == "-" or read_stdin=True)
        3. Direct argument

        Args:
            prompt_arg: Prompt string or "-" for stdin
            read_stdin: Force stdin reading
            filepath: Path to prompt file

        Returns:
            PromptSource with content and metadata
        """
        # From file
        if filepath:
            content = Path(filepath).read_text()
            return PromptSource(type="file", content=content, filepath=filepath)

        # From stdin
        if prompt_arg == "-" or read_stdin:
            content = sys.stdin.read()
            return PromptSource(type="stdin", content=content)

        # From argument
        if prompt_arg:
            return PromptSource(type="arg", content=prompt_arg)

        # No prompt provided
        raise ValueError("No prompt provided (use argument, stdin '-', or --file)")

    # ─────────────────────────────────────────────────────
    # Output Helpers
    # ─────────────────────────────────────────────────────

    @staticmethod
    def write_final_output(
        result: HeadlessResult,
        filepath: str,
    ) -> None:
        """
        Write final output to file.

        Args:
            result: HeadlessResult
            filepath: Path to output file
        """
        Path(filepath).write_text(result.final_output)

    @staticmethod
    def validate_output_schema(
        output: str,
        schema_path: str,
    ) -> bool:
        """
        Validate output against JSON schema.

        Args:
            output: Output string (should be valid JSON)
            schema_path: Path to JSON schema file

        Returns:
            True if valid, raises ValidationError otherwise
        """
        try:
            import jsonschema
        except ImportError:
            raise ImportError("jsonschema library required for schema validation")

        # Load schema
        with open(schema_path) as f:
            schema = json.load(f)

        # Parse output as JSON
        try:
            output_json = json.loads(output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Output is not valid JSON: {e}")

        # Validate
        jsonschema.validate(output_json, schema)
        return True

    # ─────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────

    async def _execute_with_events(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        context: Dict[str, Any],
    ) -> OrchestrationResult:
        """
        Execute orchestration with event logging.

        Wraps orchestrator.execute() and emits tool events.
        """
        # Execute orchestration
        result = await self.orchestrator.execute(
            tools=tools,
            inputs=inputs,
            context=context,
        )

        # Emit tool events
        for tool_result in result.tool_results:
            self.event_logger.tool_complete(
                tool_name=tool_result.tool_name,
                status=tool_result.status.value,
                duration=tool_result.duration_seconds or 0.0,
                exit_code=tool_result.exit_code or 0,
            )

        return result

    def _aggregate_playbook_output(
        self,
        step_results: List[ToolResult],
    ) -> str:
        """
        Aggregate outputs from all playbook steps.

        Args:
            step_results: Results from each step

        Returns:
            Aggregated output string
        """
        outputs = []
        for i, result in enumerate(step_results):
            outputs.append(f"# Step {i+1}: {result.tool_name}")
            outputs.append(f"Status: {result.status.value}")
            outputs.append(f"Duration: {result.duration_seconds:.2f}s")
            outputs.append(f"\n{result.combined_output}\n")
            outputs.append("=" * 70)

        return "\n".join(outputs)
