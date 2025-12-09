# test_framework.py - Meta-Orchestration Testing Framework
"""
Testing framework for CLI orchestration workflows.

Features:
- Generate example prompts for simulated CLIs
- Process outputs and write to SQLite database
- Hash lookup table for response selection
- Sequential and parallel execution support
- Workflow step persistence

Usage:
    framework = TestFramework()
    framework.add_prompt_template("audit", "Audit the {target} for issues")
    framework.add_response_mapping("error", "Fix the error: {context}")

    result = framework.run_workflow(
        workflow_type="audit-refactor",
        context={"target": "codebase"}
    )
"""

from __future__ import annotations
import sqlite3
import hashlib
import json
import time
import random
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from pathlib import Path
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from eats_core
from .transport import PTYTransport, create_transport
from .cli_orchestrator import CLISequence, OutputParser
from .response_router import (
    ResponseRouter, ActionType, IterativeWorkflow,
    create_audit_refactor_workflow, create_review_fix_workflow
)
from .cli_persistence import get_persistence
from .logging import get_logger

logger = get_logger("test_framework")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    name: str
    template: str
    category: str = "general"
    keywords: List[str] = field(default_factory=list)
    priority: int = 0

    def render(self, context: Dict[str, Any]) -> str:
        """Render template with context variables."""
        result = self.template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def hash(self) -> str:
        """Generate hash for quick lookup."""
        return hashlib.md5(self.name.encode()).hexdigest()[:12]


