#!/usr/bin/env python3
"""
Template Engine for CLI Automation

Supports defining templates for:
- Input/output patterns
- Automated responses to CLI prompts
- Follow-up command generation
- Stdin/stdout control patterns

Usage:
    template = IOTemplate(
        name="git_commit_flow",
        patterns=[
            PatternAction(
                match="Changes not staged",
                action="git add .",
            ),
            PatternAction(
                match="nothing to commit",
                action="exit",
            ),
        ]
    )

    engine = TemplateEngine()
    engine.register_template(template)
    next_action = engine.match_output(output, template_name="git_commit_flow")
"""

import re
import time
from typing import List, Dict, Any, Optional, Callable, Pattern
from dataclasses import dataclass, field
from enum import Enum
import sys
import logging as stdlib_logging

logger = stdlib_logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Structures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ActionType(Enum):
    """Type of action to take when pattern matches."""
    SEND_INPUT = "send_input"  # Send text to stdin
    SEND_KEYS = "send_keys"     # Send special keys (Ctrl+C, etc.)
    WAIT = "wait"               # Wait for duration
    EXIT = "exit"               # Exit/close the process
    CALLBACK = "callback"       # Call Python function
    CHAIN = "chain"             # Chain to another template


@dataclass
class PatternAction:
    """
    A pattern-matching rule with associated action.

    When the pattern matches CLI output, execute the action.
    """
    # Pattern matching
    match: str                           # Text or regex pattern
    action_type: ActionType = ActionType.SEND_INPUT
    action_value: Any = None            # Value for action (text, duration, etc.)

    # Pattern options
    is_regex: bool = False              # Use regex matching
    case_sensitive: bool = False        # Case-sensitive matching
    match_whole_line: bool = False      # Match entire line vs substring

    # Action options
    delay_before: float = 0.0           # Wait before action (seconds)
    delay_after: float = 0.5            # Wait after action (seconds)

    # Metadata
    description: str = ""               # Human-readable description
    priority: int = 0                   # Higher priority = checked first

    _compiled_regex: Optional[Pattern] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Compile regex if needed."""
        if self.is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self._compiled_regex = re.compile(self.match, flags)

    def matches(self, text: str) -> bool:
        """Check if pattern matches the text."""
        if self.is_regex:
            return bool(self._compiled_regex.search(text))
        else:
            if self.case_sensitive:
                return self.match in text
            else:
                return self.match.lower() in text.lower()


@dataclass
class IOTemplate:
    """
    A template defining automated I/O patterns.

    Templates contain multiple pattern-action rules that define
    how to respond to different CLI outputs.
    """
    name: str
    description: str = ""
    patterns: List[PatternAction] = field(default_factory=list)
    default_action: Optional[PatternAction] = None  # Fallback if no match
    max_iterations: int = 100  # Prevent infinite loops
    timeout: int = 300         # Overall timeout (seconds)

    def __post_init__(self):
        """Sort patterns by priority (highest first)."""
        self.patterns.sort(key=lambda p: p.priority, reverse=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-defined Templates (Common Patterns)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Git workflow templates
GIT_COMMIT_TEMPLATE = IOTemplate(
    name="git_commit",
    description="Automated git commit workflow",
    patterns=[
        PatternAction(
            match="Changes not staged",
            action_type=ActionType.SEND_INPUT,
            action_value="git add .",
            description="Auto-stage changes",
        ),
        PatternAction(
            match="nothing to commit",
            action_type=ActionType.EXIT,
            description="Exit if nothing to commit",
        ),
        PatternAction(
            match=r"Untracked files:",
            action_type=ActionType.SEND_INPUT,
            action_value="git add .",
            description="Stage untracked files",
        ),
    ],
)

# AI CLI interaction templates
AI_CODE_REVIEW_TEMPLATE = IOTemplate(
    name="ai_code_review",
    description="AI code review with automatic follow-ups",
    patterns=[
        PatternAction(
            match="vulnerability",
            action_type=ActionType.SEND_INPUT,
            action_value="Fix the security vulnerabilities you identified",
            description="Request fix for vulnerabilities",
            priority=10,
        ),
        PatternAction(
            match="performance",
            action_type=ActionType.SEND_INPUT,
            action_value="Optimize the performance issues you found",
            description="Request performance optimization",
            priority=5,
        ),
        PatternAction(
            match="looks good",
            action_type=ActionType.SEND_INPUT,
            action_value="Add comprehensive tests",
            description="Request tests if code is good",
        ),
    ],
)

# Build/Test automation templates
BUILD_TEST_TEMPLATE = IOTemplate(
    name="build_test",
    description="Build and test automation",
    patterns=[
        PatternAction(
            match=r"FAILED.*tests",
            is_regex=True,
            action_type=ActionType.SEND_INPUT,
            action_value="pytest -v --last-failed",
            description="Re-run failed tests",
        ),
        PatternAction(
            match="ModuleNotFoundError",
            action_type=ActionType.SEND_INPUT,
            action_value="pip install -r requirements.txt",
            description="Install missing dependencies",
        ),
        PatternAction(
            match="All tests passed",
            action_type=ActionType.EXIT,
            description="Exit on success",
        ),
    ],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TemplateEngine:
    """
    Engine for managing and executing I/O templates.

    Provides:
    - Template registration and lookup
    - Pattern matching against CLI output
    - Action execution
    - Template chaining
    """

    def __init__(self):
        """Initialize template engine."""
        self.templates: Dict[str, IOTemplate] = {}
        self.callbacks: Dict[str, Callable] = {}

        # Register built-in templates
        self._register_builtin_templates()

    def register_template(self, template: IOTemplate):
        """Register a template."""
        self.templates[template.name] = template
        logger.info(f"Registered template: {template.name}")

    def register_callback(self, name: str, callback: Callable):
        """Register a callback function for CALLBACK actions."""
        self.callbacks[name] = callback
        logger.info(f"Registered callback: {name}")

    def match_output(
        self,
        output: str,
        template_name: str,
    ) -> Optional[PatternAction]:
        """
        Match output against template patterns.

        Args:
            output: CLI output text to match
            template_name: Name of template to use

        Returns:
            PatternAction if match found, None otherwise
        """
        template = self.templates.get(template_name)
        if not template:
            logger.warning(f"Template not found: {template_name}")
            return None

        # Check patterns in priority order
        for pattern in template.patterns:
            if pattern.matches(output):
                logger.info(
                    f"Pattern matched: {pattern.description or pattern.match[:50]}"
                )
                return pattern

        # Try default action if no match
        if template.default_action:
            logger.info("Using default action (no patterns matched)")
            return template.default_action

        return None

    def execute_action(
        self,
        action: PatternAction,
        orchestrator: Any,  # CLIOrchestrator instance
    ) -> bool:
        """
        Execute a pattern action.

        Args:
            action: PatternAction to execute
            orchestrator: CLIOrchestrator instance to control

        Returns:
            True if should continue, False if should exit
        """
        # Wait before action
        if action.delay_before > 0:
            time.sleep(action.delay_before)

        # Execute based on action type
        if action.action_type == ActionType.SEND_INPUT:
            logger.info(f"Sending input: {action.action_value[:50]}...")
            orchestrator.send(action.action_value)

        elif action.action_type == ActionType.SEND_KEYS:
            logger.info(f"Sending keys: {action.action_value}")
            # Send special keys (Ctrl+C, etc.)
            orchestrator.send_keys(action.action_value)

        elif action.action_type == ActionType.WAIT:
            duration = action.action_value or 1.0
            logger.info(f"Waiting {duration}s...")
            time.sleep(duration)

        elif action.action_type == ActionType.EXIT:
            logger.info("Exit action triggered")
            return False

        elif action.action_type == ActionType.CALLBACK:
            callback_name = action.action_value
            if callback_name in self.callbacks:
                logger.info(f"Executing callback: {callback_name}")
                self.callbacks[callback_name](orchestrator)
            else:
                logger.warning(f"Callback not found: {callback_name}")

        elif action.action_type == ActionType.CHAIN:
            # Chain to another template (handled by caller)
            logger.info(f"Chaining to template: {action.action_value}")

        # Wait after action
        if action.delay_after > 0:
            time.sleep(action.delay_after)

        return True  # Continue execution

    def run_template(
        self,
        orchestrator: Any,
        template_name: str,
        initial_input: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run a template against a CLI orchestrator.

        This is the main automation loop - it sends input, reads output,
        matches patterns, and executes actions until exit condition.

        Args:
            orchestrator: CLIOrchestrator instance
            template_name: Name of template to run
            initial_input: Optional initial input to send

        Returns:
            Execution result dictionary
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        logger.info(f"Running template: {template_name}")
        start_time = time.time()

        # Send initial input if provided
        if initial_input:
            orchestrator.send(initial_input)
            time.sleep(0.5)

        # Main automation loop
        iterations = 0
        actions_taken = []

        while iterations < template.max_iterations:
            # Check timeout
            if time.time() - start_time > template.timeout:
                logger.warning("Template execution timeout")
                break

            # Read current output
            output = orchestrator.read_output()
            if not output:
                time.sleep(0.5)
                continue

            # Match against patterns
            action = self.match_output(output, template_name)
            if not action:
                # No match, wait for more output
                time.sleep(0.5)
                continue

            # Execute action
            should_continue = self.execute_action(action, orchestrator)
            actions_taken.append({
                'iteration': iterations,
                'pattern': action.match,
                'action_type': action.action_type.value,
                'description': action.description,
            })

            if not should_continue:
                logger.info("Exit action executed, stopping template")
                break

            iterations += 1

        duration = time.time() - start_time

        return {
            'template_name': template_name,
            'iterations': iterations,
            'actions_taken': len(actions_taken),
            'duration': duration,
            'status': 'completed',
            'actions': actions_taken,
        }

    def _register_builtin_templates(self):
        """Register built-in templates."""
        self.register_template(GIT_COMMIT_TEMPLATE)
        self.register_template(AI_CODE_REVIEW_TEMPLATE)
        self.register_template(BUILD_TEST_TEMPLATE)

    def list_templates(self) -> List[str]:
        """List all registered template names."""
        return list(self.templates.keys())

    def get_template(self, name: str) -> Optional[IOTemplate]:
        """Get template by name."""
        return self.templates.get(name)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_simple_template(
    name: str,
    patterns: Dict[str, str],
) -> IOTemplate:
    """
    Create a simple template from pattern->action dict.

    Args:
        name: Template name
        patterns: Dict of {pattern: action_text}

    Returns:
        IOTemplate
    """
    pattern_actions = [
        PatternAction(
            match=pattern,
            action_type=ActionType.SEND_INPUT,
            action_value=action,
        )
        for pattern, action in patterns.items()
    ]

    return IOTemplate(
        name=name,
        patterns=pattern_actions,
    )


if __name__ == "__main__":
    # Demo usage
    print("Template Engine Demo")
    print("=" * 60)

    engine = TemplateEngine()

    print(f"\nRegistered templates: {', '.join(engine.list_templates())}")

    # Test pattern matching
    test_output = "Found 3 security vulnerabilities in the code"
    action = engine.match_output(test_output, "ai_code_review")

    if action:
        print(f"\nPattern matched!")
        print(f"  Pattern: {action.match}")
        print(f"  Action: {action.action_type.value}")
        print(f"  Value: {action.action_value}")
        print(f"  Description: {action.description}")
