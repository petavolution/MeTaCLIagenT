"""
Terminal Emulator - Simulate keyboard input for interactive CLI tools

Supports:
- stdin/stdout for simple tools
- PTY emulation for interactive tools
- Keyboard input simulation (arrows, ctrl-c, etc.)
- ANSI escape sequence handling
"""

from __future__ import annotations
import os
import pty
import select
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Keyboard Input
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class KeyCode(Enum):
    """Special keyboard codes."""
    ENTER = "\r"
    TAB = "\t"
    BACKSPACE = "\x7f"
    ESCAPE = "\x1b"
    CTRL_C = "\x03"
    CTRL_D = "\x04"
    CTRL_Z = "\x1a"

    # Arrow keys (ANSI escape sequences)
    ARROW_UP = "\x1b[A"
    ARROW_DOWN = "\x1b[B"
    ARROW_RIGHT = "\x1b[C"
    ARROW_LEFT = "\x1b[D"

    # Function keys
    F1 = "\x1bOP"
    F2 = "\x1bOQ"
    F3 = "\x1bOR"
    F4 = "\x1bOS"


@dataclass
class KeyboardInput:
    """
    Represents keyboard input with timing.

    Example:
        # Type "hello"
        inputs = [
            KeyboardInput("h"),
            KeyboardInput("e"),
            KeyboardInput("l"),
            KeyboardInput("l"),
            KeyboardInput("o"),
            KeyboardInput(KeyCode.ENTER.value, delay=0.1)
        ]
    """
    key: str  # Key or escape sequence
    delay: float = 0.0  # Delay before sending (seconds)

    @classmethod
    def from_string(cls, text: str, char_delay: float = 0.01) -> List[KeyboardInput]:
        """
        Create keyboard inputs from string.

        Args:
            text: String to type
            char_delay: Delay between characters (simulates typing speed)

        Returns:
            List of KeyboardInput objects
        """
        inputs = []
        for char in text:
            inputs.append(KeyboardInput(char, delay=char_delay))
        return inputs

    @classmethod
    def enter(cls, delay: float = 0.0) -> KeyboardInput:
        """Create ENTER key input."""
        return KeyboardInput(KeyCode.ENTER.value, delay=delay)

    @classmethod
    def ctrl_c(cls, delay: float = 0.0) -> KeyboardInput:
        """Create CTRL+C input."""
        return KeyboardInput(KeyCode.CTRL_C.value, delay=delay)

    @classmethod
    def arrow_up(cls, delay: float = 0.0) -> KeyboardInput:
        """Create UP ARROW input."""
        return KeyboardInput(KeyCode.ARROW_UP.value, delay=delay)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Terminal Emulator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TerminalEmulator:
    """
    Emulate terminal for interactive CLI tools.

    Supports:
    - PTY-based process spawning
    - Keyboard input simulation
    - Output capturing with ANSI codes
    - Timeout handling

    Example:
        emulator = TerminalEmulator()
        emulator.spawn(["python", "-i"])

        # Send input
        emulator.send_keys([
            KeyboardInput.from_string("print('hello')"),
            KeyboardInput.enter()
        ])

        # Read output
        output = emulator.read(timeout=1.0)
        print(output)  # "hello"

        emulator.close()
    """

    def __init__(self):
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None
        self.output_buffer: str = ""

    def spawn(
        self,
        cmd: List[str],
        env: Dict[str, str] = None,
        cwd: str = None
    ):
        """
        Spawn process in pseudo-terminal.

        Args:
            cmd: Command and arguments
            env: Environment variables
            cwd: Working directory
        """
        # Create PTY
        self.master_fd, self.slave_fd = pty.openpty()

        # Spawn process
        self.process = subprocess.Popen(
            cmd,
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            env=env,
            cwd=cwd,
            preexec_fn=os.setsid  # Create new process group
        )

    def send_keys(self, inputs: List[KeyboardInput]):
        """
        Send keyboard inputs to terminal.

        Args:
            inputs: List of KeyboardInput objects
        """
        if not self.master_fd:
            raise RuntimeError("Terminal not spawned")

        for input_obj in inputs:
            # Delay if specified
            if input_obj.delay > 0:
                time.sleep(input_obj.delay)

            # Send key
            os.write(self.master_fd, input_obj.key.encode('utf-8'))

    def send_text(self, text: str, char_delay: float = 0.01, press_enter: bool = True):
        """
        Send text as if typing.

        Args:
            text: Text to send
            char_delay: Delay between characters
            press_enter: Press ENTER after text
        """
        inputs = KeyboardInput.from_string(text, char_delay=char_delay)

        if press_enter:
            inputs.append(KeyboardInput.enter())

        self.send_keys(inputs)

    def read(self, timeout: float = 1.0, max_bytes: int = 10000) -> str:
        """
        Read output from terminal.

        Args:
            timeout: Max time to wait for output
            max_bytes: Max bytes to read

        Returns:
            Output string (may contain ANSI escape codes)
        """
        if not self.master_fd:
            raise RuntimeError("Terminal not spawned")

        output = ""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if data available
            ready, _, _ = select.select([self.master_fd], [], [], 0.1)

            if ready:
                try:
                    data = os.read(self.master_fd, max_bytes)
                    if data:
                        output += data.decode('utf-8', errors='ignore')
                except OSError:
                    break
            else:
                # No data available
                if output:
                    # We got some output, wait a bit more for potential trailing data
                    time.sleep(0.1)
                    continue
                else:
                    # No output yet, keep waiting
                    continue

        self.output_buffer += output
        return output

    def read_until(self, pattern: str, timeout: float = 5.0) -> str:
        """
        Read until pattern appears in output.

        Args:
            pattern: String pattern to wait for
            timeout: Max time to wait

        Returns:
            Output up to and including pattern
        """
        output = ""
        start_time = time.time()

        while time.time() - start_time < timeout:
            chunk = self.read(timeout=0.5)
            output += chunk

            if pattern in output:
                return output

        return output

    def get_full_output(self) -> str:
        """Get all output captured so far."""
        return self.output_buffer

    def clear_output(self):
        """Clear output buffer."""
        self.output_buffer = ""

    def close(self):
        """Close terminal and terminate process."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()

        if self.master_fd:
            os.close(self.master_fd)

        if self.slave_fd:
            os.close(self.slave_fd)

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANSI Escape Code Stripper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import re

ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def strip_ansi_codes(text: str) -> str:
    """
    Remove ANSI escape codes from text.

    Args:
        text: Text with ANSI codes

    Returns:
        Clean text without escape codes
    """
    return ANSI_ESCAPE_PATTERN.sub('', text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Simple stdin/stdout Wrapper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SimpleTerminal:
    """
    Simple terminal using stdin/stdout (no PTY).

    For non-interactive tools that just read stdin and write stdout.
    """

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def spawn(self, cmd: List[str], env: Dict[str, str] = None, cwd: str = None):
        """Spawn process with pipes."""
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=cwd,
            text=True,
            bufsize=0
        )

    def send_text(self, text: str, press_enter: bool = True):
        """Send text to stdin."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Terminal not spawned")

        if press_enter and not text.endswith('\n'):
            text += '\n'

        self.process.stdin.write(text)
        self.process.stdin.flush()

    def read(self, timeout: float = 1.0) -> str:
        """Read from stdout with timeout."""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Terminal not spawned")

        import select

        # Use select to implement timeout
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)

        if ready:
            return self.process.stdout.readline()

        return ""

    def close(self):
        """Close process."""
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()

            try:
                self.process.terminate()
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_interactive_command(
    cmd: List[str],
    inputs: List[str],
    timeout: float = 5.0
) -> str:
    """
    Run command with interactive inputs.

    Args:
        cmd: Command and arguments
        inputs: List of strings to send as input
        timeout: Timeout per input

    Returns:
        Combined output
    """
    with TerminalEmulator() as term:
        term.spawn(cmd)

        outputs = []
        for input_text in inputs:
            term.send_text(input_text)
            output = term.read(timeout=timeout)
            outputs.append(output)

        return "\n".join(outputs)
