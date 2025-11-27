# cli_orchestrator.py - AI CLI Tool Sequencing & Orchestration
"""
Practical orchestration for AI coding CLI tools on Debian Linux.

Focus:
- Chain tools in sequences (claude-code → gemini → aider)
- Parse tool outputs intelligently
- Send custom follow-up inputs based on parsed results
- Real-world workflows for code generation, review, testing

Tools Supported:
- claude-code: Anthropic's Claude CLI
- gemini: Google Gemini CLI
- aider: AI pair programming
- open-interpreter: Code execution
- ollama: Local LLMs

Example:
    # Simple sequence
    sequence = CLISequence()
    sequence.add_step("claude-code", "Write a Python web scraper")
    sequence.add_step("gemini", "Review the code for bugs", use_previous_output=True)
    sequence.add_step("aider", "Fix any issues found", use_previous_output=True)

    result = sequence.run()
"""

from __future__ import annotations
import os
import re
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable, Pattern
from enum import Enum

from .transport import Transport, PTYTransport, create_transport
from .presets import get_cli_tool, CLI_TOOLS, CLIToolConfig
from .logging import get_logger
from .audit import get_audit_logger, AuditLogger
from .cli_persistence import SequencePersistence, get_persistence

logger = get_logger("orchestrator")
audit = get_audit_logger()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Security: Command Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SecurityError(Exception):
    """Raised when a security policy is violated."""
    pass


# Allowlist of approved command executables
# SECURITY: Only these commands can be executed by the orchestrator
APPROVED_COMMANDS = {
    # AI coding CLIs
    "claude", "claude-code",
    "gemini",
    "aider",
    "interpreter",
    # Local LLMs
    "ollama",
    # Programming languages (REPL mode only)
    "python", "python3",
    "ipython",
    "node",
    "ruby", "irb",
    # Development tools (read-only operations)
    "git",
    # Safe shells (for testing/dev only)
    "bash", "sh",
}


def validate_command(cmd: List[str]) -> None:
    """
    Validate that a command is safe to execute.

    Enforces security policy:
    - Command executable must be in APPROVED_COMMANDS allowlist
    - No shell metacharacters in arguments
    - No dangerous flags (e.g., -c for arbitrary code execution)

    Args:
        cmd: Command as list of strings [executable, arg1, arg2, ...]

    Raises:
        SecurityError: If command violates security policy
        ValueError: If command is malformed
    """
    if not cmd or not isinstance(cmd, list):
        raise ValueError("Command must be a non-empty list")

    # Check executable is approved
    executable = os.path.basename(cmd[0])
    if executable not in APPROVED_COMMANDS:
        reason = f"'{executable}' not in approved list"
        audit.log_command_validation(cmd=cmd, approved=False, reason=reason)
        raise SecurityError(
            f"Command '{executable}' not in approved list. "
            f"Approved commands: {', '.join(sorted(APPROVED_COMMANDS))}"
        )

    # Check for dangerous patterns in arguments
    dangerous_flags = {
        "-c",  # bash -c "arbitrary code"
        "-e",  # python -c "code" (when followed by code)
        "--eval",
    }

    for i, arg in enumerate(cmd):
        # Check for shell metacharacters that could enable injection
        if any(char in arg for char in [";", "|", "&", "$", "`", "\n", "\r"]):
            reason = f"Shell metacharacters in argument: {arg}"
            audit.log_command_validation(cmd=cmd, approved=False, reason=reason)
            raise SecurityError(
                f"Shell metacharacters detected in argument: {arg}"
            )

        # Check for dangerous flags
        if arg in dangerous_flags:
            # Allow some safe usages (e.g., python -i -c is blocked, but python -i is ok)
            if i + 1 < len(cmd):
                reason = f"Dangerous flag '{arg}' with argument"
                audit.log_command_validation(cmd=cmd, approved=False, reason=reason)
                raise SecurityError(
                    f"Dangerous flag '{arg}' detected with argument. "
                    f"Arbitrary code execution not allowed."
                )

    # AUDIT: Log approved command
    audit.log_command_validation(
        cmd=cmd,
        approved=True,
        reason="Passed all security checks"
    )
    logger.debug(f"Command validated: {cmd[0]}")


