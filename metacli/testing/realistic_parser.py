"""
Realistic Output Parser - Parse two-part AI CLI output format

Handles:
- Part 1: Base64-encoded text output
- Part 2: Hex sequence
- Keyword detection in decoded text
"""

from __future__ import annotations
import base64
import re
from dataclasses import dataclass
from typing import List, Optional, Set


# Keywords to detect in output
DETECTION_KEYWORDS = ['identified', 'error', 'complete', 'refactor', 'optimize']


@dataclass
class ParsedOutput:
    """
    Parsed two-part AI CLI output.

    Attributes:
        raw_output: Original raw output
        base64_part: Raw base64 string
        hex_part: Raw hex string
        decoded_text: Decoded text from base64
        detected_keywords: Keywords found in decoded text
        has_error: Whether 'error' keyword was detected
        is_complete: Whether 'complete' keyword was detected
    """
    raw_output: str
    base64_part: str
    hex_part: str
    decoded_text: str
    detected_keywords: Set[str]

    @property
    def has_error(self) -> bool:
        """Check if output contains 'error' keyword."""
        return 'error' in self.detected_keywords

    @property
    def is_complete(self) -> bool:
        """Check if output contains 'complete' keyword."""
        return 'complete' in self.detected_keywords

    @property
    def needs_refactor(self) -> bool:
        """Check if output contains 'refactor' keyword."""
        return 'refactor' in self.detected_keywords

    @property
    def needs_optimize(self) -> bool:
        """Check if output contains 'optimize' keyword."""
        return 'optimize' in self.detected_keywords

    @property
    def has_identified_issues(self) -> bool:
        """Check if output contains 'identified' keyword."""
        return 'identified' in self.detected_keywords


class RealisticOutputParser:
    """
    Parser for two-part AI CLI output format.

    Format:
        [OUTPUT-PART-1-BASE64]
        <base64-encoded-text>

        [OUTPUT-PART-2-HEX]
        <hex-sequence>

    Example:
        parser = RealisticOutputParser()
        parsed = parser.parse(cli_output)

        if parsed.has_error:
            print(f"Error detected: {parsed.decoded_text}")

        if parsed.is_complete:
            print("Task completed successfully")
    """

    def __init__(self):
        # Regex patterns for parsing
        self.part1_pattern = re.compile(
            r'\[OUTPUT-PART-1-BASE64\]\s*\n([A-Za-z0-9+/=\n]+)',
            re.MULTILINE
        )
        self.part2_pattern = re.compile(
            r'\[OUTPUT-PART-2-HEX\]\s*\n([0-9a-fA-F\n]+)',
            re.MULTILINE
        )

    def parse(self, output: str) -> Optional[ParsedOutput]:
        """
        Parse two-part output format.

        Args:
            output: Raw CLI output

        Returns:
            ParsedOutput object or None if parsing fails
        """
        # Extract base64 part
        base64_match = self.part1_pattern.search(output)
        if not base64_match:
            return None

        base64_part = base64_match.group(1).replace('\n', '').strip()

        # Extract hex part
        hex_match = self.part2_pattern.search(output)
        if not hex_match:
            return None

        hex_part = hex_match.group(1).replace('\n', '').strip()

        # Decode base64 to text
        try:
            decoded_bytes = base64.b64decode(base64_part)
            decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        except Exception:
            decoded_text = ""

        # Detect keywords
        detected_keywords = self._detect_keywords(decoded_text)

        return ParsedOutput(
            raw_output=output,
            base64_part=base64_part,
            hex_part=hex_part,
            decoded_text=decoded_text,
            detected_keywords=detected_keywords
        )

    def _detect_keywords(self, text: str) -> Set[str]:
        """
        Detect keywords in text.

        Args:
            text: Text to search

        Returns:
            Set of detected keywords
        """
        text_lower = text.lower()
        detected = set()

        for keyword in DETECTION_KEYWORDS:
            if keyword in text_lower:
                detected.add(keyword)

        return detected

    def quick_check_keyword(self, output: str, keyword: str) -> bool:
        """
        Quick check if output contains specific keyword without full parsing.

        Args:
            output: Raw CLI output
            keyword: Keyword to check for

        Returns:
            True if keyword detected
        """
        parsed = self.parse(output)
        if not parsed:
            return False

        return keyword in parsed.detected_keywords

    def extract_text_only(self, output: str) -> str:
        """
        Extract and decode only the text part (base64).

        Args:
            output: Raw CLI output

        Returns:
            Decoded text or empty string
        """
        parsed = self.parse(output)
        if not parsed:
            return ""

        return parsed.decoded_text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Keyword-Based Routing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class RoutingRule:
    """
    Rule for routing based on detected keywords.

    Attributes:
        keywords: Keywords that trigger this rule
        next_action: Action to take when triggered
        priority: Rule priority (higher = checked first)
    """
    keywords: Set[str]
    next_action: str
    priority: int = 0


