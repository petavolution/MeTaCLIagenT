# PHASE 1 IMPLEMENTATION: Kernel Extraction - EXECUTE NOW

**Status**: READY TO IMPLEMENT
**Timeline**: 1-2 days for immediate impact
**Goal**: Extract minimal execution kernel - prove the refactor works

---

## 🎯 IMMEDIATE OBJECTIVE

Create `metacli/kernel/` - the **1,500-line foundation** that everything else builds on.

**Why Kernel First?**
1. **Removes all duplication** (3 PTYTransport → 1 Process)
2. **Proves refactor viability** (working code, not just docs)
3. **Unlocks everything else** (Core layer can build on clean kernel)
4. **Immediate 23% reduction** (5,800 lines deleted from eats/)

---

## 📊 WHAT WE'RE EXTRACTING

### Source Files (Current Mess)
```
✗ eats_core/transport.py         (707 lines) - Has PTY + Tmux + audit
✗ eats/transport_pty.py          (263 lines) - DUPLICATE PTY
✗ eats/tmux_transport.py         (447 lines) - DUPLICATE Tmux
✗ eats_core/audit.py             (532 lines) - Security logging
✗ eats_core/logging.py           (377 lines) - Logging setup
─────────────────────────────────────────────────────────
Total: 2,326 lines (with massive duplication)
```

### Target Files (Clean Kernel)
```
✓ metacli/kernel/process.py      (400 lines) - ONE process class
✓ metacli/kernel/io.py            (300 lines) - I/O primitives
✓ metacli/kernel/security.py     (400 lines) - Validation, escaping
✓ metacli/kernel/logging.py      (400 lines) - Infrastructure
─────────────────────────────────────────────────────────
Total: 1,500 lines (zero duplication, crystal clear)
```

**Result**: 2,326 → 1,500 lines (-35%)

---

## 🔧 STEP-BY-STEP IMPLEMENTATION

### STEP 1: Create Directory Structure (5 minutes)

```bash
mkdir -p metacli/kernel
touch metacli/__init__.py
touch metacli/kernel/__init__.py
touch metacli/kernel/process.py
touch metacli/kernel/io.py
touch metacli/kernel/security.py
touch metacli/kernel/logging.py
```

### STEP 2: Extract kernel/process.py (2 hours)

**Goal**: One unified Process class that handles PTY, subprocess, Tmux

**Sources to merge**:
- `eats_core/transport.py` → PTYTransport base logic
- `eats/transport_pty.py` → Buffer overflow protection ✓ (KEEP)
- `eats/tmux_transport.py` → Tmux spawning ✓ (KEEP)

**What to REMOVE during extraction**:
- ❌ Agent, AgentDNA references
- ❌ Evolution-specific code
- ❌ Fitness tracking
- ❌ Swarm coordination
- ❌ LLM provider integration

**What to KEEP**:
- ✅ PTY spawning (pty.fork(), os.read/write)
- ✅ Subprocess spawning (subprocess.Popen)
- ✅ Tmux spawning (tmux new-session)
- ✅ Buffer overflow protection (10MB limit)
- ✅ Shell escaping (shlex.quote)
- ✅ Timeout enforcement

