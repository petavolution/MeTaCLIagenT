"""
Workflow Patterns - Pre-built Orchestration Patterns

Common workflow patterns for iterative development:
- Audit → Load → Refactor → Test loop
- Generate → Review → Fix cycle
- Plan → Execute → Validate pattern

Example:
    from metacli.core.patterns import audit_refactor_cycle

    workflow = audit_refactor_cycle(
        audit_tool="claude-code",
        refactor_tool="aider",
        max_iterations=3
    )
    result = workflow.run()
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from .decision import (
    Decision, DecisionType, DecisionFunc,
    has_errors_decision, test_pass_decision,
    code_quality_decision, max_iterations_decision,
    PromptTemplate,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowPattern:
    """
    Base class for workflow patterns.

    Provides structure for building complex, iterative workflows.
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        tool: str,
        prompt: str | PromptTemplate,
        condition: Optional[str] = None,
        decision: Optional[DecisionFunc] = None,
        max_iterations: Optional[int] = None,
        **kwargs
    ):
        """Add a step to the pattern."""
        self.steps.append({
            "name": name,
            "tool": tool,
            "prompt": prompt,
            "condition": condition,
            "decision": decision,
            "max_iterations": max_iterations,
            **kwargs
        })

    def build(self):
        """Build the workflow (override in subclasses)."""
        return self


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-built Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def audit_refactor_cycle(
    target: str,
    audit_tool: str = "claude-code",
    refactor_tool: str = "aider",
    max_iterations: int = 3,
) -> Dict[str, Any]:
    """
    Pattern: Audit codebase → Load context → Refactor → Verify

    Iterates until no errors or max iterations reached.

    Args:
        target: Code/file to audit and refactor
        audit_tool: Tool for auditing (default: claude-code)
        refactor_tool: Tool for refactoring (default: aider)
        max_iterations: Max refactor iterations

    Returns:
        Workflow definition dict

    Example:
        pattern = audit_refactor_cycle("src/api.py", max_iterations=3)
    """
    return {
        "name": "audit-refactor-cycle",
        "description": "Audit → Load → Refactor → Verify loop",
        "steps": [
            {
                "name": "audit",
                "tool": audit_tool,
                "prompt": f"Audit this code for issues: {target}",
                "decision": code_quality_decision,
            },
            {
                "name": "load_context",
                "tool": audit_tool,
                "prompt": f"Load and understand the context of: {target}",
            },
            {
                "name": "refactor",
                "tool": refactor_tool,
                "prompt": PromptTemplate(
                    "Refactor based on audit findings. Iteration {{iteration}}/{{max_iterations}}"
                ),
                "decision": max_iterations_decision(max_iterations),
                "loop_to": "verify",
            },
            {
                "name": "verify",
                "tool": audit_tool,
                "prompt": "Verify the refactoring is correct",
                "decision": has_errors_decision,
                "loop_back_to": "refactor",
            },
        ],
        "context": {
            "target": target,
            "max_iterations": max_iterations,
            "iteration": 0,
        },
    }


def generate_review_fix_cycle(
    task: str,
    generator: str = "claude-code",
    reviewer: str = "gemini",
    fixer: str = "aider",
    max_fixes: int = 2,
) -> Dict[str, Any]:
    """
    Pattern: Generate code → Review → Fix issues → Repeat

    Args:
        task: Task description
        generator: Tool for code generation
        reviewer: Tool for code review
        fixer: Tool for fixing issues
        max_fixes: Max fix iterations

    Returns:
        Workflow definition dict

    Example:
        pattern = generate_review_fix_cycle("Implement user authentication")
    """
    return {
        "name": "generate-review-fix",
        "description": "Generate → Review → Fix cycle",
        "steps": [
            {
                "name": "generate",
                "tool": generator,
                "prompt": f"Generate code for: {task}",
                "decision": code_quality_decision,
            },
            {
                "name": "review",
                "tool": reviewer,
                "prompt": PromptTemplate(
                    "Review this code for bugs, security issues, and improvements:\n\n{{previous_output}}"
                ),
                "use_previous": True,
            },
            {
                "name": "fix",
                "tool": fixer,
                "prompt": PromptTemplate(
                    "Fix the issues found in review. Iteration {{iteration}}/{{max_fixes}}"
                ),
                "decision": max_iterations_decision(max_fixes),
                "loop_back_to": "review",
                "condition": "has_errors",
            },
        ],
        "context": {
            "task": task,
            "max_fixes": max_fixes,
            "iteration": 0,
        },
    }


