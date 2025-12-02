"""
Security - Command Validation and Shell Escaping

Provides security enforcement for process execution:
- Command allowlisting
- Shell injection prevention
- Path validation
- Buffer limits

Example:
    from metacli.kernel import Security

    security = Security()

    # Validate command
    security.validate_command(["python", "-c", "print('hi')"])  # OK
    security.validate_command(["rm", "-rf", "/"])  # Raises SecurityError

    # Escape for shell
    safe = Security.escape_shell("user input with spaces")
"""

import shlex
from typing import List, Set, Optional
from pathlib import Path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SecurityError(Exception):
    """Security validation failed."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Default Allowlist and Blocklist
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT_ALLOWLIST: Set[str] = {
    # AI coding tools
    "claude-code", "aider", "gemini", "ollama", "gpt",

    # Programming languages
    "python", "python3", "node", "npm", "npx",
    "ruby", "perl", "java", "javac",

    # Development tools
    "git", "docker", "make", "cmake",

    # POSIX utilities (safe for read operations)
    "grep", "sed", "awk", "cat", "echo",
    "ls", "find", "sort", "uniq", "wc",
    "head", "tail", "cut", "tr", "diff",

    # Testing
    "pytest", "jest", "mocha", "cargo", "go",
}

# Dangerous patterns - always blocked
BLOCKLIST_PATTERNS: Set[str] = {
    # Destructive commands
    "rm -rf /",
    "mkfs",
    "dd if=",
    "fdisk",

    # Privilege escalation
    "sudo",
    "su ",

    # Remote code execution
    "curl | sh",
    "wget | sh",
    "curl | bash",
    "wget | bash",

    # System modification
    "> /dev/",
    "chmod 777",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Security Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Security:
    """
    Security validation and enforcement.

    Provides:
    - Command allowlisting (configurable)
    - Blocklist pattern detection
    - Shell escaping
    - Path validation
    """

    def __init__(
        self,
        allowlist: Optional[Set[str]] = None,
        blocklist_patterns: Optional[Set[str]] = None,
        strict: bool = True,
    ):
        """
        Initialize security validator.

        Args:
            allowlist: Set of allowed binary names (default: DEFAULT_ALLOWLIST)
            blocklist_patterns: Dangerous patterns to block (default: BLOCKLIST_PATTERNS)
            strict: If True, reject commands not in allowlist

        Example:
            # Default (strict)
            security = Security()

            # Custom allowlist
            security = Security(allowlist={"python", "node", "custom-tool"})

            # Non-strict (allow all, just check blocklist)
            security = Security(strict=False)
        """
        self.allowlist = allowlist if allowlist is not None else DEFAULT_ALLOWLIST.copy()
        self.blocklist_patterns = blocklist_patterns if blocklist_patterns is not None else BLOCKLIST_PATTERNS.copy()
        self.strict = strict

    def validate_command(self, cmd: List[str]) -> bool:
        """
        Validate command is safe to execute.

        Checks:
        1. Command is not empty
        2. No blocklist patterns in command
        3. Binary is in allowlist (if strict mode)

        Args:
            cmd: Command and arguments to validate

        Returns:
            True if valid

        Raises:
            SecurityError: If command is dangerous or not allowed

        Example:
            security = Security()
            security.validate_command(["python", "-c", "print('hi')"])  # OK
            security.validate_command(["rm", "-rf", "/"])  # Raises SecurityError
        """
        if not cmd:
            raise SecurityError("Empty command")

        binary = cmd[0]
        full_command = " ".join(cmd)

        # Check blocklist patterns
        for pattern in self.blocklist_patterns:
            if pattern in full_command:
                raise SecurityError(
                    f"Dangerous pattern detected: '{pattern}' in command '{full_command}'"
                )

        # Check allowlist (if strict)
        if self.strict and binary not in self.allowlist:
            raise SecurityError(
                f"Command '{binary}' not in allowlist. "
                f"Either add to allowlist or use Security(strict=False)."
            )

        return True

    def add_to_allowlist(self, *binaries: str) -> None:
        """
        Add binaries to allowlist.

        Example:
            security = Security()
            security.add_to_allowlist("custom-tool", "another-tool")
        """
        self.allowlist.update(binaries)

    def add_to_blocklist(self, *patterns: str) -> None:
        """
        Add dangerous patterns to blocklist.

        Example:
            security = Security()
            security.add_to_blocklist("dangerous-pattern", "another-bad-thing")
        """
        self.blocklist_patterns.update(patterns)

    @staticmethod
    def escape_shell(text: str) -> str:
        """
        Escape text for safe shell usage.

        Uses shlex.quote() for proper POSIX shell escaping.

        Args:
            text: Text to escape

        Returns:
            Safely escaped text

        Example:
            safe = Security.escape_shell("user input with spaces")
            # Returns: 'user input with spaces' (with quotes)
        """
        return shlex.quote(text)

    @staticmethod
    def validate_path(
        path: str,
        allowed_dirs: Optional[List[str]] = None,
        allow_traversal: bool = False,
    ) -> bool:
        """
        Validate file path is safe.

        Checks:
        - No directory traversal (unless explicitly allowed)
        - Within allowed directories (if specified)

        Args:
            path: Path to validate
            allowed_dirs: Optional list of allowed parent directories
            allow_traversal: If True, allow .. in paths

        Returns:
            True if valid

        Raises:
            SecurityError: If path is dangerous

        Example:
            Security.validate_path("/tmp/file.txt", allowed_dirs=["/tmp"])  # OK
            Security.validate_path("../etc/passwd")  # Raises SecurityError
        """
        # Check for traversal
        if not allow_traversal and ".." in path:
            raise SecurityError(f"Directory traversal detected in path: {path}")

        # Check allowed directories
        if allowed_dirs:
            p = Path(path).resolve()
            allowed = [Path(d).resolve() for d in allowed_dirs]

            # Check if path is within any allowed directory
            if not any(
                str(p).startswith(str(allowed_dir)) or p == allowed_dir
                for allowed_dir in allowed
            ):
                raise SecurityError(
                    f"Path '{path}' not within allowed directories: {allowed_dirs}"
                )

        return True

    def is_safe_command(self, cmd: List[str]) -> bool:
        """
        Check if command is safe (non-raising version).

        Args:
            cmd: Command to check

        Returns:
            True if safe, False if dangerous
        """
        try:
            self.validate_command(cmd)
            return True
        except SecurityError:
            return False