**API Design**:
```python
# metacli/kernel/process.py

"""
Process spawning and management.

Supports:
- PTY (pseudo-terminal for interactive CLIs)
- Subprocess (simple stdin/stdout)
- Tmux (visual debugging)

Security:
- Buffer overflow protection (10MB default)
- Timeout enforcement
- Clean termination
"""

from abc import ABC, abstractmethod
from typing import Optional, List
import pty
import os
import subprocess
import shlex
import time


class ProcessError(Exception):
    """Base exception for process errors."""
    pass


class BufferOverflowError(ProcessError):
    """Buffer exceeded maximum size."""
    pass


class TimeoutError(ProcessError):
    """Process execution timed out."""
    pass


class Process(ABC):
    """
    Universal process abstraction.

    Three implementations:
    - PTYProcess: Interactive CLIs (aider, claude-code)
    - SubProcess: Simple tools (grep, python -c)
    - TmuxProcess: Visual debugging

    Example:
        # Auto-select based on need
        proc = Process.spawn(["aider"], interactive=True)

        # Or explicit
        proc = PTYProcess(["aider", "--no-auto-commit"])
        proc.start()
        proc.write("Write a function\\n")
        output = proc.read(timeout=5.0)
        proc.terminate()
    """

    def __init__(
        self,
        cmd: List[str],
        name: str = "process",
        max_buffer: int = 10 * 1024 * 1024,  # 10MB
    ):
        self.cmd = cmd
        self.name = name
        self.max_buffer = max_buffer
        self.running = False
        self._buffer = ""
        self._start_time = 0.0

    @abstractmethod
    def start(self) -> None:
        """Start the process."""
        pass

    @abstractmethod
    def write(self, text: str) -> None:
        """Write to process stdin."""
        pass

    @abstractmethod
    def read(self, timeout: float = 1.0) -> str:
        """Read from process stdout/stderr."""
        pass

    @abstractmethod
    def terminate(self) -> None:
        """Terminate the process."""
        pass

    @staticmethod
    def spawn(
        cmd: List[str],
        interactive: bool = False,
        visual: bool = False,
        **kwargs
    ) -> 'Process':
        """
        Factory: Auto-select process type.

        Args:
            cmd: Command to execute
            interactive: True for PTY (aider, claude-code)
            visual: True for Tmux (multi-pane debugging)

        Returns:
            Process instance (PTY, Subprocess, or Tmux)
        """
        if visual:
            return TmuxProcess(cmd, **kwargs)
        elif interactive:
            return PTYProcess(cmd, **kwargs)
        else:
            return SubProcess(cmd, **kwargs)


class PTYProcess(Process):
    """PTY-based process for interactive CLIs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.master_fd = None
        self.pid = None

    def start(self) -> None:
        """Spawn process in PTY."""
        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:  # Child
            os.execvp(self.cmd[0], self.cmd)

        self.running = True
        self._start_time = time.time()

    def write(self, text: str) -> None:
        """Write to PTY."""
        if not self.running:
            raise ProcessError("Process not running")

        os.write(self.master_fd, text.encode("utf-8"))

    def read(self, timeout: float = 1.0) -> str:
        """Read from PTY with timeout."""
        import select

        if not self.running:
            raise ProcessError("Process not running")

        deadline = time.time() + timeout
        output = ""

        while time.time() < deadline:
            ready, _, _ = select.select([self.master_fd], [], [], 0.1)

            if ready:
                try:
                    chunk = os.read(self.master_fd, 4096).decode("utf-8", errors="replace")
                    output += chunk

                    # Buffer overflow protection
                    if len(self._buffer) + len(output) > self.max_buffer:
                        self.terminate()
                        raise BufferOverflowError(
                            f"Buffer exceeded {self.max_buffer} bytes"
                        )

                except OSError:
                    break

        self._buffer += output
        return output

    def terminate(self) -> None:
        """Terminate PTY process."""
        if self.running and self.pid:
            os.kill(self.pid, 15)  # SIGTERM
            time.sleep(0.1)
            try:
                os.kill(self.pid, 9)  # SIGKILL if still alive
            except:
                pass

        if self.master_fd:
            os.close(self.master_fd)

        self.running = False


class SubProcess(Process):
    """Subprocess-based process for simple tools."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proc = None

    def start(self) -> None:
        """Spawn subprocess."""
        self.proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.running = True
        self._start_time = time.time()

    def write(self, text: str) -> None:
        """Write to stdin."""
        if not self.running or not self.proc:
            raise ProcessError("Process not running")

        self.proc.stdin.write(text.encode("utf-8"))
        self.proc.stdin.flush()

    def read(self, timeout: float = 1.0) -> str:
        """Read from stdout."""
        if not self.running or not self.proc:
            raise ProcessError("Process not running")

        try:
            stdout, stderr = self.proc.communicate(timeout=timeout)
            return stdout.decode("utf-8") + stderr.decode("utf-8")
        except subprocess.TimeoutExpired:
            return ""

    def terminate(self) -> None:
        """Terminate subprocess."""
        if self.running and self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()

        self.running = False


class TmuxProcess(Process):
    """Tmux-based process for visual debugging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_name = f"metacli-{self.name}-{os.getpid()}"

    def start(self) -> None:
        """Spawn tmux session."""
        cmd_escaped = " ".join(shlex.quote(arg) for arg in self.cmd)

        tmux_cmd = [
            "tmux",
            "new-session",
            "-d",
            "-s", self.session_name,
            cmd_escaped
        ]

        subprocess.run(tmux_cmd, check=True)
        self.running = True
        self._start_time = time.time()

    def write(self, text: str) -> None:
        """Send keys to tmux."""
        if not self.running:
            raise ProcessError("Process not running")

        subprocess.run([
            "tmux",
            "send-keys",
            "-t", self.session_name,
            text,
            "Enter"
        ])

    def read(self, timeout: float = 1.0) -> str:
        """Capture tmux pane content."""
        if not self.running:
            raise ProcessError("Process not running")

        time.sleep(timeout)  # Wait for output

        result = subprocess.run(
            ["tmux", "capture-pane", "-t", self.session_name, "-p"],
            capture_output=True,
            text=True
        )

        return result.stdout

    def terminate(self) -> None:
        """Kill tmux session."""
        if self.running:
            subprocess.run([
                "tmux",
                "kill-session",
                "-t", self.session_name
            ])

        self.running = False
```

