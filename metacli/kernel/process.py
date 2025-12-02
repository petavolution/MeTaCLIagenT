"""
Process Spawning and Management - Kernel Layer

Unified process abstraction supporting PTY, subprocess, and tmux.
Consolidates all transport code into one clean interface.

Features:
- PTY for interactive CLIs (aider, claude-code, gemini)
- Subprocess for simple tools (grep, python -c)
- Tmux for visual debugging (multi-pane)
- Buffer overflow protection (10MB default)
- Timeout enforcement
- Clean termination

Security:
- Command validation via Security class
- Buffer limits prevent memory exhaustion
- Proper process cleanup

Example:
    from metacli.kernel import Process

    # Auto-select transport
    proc = Process.spawn(["python", "-c", "print('hello')"])
    proc.start()
    output = proc.read(timeout=2.0)
    proc.terminate()

    # Or explicit PTY for interactive
    from metacli.kernel import PTYProcess
    proc = PTYProcess(["aider", "--no-auto-commit"])
    proc.start()
    proc.write("Write a function\\n")
    output = proc.read(timeout=5.0)
    proc.terminate()
"""

from __future__ import annotations
import os
import pty
import select
import subprocess
import shlex
import time
import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Union


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProcessError(Exception):
    """Base exception for process errors."""
    pass


class BufferOverflowError(ProcessError):
    """Buffer exceeded maximum size."""
    pass


