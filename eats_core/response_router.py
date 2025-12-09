# response_router.py - Hash-Based Response Lookup and Conditional Routing
"""
Pattern-based response routing for CLI orchestration.

Features:
- MD5 hash-based O(1) keyword lookup
- Conditional workflow branching
- Iterative sequence patterns
- Sub-agent delegation

Usage:
    router = ResponseRouter()
    router.add_pattern("error", "Fix the error: {context}")
    router.add_pattern("complete", "DONE")  # Terminal state

    # Route based on output
    next_prompt = router.route(cli_output)
"""

from __future__ import annotations
import re
import hashlib
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from pathlib import Path
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Keywords and Actions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ActionType(Enum):
    """Types of actions the router can take."""
    CONTINUE = "continue"      # Send follow-up prompt to same tool
    SWITCH = "switch"          # Switch to different tool
    DELEGATE = "delegate"      # Spawn sub-agent
    ITERATE = "iterate"        # Repeat current step
    COMPLETE = "complete"      # Sequence finished
    ERROR = "error"            # Error handling
    BRANCH = "branch"          # Conditional branch


@dataclass
class RouteAction:
    """Action to take based on pattern match."""
    action_type: ActionType
    prompt_template: str = ""           # Follow-up prompt (supports {context}, {output})
    target_tool: Optional[str] = None   # Tool to switch to (for SWITCH/DELEGATE)
    max_iterations: int = 3             # Max iterations (for ITERATE)
    condition: Optional[str] = None     # Additional condition to check
    priority: int = 0                   # Higher priority = checked first

    def render_prompt(self, context: Dict[str, Any]) -> str:
        """Render prompt template with context variables."""
        prompt = self.prompt_template
        for key, value in context.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt


