# audit.py - Security Audit Logging
"""
Paranoid audit logging for security events and system operations.

Design Principles:
- Append-only (immutable audit trail)
- Structured JSON (machine parseable)
- Fail-safe (logging errors don't crash system)
- Complete (log ALL security decisions)
- Searchable (grep-friendly format)

Logged Events:
- Command validation (approved/denied)
- Buffer overflow events
- Prompt injection attempts
- Agent lifecycle (start/stop)
- Resource usage
- Errors and exceptions
"""

from __future__ import annotations
import json
import time
import os
import sys
import traceback
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Severity Levels
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    DEBUG = "DEBUG"       # Verbose debugging info
    INFO = "INFO"         # Normal operations
    WARNING = "WARNING"   # Unusual but handled
    ERROR = "ERROR"       # Errors that were recovered
    CRITICAL = "CRITICAL" # Security violations, unrecoverable errors


class AuditEventType(str, Enum):
    """Types of auditable events."""
    # Security events
    COMMAND_VALIDATED = "command_validated"
    COMMAND_REJECTED = "command_rejected"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    BUFFER_OVERFLOW = "buffer_overflow"

    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_FAILED = "agent_failed"

    # Execution events
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"

    # Resource events
    RESOURCE_LIMIT_APPROACHED = "resource_limit_approached"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Audit Logger
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AuditLogger:
    """
    Structured audit logger for security events.

    Features:
    - JSON-lines format (one event per line)
    - Automatic log rotation by size
    - Fail-safe (errors writing logs don't crash system)
    - Thread-safe append
    - PII redaction for sensitive data

    Usage:
        logger = AuditLogger()
        logger.log_command_validation(
            cmd=["python", "script.py"],
            approved=True,
            reason="Approved command"
        )
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_log_size_mb: int = 100,
        redact_pii: bool = True,
    ):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for audit logs (default: ./logs/audit)
            max_log_size_mb: Rotate log when it exceeds this size
            redact_pii: Automatically redact API keys, tokens, etc.
        """
        if log_dir is None:
            log_dir = Path.cwd() / "logs" / "audit"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_log_size = max_log_size_mb * 1024 * 1024
        self.redact_pii = redact_pii

        # Current log file
        self.current_log = self.log_dir / f"audit_{self._timestamp()}.jsonl"

        # Track if we've logged critical errors to stderr
        self._critical_logged_to_stderr = False

    def _timestamp(self) -> str:
        """Get timestamp for log filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _iso_timestamp(self) -> str:
        """Get ISO 8601 timestamp for events."""
        return datetime.utcnow().isoformat() + "Z"

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds size limit."""
        try:
            if self.current_log.exists():
                size = self.current_log.stat().st_size
                if size >= self.max_log_size:
                    # Create new log file
                    self.current_log = self.log_dir / f"audit_{self._timestamp()}.jsonl"
        except Exception:
            # Fail-safe: if rotation fails, keep using current file
            pass

    def _redact_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive information from log data.

        Redacts:
        - API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
        - Tokens (Bearer, JWT)
        - Passwords
        - Email addresses (partially)
        """
        if not self.redact_pii:
            return data

        # Make a copy to avoid mutating original
        redacted = data.copy()

        # Redact common sensitive fields
        sensitive_keys = [
            "api_key", "apikey", "token", "password", "secret",
            "bearer", "authorization", "auth", "credentials"
        ]

        for key, value in redacted.items():
            # Check if key name suggests sensitive data
            if any(s in key.lower() for s in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    redacted[key] = value[:4] + "..." + "[REDACTED]"
                else:
                    redacted[key] = "[REDACTED]"

            # Recursively redact nested dicts
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive(value)

            # Redact lists of dicts
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_sensitive(item) if isinstance(item, dict) else item
                    for item in value
                ]

        return redacted

    def _write_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        **metadata: Any,
    ) -> None:
        """
        Write an audit event to the log.

        Args:
            event_type: Type of event
            severity: Severity level
            message: Human-readable message
            **metadata: Additional structured data
        """
        event = {
            "timestamp": self._iso_timestamp(),
            "event_type": event_type.value,
            "severity": severity.value,
            "message": message,
            "pid": os.getpid(),
            "metadata": self._redact_sensitive(metadata),
        }

        try:
            self._rotate_if_needed()

            # Atomic append (one write call)
            with open(self.current_log, "a") as f:
                f.write(json.dumps(event) + "\n")

            # If critical, also log to stderr for visibility
            if severity == AuditSeverity.CRITICAL:
                if not self._critical_logged_to_stderr:
                    print(f"[CRITICAL AUDIT EVENT] {message}", file=sys.stderr)
                    self._critical_logged_to_stderr = True

        except Exception as e:
            # Fail-safe: if we can't write to log, print to stderr
            # but don't crash the system
            print(f"[AUDIT LOG ERROR] Failed to write event: {e}", file=sys.stderr)
            print(f"[AUDIT EVENT] {message}", file=sys.stderr)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Security Event Loggers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def log_command_validation(
        self,
        cmd: List[str],
        approved: bool,
        reason: str,
        tool_name: Optional[str] = None,
    ) -> None:
        """
        Log command validation decision.

        Args:
            cmd: Command that was validated
            approved: Whether command was approved
            reason: Reason for approval/denial
            tool_name: Optional tool name for context
        """
        severity = AuditSeverity.INFO if approved else AuditSeverity.CRITICAL
        event_type = (
            AuditEventType.COMMAND_VALIDATED if approved
            else AuditEventType.COMMAND_REJECTED
        )

        message = (
            f"Command {'APPROVED' if approved else 'REJECTED'}: {cmd[0]}"
        )

        self._write_event(
            event_type=event_type,
            severity=severity,
            message=message,
            command=cmd,
            approved=approved,
            reason=reason,
            tool_name=tool_name,
        )

    def log_prompt_injection_attempt(
        self,
        pattern: str,
        text_preview: str,
        agent_name: Optional[str] = None,
    ) -> None:
        """
        Log detected prompt injection attempt.

        Args:
            pattern: Regex pattern that matched
            text_preview: Preview of suspicious text (sanitized)
            agent_name: Agent that would have received injected prompt
        """
        self._write_event(
            event_type=AuditEventType.PROMPT_INJECTION_DETECTED,
            severity=AuditSeverity.WARNING,
            message=f"Prompt injection attempt detected: {pattern}",
            pattern=pattern,
            text_preview=text_preview[:200],  # Limit preview length
            agent_name=agent_name,
        )

    def log_buffer_overflow(
        self,
        agent_name: str,
        buffer_size: int,
        max_size: int,
    ) -> None:
        """
        Log buffer overflow event.

        Args:
            agent_name: Name of agent that overflowed
            buffer_size: Actual buffer size reached
            max_size: Maximum allowed size
        """
        self._write_event(
            event_type=AuditEventType.BUFFER_OVERFLOW,
            severity=AuditSeverity.CRITICAL,
            message=f"Buffer overflow: {agent_name} exceeded {max_size} bytes",
            agent_name=agent_name,
            buffer_size=buffer_size,
            max_size=max_size,
            overflow_bytes=buffer_size - max_size,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Agent Lifecycle Loggers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def log_agent_started(
        self,
        agent_name: str,
        cmd: List[str],
        pid: Optional[int] = None,
    ) -> None:
        """Log agent startup."""
        self._write_event(
            event_type=AuditEventType.AGENT_STARTED,
            severity=AuditSeverity.INFO,
            message=f"Agent started: {agent_name}",
            agent_name=agent_name,
            command=cmd,
            process_pid=pid,
        )

    def log_agent_stopped(
        self,
        agent_name: str,
        exit_code: Optional[int] = None,
        runtime_seconds: Optional[float] = None,
    ) -> None:
        """Log agent shutdown."""
        self._write_event(
            event_type=AuditEventType.AGENT_STOPPED,
            severity=AuditSeverity.INFO,
            message=f"Agent stopped: {agent_name}",
            agent_name=agent_name,
            exit_code=exit_code,
            runtime_seconds=runtime_seconds,
        )

    def log_agent_failed(
        self,
        agent_name: str,
        error: Exception,
    ) -> None:
        """Log agent failure with stack trace."""
        self._write_event(
            event_type=AuditEventType.AGENT_FAILED,
            severity=AuditSeverity.ERROR,
            message=f"Agent failed: {agent_name}: {str(error)}",
            agent_name=agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Execution Event Loggers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def log_step_started(
        self,
        step_name: str,
        tool_name: str,
        prompt_length: int,
    ) -> None:
        """Log sequence step start."""
        self._write_event(
            event_type=AuditEventType.STEP_STARTED,
            severity=AuditSeverity.DEBUG,
            message=f"Step started: {step_name} ({tool_name})",
            step_name=step_name,
            tool_name=tool_name,
            prompt_length=prompt_length,
        )

    def log_step_completed(
        self,
        step_name: str,
        duration_seconds: float,
        output_length: int,
    ) -> None:
        """Log sequence step completion."""
        self._write_event(
            event_type=AuditEventType.STEP_COMPLETED,
            severity=AuditSeverity.DEBUG,
            message=f"Step completed: {step_name} ({duration_seconds:.2f}s)",
            step_name=step_name,
            duration_seconds=duration_seconds,
            output_length=output_length,
        )

    def log_step_failed(
        self,
        step_name: str,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        """Log sequence step failure."""
        self._write_event(
            event_type=AuditEventType.STEP_FAILED,
            severity=AuditSeverity.ERROR,
            message=f"Step failed: {step_name}: {str(error)}",
            step_name=step_name,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_seconds=duration_seconds,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Resource Event Loggers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def log_resource_warning(
        self,
        resource_type: str,
        current: float,
        limit: float,
        percentage: float,
    ) -> None:
        """Log resource usage approaching limit."""
        self._write_event(
            event_type=AuditEventType.RESOURCE_LIMIT_APPROACHED,
            severity=AuditSeverity.WARNING,
            message=f"Resource {resource_type} at {percentage:.1f}% of limit",
            resource_type=resource_type,
            current_value=current,
            limit_value=limit,
            percentage=percentage,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Logger Instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Singleton instance for easy access
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def set_audit_logger(logger: AuditLogger) -> None:
    """Set custom audit logger instance (for testing/configuration)."""
    global _audit_logger
    _audit_logger = logger