def plan_execute_validate_pattern(
    goal: str,
    planner: str = "claude-code",
    executor: str = "aider",
    validator: str = "python",
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """
    Pattern: Generate plan → Execute plan → Validate → Iterate

    Args:
        goal: High-level goal
        planner: Tool for planning
        executor: Tool for execution
        validator: Tool for validation
        max_attempts: Max execution attempts

    Returns:
        Workflow definition dict

    Example:
        pattern = plan_execute_validate_pattern("Build REST API")
    """
    return {
        "name": "plan-execute-validate",
        "description": "Plan → Execute → Validate cycle",
        "steps": [
            {
                "name": "generate_plan",
                "tool": planner,
                "prompt": f"Generate a detailed implementation plan for: {goal}",
            },
            {
                "name": "execute_plan",
                "tool": executor,
                "prompt": PromptTemplate(
                    "Execute this plan:\n\n{{plan}}\n\nAttempt {{iteration}}/{{max_attempts}}"
                ),
                "use_previous": True,
            },
            {
                "name": "validate",
                "tool": validator,
                "prompt": "pytest -v",
                "decision": test_pass_decision,
                "loop_back_to": "execute_plan",
            },
            {
                "name": "refine_plan",
                "tool": planner,
                "prompt": PromptTemplate(
                    "Plan failed validation. Refine the plan based on errors:\n\n{{errors}}"
                ),
                "condition": "has_errors",
                "decision": max_iterations_decision(max_attempts),
                "loop_to": "execute_plan",
            },
        ],
        "context": {
            "goal": goal,
            "max_attempts": max_attempts,
            "iteration": 0,
        },
    }


def iterative_refinement_pattern(
    initial_task: str,
    tool: str = "claude-code",
    refinement_prompt: str = "Improve and refine the previous output",
    iterations: int = 3,
) -> Dict[str, Any]:
    """
    Pattern: Initial generation → Iterative refinement

    Args:
        initial_task: Initial task description
        tool: Tool to use for all steps
        refinement_prompt: Prompt for refinement steps
        iterations: Number of refinement iterations

    Returns:
        Workflow definition dict

    Example:
        pattern = iterative_refinement_pattern("Write API documentation", iterations=3)
    """
    return {
        "name": "iterative-refinement",
        "description": "Initial → Refine → Refine → ... cycle",
        "steps": [
            {
                "name": "initial",
                "tool": tool,
                "prompt": initial_task,
            },
            {
                "name": "refine",
                "tool": tool,
                "prompt": PromptTemplate(
                    f"{refinement_prompt}. Iteration {{{{iteration}}}}/{iterations}"
                ),
                "use_previous": True,
                "decision": max_iterations_decision(iterations),
                "loop_to": "refine",  # Loop to self
            },
        ],
        "context": {
            "initial_task": initial_task,
            "iterations": iterations,
            "iteration": 0,
        },
    }


def test_driven_development_pattern(
    feature: str,
    test_tool: str = "claude-code",
    impl_tool: str = "claude-code",
    fix_tool: str = "aider",
    runner: str = "python",
    max_fix_iterations: int = 3,
) -> Dict[str, Any]:
    """
    Pattern: Write tests → Implement → Run tests → Fix → Repeat

    Args:
        feature: Feature to implement
        test_tool: Tool for writing tests
        impl_tool: Tool for implementation
        fix_tool: Tool for fixing failures
        runner: Tool for running tests
        max_fix_iterations: Max fix attempts

    Returns:
        Workflow definition dict

    Example:
        pattern = test_driven_development_pattern("User authentication")
    """
    return {
        "name": "tdd-cycle",
        "description": "TDD: Tests → Implement → Run → Fix cycle",
        "steps": [
            {
                "name": "write_tests",
                "tool": test_tool,
                "prompt": f"Write comprehensive tests for: {feature}",
            },
            {
                "name": "implement",
                "tool": impl_tool,
                "prompt": f"Implement the feature to pass the tests: {feature}",
                "use_previous": True,
            },
            {
                "name": "run_tests",
                "tool": runner,
                "prompt": "pytest -v",
                "decision": test_pass_decision,
            },
            {
                "name": "fix_failures",
                "tool": fix_tool,
                "prompt": PromptTemplate(
                    "Fix the {{test_failures}} failing tests. Iteration {{iteration}}/{{max_fixes}}"
                ),
                "condition": "has_errors",
                "decision": max_iterations_decision(max_fix_iterations),
                "loop_to": "run_tests",
            },
        ],
        "context": {
            "feature": feature,
            "max_fixes": max_fix_iterations,
            "iteration": 0,
        },
    }


def multi_agent_consensus_pattern(
    question: str,
    agents: List[str] = None,
    synthesizer: str = "claude-code",
) -> Dict[str, Any]:
    """
    Pattern: Ask multiple agents → Synthesize consensus

    Args:
        question: Question to ask all agents
        agents: List of agent tools (default: claude-code, gemini, ollama)
        synthesizer: Tool to synthesize consensus

    Returns:
        Workflow definition dict

    Example:
        pattern = multi_agent_consensus_pattern(
            "What's the best architecture for this API?",
            agents=["claude-code", "gemini", "ollama"]
        )
    """
    if agents is None:
        agents = ["claude-code", "gemini", "ollama"]

    steps = [
        {
            "name": f"agent_{i}",
            "tool": agent,
            "prompt": question,
        }
        for i, agent in enumerate(agents)
    ]

    steps.append({
        "name": "synthesize",
        "tool": synthesizer,
        "prompt": PromptTemplate(
            f"Synthesize a consensus from these {len(agents)} agent responses:\n\n{{{{all_outputs}}}}"
        ),
    })

    return {
        "name": "multi-agent-consensus",
        "description": "Multiple agents → Synthesis",
        "steps": steps,
        "context": {
            "question": question,
            "agents": agents,
        },
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERNS = {
    "audit_refactor": audit_refactor_cycle,
    "generate_review_fix": generate_review_fix_cycle,
    "plan_execute_validate": plan_execute_validate_pattern,
    "iterative_refinement": iterative_refinement_pattern,
    "tdd": test_driven_development_pattern,
    "multi_agent_consensus": multi_agent_consensus_pattern,
}


def get_pattern(name: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Get a pre-built workflow pattern.

    Args:
        name: Pattern name
        **kwargs: Pattern-specific parameters

    Returns:
        Workflow definition dict or None

    Example:
        pattern = get_pattern("audit_refactor", target="src/api.py", max_iterations=3)
    """
    pattern_func = PATTERNS.get(name)
    if pattern_func:
        return pattern_func(**kwargs)
    return None


def list_patterns() -> List[str]:
    """List all available patterns."""
    return list(PATTERNS.keys())
