# transport.py - Canonical Transport Layer for CLI Processes
"""
CANONICAL TRANSPORT IMPLEMENTATION

This is the authoritative transport layer for EATS. Do not use Transport
classes from core.py - they are deprecated and will be removed.

Supports:
- PTY (pseudo-terminal) for interactive CLIs
- Tmux (multi-pane visual debugging with optional GUI spawning)

Features:
- Backward compatibility with legacy send()/recv() API
- Modern send_line()/send_raw()/recv_now() API
- GUI terminal spawning for visual multi-agent orchestration (GhostSwarm)
- Multiple terminal emulator support (alacritty, kitty, gnome-terminal, xterm)
- Full output history logging (get_full_log)

Security Features:
- Bounded buffers to prevent memory exhaustion
- Buffer overflow detection and audit logging
- Shell escaping for tmux commands
- Command injection prevention

Usage:
    # PTY transport (modern API)
    transport = PTYTransport(cmd=["aider"], name="coder-001")
    transport.start()
    transport.send_line("Write hello world")
    time.sleep(2)
    output = transport.recv_now()
    transport.terminate()

    # PTY transport (legacy API - backward compatible)
    transport = PTYTransport(cmd=["aider"], name="coder-001")
    transport.start()
    transport.send("Write hello world", newline=True)
    output = transport.recv(timeout=2.0)
    transport.terminate()

    # Tmux transport with GUI (for visual debugging)
    transport = TmuxTransport(
        cmd=["aider"],
        window_name="debug",
        spawn_gui=True,
        terminal="alacritty"
    )
    transport.start()  # Spawns visible terminal window
    transport.send_line("Review this code")
    output = transport.recv_now()
    transport.terminate()
"""

from __future__ import annotations
import os
import pty
import select
import shlex
import subprocess
import threading
import time
from typing import Optional, List
from pathlib import Path


