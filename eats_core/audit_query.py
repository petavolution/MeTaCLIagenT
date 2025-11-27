# audit_query.py - Audit Log Query and Analysis Tools
"""
Tools for querying and analyzing structured audit logs.

Features:
- Filter by event type, severity, time range
- Search for security violations
- Generate summaries and reports
- Export to various formats

Usage:
    # Command-line query
    python -m eats_core.audit_query --severity CRITICAL --last 24h

    # Programmatic query
    from eats_core.audit_query import AuditQuery
    query = AuditQuery("logs/audit")
    events = query.filter(severity="CRITICAL", event_type="command_rejected")
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


@dataclass
class AuditEvent:
    """Parsed audit event."""
    timestamp: datetime
    event_type: str
    severity: str
    message: str
    pid: int
    metadata: Dict[str, Any]
    raw_json: str

    @classmethod
    def from_json_line(cls, line: str) -> Optional[AuditEvent]:
        """Parse JSON line into AuditEvent."""
        try:
            data = json.loads(line)
            return cls(
                timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
                event_type=data["event_type"],
                severity=data["severity"],
                message=data["message"],
                pid=data["pid"],
                metadata=data.get("metadata", {}),
                raw_json=line,
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


class AuditQuery:
    """
    Query and analyze audit logs.

    Example:
        query = AuditQuery("logs/audit")

        # Find all security violations
        violations = query.filter(severity="CRITICAL")

        # Find command rejections in last hour
        recent = query.filter(
            event_type="command_rejected",
            since=datetime.now() - timedelta(hours=1)
        )

        # Generate security report
        report = query.security_summary()
    """

    def __init__(self, log_dir: str | Path):
        self.log_dir = Path(log_dir)
        self._events_cache: Optional[List[AuditEvent]] = None

    def _load_all_events(self) -> List[AuditEvent]:
        """Load all events from all log files."""
        if self._events_cache is not None:
            return self._events_cache

        events = []
        log_files = sorted(self.log_dir.glob("audit_*.jsonl"))

        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            event = AuditEvent.from_json_line(line)
                            if event:
                                events.append(event)
            except Exception as e:
                print(f"Warning: Failed to read {log_file}: {e}")

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        self._events_cache = events
        return events

    def filter(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        message_contains: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> List[AuditEvent]:
        """
        Filter events by criteria.

        Args:
            event_type: Filter by event type
            severity: Filter by severity level
            since: Only events after this time
            until: Only events before this time
            message_contains: Search in message text
            agent_name: Filter by agent name in metadata

        Returns:
            List of matching events
        """
        events = self._load_all_events()
        results = []

        for event in events:
            # Time range filter
            if since and event.timestamp < since:
                continue
            if until and event.timestamp > until:
                continue

            # Event type filter
            if event_type and event.event_type != event_type:
                continue

            # Severity filter
            if severity and event.severity != severity:
                continue

            # Message search
            if message_contains and message_contains.lower() not in event.message.lower():
                continue

            # Agent name filter
            if agent_name:
                if event.metadata.get("agent_name") != agent_name:
                    continue

            results.append(event)

        return results

    def security_violations(self) -> List[AuditEvent]:
        """Get all security violations (CRITICAL severity)."""
        return self.filter(severity="CRITICAL")

    def command_rejections(self) -> List[AuditEvent]:
        """Get all rejected commands."""
        return self.filter(event_type="command_rejected")

    def buffer_overflows(self) -> List[AuditEvent]:
        """Get all buffer overflow events."""
        return self.filter(event_type="buffer_overflow")

    def prompt_injection_attempts(self) -> List[AuditEvent]:
        """Get all prompt injection attempts."""
        return self.filter(event_type="prompt_injection_detected")

    def failed_steps(self) -> List[AuditEvent]:
        """Get all failed execution steps."""
        return self.filter(event_type="step_failed")

    def security_summary(self) -> Dict[str, Any]:
        """
        Generate security summary report.

        Returns:
            Dictionary with security metrics
        """
        all_events = self._load_all_events()

        return {
            "total_events": len(all_events),
            "critical_events": len(self.filter(severity="CRITICAL")),
            "warning_events": len(self.filter(severity="WARNING")),
            "error_events": len(self.filter(severity="ERROR")),
            "command_rejections": len(self.command_rejections()),
            "buffer_overflows": len(self.buffer_overflows()),
            "prompt_injections": len(self.prompt_injection_attempts()),
            "failed_steps": len(self.failed_steps()),
            "time_range": {
                "first_event": all_events[0].timestamp.isoformat() if all_events else None,
                "last_event": all_events[-1].timestamp.isoformat() if all_events else None,
            },
        }

    def agent_activity(self) -> Dict[str, Dict[str, int]]:
        """
        Get activity summary per agent.

        Returns:
            Dict mapping agent_name -> {events, starts, stops, failures}
        """
        all_events = self._load_all_events()
        agents = {}

        for event in all_events:
            agent_name = event.metadata.get("agent_name")
            if not agent_name:
                continue

            if agent_name not in agents:
                agents[agent_name] = {
                    "events": 0,
                    "starts": 0,
                    "stops": 0,
                    "failures": 0,
                }

            agents[agent_name]["events"] += 1

            if event.event_type == "agent_started":
                agents[agent_name]["starts"] += 1
            elif event.event_type == "agent_stopped":
                agents[agent_name]["stops"] += 1
            elif event.event_type == "agent_failed":
                agents[agent_name]["failures"] += 1

        return agents

    def print_events(
        self,
        events: List[AuditEvent],
        max_events: Optional[int] = None,
        show_metadata: bool = False,
    ) -> None:
        """
        Pretty-print events.

        Args:
            events: Events to print
            max_events: Limit number of events shown
            show_metadata: Include full metadata in output
        """
        if max_events:
            events = events[:max_events]

        for event in events:
            timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{event.severity:8s}] {event.event_type:30s} | {event.message}")

            if show_metadata and event.metadata:
                for key, value in event.metadata.items():
                    print(f"  {key}: {value}")
                print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Command-line interface for audit log queries."""
    import argparse

    parser = argparse.ArgumentParser(description="Query audit logs")
    parser.add_argument("--log-dir", default="logs/audit", help="Audit log directory")
    parser.add_argument("--severity", help="Filter by severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--type", dest="event_type", help="Filter by event type")
    parser.add_argument("--last", help="Last N hours (e.g., '24h', '1h')")
    parser.add_argument("--agent", help="Filter by agent name")
    parser.add_argument("--summary", action="store_true", help="Show security summary")
    parser.add_argument("--metadata", action="store_true", help="Show full metadata")
    parser.add_argument("--limit", type=int, help="Limit number of results")

    args = parser.parse_args()

    query = AuditQuery(args.log_dir)

    if args.summary:
        summary = query.security_summary()
        print("=== Security Summary ===")
        for key, value in summary.items():
            print(f"{key:25s}: {value}")
        return

    # Build filter criteria
    filter_kwargs = {}
    if args.severity:
        filter_kwargs["severity"] = args.severity.upper()
    if args.event_type:
        filter_kwargs["event_type"] = args.event_type
    if args.agent:
        filter_kwargs["agent_name"] = args.agent

    # Parse --last
    if args.last:
        match = re.match(r"(\d+)h", args.last)
        if match:
            hours = int(match.group(1))
            filter_kwargs["since"] = datetime.now() - timedelta(hours=hours)

    # Query and print
    events = query.filter(**filter_kwargs)
    print(f"Found {len(events)} matching events\n")
    query.print_events(events, max_events=args.limit, show_metadata=args.metadata)


if __name__ == "__main__":
    main()