### STEP 3: Create kernel/security.py (1 hour)

**Goal**: Command validation, shell escaping, allowlisting

**Sources**:
- `eats_core/cli_orchestrator.py` → APPROVED_COMMANDS
- `eats_core/audit.py` → Validation logic

**API**:
```python
# metacli/kernel/security.py

"""
Security validation and enforcement.

Features:
- Command allowlist
- Shell escaping
- Path validation
- Buffer limits
"""

import shlex
from typing import List
from pathlib import Path


class SecurityError(Exception):
    """Security validation failed."""
    pass


# Default allowlist - can be customized
DEFAULT_ALLOWLIST = {
    # AI coding tools
    "claude-code", "aider", "gemini", "ollama",

    # Development tools
    "python", "python3", "node", "npm", "git",

    # POSIX utilities
    "grep", "sed", "awk", "cat", "echo", "ls",
    "find", "sort", "uniq", "wc", "head", "tail",

    # Testing
    "pytest", "jest", "mocha",
}

# Dangerous commands - always blocked
BLOCKLIST = {
    "rm", "dd", "mkfs", "fdisk",
    "sudo", "su",
    "> /dev/", "curl | sh", "wget | sh",
}


class Security:
    """Security validation."""

    def __init__(self, allowlist: set = None):
        self.allowlist = allowlist or DEFAULT_ALLOWLIST

    def validate_command(self, cmd: List[str]) -> bool:
        """
        Validate command is safe to execute.

        Checks:
        1. First arg (binary name) is in allowlist
        2. Not in blocklist
        3. No shell injection patterns

        Raises:
            SecurityError if command is dangerous
        """
        if not cmd:
            raise SecurityError("Empty command")

        binary = cmd[0]

        # Check blocklist
        for blocked in BLOCKLIST:
            if blocked in " ".join(cmd):
                raise SecurityError(f"Blocked pattern: {blocked}")

        # Check allowlist
        if binary not in self.allowlist:
            raise SecurityError(
                f"Command '{binary}' not in allowlist. "
                f"Add to Security(allowlist={{...}}) if safe."
            )

        return True

    @staticmethod
    def escape_shell(text: str) -> str:
        """
        Escape text for safe shell usage.

        Uses shlex.quote() for proper escaping.
        """
        return shlex.quote(text)

    @staticmethod
    def validate_path(path: str, allowed_dirs: List[str] = None) -> bool:
        """
        Validate file path is safe.

        Checks:
        - No directory traversal (..)
        - Within allowed directories (if specified)
        """
        p = Path(path).resolve()

        # Check for traversal
        if ".." in path:
            raise SecurityError("Path traversal detected")

        # Check allowed directories
        if allowed_dirs:
            allowed = [Path(d).resolve() for d in allowed_dirs]
            if not any(p.is_relative_to(a) for a in allowed):
                raise SecurityError(f"Path {path} not in allowed directories")

        return True
```

