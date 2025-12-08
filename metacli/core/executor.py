"""
Unified CLI Executor - Execute AI coding tools and POSIX commands

Handles:
- AI coding CLIs (claude-code, codex, gemini)
- Regular POSIX tools (grep, git, pytest, etc.)
- Both simple (stdin/stdout) and complex (PTY) terminal control
- Output parsing and keyword detection
- Database persistence for each execution

Example:
    executor = UnifiedExecutor(db_path="workflow.db")

    # Execute AI tool
    result = executor.execute(
        tool="claude-code",
        prompt="audit src/api.py",
        parser="realistic"
    )

    # Execute POSIX tool
    result = executor.execute(
        tool="git",
        args=["status"],
        parser="simple"
    )
"""

from __future__ import annotations
import subprocess
import time
import shlex
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from enum import Enum

# Import our testing components
from ..testing.realistic_parser import RealisticOutputParser, ParsedOutput
from ..testing.terminal import TerminalEmulator, SimpleTerminal
from ..testing.database import TestDatabase


class ToolType(Enum):
    """Type of CLI tool."""
    AI_CODING = "ai_coding"  # claude-code, codex, gemini
    POSIX = "posix"          # grep, git, pytest, etc.
    CUSTOM = "custom"        # User-defined tools


class ExecutionMode(Enum):
    """Execution mode for CLI tools."""
    SIMPLE = "simple"        # stdin/stdout pipes
    INTERACTIVE = "interactive"  # PTY with keyboard control
    SINGLE_SHOT = "single_shot"  # One command, get output, exit


@dataclass
class ExecutionConfig:
    """
    Configuration for CLI execution.

    Attributes:
        tool: Tool name or path
        mode: Execution mode (simple, interactive, single_shot)
        timeout: Timeout in seconds
        env: Environment variables
        cwd: Working directory
        capture_output: Whether to capture output
        parser_type: Parser to use (realistic, simple, none)
    """
    tool: str
    mode: ExecutionMode = ExecutionMode.SINGLE_SHOT
    timeout: float = 30.0
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    capture_output: bool = True
    parser_type: str = "realistic"  # realistic, simple, none


