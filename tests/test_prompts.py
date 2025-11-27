#!/usr/bin/env python3
"""
Test Prompt Library - Prompts and Pattern-Based Follow-ups

This module contains:
1. Categorized test prompts
2. Pattern definitions (test strings to look for in output)
3. Follow-up prompts based on patterns found

The pattern matcher uses these to create intelligent multi-step test workflows.
"""

import hashlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Structures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TestPrompt:
    """A test prompt with metadata."""
    category: str
    prompt: str
    description: str
    expected_patterns: List[str]  # Patterns we expect in output


@dataclass
class PatternRule:
    """A pattern-matching rule for follow-up prompts."""
    pattern: str  # String to look for in output
    pattern_hash: str  # MD5 hash for fast lookup
    follow_up_prompt: str
    description: str
    category: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Prompts Library
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEST_PROMPTS = {
    # Code Generation Prompts
    "code_generation": [
        TestPrompt(
            category="code_generation",
            prompt="Write a Python function to calculate fibonacci numbers",
            description="Basic function generation",
            expected_patterns=["def", "fibonacci", "return"]
        ),
        TestPrompt(
            category="code_generation",
            prompt="Create a REST API endpoint for user registration",
            description="API endpoint generation",
            expected_patterns=["@app", "def", "register", "user"]
        ),
        TestPrompt(
            category="code_generation",
            prompt="Write a class for managing database connections",
            description="Class/OOP generation",
            expected_patterns=["class", "connect", "database"]
        ),
        TestPrompt(
            category="code_generation",
            prompt="Implement a binary search algorithm",
            description="Algorithm implementation",
            expected_patterns=["binary", "search", "return"]
        ),
    ],

    # Code Review Prompts
    "code_review": [
        TestPrompt(
            category="code_review",
            prompt="Review this code for security vulnerabilities",
            description="Security review",
            expected_patterns=["security", "vulnerability", "risk"]
        ),
        TestPrompt(
            category="code_review",
            prompt="Check this code for performance issues",
            description="Performance review",
            expected_patterns=["performance", "optimize", "efficiency"]
        ),
        TestPrompt(
            category="code_review",
            prompt="Analyze code quality and suggest improvements",
            description="Quality review",
            expected_patterns=["quality", "improve", "refactor"]
        ),
    ],

    # Bug Fix Prompts
    "bug_fix": [
        TestPrompt(
            category="bug_fix",
            prompt="Fix the security issues identified",
            description="Security fix",
            expected_patterns=["fixed", "secure", "updated"]
        ),
        TestPrompt(
            category="bug_fix",
            prompt="Optimize the performance bottlenecks",
            description="Performance fix",
            expected_patterns=["optimized", "faster", "improved"]
        ),
        TestPrompt(
            category="bug_fix",
            prompt="Refactor the code based on review feedback",
            description="Refactoring",
            expected_patterns=["refactored", "clean", "improved"]
        ),
    ],

    # Testing Prompts
    "testing": [
        TestPrompt(
            category="testing",
            prompt="Write unit tests for this function",
            description="Unit test generation",
            expected_patterns=["test", "assert", "def test_"]
        ),
        TestPrompt(
            category="testing",
            prompt="Create integration tests for the API",
            description="Integration test generation",
            expected_patterns=["test", "api", "request"]
        ),
    ],

    # Documentation Prompts
    "documentation": [
        TestPrompt(
            category="documentation",
            prompt="Add docstrings to this code",
            description="Docstring generation",
            expected_patterns=["\"\"\"", "Args:", "Returns:"]
        ),
        TestPrompt(
            category="documentation",
            prompt="Write API documentation",
            description="API docs generation",
            expected_patterns=["endpoint", "parameter", "response"]
        ),
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern-Based Follow-up Rules
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _hash_pattern(pattern: str) -> str:
    """Generate MD5 hash for pattern (for fast lookup)."""
    return hashlib.md5(pattern.lower().encode()).hexdigest()


# Define pattern rules - when we see X in output, send Y as follow-up
PATTERN_RULES = [
    # Code generation patterns
    PatternRule(
        pattern="def ",
        pattern_hash=_hash_pattern("def "),
        follow_up_prompt="Review this code for security vulnerabilities",
        description="Function detected → Request security review",
        category="code_to_review"
    ),
    PatternRule(
        pattern="class ",
        pattern_hash=_hash_pattern("class "),
        follow_up_prompt="Analyze this class design and suggest improvements",
        description="Class detected → Request design review",
        category="code_to_review"
    ),
    PatternRule(
        pattern="@app.",
        pattern_hash=_hash_pattern("@app."),
        follow_up_prompt="Review this API endpoint for security and best practices",
        description="API endpoint detected → Request security review",
        category="code_to_review"
    ),

    # Review patterns
    PatternRule(
        pattern="vulnerability",
        pattern_hash=_hash_pattern("vulnerability"),
        follow_up_prompt="Fix the security vulnerabilities identified in the review",
        description="Vulnerability found → Request fix",
        category="review_to_fix"
    ),
    PatternRule(
        pattern="security issue",
        pattern_hash=_hash_pattern("security issue"),
        follow_up_prompt="Address the security issues mentioned above",
        description="Security issue found → Request fix",
        category="review_to_fix"
    ),
    PatternRule(
        pattern="performance",
        pattern_hash=_hash_pattern("performance"),
        follow_up_prompt="Optimize the performance issues identified",
        description="Performance issue found → Request optimization",
        category="review_to_fix"
    ),
    PatternRule(
        pattern="improve",
        pattern_hash=_hash_pattern("improve"),
        follow_up_prompt="Implement the improvements suggested in the review",
        description="Improvements suggested → Request implementation",
        category="review_to_fix"
    ),

    # Fix patterns
    PatternRule(
        pattern="fixed",
        pattern_hash=_hash_pattern("fixed"),
        follow_up_prompt="Write unit tests for the fixed code",
        description="Code fixed → Request tests",
        category="fix_to_test"
    ),
    PatternRule(
        pattern="optimized",
        pattern_hash=_hash_pattern("optimized"),
        follow_up_prompt="Verify the optimization with performance tests",
        description="Code optimized → Request performance tests",
        category="fix_to_test"
    ),
    PatternRule(
        pattern="refactored",
        pattern_hash=_hash_pattern("refactored"),
        follow_up_prompt="Add documentation for the refactored code",
        description="Code refactored → Request documentation",
        category="fix_to_docs"
    ),

    # Test patterns
    PatternRule(
        pattern="test_",
        pattern_hash=_hash_pattern("test_"),
        follow_up_prompt="Review the test coverage and suggest additional tests",
        description="Tests written → Request coverage review",
        category="test_to_review"
    ),
    PatternRule(
        pattern="assert",
        pattern_hash=_hash_pattern("assert"),
        follow_up_prompt="Verify these assertions cover all edge cases",
        description="Assertions found → Request edge case review",
        category="test_to_review"
    ),

    # Documentation patterns
    PatternRule(
        pattern='"""',
        pattern_hash=_hash_pattern('"""'),
        follow_up_prompt="Generate example usage code based on this documentation",
        description="Docstrings found → Request examples",
        category="docs_to_examples"
    ),
    PatternRule(
        pattern="Args:",
        pattern_hash=_hash_pattern("Args:"),
        follow_up_prompt="Create type hints based on this documentation",
        description="Args documented → Request type hints",
        category="docs_to_types"
    ),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern Lookup Tables (Hash-Based)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Build hash lookup table for fast pattern matching
PATTERN_HASH_TABLE: Dict[str, PatternRule] = {
    rule.pattern_hash: rule for rule in PATTERN_RULES
}

# Build text-based lookup (for substring matching)
PATTERN_TEXT_TABLE: Dict[str, PatternRule] = {
    rule.pattern: rule for rule in PATTERN_RULES
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_prompts_by_category(category: str) -> List[TestPrompt]:
    """Get all test prompts for a category."""
    return TEST_PROMPTS.get(category, [])


def get_all_prompts() -> List[TestPrompt]:
    """Get all test prompts (flattened)."""
    all_prompts = []
    for prompts in TEST_PROMPTS.values():
        all_prompts.extend(prompts)
    return all_prompts


def get_random_prompt(category: Optional[str] = None) -> TestPrompt:
    """Get a random test prompt, optionally from specific category."""
    import random

    if category:
        prompts = get_prompts_by_category(category)
    else:
        prompts = get_all_prompts()

    if not prompts:
        raise ValueError(f"No prompts available for category: {category}")

    return random.choice(prompts)


def find_patterns_in_output(output: str) -> List[PatternRule]:
    """
    Find all matching patterns in output.

    Uses simple substring matching (not hash-based for now,
    but hash table available for optimization).

    Args:
        output: CLI output text to analyze

    Returns:
        List of matching PatternRule objects
    """
    matches = []
    output_lower = output.lower()

    for pattern, rule in PATTERN_TEXT_TABLE.items():
        if pattern.lower() in output_lower:
            matches.append(rule)

    return matches


def get_follow_up_prompt(output: str, prefer_category: Optional[str] = None) -> Optional[str]:
    """
    Get appropriate follow-up prompt based on patterns in output.

    Args:
        output: CLI output to analyze
        prefer_category: Optionally prefer rules from this category

    Returns:
        Follow-up prompt text, or None if no patterns matched
    """
    matches = find_patterns_in_output(output)

    if not matches:
        return None

    # If category preference specified, filter matches
    if prefer_category:
        category_matches = [m for m in matches if m.category == prefer_category]
        if category_matches:
            matches = category_matches

    # Return first match's follow-up prompt
    # (Could be randomized or prioritized in future)
    return matches[0].follow_up_prompt


def get_test_workflow(workflow_type: str = "generate_review_fix") -> List[TestPrompt]:
    """
    Get a pre-defined test workflow sequence.

    Args:
        workflow_type: Type of workflow to generate

    Returns:
        List of prompts that form a logical workflow
    """
    workflows = {
        "generate_review_fix": [
            get_prompts_by_category("code_generation")[0],  # Generate code
            get_prompts_by_category("code_review")[0],      # Review code
            get_prompts_by_category("bug_fix")[0],          # Fix issues
        ],
        "code_test_doc": [
            get_prompts_by_category("code_generation")[1],  # Generate code
            get_prompts_by_category("testing")[0],          # Write tests
            get_prompts_by_category("documentation")[0],    # Add docs
        ],
        "review_optimize_test": [
            get_prompts_by_category("code_review")[1],      # Performance review
            get_prompts_by_category("bug_fix")[1],          # Optimize
            get_prompts_by_category("testing")[0],          # Test
        ],
    }

    return workflows.get(workflow_type, [])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Statistics and Info
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_library_stats() -> Dict:
    """Get statistics about the prompt library."""
    total_prompts = sum(len(prompts) for prompts in TEST_PROMPTS.values())

    return {
        "total_prompts": total_prompts,
        "categories": list(TEST_PROMPTS.keys()),
        "prompts_per_category": {cat: len(prompts) for cat, prompts in TEST_PROMPTS.items()},
        "total_pattern_rules": len(PATTERN_RULES),
        "pattern_categories": list(set(rule.category for rule in PATTERN_RULES)),
        "hash_table_size": len(PATTERN_HASH_TABLE),
    }


if __name__ == "__main__":
    # Demo usage
    print("Test Prompt Library")
    print("=" * 60)

    stats = get_library_stats()
    print(f"\nLibrary Statistics:")
    print(f"  Total prompts: {stats['total_prompts']}")
    print(f"  Categories: {', '.join(stats['categories'])}")
    print(f"  Pattern rules: {stats['total_pattern_rules']}")

    print(f"\nPrompts per category:")
    for cat, count in stats['prompts_per_category'].items():
        print(f"  {cat}: {count}")

    print(f"\nExample pattern matching:")
    test_output = 'def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)'
    matches = find_patterns_in_output(test_output)
    print(f"  Test output: {test_output[:60]}...")
    print(f"  Patterns found: {len(matches)}")
    for match in matches:
        print(f"    - Pattern '{match.pattern}' → {match.description}")

    follow_up = get_follow_up_prompt(test_output)
    if follow_up:
        print(f"\n  Suggested follow-up: {follow_up}")