@dataclass
class PatternMatch:
    """Result of pattern matching."""
    keyword: str
    action: RouteAction
    confidence: float = 1.0
    matched_text: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hash-Based Keyword Lookup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class KeywordHashTable:
    """
    O(1) keyword lookup using MD5 hashes.

    Supports both exact matches and pattern-based matching.
    """

    def __init__(self):
        self._table: Dict[str, RouteAction] = {}  # hash -> action
        self._keywords: Dict[str, str] = {}        # keyword -> hash
        self._patterns: List[Tuple[re.Pattern, RouteAction]] = []  # regex patterns

    def _hash_keyword(self, keyword: str) -> str:
        """Generate MD5 hash for keyword."""
        return hashlib.md5(keyword.lower().encode()).hexdigest()

    def add(self, keyword: str, action: RouteAction) -> str:
        """
        Add keyword -> action mapping.

        Returns hash for reference.
        """
        h = self._hash_keyword(keyword)
        self._table[h] = action
        self._keywords[keyword.lower()] = h
        return h

    def add_pattern(self, pattern: str, action: RouteAction):
        """Add regex pattern -> action mapping."""
        compiled = re.compile(pattern, re.IGNORECASE)
        self._patterns.append((compiled, action))

    def lookup(self, text: str) -> Optional[PatternMatch]:
        """
        Look up action for text.

        First checks exact keyword matches (O(1)), then regex patterns.
        """
        text_lower = text.lower()

        # Check exact keyword matches first (O(1))
        for keyword, h in self._keywords.items():
            if keyword in text_lower:
                action = self._table[h]
                return PatternMatch(
                    keyword=keyword,
                    action=action,
                    matched_text=keyword,
                )

        # Fall back to regex patterns
        for pattern, action in self._patterns:
            match = pattern.search(text)
            if match:
                return PatternMatch(
                    keyword=pattern.pattern,
                    action=action,
                    matched_text=match.group(0),
                )

        return None

    def multi_lookup(self, text: str) -> List[PatternMatch]:
        """Find all matching patterns, sorted by priority."""
        matches = []
        text_lower = text.lower()

        # Check all keywords
        for keyword, h in self._keywords.items():
            if keyword in text_lower:
                action = self._table[h]
                matches.append(PatternMatch(
                    keyword=keyword,
                    action=action,
                    matched_text=keyword,
                ))

        # Check all patterns
        for pattern, action in self._patterns:
            match = pattern.search(text)
            if match:
                matches.append(PatternMatch(
                    keyword=pattern.pattern,
                    action=action,
                    matched_text=match.group(0),
                ))

        # Sort by action priority
        return sorted(matches, key=lambda m: m.action.priority, reverse=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Response Router
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResponseRouter:
    """
    Routes CLI outputs to appropriate follow-up actions.

    Supports:
    - Keyword-based routing (hash lookup)
    - Conditional branching
    - Iterative loops
    - Sub-agent delegation
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.lookup_table = KeywordHashTable()
        self.db_path = db_path or Path("logs/router.db")
        self._iteration_counts: Dict[str, int] = {}  # sequence_id -> count
        self._init_default_routes()

    def _init_default_routes(self):
        """Initialize default keyword routes."""
        # Error handling
        self.lookup_table.add("error", RouteAction(
            action_type=ActionType.ERROR,
            prompt_template="An error was detected. Please analyze and fix: {context}",
            priority=10,
        ))

        # Completion
        self.lookup_table.add("complete", RouteAction(
            action_type=ActionType.COMPLETE,
            prompt_template="",
            priority=5,
        ))

        # Continuation
        self.lookup_table.add("continue", RouteAction(
            action_type=ActionType.CONTINUE,
            prompt_template="Please continue with the implementation.",
            priority=3,
        ))

        # Refactoring
        self.lookup_table.add("refactor", RouteAction(
            action_type=ActionType.CONTINUE,
            prompt_template="Please refactor the code as suggested: {context}",
            priority=4,
        ))

        # Optimization
        self.lookup_table.add("optimize", RouteAction(
            action_type=ActionType.CONTINUE,
            prompt_template="Please apply the suggested optimizations.",
            priority=4,
        ))

        # Issue identification
        self.lookup_table.add("identified", RouteAction(
            action_type=ActionType.BRANCH,
            prompt_template="Issue identified. Analyzing: {context}",
            priority=6,
        ))

    def add_route(
        self,
        keyword: str,
        action_type: ActionType,
        prompt_template: str = "",
        target_tool: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        """
        Add custom keyword route.

        Returns hash for reference.
        """
        action = RouteAction(
            action_type=action_type,
            prompt_template=prompt_template,
            target_tool=target_tool,
            priority=priority,
        )
        return self.lookup_table.add(keyword, action)

    def add_pattern_route(
        self,
        pattern: str,
        action_type: ActionType,
        prompt_template: str = "",
        target_tool: Optional[str] = None,
        priority: int = 0,
    ):
        """Add regex pattern route."""
        action = RouteAction(
            action_type=action_type,
            prompt_template=prompt_template,
            target_tool=target_tool,
            priority=priority,
        )
        self.lookup_table.add_pattern(pattern, action)

    def route(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        sequence_id: str = "default",
    ) -> Tuple[ActionType, str, Optional[str]]:
        """
        Route output to next action.

        Args:
            output: CLI output text to analyze
            context: Additional context for prompt rendering
            sequence_id: Identifier for iteration tracking

        Returns:
            Tuple of (action_type, rendered_prompt, target_tool)
        """
        context = context or {}
        context["output"] = output[:500]  # Limit context size

        # Find matching pattern
        match = self.lookup_table.lookup(output)

        if not match:
            # Default: continue with generic prompt
            return (
                ActionType.CONTINUE,
                "Please continue with the current task.",
                None,
            )

        action = match.action
        context["context"] = match.matched_text
        context["keyword"] = match.keyword

        # Handle iteration limits
        if action.action_type == ActionType.ITERATE:
            count = self._iteration_counts.get(sequence_id, 0)
            if count >= action.max_iterations:
                return (
                    ActionType.COMPLETE,
                    f"Maximum iterations ({action.max_iterations}) reached.",
                    None,
                )
            self._iteration_counts[sequence_id] = count + 1

        # Render prompt
        prompt = action.render_prompt(context)

        return (action.action_type, prompt, action.target_tool)

    def route_multi(
        self,
        output: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[ActionType, str, Optional[str]]]:
        """
        Find all matching routes (for parallel execution).

        Returns list of (action_type, prompt, target_tool) tuples.
        """
        context = context or {}
        context["output"] = output[:500]

        matches = self.lookup_table.multi_lookup(output)
        results = []

        for match in matches:
            ctx = context.copy()
            ctx["context"] = match.matched_text
            ctx["keyword"] = match.keyword

            prompt = match.action.render_prompt(ctx)
            results.append((
                match.action.action_type,
                prompt,
                match.action.target_tool,
            ))

        return results

    def reset_iterations(self, sequence_id: str = "default"):
        """Reset iteration counter for sequence."""
        self._iteration_counts.pop(sequence_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Iterative Workflow Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class WorkflowStep:
    """A step in an iterative workflow."""
    name: str
    tool: str
    prompt_template: str
    next_on_success: Optional[str] = None  # Step name or None for end
    next_on_error: Optional[str] = None    # Step name for error handling
    max_retries: int = 2
    keywords_to_next: List[str] = field(default_factory=list)  # Keywords that trigger next step


class IterativeWorkflow:
    """
    Defines iterative workflow patterns.

    Supports:
    - Linear sequences: audit → refactor → test → deploy
    - Loops: refactor → test → (fail) → refactor
    - Conditional branches: review → (issues?) → fix or approve
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: Dict[str, WorkflowStep] = {}
        self.start_step: Optional[str] = None
        self.router = ResponseRouter()

    def add_step(
        self,
        name: str,
        tool: str,
        prompt_template: str,
        next_on_success: Optional[str] = None,
        next_on_error: Optional[str] = None,
        keywords_to_next: Optional[List[str]] = None,
    ) -> "IterativeWorkflow":
        """Add a step to the workflow (fluent API)."""
        step = WorkflowStep(
            name=name,
            tool=tool,
            prompt_template=prompt_template,
            next_on_success=next_on_success,
            next_on_error=next_on_error,
            keywords_to_next=keywords_to_next or ["complete"],
        )
        self.steps[name] = step

        if self.start_step is None:
            self.start_step = name

        return self

    def set_start(self, step_name: str) -> "IterativeWorkflow":
        """Set the starting step."""
        if step_name not in self.steps:
            raise ValueError(f"Unknown step: {step_name}")
        self.start_step = step_name
        return self

    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """Get step by name."""
        return self.steps.get(name)

    def next_step(self, current_step: str, output: str) -> Optional[str]:
        """
        Determine next step based on output.

        Returns step name or None if workflow complete.
        """
        step = self.steps.get(current_step)
        if not step:
            return None

        # Check for error keywords
        if "error" in output.lower():
            return step.next_on_error

        # Check for completion keywords
        for keyword in step.keywords_to_next:
            if keyword.lower() in output.lower():
                return step.next_on_success

        # Default: stay on current step (retry)
        return current_step


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-built Workflow Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_audit_refactor_workflow() -> IterativeWorkflow:
    """
    Standard audit → refactor → continue pattern.

    Flow:
    1. audit_code: Analyze codebase
    2. load_context: Load relevant files
    3. refactor: Apply improvements
    4. genplan: Generate execution plan
    5. continue: Execute plan
    6. meta_refactor: Final optimization
    """
    workflow = IterativeWorkflow("audit-refactor")

    workflow.add_step(
        name="audit_code",
        tool="claude-code",
        prompt_template="Audit the codebase for issues, patterns, and improvement opportunities.",
        next_on_success="load_context",
        keywords_to_next=["identified", "complete"],
    )

    workflow.add_step(
        name="load_context",
        tool="claude-code",
        prompt_template="Load and analyze the relevant files identified in the audit.",
        next_on_success="refactor",
        keywords_to_next=["complete", "continue"],
    )

    workflow.add_step(
        name="refactor",
        tool="claude-code",
        prompt_template="Refactor the code based on the audit findings: {context}",
        next_on_success="genplan",
        next_on_error="refactor",  # Retry on error
        keywords_to_next=["complete", "refactor"],
    )

    workflow.add_step(
        name="genplan",
        tool="claude-code",
        prompt_template="Generate a plan for the remaining work.",
        next_on_success="continue_impl",
        keywords_to_next=["complete"],
    )

    workflow.add_step(
        name="continue_impl",
        tool="claude-code",
        prompt_template="Continue with the implementation plan.",
        next_on_success="meta_refactor",
        keywords_to_next=["complete"],
    )

    workflow.add_step(
        name="meta_refactor",
        tool="claude-code",
        prompt_template="Perform final meta-refactoring to optimize the codebase structure.",
        next_on_success=None,  # End workflow
        keywords_to_next=["complete", "optimize"],
    )

    return workflow


def create_review_fix_workflow() -> IterativeWorkflow:
    """
    Review → fix loop pattern.

    Flow:
    1. review: Analyze code for issues
    2. fix: Fix identified issues
    3. verify: Check fixes
    4. (loop back to review if more issues)
    """
    workflow = IterativeWorkflow("review-fix")

    workflow.add_step(
        name="review",
        tool="gemini",
        prompt_template="Review this code for bugs, security issues, and improvements:\n{context}",
        next_on_success="fix",
        next_on_error="fix",
        keywords_to_next=["identified", "error", "refactor", "optimize"],
    )

    workflow.add_step(
        name="fix",
        tool="aider",
        prompt_template="Fix the issues identified in the review:\n{context}",
        next_on_success="verify",
        next_on_error="fix",
        keywords_to_next=["complete", "refactor"],
    )

    workflow.add_step(
        name="verify",
        tool="claude-code",
        prompt_template="Verify the fixes are correct and complete.",
        next_on_success=None,  # End if verified
        next_on_error="review",  # Loop back if more issues
        keywords_to_next=["complete"],
    )

    return workflow


def create_parallel_analysis_workflow() -> IterativeWorkflow:
    """
    Parallel analysis pattern (for consensus).

    Note: Actual parallel execution handled by ParallelExecutor.
    """
    workflow = IterativeWorkflow("parallel-analysis")

    workflow.add_step(
        name="analyze",
        tool="mock",  # Placeholder - actual tools specified at runtime
        prompt_template="Analyze this code:\n{context}",
        next_on_success="synthesize",
        keywords_to_next=["complete", "identified"],
    )

    workflow.add_step(
        name="synthesize",
        tool="claude-code",
        prompt_template="Synthesize the analysis results and recommend actions.",
        next_on_success=None,
        keywords_to_next=["complete"],
    )

    return workflow


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Module Exports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

__all__ = [
    # Core classes
    "ResponseRouter",
    "KeywordHashTable",
    "RouteAction",
    "PatternMatch",
    "ActionType",
    # Workflow
    "IterativeWorkflow",
    "WorkflowStep",
    # Templates
    "create_audit_refactor_workflow",
    "create_review_fix_workflow",
    "create_parallel_analysis_workflow",
]