### STEP 4: Create kernel/io.py (30 minutes)

**Goal**: I/O primitives, buffer management

```python
# metacli/kernel/io.py

"""
I/O primitives and buffer management.
"""

from typing import Optional


class BufferOverflowError(Exception):
    """Buffer size limit exceeded."""
    pass


class IOBuffer:
    """
    Buffered I/O with overflow protection.

    Features:
    - Max size enforcement
    - Efficient appending
    - Clear/reset
    """

    def __init__(self, max_size: int = 10 * 1024 * 1024):
        self.max_size = max_size
        self._buffer = ""

    def append(self, data: str) -> None:
        """Append data to buffer."""
        if len(self._buffer) + len(data) > self.max_size:
            raise BufferOverflowError(
                f"Buffer would exceed {self.max_size} bytes"
            )

        self._buffer += data

    def read(self, size: Optional[int] = None) -> str:
        """Read from buffer."""
        if size is None:
            result = self._buffer
            self._buffer = ""
            return result

        result = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return result

    def peek(self, size: Optional[int] = None) -> str:
        """Peek at buffer without removing."""
        if size is None:
            return self._buffer
        return self._buffer[:size]

    def clear(self) -> None:
        """Clear buffer."""
        self._buffer = ""

    def __len__(self) -> int:
        return len(self._buffer)

    def __str__(self) -> str:
        return self._buffer
```

### STEP 5: Create kernel/logging.py (30 minutes)

**Goal**: Standard logging setup

```python
# metacli/kernel/logging.py

"""
Logging infrastructure.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    name: str = "metacli",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure logging.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to log to

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(file_handler)

    return logger
```

### STEP 6: Create kernel/__init__.py (5 minutes)

```python
# metacli/kernel/__init__.py

"""
Kernel Layer: Execution Primitives

Provides low-level process spawning, I/O, security, and logging.

Example:
    from metacli.kernel import Process, Security

    # Validate
    Security().validate_command(["python", "-c", "print('hi')"])

    # Spawn
    proc = Process.spawn(["python", "-c", "print('hi')"])
    proc.start()
    output = proc.read()
    proc.terminate()
"""

from .process import (
    Process,
    PTYProcess,
    SubProcess,
    TmuxProcess,
    ProcessError,
    BufferOverflowError,
    TimeoutError,
)
from .security import Security, SecurityError
from .io import IOBuffer
from .logging import setup_logging

__all__ = [
    # Process
    "Process",
    "PTYProcess",
    "SubProcess",
    "TmuxProcess",
    "ProcessError",
    "BufferOverflowError",
    "TimeoutError",

    # Security
    "Security",
    "SecurityError",

    # I/O
    "IOBuffer",

    # Logging
    "setup_logging",
]
```

### STEP 7: Create Test (30 minutes)

