# cli_persistence.py - Persistence for CLI Orchestration Sequences
"""
Dual-layer persistence for CLI orchestration:

1. Text Files: Complete outputs (grep-able, diff-able, human-readable)
   - One directory per sequence
   - One file per step
   - JSON metadata

2. SQLite Database: Structured queries, full-text search
   - Sequences table (metadata, status, timing)
   - Steps table (individual step results)
   - Full-text search on outputs

Storage Layout:
    logs/sequences/
    ├── 2025-11-26/
    │   ├── seq-abc123/
    │   │   ├── metadata.json
    │   │   ├── step-1-claude-code.txt
    │   │   ├── step-2-gemini.txt
    │   │   └── step-3-aider.txt
    │   └── seq-def456/
    │       ├── metadata.json
    │       └── ...
    └── sequences.db

Usage:
    from eats_core.cli_persistence import SequencePersistence

    persistence = SequencePersistence()

    # Auto-save during execution
    persistence.save_sequence(sequence)

    # Query later
    results = persistence.search_outputs("authentication bug")
    sequences = persistence.query_sequences(status="completed", tool="claude-code")

    # Replay
    seq = persistence.load_sequence("seq-abc123")
"""

from __future__ import annotations
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class PersistedSequence:
    """Metadata for a saved sequence."""
    id: str
    name: str
    status: str  # 'running', 'completed', 'failed'
    started_at: float
    completed_at: Optional[float]
    total_steps: int
    successful_steps: int
    error_message: Optional[str]
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PersistedStep:
    """Individual step result."""
    id: str
    sequence_id: str
    step_number: int
    tool_name: str
    prompt: str
    output: str
    duration_seconds: Optional[float]
    status: str  # 'success', 'failed'
    error_message: Optional[str]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Persistence Layer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SequencePersistence:
    """
    Manage persistence for CLI orchestration sequences.

    Dual-layer storage:
    - Text files: Complete, grep-able outputs
    - SQLite: Queryable metadata with FTS
    """

    def __init__(self, base_dir: str = "logs/sequences"):
        """
        Initialize persistence layer.

        Args:
            base_dir: Root directory for sequence storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.base_dir / "sequences.db"
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Sequences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequences (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at REAL NOT NULL,
                completed_at REAL,
                total_steps INTEGER NOT NULL,
                successful_steps INTEGER NOT NULL,
                error_message TEXT,
                tags TEXT,  -- JSON array
                created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)

        # Steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id TEXT PRIMARY KEY,
                sequence_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                output TEXT NOT NULL,
                duration_seconds REAL,
                status TEXT NOT NULL,
                error_message TEXT,
                timestamp REAL NOT NULL,
                FOREIGN KEY (sequence_id) REFERENCES sequences(id)
            )
        """)

        # Indices for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sequences_status
            ON sequences(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sequences_started_at
            ON sequences(started_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_sequence_id
            ON steps(sequence_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_tool_name
            ON steps(tool_name)
        """)

        # Full-text search on step outputs
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS step_outputs_fts
            USING fts5(
                step_id UNINDEXED,
                tool_name,
                prompt,
                output,
                content='steps',
                content_rowid='rowid'
            )
        """)

        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS step_outputs_fts_insert
            AFTER INSERT ON steps
            BEGIN
                INSERT INTO step_outputs_fts(rowid, step_id, tool_name, prompt, output)
                VALUES (new.rowid, new.id, new.tool_name, new.prompt, new.output);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS step_outputs_fts_delete
            AFTER DELETE ON steps
            BEGIN
                DELETE FROM step_outputs_fts WHERE rowid = old.rowid;
            END
        """)

        conn.commit()
        conn.close()

    # ─────────────────────────────────────────────────────
    # Save Sequences
    # ─────────────────────────────────────────────────────

    def save_sequence(self, sequence_data: Dict[str, Any]) -> str:
        """
        Save a complete sequence (metadata + all steps).

        Args:
            sequence_data: Dictionary from CLISequence.run() result

        Returns:
            Sequence ID
        """
        # Generate ID if not provided
        if 'id' not in sequence_data:
            sequence_data['id'] = f"seq-{int(time.time() * 1000):x}"

        seq_id = sequence_data['id']
        name = sequence_data.get('name', 'unnamed')
        started_at = sequence_data.get('started_at', time.time())

        # Create sequence directory
        date_dir = self.base_dir / datetime.fromtimestamp(started_at).strftime('%Y-%m-%d')
        seq_dir = date_dir / seq_id
        seq_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata.json
        metadata = {
            'id': seq_id,
            'name': name,
            'status': sequence_data.get('status', 'completed'),
            'started_at': started_at,
            'completed_at': sequence_data.get('completed_at'),
            'total_steps': sequence_data.get('total_steps', 0),
            'successful_steps': sequence_data.get('successful_steps', 0),
            'duration': sequence_data.get('duration'),
            'error_message': sequence_data.get('error_message'),
            'tags': sequence_data.get('tags', []),
        }

        with open(seq_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

        # Save each step to individual text file
        steps = sequence_data.get('steps', [])
        for i, step in enumerate(steps, 1):
            tool_name = step.get('tool_name', 'unknown')
            output = step.get('raw_output', '')
            step_file = seq_dir / f"step-{i}-{tool_name}.txt"

            with open(step_file, 'w') as f:
                # Header with metadata
                f.write(f"# Step {i}: {tool_name}\n")
                f.write(f"# Prompt: {step.get('prompt', '')[:100]}...\n")
                f.write(f"# Duration: {step.get('duration', 0):.2f}s\n")
                f.write(f"# Status: {step.get('status', 'unknown')}\n")
                f.write(f"# Timestamp: {datetime.fromtimestamp(step.get('timestamp', time.time())).isoformat()}\n")
                f.write("#" + "=" * 70 + "\n\n")

                # Actual output
                f.write(output)

        # Save to database
        self._save_to_db(metadata, steps)

        return seq_id

    def _save_to_db(self, metadata: Dict[str, Any], steps: List[Dict[str, Any]]):
        """Save sequence metadata and steps to SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Insert or replace sequence
            cursor.execute("""
                INSERT OR REPLACE INTO sequences
                (id, name, status, started_at, completed_at, total_steps,
                 successful_steps, error_message, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata['id'],
                metadata['name'],
                metadata['status'],
                metadata['started_at'],
                metadata.get('completed_at'),
                metadata['total_steps'],
                metadata['successful_steps'],
                metadata.get('error_message'),
                json.dumps(metadata.get('tags', [])),
            ))

            # Insert steps
            for i, step in enumerate(steps, 1):
                step_id = f"{metadata['id']}-step-{i}"
                cursor.execute("""
                    INSERT OR REPLACE INTO steps
                    (id, sequence_id, step_number, tool_name, prompt, output,
                     duration_seconds, status, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    step_id,
                    metadata['id'],
                    i,
                    step.get('tool_name', 'unknown'),
                    step.get('prompt', ''),
                    step.get('raw_output', ''),
                    step.get('duration'),
                    'success' if step.get('success') else 'failed',
                    step.get('error_message'),
                    step.get('timestamp', time.time()),
                ))

            conn.commit()
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────
    # Load Sequences
    # ─────────────────────────────────────────────────────

    def load_sequence(self, sequence_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a complete sequence by ID.

        Args:
            sequence_id: Sequence ID to load

        Returns:
            Sequence data dictionary or None if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Load metadata
            cursor.execute("SELECT * FROM sequences WHERE id = ?", (sequence_id,))
            seq_row = cursor.fetchone()

            if not seq_row:
                return None

            sequence = dict(seq_row)
            sequence['tags'] = json.loads(sequence.get('tags') or '[]')

            # Load steps
            cursor.execute("""
                SELECT * FROM steps
                WHERE sequence_id = ?
                ORDER BY step_number
            """, (sequence_id,))

            steps = [dict(row) for row in cursor.fetchall()]
            sequence['steps'] = steps

            return sequence

        finally:
            conn.close()

    # ─────────────────────────────────────────────────────
    # Query Sequences
    # ─────────────────────────────────────────────────────

    def query_sequences(
        self,
        status: Optional[str] = None,
        tool: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query sequences with filters.

        Args:
            status: Filter by status ('running', 'completed', 'failed')
            tool: Filter sequences that used this tool
            since: Only sequences started after this timestamp
            limit: Maximum results to return

        Returns:
            List of sequence metadata dictionaries
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Build query
            query = "SELECT * FROM sequences WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if since:
                query += " AND started_at >= ?"
                params.append(since)

            if tool:
                # Join with steps to filter by tool
                query = f"""
                    SELECT DISTINCT s.* FROM sequences s
                    JOIN steps st ON s.id = st.sequence_id
                    WHERE st.tool_name = ?
                """
                params = [tool] + params

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]

            # Parse tags JSON
            for result in results:
                result['tags'] = json.loads(result.get('tags') or '[]')

            return results

        finally:
            conn.close()

    # ─────────────────────────────────────────────────────
    # Full-Text Search
    # ─────────────────────────────────────────────────────

    def search_outputs(
        self,
        query: str,
        tool: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across all step outputs.

        Args:
            query: Search query (FTS5 syntax supported)
            tool: Filter by tool name
            limit: Maximum results

        Returns:
            List of matching steps with context
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # FTS5 query using subquery approach (more compatible)
            fts_query = """
                SELECT s.id, s.sequence_id, s.step_number, s.tool_name,
                       s.prompt, s.output, s.timestamp
                FROM steps s
                WHERE s.rowid IN (
                    SELECT rowid FROM step_outputs_fts
                    WHERE step_outputs_fts MATCH ?
                )
            """
            params = [query]

            if tool:
                fts_query += " AND s.tool_name = ?"
                params.append(tool)

            fts_query += " LIMIT ?"
            params.append(limit)

            cursor.execute(fts_query, params)
            results = [dict(row) for row in cursor.fetchall()]

            return results

        finally:
            conn.close()

    # ─────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics.

        Returns:
            Dictionary with stats
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            stats = {}

            # Total sequences
            cursor.execute("SELECT COUNT(*) FROM sequences")
            stats['total_sequences'] = cursor.fetchone()[0]

            # By status
            cursor.execute("""
                SELECT status, COUNT(*)
                FROM sequences
                GROUP BY status
            """)
            stats['by_status'] = dict(cursor.fetchall())

            # Total steps
            cursor.execute("SELECT COUNT(*) FROM steps")
            stats['total_steps'] = cursor.fetchone()[0]

            # Tools used
            cursor.execute("""
                SELECT tool_name, COUNT(*)
                FROM steps
                GROUP BY tool_name
                ORDER BY COUNT(*) DESC
            """)
            stats['tools_used'] = dict(cursor.fetchall())

            # Success rate
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                FROM steps
            """)
            stats['success_rate'] = round(cursor.fetchone()[0] or 0, 2)

            return stats

        finally:
            conn.close()

    # ─────────────────────────────────────────────────────
    # Export/Import
    # ─────────────────────────────────────────────────────

    def export_sequence(self, sequence_id: str, output_path: str) -> None:
        """
        Export sequence to standalone JSON file.

        Args:
            sequence_id: Sequence to export
            output_path: Output file path
        """
        sequence = self.load_sequence(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence not found: {sequence_id}")

        with open(output_path, 'w') as f:
            json.dump(sequence, f, indent=2, default=str)

    def import_sequence(self, input_path: str) -> str:
        """
        Import sequence from JSON file.

        Args:
            input_path: Path to JSON file

        Returns:
            Imported sequence ID
        """
        with open(input_path, 'r') as f:
            sequence_data = json.load(f)

        return self.save_sequence(sequence_data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_persistence: Optional[SequencePersistence] = None


def get_persistence() -> SequencePersistence:
    """Get global persistence instance."""
    global _global_persistence
    if _global_persistence is None:
        _global_persistence = SequencePersistence()
    return _global_persistence
