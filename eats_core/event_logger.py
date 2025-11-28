# event_logger.py - JSONL Event Logging for Headless Execution
"""
JSONL Event Logger for MeTaCLIagenT Headless Mode.

Provides machine-parseable event streaming for:
- Real-time monitoring of workflow execution
- Integration with external monitoring systems
- Python wrapper parsing
- CI/CD pipeline logging

Event Format:
    Every event is a single-line JSON object with:
    - type: Event type (session_start, tool_complete, etc.)
    - timestamp: Unix timestamp (float)
    - Additional fields specific to event type

Example JSONL Output:
    {"type":"session_start","session_id":"abc123","timestamp":1701234567.89}
    {"type":"tool_start","tool":"claude-code","step":1,"timestamp":1701234568.12}
    {"type":"tool_complete","tool":"claude-code","status":"completed","duration":12.34}
    {"type":"session_complete","session_id":"abc123","status":"completed"}

Usage:
    # Log to stdout
    logger = JSONLEventLogger()
    logger.emit({"type": "session_start", "session_id": "abc123"})

    # Log to file
    with open("events.jsonl", "w") as f:
        logger = JSONLEventLogger(output_stream=f)
        logger.emit({"type": "tool_complete", "tool": "aider"})

    # Context manager (auto-flush)
    with JSONLEventLogger.to_file("events.jsonl") as logger:
        logger.session_start("abc123")
        logger.tool_complete("aider", "completed", 12.34)
"""

