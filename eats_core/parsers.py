# parsers.py - Output Parsers for Structured Extraction
"""
Parse and validate LLM outputs into structured formats.

Features:
- JSON extraction with schema validation
- Regex-based parsing
- Code block extraction
- List/structured output parsing
- Retry logic for malformed outputs
- Type coercion and validation

Zero external dependencies (no Pydantic required).
"""

from __future__ import annotations
import re
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import (
    Dict, List, Optional, Any, Type, TypeVar, Callable,
    Union, Generic, Tuple, get_type_hints
)
from enum import Enum


T = TypeVar('T')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Parsing Result
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ParseResult(Generic[T]):
    """Result of a parsing operation."""
    success: bool
    value: Optional[T] = None
    raw: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0

    @classmethod
    def ok(cls, value: T, raw: str = None) -> 'ParseResult[T]':
        return cls(success=True, value=value, raw=raw)

    @classmethod
    def fail(cls, error: str, raw: str = None) -> 'ParseResult[T]':
        return cls(success=False, error=error, raw=raw)

    def unwrap(self) -> T:
        """Get value or raise error."""
        if not self.success:
            raise ValueError(f"Parse failed: {self.error}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get value or return default."""
        return self.value if self.success else default

    def map(self, fn: Callable[[T], Any]) -> 'ParseResult':
        """Transform the value if successful."""
        if self.success:
            try:
                return ParseResult.ok(fn(self.value), self.raw)
            except Exception as e:
                return ParseResult.fail(str(e), self.raw)
        return self


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Base Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OutputParser(ABC, Generic[T]):
    """Base class for output parsers."""

    @abstractmethod
    def parse(self, text: str) -> ParseResult[T]:
        """Parse text into structured output."""
        pass

    def __call__(self, text: str) -> ParseResult[T]:
        """Alias for parse."""
        return self.parse(text)

    def parse_strict(self, text: str) -> T:
        """Parse and raise on failure."""
        return self.parse(text).unwrap()

    def with_retry(
        self,
        retry_fn: Callable[[str, str], str],
        max_retries: int = 3
    ) -> 'RetryParser[T]':
        """Wrap parser with retry logic."""
        return RetryParser(self, retry_fn, max_retries)


class RetryParser(OutputParser[T]):
    """Parser that retries on failure using a correction function."""

    def __init__(
        self,
        base_parser: OutputParser[T],
        retry_fn: Callable[[str, str], str],  # (original, error) -> corrected
        max_retries: int = 3
    ):
        self.base_parser = base_parser
        self.retry_fn = retry_fn
        self.max_retries = max_retries

    def parse(self, text: str) -> ParseResult[T]:
        result = self.base_parser.parse(text)
        retries = 0

        while not result.success and retries < self.max_retries:
            # Get corrected output
            corrected = self.retry_fn(text, result.error)
            result = self.base_parser.parse(corrected)
            retries += 1
            text = corrected

        result.retries = retries
        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JSON Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class JSONParser(OutputParser[Dict]):
    """
    Parse JSON from LLM output.

    Handles:
    - JSON in code blocks
    - Raw JSON
    - JSON with trailing/leading text
    - Common formatting issues
    """

    # Patterns to find JSON
    JSON_BLOCK = re.compile(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', re.MULTILINE)
    JSON_OBJECT = re.compile(r'\{[\s\S]*\}')
    JSON_ARRAY = re.compile(r'\[[\s\S]*\]')

    def __init__(
        self,
        schema: Optional[Dict] = None,
        strict: bool = False,
        allow_partial: bool = True
    ):
        self.schema = schema
        self.strict = strict
        self.allow_partial = allow_partial

    def parse(self, text: str) -> ParseResult[Dict]:
        # Try to find JSON
        json_str = self._extract_json(text)

        if not json_str:
            return ParseResult.fail("No JSON found in output", text)

        # Clean up common issues
        json_str = self._clean_json(json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return ParseResult.fail(f"Invalid JSON: {e}", text)

        # Validate against schema if provided
        if self.schema:
            validation_error = self._validate_schema(data)
            if validation_error:
                return ParseResult.fail(validation_error, text)

        return ParseResult.ok(data, text)

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text."""
        # Try code block first
        match = self.JSON_BLOCK.search(text)
        if match:
            return match.group(1).strip()

        # Try to find raw JSON object
        match = self.JSON_OBJECT.search(text)
        if match:
            return match.group(0)

        # Try to find JSON array
        match = self.JSON_ARRAY.search(text)
        if match:
            return match.group(0)

        return None

    def _clean_json(self, json_str: str) -> str:
        """Clean up common JSON issues."""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)

        # Fix unquoted keys (simple cases)
        json_str = re.sub(r'(\{|,)\s*(\w+)\s*:', r'\1"\2":', json_str)

        # Remove comments
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)

        return json_str

    def _validate_schema(self, data: Any) -> Optional[str]:
        """Simple schema validation (type checking)."""
        if not isinstance(self.schema, dict):
            return None

        errors = []
        for key, expected_type in self.schema.items():
            if key not in data:
                if self.strict:
                    errors.append(f"Missing required field: {key}")
                continue

            value = data[key]

            # Type checking
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{key}' should be string, got {type(value).__name__}")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{key}' should be number, got {type(value).__name__}")
            elif expected_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{key}' should be boolean, got {type(value).__name__}")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Field '{key}' should be array, got {type(value).__name__}")
            elif expected_type == "object" and not isinstance(value, dict):
                errors.append(f"Field '{key}' should be object, got {type(value).__name__}")

        return "; ".join(errors) if errors else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Code Block Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CodeBlock:
    """Extracted code block."""
    code: str
    language: str = ""
    filename: Optional[str] = None


class CodeBlockParser(OutputParser[List[CodeBlock]]):
    """
    Extract code blocks from LLM output.

    Handles:
    - Fenced code blocks (```)
    - Language hints
    - Multiple blocks
    - Filename annotations
    """

    # Pattern: optional filename comment, then code block
    BLOCK_PATTERN = re.compile(
        r'(?:#+\s*(?:File:\s*)?([^\n]+\.[\w]+)\s*\n)?'  # Optional filename
        r'```(\w*)\s*\n'  # Opening fence with optional language
        r'([\s\S]*?)'    # Code content
        r'\n```',         # Closing fence
        re.MULTILINE
    )

    def __init__(
        self,
        language_filter: Optional[str] = None,
        include_inline: bool = False
    ):
        self.language_filter = language_filter
        self.include_inline = include_inline

    def parse(self, text: str) -> ParseResult[List[CodeBlock]]:
        blocks = []

        for match in self.BLOCK_PATTERN.finditer(text):
            filename = match.group(1)
            language = match.group(2) or ""
            code = match.group(3)

            # Apply language filter
            if self.language_filter:
                if language.lower() != self.language_filter.lower():
                    continue

            blocks.append(CodeBlock(
                code=code.strip(),
                language=language,
                filename=filename
            ))

        if not blocks:
            return ParseResult.fail("No code blocks found", text)

        return ParseResult.ok(blocks, text)

    def parse_first(self, text: str) -> ParseResult[CodeBlock]:
        """Get just the first code block."""
        result = self.parse(text)
        if result.success and result.value:
            return ParseResult.ok(result.value[0], text)
        return ParseResult.fail("No code block found", text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Regex Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RegexParser(OutputParser[Dict[str, str]]):
    """
    Extract data using regex patterns.

    Usage:
        parser = RegexParser({
            "score": r"Score:\s*(\d+)",
            "reason": r"Reason:\s*(.+)",
        })
    """

    def __init__(
        self,
        patterns: Dict[str, str],
        flags: int = 0
    ):
        self.patterns = {
            name: re.compile(pattern, flags)
            for name, pattern in patterns.items()
        }

    def parse(self, text: str) -> ParseResult[Dict[str, str]]:
        results = {}
        missing = []

        for name, pattern in self.patterns.items():
            match = pattern.search(text)
            if match:
                # Get first group if exists, else full match
                results[name] = match.group(1) if match.groups() else match.group(0)
            else:
                missing.append(name)

        if missing:
            return ParseResult.fail(f"Missing patterns: {missing}", text)

        return ParseResult.ok(results, text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# List Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ListParser(OutputParser[List[str]]):
    """
    Parse lists from LLM output.

    Handles:
    - Numbered lists (1. 2. 3.)
    - Bulleted lists (- * +)
    - Lettered lists (a. b. c.)
    """

    # Various list patterns
    NUMBERED = re.compile(r'^\s*(\d+)[.)\]]\s*(.+)$', re.MULTILINE)
    BULLETED = re.compile(r'^\s*[-*+]\s*(.+)$', re.MULTILINE)
    LETTERED = re.compile(r'^\s*([a-z])[.)\]]\s*(.+)$', re.MULTILINE | re.IGNORECASE)

    def __init__(
        self,
        min_items: int = 1,
        max_items: Optional[int] = None,
        strip_markers: bool = True
    ):
        self.min_items = min_items
        self.max_items = max_items
        self.strip_markers = strip_markers

    def parse(self, text: str) -> ParseResult[List[str]]:
        items = []

        # Try numbered first
        matches = self.NUMBERED.findall(text)
        if matches:
            items = [m[1].strip() for m in matches]
        else:
            # Try bulleted
            matches = self.BULLETED.findall(text)
            if matches:
                items = [m.strip() for m in matches]
            else:
                # Try lettered
                matches = self.LETTERED.findall(text)
                if matches:
                    items = [m[1].strip() for m in matches]

        if len(items) < self.min_items:
            return ParseResult.fail(
                f"Found {len(items)} items, need at least {self.min_items}", text
            )

        if self.max_items and len(items) > self.max_items:
            items = items[:self.max_items]

        return ParseResult.ok(items, text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Structured Output Parser (Dataclass-like)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class FieldSpec:
    """Specification for a parsed field."""
    name: str
    type: Type
    required: bool = True
    default: Any = None
    validator: Optional[Callable[[Any], bool]] = None
    coerce: bool = True


class StructuredParser(OutputParser[Dict]):
    """
    Parse structured data with type coercion and validation.

    Usage:
        parser = StructuredParser([
            FieldSpec("name", str, required=True),
            FieldSpec("age", int, required=True),
            FieldSpec("active", bool, default=True),
        ])
    """

    def __init__(self, fields: List[FieldSpec]):
        self.fields = {f.name: f for f in fields}
        self.json_parser = JSONParser()

    def parse(self, text: str) -> ParseResult[Dict]:
        # First extract JSON
        json_result = self.json_parser.parse(text)
        if not json_result.success:
            return json_result

        data = json_result.value
        result = {}
        errors = []

        for name, spec in self.fields.items():
            if name in data:
                value = data[name]

                # Type coercion
                if spec.coerce:
                    value = self._coerce(value, spec.type)

                # Validation
                if spec.validator and not spec.validator(value):
                    errors.append(f"Validation failed for '{name}'")
                    continue

                result[name] = value
            elif spec.required:
                errors.append(f"Missing required field: '{name}'")
            else:
                result[name] = spec.default

        if errors:
            return ParseResult.fail("; ".join(errors), text)

        return ParseResult.ok(result, text)

    def _coerce(self, value: Any, target_type: Type) -> Any:
        """Attempt to coerce value to target type."""
        if isinstance(value, target_type):
            return value

        try:
            if target_type == bool:
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1')
                return bool(value)
            elif target_type == int:
                return int(float(value))
            elif target_type == float:
                return float(value)
            elif target_type == str:
                return str(value)
            elif target_type == list:
                if isinstance(value, str):
                    return [v.strip() for v in value.split(',')]
                return list(value)
        except (ValueError, TypeError):
            pass

        return value


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Choice Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ChoiceParser(OutputParser[str]):
    """
    Parse a choice from predefined options.

    Handles:
    - Exact matches
    - Case-insensitive matching
    - Prefix matching
    - Number selection (1, 2, 3...)
    """

    def __init__(
        self,
        choices: List[str],
        case_sensitive: bool = False,
        allow_prefix: bool = True
    ):
        self.choices = choices
        self.case_sensitive = case_sensitive
        self.allow_prefix = allow_prefix

        # Build lookup
        if case_sensitive:
            self._lookup = {c: c for c in choices}
        else:
            self._lookup = {c.lower(): c for c in choices}

    def parse(self, text: str) -> ParseResult[str]:
        text = text.strip()
        check_text = text if self.case_sensitive else text.lower()

        # Exact match
        if check_text in self._lookup:
            return ParseResult.ok(self._lookup[check_text], text)

        # Number match (1, 2, 3...)
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(self.choices):
                return ParseResult.ok(self.choices[idx], text)

        # Prefix match
        if self.allow_prefix:
            matches = [
                orig for key, orig in self._lookup.items()
                if key.startswith(check_text)
            ]
            if len(matches) == 1:
                return ParseResult.ok(matches[0], text)

        return ParseResult.fail(
            f"Invalid choice '{text}'. Options: {self.choices}", text
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Boolean Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BooleanParser(OutputParser[bool]):
    """Parse yes/no, true/false, etc."""

    TRUE_VALUES = {'yes', 'true', '1', 'y', 'correct', 'affirmative', 'indeed'}
    FALSE_VALUES = {'no', 'false', '0', 'n', 'incorrect', 'negative', 'nope'}

    def parse(self, text: str) -> ParseResult[bool]:
        # Clean text
        clean = text.strip().lower()

        # Remove common prefixes
        for prefix in ['answer:', 'result:', 'response:']:
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()

        # Check first word
        first_word = clean.split()[0] if clean.split() else ""

        if first_word in self.TRUE_VALUES:
            return ParseResult.ok(True, text)
        if first_word in self.FALSE_VALUES:
            return ParseResult.ok(False, text)

        return ParseResult.fail(f"Cannot parse as boolean: '{text}'", text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Score/Rating Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Score:
    """Parsed score/rating."""
    value: float
    max_value: float = 10.0
    normalized: float = field(init=False)
    confidence: Optional[float] = None
    reasoning: Optional[str] = None

    def __post_init__(self):
        self.normalized = self.value / self.max_value


class ScoreParser(OutputParser[Score]):
    """
    Parse scores/ratings from LLM output.

    Handles:
    - "Score: 8/10"
    - "Rating: 4.5 out of 5"
    - "7.5"
    - "Grade: B+"
    """

    # Various score patterns
    SCORE_PATTERNS = [
        re.compile(r'(?:score|rating|grade)[:\s]*(\d+(?:\.\d+)?)\s*/\s*(\d+)', re.I),
        re.compile(r'(?:score|rating|grade)[:\s]*(\d+(?:\.\d+)?)\s*(?:out of|of)\s*(\d+)', re.I),
        re.compile(r'(\d+(?:\.\d+)?)\s*/\s*(\d+)'),
        re.compile(r'(?:score|rating|grade)[:\s]*(\d+(?:\.\d+)?)', re.I),
    ]

    GRADE_MAP = {
        'a+': 10, 'a': 9.5, 'a-': 9,
        'b+': 8.5, 'b': 8, 'b-': 7.5,
        'c+': 7, 'c': 6.5, 'c-': 6,
        'd+': 5.5, 'd': 5, 'd-': 4.5,
        'f': 2.5,
    }

    def __init__(self, max_value: float = 10.0):
        self.max_value = max_value

    def parse(self, text: str) -> ParseResult[Score]:
        # Try score patterns
        for pattern in self.SCORE_PATTERNS:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                value = float(groups[0])
                max_val = float(groups[1]) if len(groups) > 1 else self.max_value

                # Normalize to our max_value
                normalized_value = (value / max_val) * self.max_value

                return ParseResult.ok(Score(
                    value=normalized_value,
                    max_value=self.max_value,
                    reasoning=self._extract_reasoning(text)
                ), text)

        # Try letter grades
        grade_match = re.search(r'(?:grade)[:\s]*([a-f][+-]?)', text, re.I)
        if grade_match:
            grade = grade_match.group(1).lower()
            if grade in self.GRADE_MAP:
                return ParseResult.ok(Score(
                    value=self.GRADE_MAP[grade],
                    max_value=10.0,
                    reasoning=self._extract_reasoning(text)
                ), text)

        # Try bare number
        num_match = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
        if num_match:
            value = float(num_match.group(1))
            # Assume it's already on our scale if reasonable
            if value <= self.max_value:
                return ParseResult.ok(Score(value=value, max_value=self.max_value), text)

        return ParseResult.fail("No score found", text)

    def _extract_reasoning(self, text: str) -> Optional[str]:
        """Try to extract reasoning/explanation."""
        # Look for reasoning after score
        match = re.search(r'(?:because|reason|explanation)[:\s]*(.+?)(?:\.|$)', text, re.I)
        if match:
            return match.group(1).strip()
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Composite Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CompositeParser(OutputParser[Dict[str, Any]]):
    """
    Combine multiple parsers for complex outputs.

    Usage:
        parser = CompositeParser({
            "code": CodeBlockParser(),
            "score": ScoreParser(),
            "approved": BooleanParser(),
        })
    """

    def __init__(
        self,
        parsers: Dict[str, OutputParser],
        require_all: bool = False
    ):
        self.parsers = parsers
        self.require_all = require_all

    def parse(self, text: str) -> ParseResult[Dict[str, Any]]:
        results = {}
        errors = []

        for name, parser in self.parsers.items():
            result = parser.parse(text)
            if result.success:
                results[name] = result.value
            elif self.require_all:
                errors.append(f"{name}: {result.error}")

        if errors:
            return ParseResult.fail("; ".join(errors), text)

        if not results:
            return ParseResult.fail("No parsers succeeded", text)

        return ParseResult.ok(results, text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def parse_json(text: str, schema: Optional[Dict] = None) -> ParseResult[Dict]:
    """Parse JSON from text."""
    return JSONParser(schema=schema).parse(text)


def parse_code(text: str, language: Optional[str] = None) -> ParseResult[List[CodeBlock]]:
    """Parse code blocks from text."""
    return CodeBlockParser(language_filter=language).parse(text)


def parse_list(text: str, min_items: int = 1) -> ParseResult[List[str]]:
    """Parse a list from text."""
    return ListParser(min_items=min_items).parse(text)


def parse_bool(text: str) -> ParseResult[bool]:
    """Parse a boolean from text."""
    return BooleanParser().parse(text)


def parse_score(text: str, max_value: float = 10.0) -> ParseResult[Score]:
    """Parse a score from text."""
    return ScoreParser(max_value=max_value).parse(text)


def parse_choice(text: str, choices: List[str]) -> ParseResult[str]:
    """Parse a choice from text."""
    return ChoiceParser(choices).parse(text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Parser Factory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ParserFactory:
    """Factory for creating parsers from specifications."""

    @staticmethod
    def from_type(type_hint: Type) -> OutputParser:
        """Create a parser for a Python type."""
        if type_hint == bool:
            return BooleanParser()
        elif type_hint == int or type_hint == float:
            return ScoreParser()
        elif type_hint == str:
            return RegexParser({"value": r"(.+)"})
        elif type_hint == list:
            return ListParser()
        elif type_hint == dict:
            return JSONParser()
        else:
            raise ValueError(f"No parser for type: {type_hint}")

    @staticmethod
    def for_schema(schema: Dict) -> OutputParser:
        """Create a parser for a JSON schema."""
        return JSONParser(schema=schema)

    @staticmethod
    def for_choices(choices: List[str]) -> OutputParser:
        """Create a choice parser."""
        return ChoiceParser(choices)
