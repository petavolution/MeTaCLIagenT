"""
MetaCLI Kernel Layer - Execution Primitives

The foundation layer providing process spawning, I/O, and security.

Components:
- Process: Universal process abstraction (PTY, Subprocess, Tmux)
- Security: Command validation and shell escaping
- IOBuffer: Buffer management with overflow protection
- Logging: Structured logging setup

Example:
    from metacli.kernel import Process, Security

    # Validate command
    security = Security()
    security.validate_command(["python", "-c", "print('hello')"])

    # Spawn and execute
    proc = Process.spawn(["python", "-c", "print('hello')"])
    proc.start()
    output = proc.read(timeout=2.0)
    proc.terminate()

    print(output)  # "hello"
"""

# Process classes
from .process import (
    Process,
    PTYProcess,
    SubProcess,
    TmuxProcess,
    ProcessError,
    BufferOverflowError,
    TimeoutError,
)

# Security
from .security import (
    Security,
    SecurityError,
    DEFAULT_ALLOWLIST,
    BLOCKLIST_PATTERNS,
)

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
    "DEFAULT_ALLOWLIST",
    "BLOCKLIST_PATTERNS",
]

__version__ = "2.0.0-alpha"