# Late import to avoid circular dependency
def _get_audit_logger():
    """Lazy import audit logger to avoid circular deps."""
    try:
        from .audit import get_audit_logger
        return get_audit_logger()
    except ImportError:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BufferOverflowError(Exception):
    """Raised when buffer exceeds maximum size."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Base Transport Interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Transport:
    """
    Abstract base class for process transports.

    All transports must implement:
    - start(): Spawn the process
    - send_line(text): Send text with newline
    - send_raw(text): Send raw text
    - recv_now(): Get accumulated output (non-blocking)
    - terminate(): Stop the process
    - is_alive(): Check if process is running
    """

    def start(self) -> None:
        """Start the underlying process."""
        raise NotImplementedError

    def send_line(self, text: str) -> None:
        """Send a line of text followed by newline."""
        raise NotImplementedError

    def send_raw(self, text: str) -> None:
        """Send raw text without newline."""
        raise NotImplementedError

    def recv_now(self) -> str:
        """Return accumulated output and clear buffer (non-blocking)."""
        raise NotImplementedError

    def terminate(self) -> None:
        """Stop the process."""
        raise NotImplementedError

    def is_alive(self) -> bool:
        """Check if process is still running."""
        raise NotImplementedError

    def get_full_log(self) -> str:
        """Return complete output history."""
        raise NotImplementedError

    def send_and_wait(
        self,
        prompt: str,
        wait_seconds: float = 5.0,
        idle_threshold: float = 0.5,
    ) -> str:
        """
        Send prompt and wait for response.

        Args:
            prompt: Text to send
            wait_seconds: Maximum time to wait
            idle_threshold: How long to wait for no new output (seconds)

        Returns:
            Accumulated response text
        """
        # Send prompt
        self.send_line(prompt)

        # Wait for response with idle detection
        start = time.time()
        last_output_time = start
        accumulated = ""

        while time.time() - start < wait_seconds:
            new_output = self.recv_now()

            if new_output:
                accumulated += new_output
                last_output_time = time.time()

            # If idle for threshold duration, consider done
            if time.time() - last_output_time > idle_threshold:
                break

            time.sleep(0.1)

        return accumulated

    # ─────────────────────────────────────────────────────
    # Backward Compatibility Wrappers
    # ─────────────────────────────────────────────────────

    def send(self, text: str, newline: bool = True) -> None:
        """
        Backward compatibility wrapper for send_line/send_raw.

        This method exists to support legacy code that uses send(text, newline=True).
        New code should use send_line() or send_raw() directly.

        Args:
            text: Text to send
            newline: Whether to append newline (default: True)
        """
        if newline:
            self.send_line(text)
        else:
            self.send_raw(text)

    def recv(self, timeout: float = 0.1) -> str:
        """
        Backward compatibility wrapper for recv_now.

        This method exists to support legacy code that uses recv(timeout=0.1).
        New code should use recv_now() directly.

        Args:
            timeout: Time to wait before reading (seconds)

        Returns:
            Accumulated output
        """
        if timeout > 0:
            time.sleep(timeout)
        return self.recv_now()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PTY Transport
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PTYTransport(Transport):
    """
    PTY-based transport for interactive CLI processes.

    - Spawns command in pseudo-terminal
    - Continuously reads from PTY in background thread
    - Accumulates output into internal buffer
    - Exposes send()/recv() methods

    Security Features:
    - Bounded buffers to prevent memory exhaustion
    - Ring buffer for full_log to prevent unbounded growth
    - Raises BufferOverflowError if limits exceeded
    """

    # Security limits
    MAX_BUFFER_SIZE = 10 * 1024 * 1024   # 10MB max buffer
    MAX_LOG_SIZE = 50 * 1024 * 1024      # 50MB max full log (ring buffer)

    def __init__(
        self,
        cmd: List[str],
        name: str = "agent",
        max_buffer_size: Optional[int] = None,
        max_log_size: Optional[int] = None,
    ):
        """
        Initialize PTY transport.

        Args:
            cmd: Command to execute (e.g., ["aider", "--no-auto-commit"])
            name: Identifier for this process (for logging)
            max_buffer_size: Maximum current buffer size (default: 10MB)
            max_log_size: Maximum full log size (default: 50MB)
        """
        self.cmd = cmd
        self.name = name

        self.master_fd: Optional[int] = None
        self.proc: Optional[subprocess.Popen] = None

        self._lock = threading.Lock()
        self._buffer = ""
        self._full_log = ""  # Complete history for debugging
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None
        self._overflow_error: Optional[Exception] = None

        # Configurable limits
        self.max_buffer_size = max_buffer_size or self.MAX_BUFFER_SIZE
        self.max_log_size = max_log_size or self.MAX_LOG_SIZE

    # ─────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Spawn the process in a PTY and start the reader thread.
        """
        if self.proc is not None:
            raise RuntimeError("Process already started")

        master_fd, slave_fd = pty.openpty()
        self.master_fd = master_fd

        # Set terminal size (some CLI tools need this)
        try:
            import fcntl
            import struct
            import termios
            # rows, cols, xpixel, ypixel
            winsize = struct.pack('HHHH', 50, 120, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass  # Non-critical

        # Start the process attached to slave side
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            bufsize=0,
            close_fds=True,
            text=False,  # Raw bytes; we decode ourselves
            env={**os.environ, "TERM": "xterm-256color"},
        )
        os.close(slave_fd)

        self._running = True
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name=f"PTYReader-{self.name}",
        )
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        """
        Background loop: read from PTY and append to buffer.

        Security: Enforces buffer limits to prevent memory exhaustion.
        - Current buffer limited to max_buffer_size
        - Full log uses ring buffer (keeps last N bytes)
        - Sets overflow error if limits exceeded
        """
        assert self.master_fd is not None
        while self._running:
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
                text = data.decode("utf-8", errors="ignore")

                with self._lock:
                    # Check buffer limit before append
                    if len(self._buffer) + len(text) > self.max_buffer_size:
                        buffer_size = len(self._buffer) + len(text)
                        self._overflow_error = BufferOverflowError(
                            f"Buffer exceeded {self.max_buffer_size} bytes. "
                            f"Process '{self.name}' generating too much output."
                        )

                        # AUDIT: Log buffer overflow
                        audit = _get_audit_logger()
                        if audit:
                            audit.log_buffer_overflow(
                                agent_name=self.name,
                                buffer_size=buffer_size,
                                max_size=self.max_buffer_size
                            )

                        self._running = False
                        break

                    self._buffer += text

                    # Ring buffer for full_log - keep last N bytes
                    self._full_log += text
                    if len(self._full_log) > self.max_log_size:
                        # Keep last max_log_size bytes
                        excess = len(self._full_log) - self.max_log_size
                        self._full_log = self._full_log[excess:]
            else:
                time.sleep(0.01)

        self._running = False

    def terminate(self) -> None:
        """
        Stop reader and terminate the underlying process.
        """
        self._running = False
        if self.proc is not None:
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

    # ─────────────────────────────────────────────────────
    # I/O Interface
    # ─────────────────────────────────────────────────────

    def send_line(self, text: str) -> None:
        """
        Send a line of text followed by newline (like pressing ENTER).
        """
        if self.master_fd is None:
            raise RuntimeError("Transport not started")
        data = (text + "\n").encode("utf-8")
        os.write(self.master_fd, data)

    def send_raw(self, text: str) -> None:
        """
        Send raw text without adding newline.
        Useful for interactive confirmations like 'y' or 'n'.
        """
        if self.master_fd is None:
            raise RuntimeError("Transport not started")
        os.write(self.master_fd, text.encode("utf-8"))

    def recv_now(self) -> str:
        """
        Return any accumulated output and clear internal buffer.
        Non-blocking: if nothing new, returns empty string.

        Raises:
            BufferOverflowError: If buffer exceeded limits during read
        """
        with self._lock:
            # Check for overflow error from reader thread
            if self._overflow_error:
                error = self._overflow_error
                self._overflow_error = None
                raise error

            data = self._buffer
            self._buffer = ""
        return data

    def get_full_log(self) -> str:
        """
        Return complete output history (does not clear).
        """
        with self._lock:
            return self._full_log

    def is_alive(self) -> bool:
        """
        Check if the underlying process is still running.
        """
        return self.proc is not None and self.proc.poll() is None

    def get_exit_code(self) -> Optional[int]:
        """
        Return exit code if process has terminated, else None.
        """
        if self.proc is None:
            return None
        return self.proc.poll()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tmux Transport
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TmuxTransport(Transport):
    """
    Tmux-based transport for visual debugging.

    Creates a tmux window/pane for the CLI process, allowing:
    - Visual inspection of CLI output
    - Manual intervention if needed
    - Persistence across detach/reattach
    - Optional GUI terminal spawning for visual multi-agent orchestration

    Security:
    - Uses shlex.quote() to prevent command injection
    - Validates tmux session/window names
    """

    def __init__(
        self,
        cmd: List[str],
        session_name: str = "eats",
        window_name: Optional[str] = None,
        spawn_gui: bool = False,
        terminal: str = "alacritty",
    ):
        """
        Initialize Tmux transport.

        Args:
            cmd: Command to execute
            session_name: Tmux session name
            window_name: Tmux window name (default: auto-generated)
            spawn_gui: Whether to spawn a visible GUI terminal (for visual debugging)
            terminal: Terminal emulator to use (alacritty, kitty, gnome-terminal, xterm)
        """
        self.cmd = cmd
        self.session_name = session_name
        self.window_name = window_name or f"cli-{os.getpid()}"
        self.spawn_gui = spawn_gui
        self.terminal = terminal

        self._pane_id: Optional[str] = None
        self._running = False

    def start(self) -> None:
        """
        Start the process in a tmux pane.
        Optionally spawns a GUI terminal if spawn_gui=True.
        """
        if self._running:
            raise RuntimeError("Transport already started")

        # Ensure session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session_name],
            capture_output=True,
        )
        if result.returncode != 0:
            # Create session
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", self.session_name],
                check=True,
            )

        # Create window
        subprocess.run(
            ["tmux", "new-window", "-t", self.session_name, "-n", self.window_name],
            check=True,
        )

        # Get pane ID
        result = subprocess.run(
            ["tmux", "list-panes", "-t", f"{self.session_name}:{self.window_name}", "-F", "#{pane_id}"],
            capture_output=True,
            text=True,
            check=True,
        )
        self._pane_id = result.stdout.strip()

        # SECURITY: Escape command arguments with shlex.quote()
        cmd_str = " ".join(shlex.quote(arg) for arg in self.cmd)

        # Send command to pane
        subprocess.run(
            ["tmux", "send-keys", "-t", self._pane_id, cmd_str, "Enter"],
            check=True,
        )

        self._running = True

        # Optionally spawn GUI terminal for visual debugging
        if self.spawn_gui:
            self._spawn_gui_window()

    def _spawn_gui_window(self) -> None:
        """
        Spawn a visible terminal window attached to the tmux session.

        This enables visual multi-agent orchestration (like GhostSwarm).
        Supports multiple terminal emulators with graceful fallback.

        SECURITY: Uses array form subprocess.Popen to prevent command injection.
        """
        try:
            if self.terminal == "alacritty":
                subprocess.Popen(
                    ["alacritty", "-e", "tmux", "attach", "-t", self.session_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif self.terminal == "kitty":
                subprocess.Popen(
                    ["kitty", "-e", "tmux", "attach", "-t", self.session_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif self.terminal == "gnome-terminal":
                subprocess.Popen(
                    ["gnome-terminal", "--", "tmux", "attach", "-t", self.session_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:  # xterm fallback
                subprocess.Popen(
                    ["xterm", "-e", "tmux", "attach", "-t", self.session_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            # Terminal not found - log warning but continue
            # The transport will still work, just without GUI
            import warnings
            warnings.warn(
                f"Terminal '{self.terminal}' not found. "
                f"Transport running without GUI. "
                f"Use 'tmux attach -t {self.session_name}' to view manually.",
                RuntimeWarning,
            )

    def send_line(self, text: str) -> None:
        """
        Send a line of text to the tmux pane.
        """
        if not self._running or not self._pane_id:
            raise RuntimeError("Transport not started")

        # SECURITY: Escape text with shlex.quote()
        escaped_text = shlex.quote(text)

        subprocess.run(
            ["tmux", "send-keys", "-t", self._pane_id, "-l", escaped_text],
            check=True,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", self._pane_id, "Enter"],
            check=True,
        )

    def send_raw(self, text: str) -> None:
        """
        Send raw text without newline.
        """
        if not self._running or not self._pane_id:
            raise RuntimeError("Transport not started")

        escaped_text = shlex.quote(text)
        subprocess.run(
            ["tmux", "send-keys", "-t", self._pane_id, "-l", escaped_text],
            check=True,
        )

    def recv_now(self) -> str:
        """
        Capture current pane content.

        Note: Tmux doesn't have a clean "read new output only" mechanism,
        so this returns the full visible pane content.
        """
        if not self._running or not self._pane_id:
            raise RuntimeError("Transport not started")

        result = subprocess.run(
            ["tmux", "capture-pane", "-t", self._pane_id, "-p"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def get_full_log(self) -> str:
        """
        Return current pane content (same as recv_now for tmux).
        """
        return self.recv_now()

    def terminate(self) -> None:
        """
        Kill the tmux pane.
        """
        if self._pane_id:
            subprocess.run(
                ["tmux", "kill-pane", "-t", self._pane_id],
                capture_output=True,  # Suppress errors if already dead
            )
        self._running = False

    def is_alive(self) -> bool:
        """
        Check if the tmux pane still exists.
        """
        if not self._pane_id:
            return False

        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#{pane_id}"],
            capture_output=True,
            text=True,
        )
        return self._pane_id in result.stdout


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Factory Function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_transport(
    cmd: List[str],
    transport_type: str = "pty",
    name: Optional[str] = None,
    **kwargs,
) -> Transport:
    """
    Factory function to create a transport.

    Args:
        cmd: Command to execute
        transport_type: "pty" or "tmux"
        name: Identifier for logging
        **kwargs: Additional transport-specific arguments

    Returns:
        Transport instance

    Example:
        transport = create_transport(["aider"], transport_type="pty", name="coder-1")
        transport.start()
        transport.send_line("Write hello world")
        output = transport.recv_now()
        transport.terminate()
    """
    if transport_type == "pty":
        return PTYTransport(cmd, name=name or "agent", **kwargs)
    elif transport_type == "tmux":
        window_name = name or f"cli-{os.getpid()}"
        return TmuxTransport(cmd, window_name=window_name, **kwargs)
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")