# Default prompt templates for iterative workflows
DEFAULT_PROMPTS: Dict[str, PromptTemplate] = {
    "audit_code": PromptTemplate(
        name="audit_code",
        template="Audit the codebase at {path} for issues, patterns, and improvements.",
        category="analysis",
        keywords=["identified", "error", "refactor"],
    ),
    "load_context": PromptTemplate(
        name="load_context",
        template="Load and analyze files: {files}",
        category="context",
        keywords=["complete", "continue"],
    ),
    "refactor": PromptTemplate(
        name="refactor",
        template="Refactor the code based on: {context}",
        category="modification",
        keywords=["complete", "refactor", "error"],
    ),
    "genplan": PromptTemplate(
        name="genplan",
        template="Generate an execution plan for: {task}",
        category="planning",
        keywords=["complete"],
    ),
    "continue": PromptTemplate(
        name="continue",
        template="Continue with the implementation. Previous output:\n{previous_output}",
        category="execution",
        keywords=["complete", "continue", "error"],
    ),
    "meta_refactor": PromptTemplate(
        name="meta_refactor",
        template="Perform meta-level optimization of the codebase structure.",
        category="optimization",
        keywords=["complete", "optimize"],
    ),
    "review": PromptTemplate(
        name="review",
        template="Review this code for bugs and improvements:\n{code}",
        category="analysis",
        keywords=["identified", "error", "refactor", "optimize"],
    ),
    "fix": PromptTemplate(
        name="fix",
        template="Fix the issues identified:\n{issues}",
        category="modification",
        keywords=["complete", "error"],
    ),
    "test": PromptTemplate(
        name="test",
        template="Run tests for: {target}",
        category="verification",
        keywords=["complete", "error"],
    ),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Response Mappings (Hash Lookup Table)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ResponseMapping:
    """Maps detected keywords to follow-up prompts."""
    keyword: str
    response_template: str
    next_action: str = "continue"  # continue, switch, delegate, complete
    target_tool: Optional[str] = None
    priority: int = 0

    def hash(self) -> str:
        """Generate hash for O(1) lookup."""
        return hashlib.md5(self.keyword.lower().encode()).hexdigest()


class ResponseHashTable:
    """
    Hash table for O(1) keyword -> response lookup.

    Stores mappings in SQLite for persistence.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("logs/response_mappings.db")
        self._table: Dict[str, ResponseMapping] = {}
        self._init_db()
        self._load_defaults()

    def _init_db(self):
        """Initialize SQLite database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS response_mappings (
                hash TEXT PRIMARY KEY,
                keyword TEXT NOT NULL,
                response_template TEXT NOT NULL,
                next_action TEXT DEFAULT 'continue',
                target_tool TEXT,
                priority INTEGER DEFAULT 0,
                created_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def _load_defaults(self):
        """Load default response mappings."""
        defaults = [
            ResponseMapping("error", "An error was detected. Please fix: {context}", "continue", priority=10),
            ResponseMapping("identified", "Issue identified. Analyzing: {context}", "continue", priority=8),
            ResponseMapping("refactor", "Refactoring as suggested: {context}", "continue", priority=6),
            ResponseMapping("optimize", "Applying optimization: {context}", "continue", priority=6),
            ResponseMapping("complete", "", "complete", priority=5),
            ResponseMapping("continue", "Continuing with next step.", "continue", priority=3),
        ]
        for mapping in defaults:
            self.add(mapping)

    def add(self, mapping: ResponseMapping) -> str:
        """Add mapping to table and persist."""
        h = mapping.hash()
        self._table[h] = mapping

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO response_mappings
            (hash, keyword, response_template, next_action, target_tool, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (h, mapping.keyword, mapping.response_template,
              mapping.next_action, mapping.target_tool, mapping.priority, time.time()))
        conn.commit()
        conn.close()
        return h

    def lookup(self, text: str) -> Optional[ResponseMapping]:
        """O(1) lookup by scanning for keywords in text."""
        text_lower = text.lower()
        matches = []

        for h, mapping in self._table.items():
            if mapping.keyword.lower() in text_lower:
                matches.append(mapping)

        if not matches:
            return None

        # Return highest priority match
        return max(matches, key=lambda m: m.priority)

    def get_response(self, text: str, context: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        Get response prompt for given output text.

        Returns: (rendered_response, next_action)
        """
        context = context or {}
        mapping = self.lookup(text)

        if not mapping:
            return ("Please continue.", "continue")

        # Render template
        response = mapping.response_template
        context["context"] = text[:200]  # Include snippet of original
        for key, value in context.items():
            response = response.replace(f"{{{key}}}", str(value))

        return (response, mapping.next_action)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Execution Record
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class WorkflowStep:
    """Record of a single workflow step execution."""
    step_id: str
    step_name: str
    tool: str
    prompt: str
    output: str = ""
    keywords_detected: List[str] = field(default_factory=list)
    next_action: str = ""
    duration: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorkflowExecution:
    """Complete record of a workflow execution."""
    execution_id: str
    workflow_name: str
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "running"
    steps: List[WorkflowStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: WorkflowStep):
        """Add step to execution record."""
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "execution_id": self.execution_id,
            "workflow_name": self.workflow_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "total_steps": len(self.steps),
            "successful_steps": sum(1 for s in self.steps if s.success),
            "duration": (self.completed_at or time.time()) - self.started_at,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_name": s.step_name,
                    "tool": s.tool,
                    "prompt": s.prompt[:200],
                    "output_preview": s.output[:200] if s.output else "",
                    "keywords": s.keywords_detected,
                    "next_action": s.next_action,
                    "duration": s.duration,
                    "success": s.success,
                    "error": s.error,
                }
                for s in self.steps
            ],
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Framework
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFramework:
    """
    Comprehensive testing framework for meta-orchestration.

    Features:
    - Generate prompts from templates
    - Run workflows (sequential/parallel)
    - Detect keywords and route responses
    - Persist all steps to database
    - Support both mock and real CLI tools
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("logs/test_framework.db")
        self.prompts = dict(DEFAULT_PROMPTS)
        self.response_table = ResponseHashTable()
        self.router = ResponseRouter()
        self.executions: Dict[str, WorkflowExecution] = {}
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for workflow persistence."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                execution_id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                started_at REAL,
                completed_at REAL,
                status TEXT,
                total_steps INTEGER,
                successful_steps INTEGER,
                context_json TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                step_id TEXT PRIMARY KEY,
                execution_id TEXT,
                step_name TEXT,
                tool TEXT,
                prompt TEXT,
                output TEXT,
                keywords_json TEXT,
                next_action TEXT,
                duration REAL,
                success INTEGER,
                error TEXT,
                timestamp REAL,
                FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id)
            )
        """)

        # Full-text search on outputs
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS step_outputs_fts
            USING fts5(step_id, output, keywords)
        """)

        conn.commit()
        conn.close()

    def add_prompt_template(self, name: str, template: str,
                           category: str = "general", keywords: List[str] = None):
        """Add a prompt template."""
        self.prompts[name] = PromptTemplate(
            name=name,
            template=template,
            category=category,
            keywords=keywords or [],
        )

    def add_response_mapping(self, keyword: str, response_template: str,
                            next_action: str = "continue", priority: int = 0):
        """Add a keyword -> response mapping."""
        mapping = ResponseMapping(
            keyword=keyword,
            response_template=response_template,
            next_action=next_action,
            priority=priority,
        )
        self.response_table.add(mapping)

    def generate_prompt(self, template_name: str, context: Dict[str, Any]) -> str:
        """Generate prompt from template."""
        if template_name not in self.prompts:
            return f"Execute: {template_name}"
        return self.prompts[template_name].render(context)

    def detect_keywords(self, output: str) -> List[str]:
        """Detect keywords in output."""
        keywords = ["identified", "error", "complete", "refactor", "optimize", "continue"]
        found = []
        output_lower = output.lower()
        for kw in keywords:
            if kw in output_lower:
                found.append(kw)
        return found

    def _save_step(self, execution_id: str, step: WorkflowStep):
        """Save step to database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT INTO workflow_steps
            (step_id, execution_id, step_name, tool, prompt, output,
             keywords_json, next_action, duration, success, error, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step.step_id, execution_id, step.step_name, step.tool,
            step.prompt, step.output, json.dumps(step.keywords_detected),
            step.next_action, step.duration, 1 if step.success else 0,
            step.error, step.timestamp
        ))

        # Add to FTS
        conn.execute("""
            INSERT INTO step_outputs_fts (step_id, output, keywords)
            VALUES (?, ?, ?)
        """, (step.step_id, step.output, ",".join(step.keywords_detected)))

        conn.commit()
        conn.close()

    def _save_execution(self, execution: WorkflowExecution):
        """Save execution record to database."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO workflow_executions
            (execution_id, workflow_name, started_at, completed_at, status,
             total_steps, successful_steps, context_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.execution_id, execution.workflow_name,
            execution.started_at, execution.completed_at, execution.status,
            len(execution.steps), sum(1 for s in execution.steps if s.success),
            json.dumps(execution.context)
        ))
        conn.commit()
        conn.close()

    def run_step(self, tool: str, prompt: str,
                 use_mock: bool = True, timeout: float = 30.0) -> WorkflowStep:
        """
        Run a single workflow step.

        Args:
            tool: CLI tool to use (or 'mock' for mock_ai_cli)
            prompt: Prompt to send
            use_mock: Use mock CLI instead of real tool
            timeout: Execution timeout

        Returns:
            WorkflowStep with results
        """
        step_id = hashlib.md5(f"{time.time()}{prompt[:20]}".encode()).hexdigest()[:12]
        start_time = time.time()

        step = WorkflowStep(
            step_id=step_id,
            step_name=f"{tool}_step",
            tool=tool,
            prompt=prompt,
        )

        try:
            # Determine command
            if use_mock or tool == "mock":
                cmd = ["python3", "tools/mock_ai_cli.py", "--mode", "coder"]
            elif tool == "python":
                cmd = ["python3", "-i"]
            else:
                cmd = [tool]

            # Create transport and execute
            transport = create_transport(cmd, transport_type="pty", name=f"step-{step_id}")
            transport.start()
            time.sleep(0.3)  # Wait for startup

            # Send prompt
            transport.send_line(prompt)
            time.sleep(0.5)  # Wait for response

            # Collect output
            output = ""
            for _ in range(10):  # Max 10 iterations
                chunk = transport.recv_now()
                if chunk:
                    output += chunk
                time.sleep(0.2)
                if len(output) > 100:  # Got enough output
                    break

            transport.terminate()

            # Process output
            step.output = output
            step.keywords_detected = self.detect_keywords(output)
            step.duration = time.time() - start_time
            step.success = True

            # Determine next action
            response, action = self.response_table.get_response(output)
            step.next_action = action

        except Exception as e:
            step.success = False
            step.error = str(e)
            step.duration = time.time() - start_time
            step.next_action = "error"
            logger.error(f"Step {step_id} failed: {e}")

        return step

    def run_workflow_sequential(
        self,
        workflow: IterativeWorkflow,
        context: Dict[str, Any],
        use_mock: bool = True,
        max_steps: int = 10,
    ) -> WorkflowExecution:
        """
        Run workflow sequentially.

        Executes steps one at a time, routing based on output.
        """
        execution_id = hashlib.md5(f"{time.time()}{workflow.name}".encode()).hexdigest()[:12]
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name=workflow.name,
            context=context,
        )
        self.executions[execution_id] = execution

        current_step_name = workflow.start_step
        step_count = 0

        while current_step_name and step_count < max_steps:
            step_def = workflow.get_step(current_step_name)
            if not step_def:
                break

            # Generate prompt
            prompt = self.generate_prompt(current_step_name, context)

            # Run step
            logger.info(f"Running step: {current_step_name} (tool: {step_def.tool})")
            step = self.run_step(step_def.tool, prompt, use_mock=use_mock)
            step.step_name = current_step_name

            # Save step
            execution.add_step(step)
            self._save_step(execution_id, step)

            # Update context with output
            context["previous_output"] = step.output[:500]
            context["last_keywords"] = step.keywords_detected

            # Determine next step
            if step.next_action == "complete" or not step.success:
                break

            current_step_name = workflow.next_step(current_step_name, step.output)
            step_count += 1

        # Finalize
        execution.completed_at = time.time()
        execution.status = "completed" if all(s.success for s in execution.steps) else "failed"
        self._save_execution(execution)

        return execution

    def run_workflow_parallel(
        self,
        tools: List[str],
        prompt: str,
        use_mock: bool = True,
        max_workers: int = 4,
    ) -> List[WorkflowStep]:
        """
        Run same prompt on multiple tools in parallel.

        Useful for consensus/comparison workflows.
        """
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.run_step, tool, prompt, use_mock): tool
                for tool in tools
            }

            for future in as_completed(futures):
                tool = futures[future]
                try:
                    step = future.result()
                    results.append(step)
                except Exception as e:
                    logger.error(f"Parallel step {tool} failed: {e}")

        return results

    def query_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Query recent workflow executions."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM workflow_executions
            ORDER BY started_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_outputs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search on step outputs."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT s.*, f.output as matched_output
            FROM workflow_steps s
            JOIN step_outputs_fts f ON s.step_id = f.step_id
            WHERE step_outputs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_audit_refactor_test(context: Dict[str, Any] = None, use_mock: bool = True):
    """Run standard audit-refactor workflow test."""
    framework = TestFramework()
    workflow = create_audit_refactor_workflow()
    context = context or {"path": ".", "files": "*.py"}
    return framework.run_workflow_sequential(workflow, context, use_mock=use_mock)


def run_parallel_analysis_test(prompt: str, tools: List[str] = None, use_mock: bool = True):
    """Run parallel analysis across multiple tools."""
    framework = TestFramework()
    tools = tools or ["mock", "mock", "mock"]  # Default to 3 mock instances
    return framework.run_workflow_parallel(tools, prompt, use_mock=use_mock)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Module Exports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

__all__ = [
    # Core classes
    "TestFramework",
    "PromptTemplate",
    "ResponseMapping",
    "ResponseHashTable",
    "WorkflowStep",
    "WorkflowExecution",
    # Templates
    "DEFAULT_PROMPTS",
    # Convenience functions
    "run_audit_refactor_test",
    "run_parallel_analysis_test",
]
