"""
Sequence - CLI Tool Orchestration

Sequential execution of CLI tools with output chaining and auto-persistence.

Features:
- Chain AI CLI tools in sequences (claude-code → gemini → aider)
- Parse outputs intelligently
- Auto-save to files + SQLite
- Output chaining between steps
- Built on clean kernel.Process layer

Example:
    from metacli.core import CLISequence

    seq = CLISequence("code-review")
    seq.add_step("claude-code", "Write a Python web scraper")
    seq.add_step("gemini", "Review for bugs", use_previous=True)
    seq.add_step("aider", "Fix any issues", use_previous=True)

    result = seq.run()  # Auto-saved
    seq.cleanup()
"""

from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..kernel import Process, PTYProcess, Security, SecurityError
from .parser import OutputParser


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Tool Presets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CLIToolConfig:
    """Configuration for a known CLI tool."""
    name: str
    cmd: List[str]
    requires_pty: bool = True  # Most AI tools need PTY
    timeout: float = 60.0


# Known AI coding tools
CLI_TOOLS = {
    "claude-code": CLIToolConfig(
        name="claude-code",
        cmd=["claude-code"],
        requires_pty=True,
        timeout=120.0,
    ),
    "aider": CLIToolConfig(
        name="aider",
        cmd=["aider", "--no-auto-commit"],
        requires_pty=True,
        timeout=120.0,
    ),
    "gemini": CLIToolConfig(
        name="gemini",
        cmd=["gemini"],
        requires_pty=True,
        timeout=120.0,
    ),
    "ollama": CLIToolConfig(
        name="ollama",
        cmd=["ollama", "run", "codellama"],
        requires_pty=True,
        timeout=120.0,
    ),
    "python": CLIToolConfig(
        name="python",
        cmd=["python3", "-i"],
        requires_pty=False,
        timeout=30.0,
    ),
}


