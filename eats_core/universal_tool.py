# universal_tool.py - Universal CLI Tool Abstraction
"""
Universal abstraction for ANY CLI tool.

This is the foundation of the meta-framework, providing a uniform interface
for AI assistants, POSIX utilities, and custom applications.

Philosophy:
- "If it runs in a terminal, we can orchestrate it"
- Every tool, regardless of complexity, shares the same interface
- Capabilities describe what a tool can do
- Execution is uniform across all tool types

Usage:
    # AI tool
    aider = UniversalTool.from_config({
        "name": "aider",
        "command": ["aider", "--no-auto-commit"],
        "type": "ai_assistant",
        "capabilities": {
            "interactive": True,
            "needs_pty": True,
            "stateful": True,
        }
    })

    # POSIX tool
    grep = UniversalTool.from_config({
        "name": "grep",
        "command": ["grep", "-r"],
        "type": "posix",
        "capabilities": {
            "interactive": False,
            "needs_pty": False,
            "stateful": False,
        }
    })

    # Execute uniformly
    result1 = await aider.execute("Write a function to sort a list")
    result2 = await grep.execute("TODO", context={"path": "src/"})
"""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import time

from .transport import Transport, PTYTransport, TmuxTransport, create_transport


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums and Data Classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ToolType(Enum):
    """Type of CLI tool."""
    AI_ASSISTANT = "ai_assistant"      # AI coding tools (aider, claude-code)
    POSIX_UTILITY = "posix_utility"    # Standard UNIX tools (grep, sed, awk)
    CUSTOM = "custom"                  # User-defined tools
    PYTHON_SCRIPT = "python_script"    # Python scripts
    SHELL_SCRIPT = "shell_script"      # Shell scripts


class TransportType(Enum):
    """Transport mechanism for tool I/O."""
    STDIN_STDOUT = "stdin_stdout"      # Simple pipe
    PTY = "pty"                        # Pseudo-terminal
    TMUX = "tmux"                      # Tmux session
    AUTO = "auto"                      # Automatic selection