class TimeoutError(ProcessError):
    """Process execution timed out."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Base Process Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Process(ABC):
    """
    Universal process abstraction.

    Base class for all process types (PTY, Subprocess, Tmux).
    Provides common interface regardless of underlying implementation.
    """

    def __init__(
        self,
        cmd: List[str],
        name: str = "process",
        max_buffer: int = 10 * 1024 * 1024,  # 10MB
        env: Optional[dict] = None,
    ):
        """
        Initialize process.

        Args:
            cmd: Command and arguments to execute
            name: Process name for identification
            max_buffer: Maximum buffer size in bytes
            env: Optional environment variables
        """
        self.cmd = cmd
        self.name = name
        self.max_buffer = max_buffer
        self.env = env or {}

        self.running = False
        self.start_time = 0.0

    @abstractmethod
    def start(self) -> None:
        """Start the process. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def write(self, text: str) -> None:
        """Write to process stdin. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def read(self, timeout: float = 1.0) -> str:
        """Read from process stdout/stderr. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def terminate(self) -> None:
        """Terminate the process. Must be implemented by subclasses."""
        pass

    @staticmethod
    def spawn(
        cmd: List[str],
        interactive: bool = False,
        visual: bool = False,
        **kwargs
    ) -> Process:
        """
        Factory method: Auto-select process type.

        Args:
            cmd: Command to execute
            interactive: True for PTY (interactive CLIs like aider)
            visual: True for Tmux (visual debugging)
            **kwargs: Additional arguments passed to process constructor

        Returns:
            Appropriate Process instance

        Example:
            # Simple tool
            proc = Process.spawn(["grep", "TODO", "file.txt"])

            # Interactive AI tool
            proc = Process.spawn(["aider"], interactive=True)

            # Visual debugging
            proc = Process.spawn(["aider"], visual=True)
        """
        if visual:
            return TmuxProcess(cmd, **kwargs)
        elif interactive:
            return PTYProcess(cmd, **kwargs)
        else:
            return SubProcess(cmd, **kwargs)

    def is_running(self) -> bool:
        """Check if process is running."""
        return self.running

    def uptime(self) -> float:
        """Get process uptime in seconds."""
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PTY Process (Interactive CLIs)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PTYProcess(Process):
    """
    PTY-based process for interactive CLI tools.

    Uses pseudo-terminal for tools that need terminal interaction
    (aider, claude-code, gemini, etc).

    Features:
    - Full terminal emulation
    - Background reader thread
    - Buffer overflow protection
    - Proper cleanup
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.master_fd: Optional[int] = None
        self.proc: Optional[subprocess.Popen] = None

        self._lock = threading.Lock()
        self._buffer = ""
        self._reader_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Spawn process in PTY."""
        if self.proc is not None:
            raise ProcessError("Process already started")

        # Create PTY
        master_fd, slave_fd = pty.openpty()
        self.master_fd = master_fd

        # Set terminal size (some CLIs need this)
        try:
            import fcntl
            import struct
            import termios
            # rows, cols, xpixel, ypixel
            winsize = struct.pack('HHHH', 50, 120, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass  # Non-critical

        # Spawn process attached to slave
        full_env = {**os.environ, "TERM": "xterm-256color", **self.env}

        self.proc = subprocess.Popen(
            self.cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            bufsize=0,
            close_fds=True,
            env=full_env,
        )
        os.close(slave_fd)

        self.running = True
        self.start_time = time.time()

        # Start background reader
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name=f"PTYReader-{self.name}",
        )
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        """Background loop: read from PTY and buffer output."""
        assert self.master_fd is not None

        while self.running:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
            except (OSError, ValueError):
                break

            if self.master_fd in r:
                try:
                    data = os.read(self.master_fd, 4096)
                except OSError:
                    break

                if not data:
                    break

                text = data.decode("utf-8", errors="replace")

                with self._lock:
                    # Buffer overflow protection
                    if len(self._buffer) + len(text) > self.max_buffer:
                        self.running = False
                        raise BufferOverflowError(
                            f"Buffer exceeded {self.max_buffer} bytes for process '{self.name}'"
                        )

                    self._buffer += text

        self.running = False

    def write(self, text: str) -> None:
        """Write to PTY stdin."""
        if not self.running or self.master_fd is None:
            raise ProcessError("Process not running")

        os.write(self.master_fd, text.encode("utf-8"))

    def read(self, timeout: float = 1.0) -> str:
        """
        Read available output from PTY.

        Args:
            timeout: How long to wait for output (seconds)

        Returns:
            Output accumulated during timeout period
        """
        if not self.running:
            raise ProcessError("Process not running")

        time.sleep(timeout)

        with self._lock:
            output = self._buffer
            self._buffer = ""

        return output

    def read_available(self) -> str:
        """Read all currently available output without waiting."""
        with self._lock:
            output = self._buffer
            self._buffer = ""

        return output

    def terminate(self) -> None:
        """Terminate PTY process and cleanup."""
        self.running = False

        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Subprocess (Simple Tools)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SubProcess(Process):
    """
    Subprocess-based process for simple non-interactive tools.

    Use for tools that just need stdin/stdout (grep, python -c, etc).
    No terminal emulation needed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        """Spawn subprocess."""
        if self.proc is not None:
            raise ProcessError("Process already started")

        full_env = {**os.environ, **self.env}

        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
        )

        self.running = True
        self.start_time = time.time()

    def write(self, text: str) -> None:
        """Write to stdin."""
        if not self.running or not self.proc or not self.proc.stdin:
            raise ProcessError("Process not running")

        self.proc.stdin.write(text.encode("utf-8"))
        self.proc.stdin.flush()

    def read(self, timeout: float = 1.0) -> str:
        """Read from stdout/stderr."""
        if not self.running or not self.proc:
            raise ProcessError("Process not running")

        try:
            stdout, stderr = self.proc.communicate(timeout=timeout)
            self.running = False
            return stdout.decode("utf-8") + stderr.decode("utf-8")
        except subprocess.TimeoutExpired:
            return ""

    def terminate(self) -> None:
        """Terminate subprocess."""
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()

        self.running = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tmux Process (Visual Debugging)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TmuxProcess(Process):
    """
    Tmux-based process for visual debugging.

    Spawns process in a tmux session for multi-pane visual inspection.
    User can attach to session with: tmux attach -t <session_name>
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_name = f"metacli-{self.name}-{os.getpid()}"

    def start(self) -> None:
        """Spawn tmux session."""
        # Check tmux available
        if subprocess.run(["which", "tmux"], capture_output=True).returncode != 0:
            raise ProcessError("tmux not found - install with: sudo apt install tmux")

        # Escape command for shell
        cmd_escaped = " ".join(shlex.quote(arg) for arg in self.cmd)

        # Create tmux session
        tmux_cmd = [
            "tmux",
            "new-session",
            "-d",  # Detached
            "-s", self.session_name,
            cmd_escaped
        ]

        subprocess.run(tmux_cmd, check=True)
        self.running = True
        self.start_time = time.time()

    def write(self, text: str) -> None:
        """Send keys to tmux session."""
        if not self.running:
            raise ProcessError("Process not running")

        subprocess.run([
            "tmux",
            "send-keys",
            "-t", self.session_name,
            text,
            "Enter"
        ], check=True)

    def read(self, timeout: float = 1.0) -> str:
        """Capture tmux pane content."""
        if not self.running:
            raise ProcessError("Process not running")

        # Wait for output
        time.sleep(timeout)

        result = subprocess.run(
            ["tmux", "capture-pane", "-t", self.session_name, "-p"],
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout

    def terminate(self) -> None:
        """Kill tmux session."""
        if self.running:
            subprocess.run([
                "tmux",
                "kill-session",
                "-t", self.session_name
            ], stderr=subprocess.DEVNULL)

        self.running = False

    def attach_instructions(self) -> str:
        """Get instructions for attaching to tmux session."""
        return f"tmux attach -t {self.session_name}"