def get_tool_config(tool_name: str) -> Optional[CLIToolConfig]:
    """Get configuration for a known tool."""
    return CLI_TOOLS.get(tool_name)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sequence Step
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SequenceStep:
    """A single step in a CLI tool sequence."""
    tool_name: str                      # e.g., "claude-code"
    prompt: str                         # Input prompt
    use_previous: bool = False          # Include previous step's output
    parse_output: bool = True           # Parse output for structured data
    timeout: float = 60.0               # Timeout in seconds

    # Results (populated after execution)
    raw_output: str = ""
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None
    duration: float = 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Sequence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CLISequence:
    """
    Orchestrate multiple CLI tools in sequence.

    Features:
    - Chain tools with output passing
    - Parse outputs intelligently
    - Handle errors gracefully
    - Auto-save results

    Example:
        seq = CLISequence("code-review")
        seq.add_step("claude-code", "Write a web scraper")
        seq.add_step("gemini", "Review this code", use_previous=True)
        result = seq.run()
        seq.cleanup()
    """

    def __init__(self, name: str = "sequence", auto_save: bool = True):
        """
        Initialize sequence.

        Args:
            name: Sequence name for identification
            auto_save: Auto-save results to persistence layer
        """
        self.name = name
        self.steps: List[SequenceStep] = []
        self.processes: Dict[str, Process] = {}
        self.parser = OutputParser()
        self.security = Security()
        self.auto_save = auto_save
        self.sequence_id: Optional[str] = None
        self.started_at: Optional[float] = None

    def add_step(
        self,
        tool_name: str,
        prompt: str,
        use_previous: bool = False,
        parse_output: bool = True,
        timeout: float = 60.0,
    ) -> SequenceStep:
        """
        Add a step to the sequence.

        Args:
            tool_name: Name of CLI tool (must be in CLI_TOOLS or security allowlist)
            prompt: Input prompt for the tool
            use_previous: Include previous step's output
            parse_output: Parse output for structured data
            timeout: Timeout in seconds

        Returns:
            Created SequenceStep
        """
        step = SequenceStep(
            tool_name=tool_name,
            prompt=prompt,
            use_previous=use_previous,
            parse_output=parse_output,
            timeout=timeout,
        )
        self.steps.append(step)
        return step

    def run(self) -> Dict[str, Any]:
        """
        Execute the sequence.

        Returns:
            Summary with all steps, outputs, and metadata
        """
        start_time = time.time()
        self.started_at = start_time
        self.sequence_id = f"seq-{int(start_time * 1000):x}"

        previous_output = ""

        for i, step in enumerate(self.steps, 1):
            # Build prompt
            if step.use_previous and previous_output:
                full_prompt = f"{step.prompt}\n\nPrevious output:\n{previous_output}"
            else:
                full_prompt = step.prompt

            # Execute step
            try:
                output = self._execute_step(step, full_prompt)
                step.raw_output = output
                step.success = True

                # Parse output
                if step.parse_output:
                    step.parsed_data = self._parse_step_output(output)

                # Update previous output for next step
                previous_output = self.parser.summarize_output(output)

            except Exception as e:
                step.success = False
                step.error = str(e)

                # Stop on error
                break

        total_duration = time.time() - start_time
        result = self._build_result(total_duration)

        # Auto-save if enabled
        if self.auto_save:
            self._save_result(result)

        return result

    def _execute_step(self, step: SequenceStep, prompt: str) -> str:
        """
        Execute a single step.

        Validates tool, spawns process using kernel.Process, and returns output.

        Raises:
            SecurityError: If tool fails security validation
        """
        start = time.time()

        # Get tool config
        tool_config = get_tool_config(step.tool_name)
        if not tool_config:
            raise SecurityError(f"Unknown tool: {step.tool_name}")

        # Validate command
        self.security.validate_command(tool_config.cmd)

        # Get or create process
        if step.tool_name not in self.processes:
            # Spawn process using kernel
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
        """Parse step output into structured data."""
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
            "id": self.sequence_id,
            "name": self.name,
            "status": "failed" if has_error else "completed",
            "started_at": self.started_at,
            "completed_at": time.time(),
            "total_steps": len(self.steps),
            "successful_steps": successful_steps,
            "duration": total_duration,
            "error_message": self.steps[-1].error if has_error else None,
            "tags": [],
            "steps": [
                {
                    "tool_name": s.tool_name,
                    "prompt": s.prompt,
                    "raw_output": s.raw_output or "",
                    "success": s.success,
                    "duration": s.duration,
                    "parsed_data": s.parsed_data,
                    "error_message": s.error,
                    "timestamp": self.started_at + sum(st.duration or 0 for st in self.steps[:i]),
                    "status": "success" if s.success else "failed",
                }
                for i, s in enumerate(self.steps)
            ],
            "final_output": self.steps[-1].raw_output if self.steps and self.steps[-1].success else None,
        }

    def _save_result(self, result: Dict[str, Any]) -> None:
        """Save result to persistence layer."""
        try:
            from .persistence import get_persistence
            persistence = get_persistence()
            persistence.save(result)
        except Exception:
            # Don't fail sequence if persistence fails
            pass

    def cleanup(self):
        """Stop all processes."""
        for tool_name, proc in self.processes.items():
            proc.terminate()
        self.processes.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_sequence(steps: List[tuple], name: str = "sequence") -> Dict[str, Any]:
    """
    Quick run a sequence from a list of tuples.

    Args:
        steps: List of (tool_name, prompt, use_previous?) tuples
        name: Sequence name

    Returns:
        Result dictionary

    Example:
        result = run_sequence([
            ("claude-code", "Write hello world"),
            ("gemini", "Review this code", True),
        ])
    """
    seq = CLISequence(name)
    for step in steps:
        tool = step[0]
        prompt = step[1]
        use_prev = step[2] if len(step) > 2 else False
        seq.add_step(tool, prompt, use_previous=use_prev)

    result = seq.run()
    seq.cleanup()
    return result


def quick_chain(tool_names: List[str], initial_prompt: str) -> str:
    """
    Chain tools with output passing, return final output.

    Args:
        tool_names: List of tools to chain
        initial_prompt: Starting prompt

    Returns:
        Final output string

    Example:
        output = quick_chain(
            ["claude-code", "gemini", "aider"],
            "Write a web scraper"
        )
    """
    seq = CLISequence("quick-chain")
    seq.add_step(tool_names[0], initial_prompt)

    for tool in tool_names[1:]:
        seq.add_step(tool, "Continue working on this", use_previous=True)

    result = seq.run()
    seq.cleanup()

    return result.get("final_output", "")