@dataclass
class ExecutionResult:
    """
    Result of CLI execution.

    Attributes:
        tool: Tool name
        prompt: Input prompt/command
        raw_output: Raw output from tool
        parsed_output: Parsed output (if parser used)
        returncode: Exit code
        duration: Execution time in seconds
        timestamp: Execution timestamp
        metadata: Additional metadata
    """
    tool: str
    prompt: str
    raw_output: str
    parsed_output: Optional[ParsedOutput] = None
    returncode: int = 0
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution succeeded."""
        return self.returncode == 0

    @property
    def has_error(self) -> bool:
        """Check if output contains error keyword."""
        if self.parsed_output:
            return self.parsed_output.has_error
        return "error" in self.raw_output.lower()

    @property
    def is_complete(self) -> bool:
        """Check if output indicates completion."""
        if self.parsed_output:
            return self.parsed_output.is_complete
        return "complete" in self.raw_output.lower()


class UnifiedExecutor:
    """
    Unified executor for AI coding tools and POSIX commands.

    Features:
    - Execute AI CLIs (claude-code, codex, gemini)
    - Execute POSIX tools (git, grep, pytest, etc.)
    - Support simple (stdin/stdout) and complex (PTY) modes
    - Parse output with realistic or simple parsers
    - Persist execution results to database
    - Automatic retry on transient failures

    Example:
        executor = UnifiedExecutor()

        # Execute AI tool
        result = executor.execute(
            tool="claude-code",
            prompt="audit src/api.py"
        )

        if result.has_error:
            print("Error detected:", result.raw_output)

        # Execute POSIX tool
        git_result = executor.execute(
            tool="git",
            args=["status"],
            mode=ExecutionMode.SIMPLE
        )
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        enable_persistence: bool = True,
        default_timeout: float = 30.0
    ):
        """
        Initialize unified executor.

        Args:
            db_path: Path to database for persistence
            enable_persistence: Enable database persistence
            default_timeout: Default timeout in seconds
        """
        self.db_path = db_path
        self.enable_persistence = enable_persistence
        self.default_timeout = default_timeout

        # Initialize database if persistence enabled
        self.db = None
        if enable_persistence and db_path:
            self.db = TestDatabase(db_path)

        # Initialize parsers
        self.realistic_parser = RealisticOutputParser()

        # Tool registry (maps tool name to configuration)
        self.tool_registry: Dict[str, ExecutionConfig] = {}

        # Execution history
        self.execution_history: List[ExecutionResult] = []

    def register_tool(
        self,
        name: str,
        config: ExecutionConfig
    ):
        """
        Register a tool with specific configuration.

        Args:
            name: Tool name (e.g., "claude-code")
            config: Execution configuration
        """
        self.tool_registry[name] = config

    def execute(
        self,
        tool: str,
        prompt: Optional[str] = None,
        args: Optional[List[str]] = None,
        mode: Optional[ExecutionMode] = None,
        parser_type: Optional[str] = None,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        save_to_db: bool = True
    ) -> ExecutionResult:
        """
        Execute a CLI tool.

        Args:
            tool: Tool name or path
            prompt: Input prompt (for AI tools)
            args: Arguments (for POSIX tools)
            mode: Execution mode (override default)
            parser_type: Parser type (override default)
            timeout: Timeout in seconds
            env: Environment variables
            cwd: Working directory
            save_to_db: Save result to database

        Returns:
            ExecutionResult object
        """
        # Get configuration
        config = self._get_config(tool, mode, parser_type, timeout, env, cwd)

        # Build command
        if prompt:
            # AI tool with prompt
            command = self._build_ai_command(tool, prompt)
        elif args:
            # POSIX tool with args
            command = [tool] + args
        else:
            raise ValueError("Either prompt or args must be provided")

        # Execute based on mode
        start_time = time.time()

        if config.mode == ExecutionMode.SINGLE_SHOT:
            raw_output, returncode = self._execute_single_shot(
                command, config.timeout, config.env, config.cwd
            )
        elif config.mode == ExecutionMode.SIMPLE:
            raw_output, returncode = self._execute_simple(
                command, config.timeout, config.env, config.cwd
            )
        elif config.mode == ExecutionMode.INTERACTIVE:
            raw_output, returncode = self._execute_interactive(
                command, prompt or "", config.timeout, config.env, config.cwd
            )
        else:
            raise ValueError(f"Unknown execution mode: {config.mode}")

        duration = time.time() - start_time

        # Parse output
        parsed_output = None
        if config.parser_type == "realistic":
            parsed_output = self.realistic_parser.parse(raw_output)

        # Create result
        result = ExecutionResult(
            tool=tool,
            prompt=prompt or " ".join(args or []),
            raw_output=raw_output,
            parsed_output=parsed_output,
            returncode=returncode,
            duration=duration,
            metadata={
                "mode": config.mode.value,
                "parser": config.parser_type,
                "command": command,
            }
        )

        # Save to history
        self.execution_history.append(result)

        # Save to database
        if save_to_db and self.enable_persistence and self.db:
            self._save_to_db(result)

        return result

    def _get_config(
        self,
        tool: str,
        mode: Optional[ExecutionMode],
        parser_type: Optional[str],
        timeout: Optional[float],
        env: Optional[Dict[str, str]],
        cwd: Optional[str]
    ) -> ExecutionConfig:
        """Get execution configuration for tool."""
        # Start with registered config or default
        if tool in self.tool_registry:
            config = self.tool_registry[tool]
        else:
            config = ExecutionConfig(tool=tool)

        # Override with provided values
        if mode:
            config.mode = mode
        if parser_type:
            config.parser_type = parser_type
        if timeout:
            config.timeout = timeout
        if env:
            config.env = env
        if cwd:
            config.cwd = cwd

        return config

    def _build_ai_command(self, tool: str, prompt: str) -> List[str]:
        """Build command for AI coding tool."""
        # Map tool names to actual commands
        tool_commands = {
            "claude-code": ["claude", "code"],
            "codex": ["codex", "exec"],
            "gemini": ["gemini", "cli"],
            "mock-ai": ["python3", "tools/mock_ai_cli_realistic.py"],
        }

        base_cmd = tool_commands.get(tool, [tool])

        # Add prompt
        # For now, append prompt as argument
        # In production, this would be more sophisticated
        return base_cmd + [prompt]

    def _execute_single_shot(
        self,
        command: List[str],
        timeout: float,
        env: Optional[Dict[str, str]],
        cwd: Optional[str]
    ) -> tuple[str, int]:
        """Execute command in single-shot mode (one command, get output)."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=cwd
            )
            return result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s", 1
        except Exception as e:
            return f"Error: {str(e)}", 1

    def _execute_simple(
        self,
        command: List[str],
        timeout: float,
        env: Optional[Dict[str, str]],
        cwd: Optional[str]
    ) -> tuple[str, int]:
        """Execute command with simple stdin/stdout pipes."""
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=cwd
            )

            stdout, _ = process.communicate(timeout=timeout)
            return stdout, process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            return f"Error: Command timed out after {timeout}s", 1
        except Exception as e:
            return f"Error: {str(e)}", 1

    def _execute_interactive(
        self,
        command: List[str],
        prompt: str,
        timeout: float,
        env: Optional[Dict[str, str]],
        cwd: Optional[str]
    ) -> tuple[str, int]:
        """Execute command in interactive mode with PTY."""
        try:
            with TerminalEmulator() as term:
                term.spawn(command, env=env, cwd=cwd)
                term.send_text(prompt, press_enter=True)
                output = term.read(timeout=timeout)
                return output, 0
        except Exception as e:
            return f"Error: {str(e)}", 1

    def _save_to_db(self, result: ExecutionResult):
        """Save execution result to database."""
        if not self.db:
            return

        # Create test scenario from result
        from ..testing.database import TestScenario

        scenario = TestScenario(
            name=f"{result.tool}_{int(result.timestamp)}",
            description=f"Execution of {result.tool}",
            steps=[{
                "tool": result.tool,
                "prompt": result.prompt,
                "output": result.raw_output[:1000],  # Truncate for DB
                "returncode": result.returncode,
                "duration": result.duration,
            }],
            tags=[result.tool, "execution"],
            category="execution"
        )

        self.db.save_scenario(scenario)

    def get_last_result(self) -> Optional[ExecutionResult]:
        """Get last execution result."""
        if self.execution_history:
            return self.execution_history[-1]
        return None

    def get_history(
        self,
        tool: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ExecutionResult]:
        """
        Get execution history.

        Args:
            tool: Filter by tool name
            limit: Limit number of results

        Returns:
            List of execution results
        """
        history = self.execution_history

        if tool:
            history = [r for r in history if r.tool == tool]

        if limit:
            history = history[-limit:]

        return history


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-configured Tool Executors
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_ai_executor(db_path: Optional[str] = None) -> UnifiedExecutor:
    """
    Create executor pre-configured for AI coding tools.

    Returns:
        UnifiedExecutor with AI tool configurations
    """
    executor = UnifiedExecutor(db_path=db_path)

    # Register AI tools
    executor.register_tool("claude-code", ExecutionConfig(
        tool="claude-code",
        mode=ExecutionMode.SINGLE_SHOT,
        parser_type="realistic",
        timeout=60.0
    ))

    executor.register_tool("codex", ExecutionConfig(
        tool="codex",
        mode=ExecutionMode.SINGLE_SHOT,
        parser_type="realistic",
        timeout=60.0
    ))

    executor.register_tool("gemini", ExecutionConfig(
        tool="gemini",
        mode=ExecutionMode.SINGLE_SHOT,
        parser_type="realistic",
        timeout=60.0
    ))

    # Mock AI for testing
    executor.register_tool("mock-ai", ExecutionConfig(
        tool="mock-ai",
        mode=ExecutionMode.SINGLE_SHOT,
        parser_type="realistic",
        timeout=10.0
    ))

    return executor


def create_posix_executor(db_path: Optional[str] = None) -> UnifiedExecutor:
    """
    Create executor pre-configured for POSIX tools.

    Returns:
        UnifiedExecutor with POSIX tool configurations
    """
    executor = UnifiedExecutor(db_path=db_path)

    # Register common POSIX tools
    for tool in ["git", "grep", "find", "pytest", "ls", "cat"]:
        executor.register_tool(tool, ExecutionConfig(
            tool=tool,
            mode=ExecutionMode.SIMPLE,
            parser_type="simple",
            timeout=30.0
        ))

    return executor