from __future__ import annotations
import sys
import json
import time
from typing import Dict, Any, Optional, TextIO
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventType(Enum):
    """Types of JSONL events."""

    # Session events
    SESSION_START = "session_start"
    SESSION_COMPLETE = "session_complete"
    SESSION_RESUME = "session_resume"
    SESSION_ERROR = "session_error"

    # Tool events
    TOOL_START = "tool_start"
    TOOL_OUTPUT = "tool_output"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"

    # Step events (for playbooks)
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_SKIP = "step_skip"
    STEP_ERROR = "step_error"

    # Checkpoint events
    CHECKPOINT_SAVE = "checkpoint_save"
    CHECKPOINT_LOAD = "checkpoint_load"

    # Generic events
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class Event:
    """
    Structured event for JSONL logging.

    All events have type and timestamp. Additional fields
    can be added via the `data` dict or as direct attributes.
    """
    type: EventType
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            **self.data,
        }

    def to_json(self) -> str:
        """Convert to JSON string (single line)."""
        return json.dumps(self.to_dict(), separators=(',', ':'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JSONL Event Logger
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class JSONLEventLogger:
    """
    JSONL event logger for headless execution.

    Emits newline-delimited JSON events to stdout or file,
    enabling machine parsing and real-time monitoring.

    Features:
    - Automatic timestamp injection
    - Type-safe event emission
    - Buffering control (auto-flush by default)
    - Context manager support
    - Convenience methods for common events
    """

    def __init__(
        self,
        output_stream: Optional[TextIO] = None,
        auto_flush: bool = True,
        pretty: bool = False,
    ):
        """
        Initialize JSONL event logger.

        Args:
            output_stream: Stream to write to (default: stdout)
            auto_flush: Flush after every event (default: True)
            pretty: Pretty-print JSON (default: False, for JSONL compliance)
        """
        self.stream = output_stream or sys.stdout
        self.auto_flush = auto_flush
        self.pretty = pretty
        self._event_count = 0

    # ─────────────────────────────────────────────────────
    # Core Emission
    # ─────────────────────────────────────────────────────

    def emit(self, event: Dict[str, Any]) -> None:
        """
        Emit a single JSONL event.

        Args:
            event: Event dictionary with 'type' field required
        """
        # Ensure timestamp
        if "timestamp" not in event:
            event["timestamp"] = time.time()

        # Serialize to JSON
        if self.pretty:
            event_json = json.dumps(event, indent=2)
        else:
            event_json = json.dumps(event, separators=(',', ':'))

        # Write to stream
        self.stream.write(event_json + "\n")

        if self.auto_flush:
            self.stream.flush()

        self._event_count += 1

    def emit_event(self, event: Event) -> None:
        """
        Emit a structured Event object.

        Args:
            event: Event instance
        """
        self.emit(event.to_dict())

    # ─────────────────────────────────────────────────────
    # Convenience Methods - Session Events
    # ─────────────────────────────────────────────────────

    def session_start(
        self,
        session_id: str,
        workflow: str = "",
        variables: Optional[Dict[str, str]] = None,
    ) -> None:
        """Emit session_start event."""
        self.emit({
            "type": EventType.SESSION_START.value,
            "session_id": session_id,
            "workflow": workflow,
            "variables": variables or {},
        })

    def session_complete(
        self,
        session_id: str,
        status: str,
        total_duration: float = 0.0,
        summary: str = "",
    ) -> None:
        """Emit session_complete event."""
        self.emit({
            "type": EventType.SESSION_COMPLETE.value,
            "session_id": session_id,
            "status": status,
            "total_duration": total_duration,
            "summary": summary,
        })

    def session_resume(
        self,
        session_id: str,
        from_step: int,
    ) -> None:
        """Emit session_resume event."""
        self.emit({
            "type": EventType.SESSION_RESUME.value,
            "session_id": session_id,
            "from_step": from_step,
        })

    def session_error(
        self,
        session_id: str,
        error: str,
        traceback: str = "",
    ) -> None:
        """Emit session_error event."""
        self.emit({
            "type": EventType.SESSION_ERROR.value,
            "session_id": session_id,
            "error": error,
            "traceback": traceback,
        })

    # ─────────────────────────────────────────────────────
    # Convenience Methods - Tool Events
    # ─────────────────────────────────────────────────────

    def tool_start(
        self,
        tool_name: str,
        step: int = 0,
        input_text: str = "",
    ) -> None:
        """Emit tool_start event."""
        self.emit({
            "type": EventType.TOOL_START.value,
            "tool": tool_name,
            "step": step,
            "input_preview": input_text[:100] if input_text else "",
        })

    def tool_output(
        self,
        tool_name: str,
        output: str,
        output_type: str = "stdout",
    ) -> None:
        """Emit tool_output event."""
        self.emit({
            "type": EventType.TOOL_OUTPUT.value,
            "tool": tool_name,
            "output_type": output_type,
            "output": output,
        })

    def tool_complete(
        self,
        tool_name: str,
        status: str,
        duration: float,
        exit_code: int = 0,
    ) -> None:
        """Emit tool_complete event."""
        self.emit({
            "type": EventType.TOOL_COMPLETE.value,
            "tool": tool_name,
            "status": status,
            "duration": duration,
            "exit_code": exit_code,
        })

    def tool_error(
        self,
        tool_name: str,
        error: str,
        exit_code: int = 1,
    ) -> None:
        """Emit tool_error event."""
        self.emit({
            "type": EventType.TOOL_ERROR.value,
            "tool": tool_name,
            "error": error,
            "exit_code": exit_code,
        })

    # ─────────────────────────────────────────────────────
    # Convenience Methods - Step Events (Playbooks)
    # ─────────────────────────────────────────────────────

    def step_start(
        self,
        session_id: str,
        step: int,
        total_steps: int,
        name: str,
    ) -> None:
        """Emit step_start event."""
        self.emit({
            "type": EventType.STEP_START.value,
            "session_id": session_id,
            "step": step,
            "total_steps": total_steps,
            "name": name,
        })

    def step_complete(
        self,
        step: int,
        status: str,
        duration: float = 0.0,
    ) -> None:
        """Emit step_complete event."""
        self.emit({
            "type": EventType.STEP_COMPLETE.value,
            "step": step,
            "status": status,
            "duration": duration,
        })

    def step_skip(
        self,
        step: int,
        reason: str,
    ) -> None:
        """Emit step_skip event."""
        self.emit({
            "type": EventType.STEP_SKIP.value,
            "step": step,
            "reason": reason,
        })

    # ─────────────────────────────────────────────────────
    # Convenience Methods - Checkpoint Events
    # ─────────────────────────────────────────────────────

    def checkpoint_save(
        self,
        session_id: str,
        step: int,
    ) -> None:
        """Emit checkpoint_save event."""
        self.emit({
            "type": EventType.CHECKPOINT_SAVE.value,
            "session_id": session_id,
            "step": step,
        })

    def checkpoint_load(
        self,
        session_id: str,
        step: int,
    ) -> None:
        """Emit checkpoint_load event."""
        self.emit({
            "type": EventType.CHECKPOINT_LOAD.value,
            "session_id": session_id,
            "step": step,
        })

    # ─────────────────────────────────────────────────────
    # Convenience Methods - Generic Events
    # ─────────────────────────────────────────────────────

    def info(self, message: str, **kwargs: Any) -> None:
        """Emit info event."""
        self.emit({
            "type": EventType.INFO.value,
            "message": message,
            **kwargs,
        })

    def warning(self, message: str, **kwargs: Any) -> None:
        """Emit warning event."""
        self.emit({
            "type": EventType.WARNING.value,
            "message": message,
            **kwargs,
        })

    def error(self, message: str, **kwargs: Any) -> None:
        """Emit error event."""
        self.emit({
            "type": EventType.ERROR.value,
            "message": message,
            **kwargs,
        })

    def debug(self, message: str, **kwargs: Any) -> None:
        """Emit debug event."""
        self.emit({
            "type": EventType.DEBUG.value,
            "message": message,
            **kwargs,
        })

    # ─────────────────────────────────────────────────────
    # Context Manager & Utilities
    # ─────────────────────────────────────────────────────

    def flush(self) -> None:
        """Flush output stream."""
        self.stream.flush()

    def close(self) -> None:
        """Close output stream if it's not stdout/stderr."""
        if self.stream not in (sys.stdout, sys.stderr):
            self.stream.close()

    @staticmethod
    @contextmanager
    def to_file(filepath: str, **kwargs):
        """
        Context manager for file-based logging.

        Usage:
            with JSONLEventLogger.to_file("events.jsonl") as logger:
                logger.session_start("abc123")
                logger.tool_complete("aider", "completed", 12.34)

        Args:
            filepath: Path to JSONL file
            **kwargs: Additional arguments for JSONLEventLogger
        """
        with open(filepath, "w") as f:
            logger = JSONLEventLogger(output_stream=f, **kwargs)
            try:
                yield logger
            finally:
                logger.flush()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.flush()
        self.close()
        return False

    @property
    def event_count(self) -> int:
        """Get number of events emitted."""
        return self._event_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Null Logger (for disabling logging)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NullEventLogger(JSONLEventLogger):
    """
    Null event logger that does nothing.

    Useful for disabling logging without changing code:
        logger = NullEventLogger()
        logger.session_start("abc123")  # No-op
    """

    def emit(self, event: Dict[str, Any]) -> None:
        """No-op emit."""
        pass

    def flush(self) -> None:
        """No-op flush."""
        pass

    def close(self) -> None:
        """No-op close."""
        pass
