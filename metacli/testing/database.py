"""
Test Database - Store test scenarios and execution history

Stores:
- Test scenarios (prompt sequences)
- Expected outputs
- Execution history
- Template usage statistics
"""

from __future__ import annotations
import sqlite3
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TestScenario:
    """
    A test scenario with sequence of prompts and expected outputs.

    Example:
        scenario = TestScenario(
            name="audit-refactor-cycle",
            description="Test audit → refactor workflow",
            steps=[
                {"tool": "claude-code", "prompt": "Audit src/", "expected_output": "Found 3 issues"},
                {"tool": "aider", "prompt": "Fix issues", "expected_output": "Fixed 3 issues"},
            ]
        )
    """
    name: str
    description: str
    steps: List[Dict[str, str]]
    tags: List[str] = field(default_factory=list)
    category: str = "default"

    # Metadata
    id: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class TestExecution:
    """Record of a test scenario execution."""
    scenario_id: int
    scenario_name: str
    started_at: float
    completed_at: float
    duration: float
    status: str  # "passed", "failed", "error"

    # Results
    steps_executed: int
    steps_passed: int
    steps_failed: int

    # Detailed results
    step_results: List[Dict[str, Any]]

    # Metadata
    id: Optional[int] = None
    error_message: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Database
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDatabase:
    """
    SQLite database for test scenarios and execution history.

    Schema:
        test_scenarios: Test scenario definitions
        test_executions: Execution results
        step_results: Detailed step-by-step results
        template_usage: Track which templates are used most
    """

    def __init__(self, db_path: str = "tests/test_database.db"):
        self.db_path = db_path
        self._ensure_db_exists()
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _ensure_db_exists(self):
        """Create database directory if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _create_schema(self):
        """Create database schema."""
        cursor = self.conn.cursor()

        # Test scenarios table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                steps TEXT NOT NULL,  -- JSON array
                tags TEXT,  -- JSON array
                category TEXT DEFAULT 'default',
                created_at REAL,
                updated_at REAL
            )
        """)

        # Test executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                scenario_name TEXT NOT NULL,
                started_at REAL NOT NULL,
                completed_at REAL NOT NULL,
                duration REAL NOT NULL,
                status TEXT NOT NULL,
                steps_executed INTEGER,
                steps_passed INTEGER,
                steps_failed INTEGER,
                step_results TEXT,  -- JSON array
                error_message TEXT,
                FOREIGN KEY (scenario_id) REFERENCES test_scenarios(id)
            )
        """)

        # Template usage statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS template_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL,
                category TEXT,
                used_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_used REAL,
                UNIQUE(template_name, category)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_executions_scenario
            ON test_executions(scenario_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_executions_status
            ON test_executions(status)
        """)

        self.conn.commit()

    def save_scenario(self, scenario: TestScenario) -> int:
        """Save test scenario to database."""
        cursor = self.conn.cursor()

        scenario.updated_at = time.time()

        if scenario.id:
            # Update existing
            cursor.execute("""
                UPDATE test_scenarios
                SET description = ?, steps = ?, tags = ?, category = ?, updated_at = ?
                WHERE id = ?
            """, (
                scenario.description,
                json.dumps(scenario.steps),
                json.dumps(scenario.tags),
                scenario.category,
                scenario.updated_at,
                scenario.id
            ))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO test_scenarios (name, description, steps, tags, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                scenario.name,
                scenario.description,
                json.dumps(scenario.steps),
                json.dumps(scenario.tags),
                scenario.category,
                scenario.created_at,
                scenario.updated_at
            ))
            scenario.id = cursor.lastrowid

        self.conn.commit()
        return scenario.id

    def load_scenario(self, scenario_id: int = None, name: str = None) -> Optional[TestScenario]:
        """Load test scenario by ID or name."""
        cursor = self.conn.cursor()

        if scenario_id:
            cursor.execute("SELECT * FROM test_scenarios WHERE id = ?", (scenario_id,))
        elif name:
            cursor.execute("SELECT * FROM test_scenarios WHERE name = ?", (name,))
        else:
            return None

        row = cursor.fetchone()
        if not row:
            return None

        return TestScenario(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            steps=json.loads(row["steps"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            category=row["category"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def list_scenarios(
        self,
        category: str = None,
        tags: List[str] = None,
        limit: int = 100
    ) -> List[TestScenario]:
        """List test scenarios with optional filtering."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM test_scenarios WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        scenarios = []
        for row in rows:
            scenario = TestScenario(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                steps=json.loads(row["steps"]),
                tags=json.loads(row["tags"]) if row["tags"] else [],
                category=row["category"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

            # Filter by tags if specified
            if tags:
                if any(tag in scenario.tags for tag in tags):
                    scenarios.append(scenario)
            else:
                scenarios.append(scenario)

        return scenarios

    def save_execution(self, execution: TestExecution) -> int:
        """Save test execution result."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO test_executions (
                scenario_id, scenario_name, started_at, completed_at, duration,
                status, steps_executed, steps_passed, steps_failed,
                step_results, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.scenario_id,
            execution.scenario_name,
            execution.started_at,
            execution.completed_at,
            execution.duration,
            execution.status,
            execution.steps_executed,
            execution.steps_passed,
            execution.steps_failed,
            json.dumps(execution.step_results),
            execution.error_message
        ))

        execution.id = cursor.lastrowid
        self.conn.commit()
        return execution.id

    def get_execution_history(
        self,
        scenario_id: int = None,
        status: str = None,
        limit: int = 100
    ) -> List[TestExecution]:
        """Get execution history with optional filtering."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM test_executions WHERE 1=1"
        params = []

        if scenario_id:
            query += " AND scenario_id = ?"
            params.append(scenario_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        executions = []
        for row in rows:
            execution = TestExecution(
                id=row["id"],
                scenario_id=row["scenario_id"],
                scenario_name=row["scenario_name"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                duration=row["duration"],
                status=row["status"],
                steps_executed=row["steps_executed"],
                steps_passed=row["steps_passed"],
                steps_failed=row["steps_failed"],
                step_results=json.loads(row["step_results"]),
                error_message=row["error_message"]
            )
            executions.append(execution)

        return executions

    def record_template_usage(self, template_name: str, category: str, success: bool):
        """Record that a template was used."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO template_usage (template_name, category, used_count, success_count, last_used)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(template_name, category) DO UPDATE SET
                used_count = used_count + 1,
                success_count = success_count + ?,
                last_used = ?
        """, (
            template_name,
            category,
            1 if success else 0,
            time.time(),
            1 if success else 0,
            time.time()
        ))

        self.conn.commit()

    def get_template_statistics(self) -> List[Dict[str, Any]]:
        """Get template usage statistics."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT template_name, category, used_count, success_count,
                   CAST(success_count AS REAL) / used_count AS success_rate,
                   last_used
            FROM template_usage
            ORDER BY used_count DESC
        """)

        stats = []
        for row in cursor.fetchall():
            stats.append({
                "template_name": row["template_name"],
                "category": row["category"],
                "used_count": row["used_count"],
                "success_count": row["success_count"],
                "success_rate": row["success_rate"],
                "last_used": row["last_used"]
            })

        return stats

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall test statistics."""
        cursor = self.conn.cursor()

        # Total scenarios
        cursor.execute("SELECT COUNT(*) as count FROM test_scenarios")
        total_scenarios = cursor.fetchone()["count"]

        # Total executions
        cursor.execute("SELECT COUNT(*) as count FROM test_executions")
        total_executions = cursor.fetchone()["count"]

        # Pass/fail stats
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM test_executions
            GROUP BY status
        """)
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        # Success rate
        passed = status_counts.get("passed", 0)
        total = sum(status_counts.values())
        success_rate = (passed / total * 100) if total > 0 else 0

        return {
            "total_scenarios": total_scenarios,
            "total_executions": total_executions,
            "status_counts": status_counts,
            "success_rate": success_rate
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_test_db = None

def get_test_database(db_path: str = "tests/test_database.db") -> TestDatabase:
    """Get global test database instance."""
    global _global_test_db
    if _global_test_db is None:
        _global_test_db = TestDatabase(db_path)
    return _global_test_db