```python
# tests/test_kernel.py

"""Test kernel layer."""

import pytest
from metacli.kernel import Process, Security, IOBuffer


def test_subprocess_spawn():
    """Test simple subprocess execution."""
    proc = Process.spawn(["echo", "hello"], interactive=False)
    proc.start()
    output = proc.read(timeout=1.0)
    proc.terminate()

    assert "hello" in output


def test_security_allowlist():
    """Test command allowlist."""
    security = Security()

    # Allowed
    assert security.validate_command(["python", "-c", "print('hi')"])

    # Blocked
    with pytest.raises(SecurityError):
        security.validate_command(["rm", "-rf", "/"])


def test_buffer_overflow():
    """Test buffer overflow protection."""
    buffer = IOBuffer(max_size=100)

    # OK
    buffer.append("a" * 50)
    buffer.append("b" * 50)

    # Overflow
    with pytest.raises(BufferOverflowError):
        buffer.append("c" * 1)


def test_pty_process():
    """Test PTY process execution."""
    proc = Process.spawn(["python", "-c", "print('test')"], interactive=True)
    proc.start()

    # Give it time to execute
    output = proc.read(timeout=2.0)
    proc.terminate()

    assert "test" in output
```

### STEP 8: Create Example (15 minutes)

```python
# examples/01_kernel_basics.py

"""
Example: Using the kernel layer directly.

Demonstrates raw process spawning, security validation, and I/O.
"""

from metacli.kernel import Process, Security, setup_logging


def main():
    # Setup logging
    logger = setup_logging("kernel-demo", level=logging.INFO)

    # Security validation
    security = Security()

    cmd = ["python", "-c", "print('Hello from kernel!')"]

    logger.info(f"Validating command: {cmd}")
    security.validate_command(cmd)

    # Spawn process
    logger.info("Spawning process...")
    proc = Process.spawn(cmd, interactive=False)

    proc.start()
    logger.info("Process started")

    # Read output
    output = proc.read(timeout=2.0)
    logger.info(f"Output: {output}")

    # Terminate
    proc.terminate()
    logger.info("Process terminated")


if __name__ == "__main__":
    import logging
    main()
```

---

## ✅ VALIDATION CRITERIA

Before moving to Phase 2, ensure:

1. **All tests pass**
   ```bash
   pytest tests/test_kernel.py -v
   ```

2. **Example runs successfully**
   ```bash
   python examples/01_kernel_basics.py
   ```

3. **Zero dependencies on old code**
   ```bash
   # Kernel should NOT import from eats_core or eats
   grep -r "from eats" metacli/kernel/
   # Should return nothing!
   ```

4. **Documentation complete**
   - API docstrings ✓
   - Usage examples ✓
   - Type hints ✓

---

## 📊 IMMEDIATE IMPACT

### Code Reduction
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Process implementations | 3 files | 1 file | **-67%** |
| Lines for process handling | 1,417 | 400 | **-72%** |
| Duplication | High | Zero | **-100%** |

### Clarity Improvement
- ✅ **One Process class** (not 3)
- ✅ **Clear API** (spawn, start, read, write, terminate)
- ✅ **No evolution baggage** (just execution)
- ✅ **Testable in isolation** (no dependencies)

---

## 🚀 NEXT ACTIONS

### Option A: Continue to Phase 2 (Core Layer)
Once kernel works, build core orchestration:
- `metacli/core/sequence.py` using `kernel.Process`
- `metacli/core/persistence.py`
- Delete `eats/` directory

### Option B: Perfect the Kernel
- Add more tests
- Optimize PTY I/O
- Add async support
- Documentation polish

### Option C: Both (Recommended)
- Ship kernel (1,500 lines working)
- Start core layer in parallel
- Delete `eats/` once core uses kernel

---

## 💡 WHY THIS WORKS

1. **Kernel is self-contained** - No dependencies on rest of codebase
2. **Proves refactor viability** - Working code, not just plans
3. **Immediate value** - Can use kernel standalone
4. **Unlocks everything else** - Core layer builds on clean foundation
5. **Reversible** - Old code still works, new kernel is additive

---

**READY TO IMPLEMENT?**

Say the word and I'll:
1. Create the directory structure
2. Extract `kernel/process.py` from existing code
3. Create `kernel/security.py`
4. Write tests
5. Run validation

**Or**: Review this plan first, suggest modifications, then execute.

**Your choice!** 🚀