def validate_cli_tool(tool_name: str) -> CLIToolConfig:
    """
    Get and validate a CLI tool configuration.

    Args:
        tool_name: Name of the CLI tool

    Returns:
        Validated CLIToolConfig

    Raises:
        SecurityError: If tool is not found or fails validation
    """
    tool_config = get_cli_tool(tool_name)
    if not tool_config:
        raise SecurityError(f"Unknown or unauthorized tool: {tool_name}")

    # Validate the tool's command
    try:
        validate_command(tool_config.cmd)
    except (SecurityError, ValueError) as e:
        raise SecurityError(f"Tool '{tool_name}' has invalid command: {e}")

    return tool_config


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Parsers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OutputParser:
    """
    Parse CLI tool outputs to extract structured data.

    Patterns for common scenarios:
    - Code blocks (```python ... ```)
    - Error messages
    - File paths
    - Test results
    - Success/failure indicators
    """

    # Common patterns
    CODE_BLOCK = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
    ERROR_PATTERN = re.compile(r'(error|exception|failed|traceback):', re.IGNORECASE)
    FILE_PATH = re.compile(r'(?:^|\s)((?:/|\./)[\w./\-]+\.[\w]+)')
    TEST_PASSED = re.compile(r'(\d+)\s+passed', re.IGNORECASE)
    TEST_FAILED = re.compile(r'(\d+)\s+failed', re.IGNORECASE)

    @classmethod
    def extract_code_blocks(cls, text: str) -> List[Dict[str, str]]:
        """Extract all code blocks with their languages."""
        blocks = []
        for match in cls.CODE_BLOCK.finditer(text):
            lang = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append({"language": lang, "code": code})
        return blocks

    @classmethod
    def has_errors(cls, text: str) -> bool:
        """Check if output contains errors."""
        return bool(cls.ERROR_PATTERN.search(text))

    @classmethod
    def extract_file_paths(cls, text: str) -> List[str]:
        """Extract file paths from output."""
        matches = cls.FILE_PATH.findall(text)
        return list(set(matches))  # Deduplicate

    @classmethod
    def parse_test_results(cls, text: str) -> Dict[str, int]:
        """Parse test results (pytest, jest, etc.)."""
        passed_match = cls.TEST_PASSED.search(text)
        failed_match = cls.TEST_FAILED.search(text)

        return {
            "passed": int(passed_match.group(1)) if passed_match else 0,
            "failed": int(failed_match.group(1)) if failed_match else 0,
        }

    @classmethod
    def extract_first_code_block(cls, text: str, language: Optional[str] = None) -> Optional[str]:
        """Extract first code block, optionally filtered by language."""
        blocks = cls.extract_code_blocks(text)
        if not blocks:
            return None

        if language:
            for block in blocks:
                if block["language"].lower() == language.lower():
                    return block["code"]

        return blocks[0]["code"]

    @classmethod
    def sanitize_for_chaining(cls, text: str, max_length: int = 5000) -> str:
        """
        Sanitize LLM output before using in subsequent prompts.

        Removes potential prompt injection patterns that could hijack
        downstream agents:
        - System-level tokens
        - Instruction override attempts
        - Special control sequences

        Args:
            text: Raw LLM output
            max_length: Maximum length to include (truncate longer outputs)

        Returns:
            Sanitized text safe to include in prompts
        """
        # Remove dangerous prompt injection patterns
        dangerous_patterns = [
            (r"<\|im_start\|>.*?<\|im_end\|>", "[REDACTED_CONTROL_TOKEN]"),
            (r"<\|system\|>", "[REDACTED]"),
            (r"<\|assistant\|>", "[REDACTED]"),
            (r"<\|user\|>", "[REDACTED]"),
            (r"\bSYSTEM\s*:", "[REDACTED]:"),
            (r"\bASSISTANT\s*:", "[REDACTED]:"),
            (r"(?i)ignore\s+(all\s+)?previous\s+instructions?", "[INSTRUCTION_OVERRIDE_ATTEMPT]"),
            (r"(?i)you\s+are\s+now", "[ROLE_OVERRIDE_ATTEMPT]"),
            (r"(?i)forget\s+(all\s+)?prior", "[MEMORY_OVERRIDE_ATTEMPT]"),
            (r"(?i)disregard\s+(all\s+)?above", "[INSTRUCTION_OVERRIDE_ATTEMPT]"),
        ]

        sanitized = text
        for pattern, replacement in dangerous_patterns:
            # Check if pattern matches before replacing
            if re.search(pattern, sanitized, flags=re.MULTILINE | re.DOTALL):
                # AUDIT: Log injection attempt
                audit.log_prompt_injection_attempt(
                    pattern=pattern,
                    text_preview=sanitized[:300]
                )
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.MULTILINE | re.DOTALL)

        # Truncate to reasonable size
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "\n[... output truncated for safety ...]"

        return sanitized

    @classmethod
    def summarize_output(cls, text: str, max_length: int = 500) -> str:
        """
        Create a summary of output for chaining.

        SECURITY: This method sanitizes output to prevent prompt injection.
        """
        # Sanitize first to remove injection attempts
        sanitized = cls.sanitize_for_chaining(text, max_length=5000)

        # Extract key information from sanitized text
        has_code = bool(cls.CODE_BLOCK.search(sanitized))
        has_errors = cls.has_errors(sanitized)
        files = cls.extract_file_paths(sanitized)

        summary_parts = []

        if has_code:
            summary_parts.append("Generated code")
        if has_errors:
            summary_parts.append("Contains errors")
        if files:
            summary_parts.append(f"Modified files: {', '.join(files[:3])}")

        # Add truncated output
        if len(sanitized) > max_length:
            summary_parts.append(f"\n\nOutput preview:\n{sanitized[:max_length]}...")
        else:
            summary_parts.append(f"\n\nOutput:\n{sanitized}")

        return " | ".join(summary_parts) if summary_parts else sanitized[:max_length]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sequence Step
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SequenceStep:
    """A single step in a CLI tool sequence."""
    tool_name: str                          # e.g., "claude-code"
    prompt: str                             # Input prompt
    use_previous_output: bool = False       # Include previous step's output
    parse_output: bool = True               # Parse output for structured data
    timeout: float = 60.0                   # Timeout in seconds

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
    - Handle errors and retries
    - Track execution metrics

    Example:
        seq = CLISequence()
        seq.add_step("claude-code", "Write a web scraper")
        seq.add_step("gemini", "Review this code", use_previous_output=True)
        result = seq.run()
    """

    def __init__(self, name: str = "sequence", auto_save: bool = True):
        self.name = name
        self.steps: List[SequenceStep] = []
        self.transports: Dict[str, Transport] = {}
        self.parser = OutputParser()
        self.auto_save = auto_save
        self.sequence_id: Optional[str] = None
        self.started_at: Optional[float] = None

    def add_step(
        self,
        tool_name: str,
        prompt: str,
        use_previous_output: bool = False,
        parse_output: bool = True,
        timeout: float = 60.0,
    ) -> SequenceStep:
        """Add a step to the sequence."""
        step = SequenceStep(
            tool_name=tool_name,
            prompt=prompt,
            use_previous_output=use_previous_output,
            parse_output=parse_output,
            timeout=timeout,
        )
        self.steps.append(step)
        logger.info(f"Added step {len(self.steps)}: {tool_name}")
        return step

    def run(self) -> Dict[str, Any]:
        """
        Execute the sequence.

        Returns:
            Summary with all steps, outputs, and metadata
        """
        logger.info(f"Running sequence '{self.name}' with {len(self.steps)} steps")
        start_time = time.time()
        self.started_at = start_time
        self.sequence_id = f"seq-{int(start_time * 1000):x}"

        previous_output = ""

        for i, step in enumerate(self.steps, 1):
            logger.info(f"Step {i}/{len(self.steps)}: {step.tool_name}")

            # Build prompt
            if step.use_previous_output and previous_output:
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

                logger.info(f"Step {i} completed ({step.duration:.1f}s)")

            except Exception as e:
                step.success = False
                step.error = str(e)
                logger.error(f"Step {i} failed: {e}")

                # Stop on error (could make this configurable)
                break

        total_duration = time.time() - start_time
        result = self._build_result(total_duration)

        # Auto-save if enabled
        if self.auto_save:
            try:
                persistence = get_persistence()
                persistence.save_sequence(result)
                logger.info(f"Sequence '{self.name}' saved with ID: {self.sequence_id}")
            except Exception as e:
                logger.error(f"Failed to save sequence: {e}")

        return result

    def _execute_step(self, step: SequenceStep, prompt: str) -> str:
        """
        Execute a single step.

        SECURITY: Validates tool configuration before execution.

        Raises:
            SecurityError: If tool fails security validation
        """
        start = time.time()

        # Get or create transport
        if step.tool_name not in self.transports:
            # SECURITY: Validate tool before creating transport
            tool_config = validate_cli_tool(step.tool_name)

            transport = create_transport(
                cmd=tool_config.cmd,
                transport_type="pty",
                name=tool_config.name,
            )

            transport.start()
            self.transports[step.tool_name] = transport

            # AUDIT: Log transport start
            audit.log_agent_started(
                agent_name=tool_config.name,
                cmd=tool_config.cmd
            )

        transport = self.transports[step.tool_name]

        # AUDIT: Log step start
        audit.log_step_started(
            step_name=f"{self.name}_{step.tool_name}",
            tool_name=step.tool_name,
            prompt_length=len(prompt)
        )

        # Send prompt and get response
        try:
            response = transport.send_and_wait(prompt, wait_seconds=step.timeout)
            step.duration = time.time() - start

            # AUDIT: Log step completion
            audit.log_step_completed(
                step_name=f"{self.name}_{step.tool_name}",
                duration_seconds=step.duration,
                output_length=len(response)
            )

            return response

        except Exception as e:
            step.duration = time.time() - start
            # AUDIT: Log step failure
            audit.log_step_failed(
                step_name=f"{self.name}_{step.tool_name}",
                error=e,
                duration_seconds=step.duration
            )
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
            "tags": [],  # Can be extended later
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

    def cleanup(self):
        """Stop all transports."""
        for tool_name, transport in self.transports.items():
            # AUDIT: Log transport stop
            total_duration = sum(s.duration for s in self.steps if s.tool_name == tool_name and s.duration)
            audit.log_agent_stopped(
                agent_name=tool_name,
                runtime_seconds=total_duration
            )
            transport.terminate()
        self.transports.clear()
        logger.info(f"Sequence '{self.name}' cleanup complete")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Common Workflow Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowPatterns:
    """Pre-built workflow patterns for common scenarios."""

    @staticmethod
    def code_review_fix(task: str) -> CLISequence:
        """
        Generate code → Review → Fix issues.

        Tools: claude-code → gemini → aider
        """
        seq = CLISequence("code-review-fix")
        seq.add_step("claude-code", f"Write code for: {task}")
        seq.add_step("gemini", "Review this code for bugs, security issues, and improvements",
                    use_previous_output=True)
        seq.add_step("aider", "Fix any issues found in the review",
                    use_previous_output=True)
        return seq

    @staticmethod
    def multi_llm_consensus(question: str, tools: List[str] = None) -> CLISequence:
        """
        Get answers from multiple LLMs for consensus.

        Default tools: claude-code, gemini, ollama
        """
        if tools is None:
            tools = ["claude-code", "gemini", "ollama"]

        seq = CLISequence("multi-llm-consensus")
        for tool in tools:
            seq.add_step(tool, question, use_previous_output=False)
        return seq

    @staticmethod
    def iterative_refinement(initial_task: str, iterations: int = 3) -> CLISequence:
        """
        Iteratively refine output through multiple passes.

        Tool: claude-code (multiple iterations)
        """
        seq = CLISequence("iterative-refinement")

        # First iteration
        seq.add_step("claude-code", initial_task)

        # Refinement iterations
        for i in range(iterations - 1):
            seq.add_step("claude-code",
                        f"Improve and refine the previous output. Iteration {i+2}/{iterations}",
                        use_previous_output=True)

        return seq

    @staticmethod
    def test_driven_development(feature: str) -> CLISequence:
        """
        TDD workflow: Tests → Implementation → Run Tests → Fix.

        Tools: claude-code → python → claude-code
        """
        seq = CLISequence("tdd-workflow")
        seq.add_step("claude-code", f"Write pytest tests for: {feature}")
        seq.add_step("claude-code", f"Implement the feature: {feature}",
                    use_previous_output=True)
        seq.add_step("python", "pytest -v", timeout=30.0)
        # Could add conditional step if tests fail
        return seq


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_sequence(steps: List[tuple], name: str = "sequence") -> Dict[str, Any]:
    """
    Quick run a sequence from a list of (tool, prompt) tuples.

    Args:
        steps: List of (tool_name, prompt, use_previous_output?) tuples
        name: Sequence name

    Returns:
        Result dictionary

    Example:
        result = run_sequence([
            ("claude-code", "Write hello world in Python"),
            ("gemini", "Review this code", True),
        ])
    """
    seq = CLISequence(name)
    for step in steps:
        tool = step[0]
        prompt = step[1]
        use_prev = step[2] if len(step) > 2 else False
        seq.add_step(tool, prompt, use_previous_output=use_prev)

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
        seq.add_step(tool, "Continue working on this", use_previous_output=True)

    result = seq.run()
    seq.cleanup()

    return result.get("final_output", "")