class ExecutionStatus(Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolCapabilities:
    """
    Capabilities that describe what a tool can do.

    This drives automatic transport selection and execution strategy.
    """
    # I/O capabilities
    supports_stdin: bool = True
    supports_stdout: bool = True
    interactive: bool = False          # Expects keyboard input
    needs_pty: bool = False            # Requires pseudo-terminal
    needs_gui: bool = False            # Requires GUI terminal

    # Execution characteristics
    stateful: bool = False             # Maintains state between calls
    async_capable: bool = True         # Can run asynchronously
    long_running: bool = False         # Expected to run for minutes/hours

    # Resource requirements
    cpu_intensive: bool = False
    memory_intensive: bool = False
    requires_network: bool = False

    # Security/sandboxing
    requires_sandbox: bool = False
    allowed_paths: Optional[List[str]] = None
    forbidden_paths: Optional[List[str]] = None


@dataclass
class ToolResult:
    """
    Result of tool execution.

    Universal result format across all tool types.
    """
    # Execution metadata
    tool_name: str
    status: ExecutionStatus
    exit_code: Optional[int] = None

    # Output
    stdout: str = ""
    stderr: str = ""
    combined_output: str = ""

    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None

    # Context
    input_text: str = ""
    command: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    # Error info
    error: Optional[Exception] = None
    error_message: Optional[str] = None

    # Artifacts
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to strings
        data['status'] = self.status.value
        if self.error:
            data['error'] = str(self.error)
        return data

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.COMPLETED and self.exit_code == 0

    def is_failure(self) -> bool:
        """Check if execution failed."""
        return self.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Universal Tool Base Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UniversalTool(ABC):
    """
    Universal abstraction for ANY CLI tool.

    This is the core abstraction of the meta-framework. Every tool -
    whether AI assistant, POSIX utility, or custom application -
    implements this interface.

    The framework treats all tools uniformly, selecting appropriate
    transports and execution strategies based on capabilities.
    """

    def __init__(
        self,
        name: str,
        command: List[str],
        tool_type: ToolType,
        capabilities: ToolCapabilities,
        description: str = "",
        version: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a universal tool.

        Args:
            name: Tool identifier
            command: Command to execute (e.g., ["aider", "--no-auto-commit"])
            tool_type: Type of tool
            capabilities: What the tool can do
            description: Human-readable description
            version: Tool version
            metadata: Additional metadata
        """
        self.name = name
        self.command = command
        self.tool_type = tool_type
        self.capabilities = capabilities
        self.description = description
        self.version = version
        self.metadata = metadata or {}

        # Runtime state
        self._transport: Optional[Transport] = None
        self._running = False

    # ─────────────────────────────────────────────────────
    # Core Execution Interface
    # ─────────────────────────────────────────────────────

    async def execute(
        self,
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """
        Execute the tool with given input.

        This is the main execution method that all tools must implement.

        Args:
            input_text: Input to send to the tool
            context: Execution context (variables, paths, etc.)
            timeout: Execution timeout in seconds

        Returns:
            ToolResult with outputs and metadata
        """
        context = context or {}
        result = ToolResult(
            tool_name=self.name,
            status=ExecutionStatus.PENDING,
            input_text=input_text,
            command=self.command,
            context=context,
        )

        try:
            result.status = ExecutionStatus.RUNNING
            result.start_time = time.time()

            # Execute via appropriate transport
            output = await self._execute_via_transport(input_text, context, timeout)

            result.stdout = output
            result.combined_output = output
            result.status = ExecutionStatus.COMPLETED
            result.exit_code = 0

        except asyncio.TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = f"Execution timed out after {timeout}s"

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = e
            result.error_message = str(e)

        finally:
            result.end_time = time.time()
            result.duration_seconds = result.end_time - result.start_time

        return result

    @abstractmethod
    async def _execute_via_transport(
        self,
        input_text: str,
        context: Dict[str, Any],
        timeout: Optional[float],
    ) -> str:
        """
        Execute via appropriate transport mechanism.

        Subclasses implement this based on their specific needs.
        """
        pass

    # ─────────────────────────────────────────────────────
    # Transport Management
    # ─────────────────────────────────────────────────────

    def select_transport(self) -> TransportType:
        """
        Select appropriate transport based on capabilities.

        Returns:
            TransportType to use for this tool
        """
        if self.capabilities.needs_pty or self.capabilities.interactive:
            if self.capabilities.needs_gui:
                return TransportType.TMUX
            else:
                return TransportType.PTY
        else:
            return TransportType.STDIN_STDOUT

    def create_transport(self, transport_type: Optional[TransportType] = None) -> Transport:
        """
        Create appropriate transport for this tool.

        Args:
            transport_type: Specific transport to use (or auto-select)

        Returns:
            Transport instance
        """
        if transport_type is None or transport_type == TransportType.AUTO:
            transport_type = self.select_transport()

        if transport_type == TransportType.PTY:
            return PTYTransport(cmd=self.command, name=self.name)

        elif transport_type == TransportType.TMUX:
            return TmuxTransport(
                cmd=self.command,
                window_name=self.name,
                spawn_gui=self.capabilities.needs_gui,
            )

        else:
            # For stdin/stdout, we'll use PTYTransport but without interactive features
            return PTYTransport(cmd=self.command, name=self.name)

    # ─────────────────────────────────────────────────────
    # Validation and Helpers
    # ─────────────────────────────────────────────────────

    def validate_input(self, input_text: str) -> bool:
        """
        Validate input before execution.

        Override in subclasses for tool-specific validation.
        """
        return len(input_text) > 0

    def preprocess_input(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Preprocess input before execution.

        Override in subclasses for tool-specific preprocessing.
        """
        return input_text

    def postprocess_output(self, output: str, context: Dict[str, Any]) -> str:
        """
        Postprocess output after execution.

        Override in subclasses for tool-specific postprocessing.
        """
        return output

    # ─────────────────────────────────────────────────────
    # Factory Methods
    # ─────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> UniversalTool:
        """
        Create tool from configuration dictionary.

        Args:
            config: Configuration with tool details

        Returns:
            UniversalTool instance
        """
        # Determine tool type
        tool_type_str = config.get("type", "custom")
        tool_type = ToolType(tool_type_str)

        # Build capabilities
        cap_config = config.get("capabilities", {})
        capabilities = ToolCapabilities(**cap_config)

        # Select appropriate concrete class
        if tool_type == ToolType.AI_ASSISTANT:
            return AIAssistantTool(
                name=config["name"],
                command=config["command"],
                capabilities=capabilities,
                description=config.get("description", ""),
                version=config.get("version", "unknown"),
            )
        elif tool_type == ToolType.POSIX_UTILITY:
            return POSIXTool(
                name=config["name"],
                command=config["command"],
                capabilities=capabilities,
                description=config.get("description", ""),
            )
        else:
            return CustomTool(
                name=config["name"],
                command=config["command"],
                capabilities=capabilities,
                description=config.get("description", ""),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for serialization."""
        return {
            "name": self.name,
            "command": self.command,
            "type": self.tool_type.value,
            "capabilities": asdict(self.capabilities),
            "description": self.description,
            "version": self.version,
            "metadata": self.metadata,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Concrete Tool Implementations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AIAssistantTool(UniversalTool):
    """
    AI coding assistant tool (aider, claude-code, etc.).

    These tools are typically:
    - Interactive (need PTY)
    - Stateful (maintain conversation context)
    - Long-running
    """

    def __init__(self, *args, **kwargs):
        # Default capabilities for AI assistants
        if "capabilities" not in kwargs:
            kwargs["capabilities"] = ToolCapabilities(
                interactive=True,
                needs_pty=True,
                stateful=True,
                long_running=True,
                async_capable=True,
            )
        super().__init__(*args, tool_type=ToolType.AI_ASSISTANT, **kwargs)

    async def _execute_via_transport(
        self,
        input_text: str,
        context: Dict[str, Any],
        timeout: Optional[float],
    ) -> str:
        """Execute AI assistant via PTY/Tmux transport."""
        # Create transport if needed
        if not self._transport:
            self._transport = self.create_transport()
            self._transport.start()

        # Send input
        self._transport.send_line(input_text)

        # Wait for response
        wait_time = timeout or 30.0
        output = ""

        # Use send_and_wait if available
        if hasattr(self._transport, 'send_and_wait'):
            output = self._transport.send_and_wait(input_text, wait_seconds=wait_time)
        else:
            # Fallback: manual wait
            await asyncio.sleep(wait_time)
            output = self._transport.recv_now()

        return output


class POSIXTool(UniversalTool):
    """
    POSIX utility (grep, sed, awk, git, etc.).

    These tools are typically:
    - Non-interactive
    - Stateless
    - Quick execution
    """

    def __init__(self, *args, **kwargs):
        # Default capabilities for POSIX tools
        if "capabilities" not in kwargs:
            kwargs["capabilities"] = ToolCapabilities(
                interactive=False,
                needs_pty=False,
                stateful=False,
                long_running=False,
                supports_stdin=True,
            )
        super().__init__(*args, tool_type=ToolType.POSIX_UTILITY, **kwargs)

    async def _execute_via_transport(
        self,
        input_text: str,
        context: Dict[str, Any],
        timeout: Optional[float],
    ) -> str:
        """Execute POSIX tool via subprocess."""
        import subprocess

        # Add input as stdin or as argument
        if self.capabilities.supports_stdin:
            proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input_text.encode())
            return stdout.decode()
        else:
            # Add input as command argument
            cmd = self.command + [input_text]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return stdout.decode()


class CustomTool(UniversalTool):
    """
    Custom user-defined tool.

    Capabilities must be explicitly specified.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, tool_type=ToolType.CUSTOM, **kwargs)

    async def _execute_via_transport(
        self,
        input_text: str,
        context: Dict[str, Any],
        timeout: Optional[float],
    ) -> str:
        """Execute custom tool via appropriate transport."""
        # Select transport based on capabilities
        transport_type = self.select_transport()

        if transport_type == TransportType.PTY or transport_type == TransportType.TMUX:
            # Use PTY/Tmux transport
            if not self._transport:
                self._transport = self.create_transport(transport_type)
                self._transport.start()

            self._transport.send_line(input_text)
            await asyncio.sleep(timeout or 5.0)
            return self._transport.recv_now()

        else:
            # Use subprocess
            proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input_text.encode())
            return stdout.decode()
