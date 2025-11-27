# logging.py - Centralized Logging for EATS Core
"""
Unified logging system with:
- Console output
- File output (debug-log.txt)
- Structured logging with levels
- Error tracking
- Performance timing
"""

from __future__ import annotations
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps

# Default log file path
DEFAULT_LOG_FILE = Path("debug-log.txt")


# ============================================================
# Log Formatter
# ============================================================

class EATSFormatter(logging.Formatter):
    """Custom formatter with colors for console, plain for file."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        level = record.levelname
        name = record.name.split(".")[-1] if "." in record.name else record.name
        message = record.getMessage()

        # Add exception info if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        if self.use_colors:
            color = self.COLORS.get(level, "")
            return f"{timestamp} {color}[{level:8}]{self.RESET} {name}: {message}"
        else:
            return f"{timestamp} [{level:8}] {name}: {message}"


# ============================================================
# Logger Setup
# ============================================================

_loggers: Dict[str, logging.Logger] = {}
_file_handler: Optional[logging.FileHandler] = None
_console_handler: Optional[logging.StreamHandler] = None
_initialized = False


def init_logging(
    log_file: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """
    Initialize the logging system.

    Args:
        log_file: Path to log file (default: debug-log.txt)
        console_level: Minimum level for console output
        file_level: Minimum level for file output
        enable_console: Whether to output to console
        enable_file: Whether to output to file
    """
    global _file_handler, _console_handler, _initialized

    if _initialized:
        return

    log_file = log_file or DEFAULT_LOG_FILE

    # Console handler
    if enable_console:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setLevel(console_level)
        _console_handler.setFormatter(EATSFormatter(use_colors=True))

    # File handler
    if enable_file:
        _file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        _file_handler.setLevel(file_level)
        _file_handler.setFormatter(EATSFormatter(use_colors=False))

        # Write startup marker
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"EATS Core - Session started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured logger instance
    """
    if not _initialized:
        init_logging()

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(f"eats.{name}")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    logger.handlers = []

    # Add handlers
    if _console_handler:
        logger.addHandler(_console_handler)
    if _file_handler:
        logger.addHandler(_file_handler)

    # Don't propagate to root logger
    logger.propagate = False

    _loggers[name] = logger
    return logger


# ============================================================
# Convenience Functions
# ============================================================

def debug(msg: str, **kwargs) -> None:
    """Log debug message."""
    get_logger("main").debug(msg, **kwargs)


def info(msg: str, **kwargs) -> None:
    """Log info message."""
    get_logger("main").info(msg, **kwargs)


def warning(msg: str, **kwargs) -> None:
    """Log warning message."""
    get_logger("main").warning(msg, **kwargs)


def error(msg: str, exc_info: bool = False, **kwargs) -> None:
    """Log error message."""
    get_logger("main").error(msg, exc_info=exc_info, **kwargs)


def critical(msg: str, exc_info: bool = True, **kwargs) -> None:
    """Log critical message."""
    get_logger("main").critical(msg, exc_info=exc_info, **kwargs)


def exception(msg: str, **kwargs) -> None:
    """Log exception with traceback."""
    get_logger("main").exception(msg, **kwargs)


# ============================================================
# Error Tracking
# ============================================================

@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    timestamp: float
    module: str
    error_type: str
    message: str
    traceback: str
    context: Dict[str, Any] = field(default_factory=dict)


class ErrorTracker:
    """
    Track errors across the system.

    Usage:
        tracker = ErrorTracker()

        try:
            risky_operation()
        except Exception as e:
            tracker.record(e, module="agent", context={"agent_id": "123"})
    """

    def __init__(self, max_errors: int = 1000):
        self._errors: list[ErrorRecord] = []
        self._max_errors = max_errors
        self._logger = get_logger("errors")

    def record(
        self,
        error: Exception,
        module: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorRecord:
        """Record an error."""
        record = ErrorRecord(
            timestamp=time.time(),
            module=module,
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context or {},
        )

        self._errors.append(record)

        # Trim if needed
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]

        # Log it
        self._logger.error(
            f"[{module}] {record.error_type}: {record.message}",
            exc_info=True,
        )

        return record

    def get_errors(
        self,
        module: Optional[str] = None,
        error_type: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> list[ErrorRecord]:
        """Get recorded errors with optional filtering."""
        errors = self._errors

        if module:
            errors = [e for e in errors if e.module == module]
        if error_type:
            errors = [e for e in errors if e.error_type == error_type]
        if since:
            errors = [e for e in errors if e.timestamp >= since]

        return errors[-limit:]

    def clear(self) -> None:
        """Clear all recorded errors."""
        self._errors.clear()

    @property
    def count(self) -> int:
        """Total error count."""
        return len(self._errors)

    def summary(self) -> Dict[str, Any]:
        """Get error summary statistics."""
        by_module: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for e in self._errors:
            by_module[e.module] = by_module.get(e.module, 0) + 1
            by_type[e.error_type] = by_type.get(e.error_type, 0) + 1

        return {
            "total": len(self._errors),
            "by_module": by_module,
            "by_type": by_type,
        }


# Global error tracker
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker."""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def track_error(
    error: Exception,
    module: str = "unknown",
    context: Optional[Dict] = None,
) -> ErrorRecord:
    """Track an error globally."""
    return get_error_tracker().record(error, module, context)


# ============================================================
# Performance Timing
# ============================================================

@contextmanager
def timer(name: str, log_level: int = logging.DEBUG):
    """
    Context manager for timing code blocks.

    Usage:
        with timer("database_query"):
            result = db.query(...)
    """
    logger = get_logger("timer")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        logger.log(log_level, f"{name}: {elapsed:.2f}ms")


def timed(name: Optional[str] = None):
    """
    Decorator for timing functions.

    Usage:
        @timed("agent_spawn")
        def spawn_agent(...):
            ...
    """
    def decorator(func):
        func_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            with timer(func_name):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with timer(func_name):
                return await func(*args, **kwargs)

        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def asyncio_iscoroutinefunction(func) -> bool:
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# ============================================================
# Initialization on import
# ============================================================

# Auto-initialize with defaults
init_logging()
