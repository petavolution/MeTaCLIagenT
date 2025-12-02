"""
Decision Engine - Conditional Routing & Dynamic Prompt Generation

Analyze step outputs, make routing decisions, and generate dynamic prompts
for complex iterative workflows.

Features:
- Conditional execution (if/else)
- Output analysis
- Dynamic prompt generation
- Context-aware routing

Example:
    from metacli.core import DecisionEngine, Decision

    # Analyze output and decide next step
    decision = DecisionEngine.analyze(output, context)
    if decision.should_continue:
        next_prompt = decision.generate_prompt()
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Decision Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DecisionType(Enum):
    """Types of routing decisions."""
    CONTINUE = "continue"      # Continue to next step
    BRANCH = "branch"          # Branch to specific step
    LOOP = "loop"              # Loop back to previous step
    DELEGATE = "delegate"      # Delegate to sub-agent
    STOP = "stop"              # Stop execution
    RETRY = "retry"            # Retry current step


@dataclass
class Decision:
    """Result of a decision analysis."""
    type: DecisionType
    reason: str
    next_step: Optional[str] = None        # Step name to go to
    next_prompt: Optional[str] = None      # Generated prompt
    context: Dict[str, Any] = field(default_factory=dict)  # Updated context
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def should_continue(self) -> bool:
        """Whether execution should continue."""
        return self.type not in [DecisionType.STOP]

    @property
    def should_loop(self) -> bool:
        """Whether to loop back."""
        return self.type == DecisionType.LOOP

    @property
    def should_delegate(self) -> bool:
        """Whether to delegate to sub-agent."""
        return self.type == DecisionType.DELEGATE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Decision Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DecisionFunc = Callable[[str, Dict[str, Any]], Decision]


def has_errors_decision(output: str, context: Dict[str, Any]) -> Decision:
    """
    Decision: If output has errors, loop to fix them.

    Example:
        step.decision = has_errors_decision
    """
    from .parser import OutputParser

    if OutputParser.has_errors(output):
        errors = OutputParser.extract_errors(output)
        return Decision(
            type=DecisionType.LOOP,
            reason="Errors detected in output",
            next_prompt=f"Fix these errors:\n{errors[0] if errors else output[:500]}",
            context={**context, "error_count": context.get("error_count", 0) + 1},
        )
    else:
        return Decision(
            type=DecisionType.CONTINUE,
            reason="No errors detected",
            context=context,
        )


def max_iterations_decision(max_iter: int = 3) -> DecisionFunc:
    """
    Decision factory: Continue looping until max iterations reached.

    Example:
        step.decision = max_iterations_decision(5)
    """
    def _decision(output: str, context: Dict[str, Any]) -> Decision:
        iteration = context.get("iteration", 0) + 1
        context["iteration"] = iteration

        if iteration >= max_iter:
            return Decision(
                type=DecisionType.STOP,
                reason=f"Reached max iterations ({max_iter})",
                context=context,
            )
        else:
            return Decision(
                type=DecisionType.CONTINUE,
                reason=f"Continue (iteration {iteration}/{max_iter})",
                context=context,
            )

    return _decision


def test_pass_decision(output: str, context: Dict[str, Any]) -> Decision:
    """
    Decision: If tests pass, continue; otherwise loop to fix.

    Example:
        step.decision = test_pass_decision
    """
    from .parser import OutputParser

    test_results = OutputParser.parse_test_results(output)

    if test_results["failed"] > 0:
        return Decision(
            type=DecisionType.LOOP,
            reason=f"{test_results['failed']} tests failed",
            next_prompt=f"Fix the {test_results['failed']} failing tests",
            context={**context, "test_failures": test_results["failed"]},
        )
    elif test_results["passed"] > 0:
        return Decision(
            type=DecisionType.CONTINUE,
            reason=f"All {test_results['passed']} tests passed",
            context=context,
        )
    else:
        return Decision(
            type=DecisionType.CONTINUE,
            reason="No test results found",
            context=context,
        )


def code_quality_decision(output: str, context: Dict[str, Any]) -> Decision:
    """
    Decision: Delegate to reviewer if code was generated.

    Example:
        step.decision = code_quality_decision
    """
    from .parser import OutputParser

    code_blocks = OutputParser.extract_code_blocks(output)

    if code_blocks:
        return Decision(
            type=DecisionType.DELEGATE,
            reason=f"Code generated ({len(code_blocks)} blocks), delegate to reviewer",
            next_step="review",
            next_prompt=f"Review this code for bugs and security issues:\n\n{output[:1000]}",
            context={**context, "code_blocks": len(code_blocks)},
        )
    else:
        return Decision(
            type=DecisionType.CONTINUE,
            reason="No code generated",
            context=context,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Decision Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DecisionEngine:
    """
    Analyze outputs and make routing decisions.

    Features:
    - Built-in decision functions
    - Custom decision logic
    - Context tracking
    - Dynamic prompt generation
    """

    # Built-in decision functions
    DECISIONS = {
        "has_errors": has_errors_decision,
        "test_pass": test_pass_decision,
        "code_quality": code_quality_decision,
    }

    @classmethod
    def analyze(
        cls,
        output: str,
        context: Dict[str, Any],
        decision_func: Optional[DecisionFunc] = None,
    ) -> Decision:
        """
        Analyze output and make routing decision.

        Args:
            output: Step output to analyze
            context: Current execution context
            decision_func: Optional custom decision function

        Returns:
            Decision object

        Example:
            decision = DecisionEngine.analyze(output, context, has_errors_decision)
            if decision.should_loop:
                # Loop back with new prompt
                next_prompt = decision.next_prompt
        """
        if decision_func:
            return decision_func(output, context)
        else:
            # Default: continue
            return Decision(
                type=DecisionType.CONTINUE,
                reason="No decision function specified",
                context=context,
            )

    @classmethod
    def get_decision(cls, name: str) -> Optional[DecisionFunc]:
        """Get built-in decision function by name."""
        return cls.DECISIONS.get(name)

    @classmethod
    def register_decision(cls, name: str, func: DecisionFunc):
        """Register custom decision function."""
        cls.DECISIONS[name] = func


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PromptTemplate:
    """
    Dynamic prompt generation with variable substitution.

    Example:
        template = PromptTemplate("Fix {{error_count}} errors: {{error_list}}")
        prompt = template.render({"error_count": 3, "error_list": "..."})
    """

    def __init__(self, template: str):
        self.template = template

    def render(self, context: Dict[str, Any]) -> str:
        """Render template with context variables."""
        result = self.template

        # Simple {{var}} substitution
        for key, value in context.items():
            pattern = r'\{\{' + re.escape(key) + r'\}\}'
            result = re.sub(pattern, str(value), result)

        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Condition Evaluators
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ConditionFunc = Callable[[str, Dict[str, Any]], bool]


def has_errors_condition(output: str, context: Dict[str, Any]) -> bool:
    """Condition: Output contains errors."""
    from .parser import OutputParser
    return OutputParser.has_errors(output)


def has_code_condition(output: str, context: Dict[str, Any]) -> bool:
    """Condition: Output contains code blocks."""
    from .parser import OutputParser
    return len(OutputParser.extract_code_blocks(output)) > 0


def iteration_limit_condition(max_iter: int) -> ConditionFunc:
    """Condition factory: Iteration count below limit."""
    def _condition(output: str, context: Dict[str, Any]) -> bool:
        return context.get("iteration", 0) < max_iter
    return _condition


class Condition:
    """Condition evaluator for workflow branching."""

    BUILT_IN = {
        "has_errors": has_errors_condition,
        "has_code": has_code_condition,
    }

    @classmethod
    def evaluate(
        cls,
        condition: Optional[str | ConditionFunc],
        output: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        Evaluate condition.

        Args:
            condition: Condition name, function, or None (always True)
            output: Step output
            context: Execution context

        Returns:
            True if condition met
        """
        if condition is None:
            return True
        elif isinstance(condition, str):
            func = cls.BUILT_IN.get(condition)
            if func:
                return func(output, context)
            else:
                return True
        elif callable(condition):
            return condition(output, context)
        else:
            return True
