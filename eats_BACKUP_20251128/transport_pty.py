# transport_pty.py
"""
PTY Transport: Low-level control of terminal-driven LLM CLI processes.

This module provides the foundational I/O layer for spawning and controlling
interactive CLI processes (like aider, gpt4all, open-interpreter) via
pseudo-terminals on Linux.
"""

import os
import pty
import select
import subprocess
import threading
import time
from typing import Optional, List


# Late import to avoid circular dependency
def _get_audit_logger():
    """Lazy import audit logger to avoid circular deps."""
    try:
        from eats_core.audit import get_audit_logger
        return get_audit_logger()
    except ImportError:
        return None


class BufferOverflowError(Exception):
    """Raised when buffer exceeds maximum size."""
    pass


class PTYTransport:
    """
    PTY-based transport for an interactive CLI process.

    - Spawns the given command in a pseudo-terminal.
    - Continuously reads from the PTY in a background thread.
    - Accumulates output into an internal buffer.
    - Exposes send()/recv() methods for higher-level agent code.

    Security Features:
    - Bounded buffers to prevent memory exhaustion
    - Ring buffer for full_log to prevent unbounded growth
    - Raises BufferOverflowError if limits exceeded

    Usage:
        transport = PTYTransport(cmd=["aider"], name="coder-001")
        transport.start()
        transport.send_line("Write a hello world function")
        time.sleep(2)
        output = transport.recv_now()
        transport.terminate()
    """

    # Security limits
    MAX_BUFFER_SIZE = 10 * 1024 * 1024   # 10MB max buffer
    MAX_LOG_SIZE = 50 * 1024 * 1024      # 50MB max full log (ring buffer)

    def __init__(self, cmd: List[str], name: str = "agent",
                 max_buffer_size: Optional[int] = None,
                 max_log_size: Optional[int] = None):
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