class KeywordRouter:
    """
    Route to next action based on detected keywords.

    Example:
        router = KeywordRouter()
        router.add_rule({'error'}, 'Fix the error', priority=10)
        router.add_rule({'complete'}, 'Proceed to next step', priority=5)

        parsed = parser.parse(output)
        next_action = router.route(parsed)
    """

    def __init__(self):
        self.rules: List[RoutingRule] = []

    def add_rule(self, keywords: Set[str], next_action: str, priority: int = 0):
        """
        Add routing rule.

        Args:
            keywords: Keywords that trigger this rule
            next_action: Action to take
            priority: Rule priority (higher = checked first)
        """
        rule = RoutingRule(
            keywords=keywords,
            next_action=next_action,
            priority=priority
        )
        self.rules.append(rule)

        # Sort by priority (descending)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def route(self, parsed: ParsedOutput, default: str = "Continue") -> str:
        """
        Determine next action based on detected keywords.

        Args:
            parsed: Parsed output
            default: Default action if no rules match

        Returns:
            Next action string
        """
        for rule in self.rules:
            # Check if any keyword from rule matches
            if rule.keywords & parsed.detected_keywords:
                return rule.next_action

        return default

    def route_from_output(
        self,
        output: str,
        parser: RealisticOutputParser,
        default: str = "Continue"
    ) -> str:
        """
        Parse output and route in one step.

        Args:
            output: Raw CLI output
            parser: Parser instance
            default: Default action

        Returns:
            Next action string
        """
        parsed = parser.parse(output)
        if not parsed:
            return default

        return self.route(parsed, default)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-configured Routers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_audit_refactor_router() -> KeywordRouter:
    """
    Create router for audit-refactor cycle.

    Routing logic:
    - 'error' → Fix the error
    - 'identified' → Load context about issues
    - 'complete' + 'refactor' → Generate verification plan
    - 'complete' → Proceed to next step
    - 'optimize' → Apply optimizations
    """
    router = KeywordRouter()

    # High priority: errors
    router.add_rule({'error'}, 'Fix the error immediately', priority=10)

    # Medium priority: specific actions
    router.add_rule({'identified'}, 'Load context about identified issues', priority=8)
    router.add_rule({'refactor'}, 'Generate refactoring plan', priority=7)
    router.add_rule({'optimize'}, 'Apply optimization suggestions', priority=7)

    # Low priority: completion
    router.add_rule({'complete'}, 'Proceed to next workflow step', priority=5)

    return router


def create_test_fix_router() -> KeywordRouter:
    """
    Create router for test-fix cycle.

    Routing logic:
    - 'error' → Debug and fix
    - 'identified' → Load test context
    - 'complete' → Run next test
    """
    router = KeywordRouter()

    router.add_rule({'error'}, 'Debug and fix the failing test', priority=10)
    router.add_rule({'identified'}, 'Load context about test failures', priority=8)
    router.add_rule({'complete'}, 'Run next test suite', priority=5)

    return router


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def parse_and_route(
    output: str,
    router: KeywordRouter = None,
    default: str = "Continue"
) -> tuple[Optional[ParsedOutput], str]:
    """
    Parse output and determine next action.

    Args:
        output: Raw CLI output
        router: Router to use (default: audit-refactor router)
        default: Default action

    Returns:
        Tuple of (parsed_output, next_action)
    """
    parser = RealisticOutputParser()
    parsed = parser.parse(output)

    if not parsed:
        return None, default

    if router is None:
        router = create_audit_refactor_router()

    next_action = router.route(parsed, default)

    return parsed, next_action
