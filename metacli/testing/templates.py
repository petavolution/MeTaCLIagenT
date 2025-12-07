"""
Response Template System

Define patterns for matching CLI outputs and generating follow-up commands.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Pattern
from enum import Enum


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MatchStrategy(Enum):
    """How to match output against pattern."""
    EXACT = "exact"  # Exact string match
    CONTAINS = "contains"  # Contains substring
    REGEX = "regex"  # Regex pattern
    FUZZY = "fuzzy"  # Fuzzy string match
    SEMANTIC = "semantic"  # Semantic similarity (future)


@dataclass
class ResponseTemplate:
    """
    Template for matching output and generating response.

    Example:
        template = ResponseTemplate(
            name="error_handler",
            pattern=r"Error: (.*)",
            response="Fix error: {match[1]}",
            strategy=MatchStrategy.REGEX
        )
    """
    name: str
    pattern: str  # Pattern to match in output
    response: str | Callable  # Response template or function
    strategy: MatchStrategy = MatchStrategy.CONTAINS

    # Optional configuration
    keywords: List[str] = field(default_factory=list)
    priority: int = 0  # Higher = checked first
    conditions: List[Callable] = field(default_factory=list)  # Additional conditions

    # Compiled pattern (set automatically)
    _compiled_pattern: Optional[Pattern] = field(default=None, repr=False)

    def __post_init__(self):
        """Compile regex pattern if needed."""
        if self.strategy == MatchStrategy.REGEX:
            self._compiled_pattern = re.compile(self.pattern, re.DOTALL | re.MULTILINE)

    def matches(self, output: str, context: Dict[str, Any] = None) -> bool:
        """Check if output matches this template."""
        context = context or {}

        # Check strategy-specific matching
        if self.strategy == MatchStrategy.EXACT:
            match = output == self.pattern

        elif self.strategy == MatchStrategy.CONTAINS:
            match = self.pattern.lower() in output.lower()

        elif self.strategy == MatchStrategy.REGEX:
            match = bool(self._compiled_pattern.search(output))

        elif self.strategy == MatchStrategy.FUZZY:
            match = self._fuzzy_match(output, self.pattern)

        else:
            match = False

        # Check additional conditions
        if match and self.conditions:
            for condition in self.conditions:
                if not condition(output, context):
                    return False

        return match

    def generate_response(self, output: str, context: Dict[str, Any] = None) -> str:
        """Generate response based on output."""
        context = context or {}

        # If response is callable, call it
        if callable(self.response):
            return self.response(output, context)

        # If response is template string, format it
        response = self.response

        # Extract regex match groups
        if self.strategy == MatchStrategy.REGEX:
            match = self._compiled_pattern.search(output)
            if match:
                # Replace {match[0]}, {match[1]}, etc.
                for i, group in enumerate(match.groups()):
                    response = response.replace(f"{{match[{i+1}]}}", group)
                response = response.replace("{match[0]}", match.group(0))

        # Replace context variables
        for key, value in context.items():
            response = response.replace(f"{{{key}}}", str(value))

        return response

    @staticmethod
    def _fuzzy_match(text: str, pattern: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy string matching."""
        # Simple implementation - can be improved with proper fuzzy matching
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        # Check if most words from pattern appear in text
        pattern_words = set(pattern_lower.split())
        text_words = set(text_lower.split())

        if not pattern_words:
            return False

        overlap = len(pattern_words & text_words)
        similarity = overlap / len(pattern_words)

        return similarity >= threshold


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Template Library
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TemplateLibrary:
    """
    Collection of response templates organized by category.

    Provides template matching, prioritization, and composition.
    """

    def __init__(self):
        self.templates: Dict[str, List[ResponseTemplate]] = {}
        self.global_templates: List[ResponseTemplate] = []

    def add_template(self, template: ResponseTemplate, category: str = "default"):
        """Add template to library."""
        if category not in self.templates:
            self.templates[category] = []

        self.templates[category].append(template)
        self._sort_category(category)

    def add_global_template(self, template: ResponseTemplate):
        """Add template that applies to all categories."""
        self.global_templates.append(template)
        self.global_templates.sort(key=lambda t: t.priority, reverse=True)

    def find_matching_template(
        self,
        output: str,
        category: str = "default",
        context: Dict[str, Any] = None
    ) -> Optional[ResponseTemplate]:
        """Find first matching template."""
        context = context or {}

        # Check category-specific templates first
        if category in self.templates:
            for template in self.templates[category]:
                if template.matches(output, context):
                    return template

        # Check global templates
        for template in self.global_templates:
            if template.matches(output, context):
                return template

        return None

    def generate_response(
        self,
        output: str,
        category: str = "default",
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Generate response for output."""
        template = self.find_matching_template(output, category, context)

        if template:
            return template.generate_response(output, context)

        return None

    def _sort_category(self, category: str):
        """Sort templates by priority."""
        self.templates[category].sort(key=lambda t: t.priority, reverse=True)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> TemplateLibrary:
        """Load template library from YAML file."""
        import yaml

        library = cls()

        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        # Load templates by category
        for category, templates in data.get("templates", {}).items():
            for template_data in templates:
                template = ResponseTemplate(
                    name=template_data["name"],
                    pattern=template_data["pattern"],
                    response=template_data["response"],
                    strategy=MatchStrategy(template_data.get("strategy", "contains")),
                    keywords=template_data.get("keywords", []),
                    priority=template_data.get("priority", 0)
                )
                library.add_template(template, category)

        # Load global templates
        for template_data in data.get("global_templates", []):
            template = ResponseTemplate(
                name=template_data["name"],
                pattern=template_data["pattern"],
                response=template_data["response"],
                strategy=MatchStrategy(template_data.get("strategy", "contains")),
                priority=template_data.get("priority", 0)
            )
            library.add_global_template(template)

        return library


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Response Matcher
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResponseMatcher:
    """
    Matches CLI outputs to follow-up commands using templates.

    Example workflow:
        output = "Error: File not found"
        matcher = ResponseMatcher(template_library)
        next_command = matcher.match(output, category="error_handling")
        # next_command = "Check if file exists first"
    """

    def __init__(self, library: TemplateLibrary):
        self.library = library
        self.match_history: List[Dict[str, Any]] = []

    def match(
        self,
        output: str,
        category: str = "default",
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Match output to template and generate response.

        Args:
            output: CLI tool output
            category: Template category
            context: Additional context variables

        Returns:
            Generated response command or None
        """
        context = context or {}

        # Find matching template
        template = self.library.find_matching_template(output, category, context)

        if not template:
            return None

        # Generate response
        response = template.generate_response(output, context)

        # Record match
        self.match_history.append({
            "output": output,
            "template": template.name,
            "response": response,
            "category": category,
            "context": context
        })

        return response

    def get_match_history(self) -> List[Dict[str, Any]]:
        """Get history of all matches."""
        return self.match_history


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-Built Template Libraries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_coding_templates() -> TemplateLibrary:
    """Create template library for AI coding tools."""
    library = TemplateLibrary()

    # Error handling templates
    error_templates = [
        ResponseTemplate(
            name="syntax_error",
            pattern=r"SyntaxError.*line (\d+)",
            response="Fix syntax error on line {match[1]}",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
        ResponseTemplate(
            name="import_error",
            pattern=r"ImportError|ModuleNotFoundError",
            response="Add missing import statement",
            strategy=MatchStrategy.REGEX,
            priority=9
        ),
        ResponseTemplate(
            name="general_error",
            pattern="error",
            response="Debug and fix the error",
            strategy=MatchStrategy.CONTAINS,
            priority=1
        ),
    ]

    for template in error_templates:
        library.add_template(template, "error_handling")

    # Code review templates
    review_templates = [
        ResponseTemplate(
            name="has_code",
            pattern=r"```(\w+)",
            response="Review the {match[1]} code for issues",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
        ResponseTemplate(
            name="optimization",
            pattern="performance|slow|optimize",
            response="Optimize the code for better performance",
            strategy=MatchStrategy.CONTAINS,
            priority=5
        ),
    ]

    for template in review_templates:
        library.add_template(template, "code_review")

    # Test result templates
    test_templates = [
        ResponseTemplate(
            name="tests_failed",
            pattern=r"(\d+)\s+failed",
            response="Fix the {match[1]} failing tests",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
        ResponseTemplate(
            name="tests_passed",
            pattern=r"(\d+)\s+passed.*0\s+failed",
            response="All tests passed, continue to next step",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
    ]

    for template in test_templates:
        library.add_template(template, "testing")

    # Global templates (apply to all categories)
    library.add_global_template(
        ResponseTemplate(
            name="success",
            pattern=r"(success|complete|done|finished)",
            response="Task completed successfully, proceed to next step",
            strategy=MatchStrategy.REGEX,
            priority=5
        )
    )

    return library


def create_audit_refactor_templates() -> TemplateLibrary:
    """
    Create templates for audit → refactor → verify cycle.

    Specifically designed for the user's use case.
    """
    library = TemplateLibrary()

    # Audit phase templates
    audit_templates = [
        ResponseTemplate(
            name="found_issues",
            pattern=r"Found (\d+) issue",
            response="Load context about the {match[1]} issues found",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
        ResponseTemplate(
            name="audit_complete",
            pattern="audit complete|analysis complete",
            response="Load relevant context for refactoring",
            strategy=MatchStrategy.FUZZY,
            priority=5
        ),
    ]

    for template in audit_templates:
        library.add_template(template, "audit")

    # Load context templates
    context_templates = [
        ResponseTemplate(
            name="context_loaded",
            pattern="context loaded|files loaded",
            response="Begin refactoring based on audit findings",
            strategy=MatchStrategy.FUZZY,
            priority=10
        ),
    ]

    for template in context_templates:
        library.add_template(template, "load_context")

    # Refactor templates
    refactor_templates = [
        ResponseTemplate(
            name="refactor_complete",
            pattern="refactor.*complete|changes.*applied",
            response="Generate plan for verification",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
        ResponseTemplate(
            name="refactor_partial",
            pattern=r"refactored (\d+) of (\d+)",
            response="Continue refactoring remaining items",
            strategy=MatchStrategy.REGEX,
            priority=9
        ),
    ]

    for template in refactor_templates:
        library.add_template(template, "refactor")

    # Verification templates
    verify_templates = [
        ResponseTemplate(
            name="verification_passed",
            pattern="verification.*pass|tests.*pass",
            response="Continue to meta-refactor stage",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
        ResponseTemplate(
            name="verification_failed",
            pattern="verification.*fail|tests.*fail",
            response="Fix issues and re-verify",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
    ]

    for template in verify_templates:
        library.add_template(template, "verify")

    # Meta-refactor templates
    meta_templates = [
        ResponseTemplate(
            name="meta_complete",
            pattern="meta.*complete|workflow.*optimized",
            response="Cycle complete, ready for next iteration",
            strategy=MatchStrategy.REGEX,
            priority=10
        ),
    ]

    for template in meta_templates:
        library.add_template(template, "meta_refactor")

    return library
