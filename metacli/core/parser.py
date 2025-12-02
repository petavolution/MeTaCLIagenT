"""
Parser - Output Parsing for CLI Tools

Parse and extract structured data from CLI tool outputs.

Features:
- Code block extraction (with language detection)
- Error detection
- File path extraction
- JSON parsing
- Test result parsing
- Prompt injection sanitization

Example:
    from metacli.core import OutputParser

    parser = OutputParser()
    blocks = parser.extract_code_blocks(output)
    errors = parser.has_errors(output)
    files = parser.extract_file_paths(output)
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CodeBlock:
    """Extracted code block."""
    code: str
    language: str = "text"
    filename: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OutputParser:
    """
    Parse CLI tool outputs to extract structured data.

    Supports:
    - Code blocks (```language ... ```)
    - Errors (exceptions, failures, tracebacks)
    - File paths (/path/to/file.py, ./relative/file.js)
    - Test results (pytest, jest)
    - JSON extraction
    - Prompt injection sanitization
    """

    # Regex patterns
    CODE_BLOCK = re.compile(
        r'(?:#+\s*(?:File:\s*)?([^\n]+\.[\w]+)\s*\n)?'  # Optional filename
        r'```(\w*)\s*\n'  # Opening fence with optional language
        r'([\s\S]*?)'    # Code content
        r'\n```',         # Closing fence
        re.MULTILINE
    )
    ERROR_PATTERN = re.compile(r'(error|exception|failed|traceback):', re.IGNORECASE)
    FILE_PATH = re.compile(r'(?:^|\s)((?:/|\./)[\w./\-]+\.[\w]+)')
    TEST_PASSED = re.compile(r'(\d+)\s+passed', re.IGNORECASE)
    TEST_FAILED = re.compile(r'(\d+)\s+failed', re.IGNORECASE)
    JSON_BLOCK = re.compile(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', re.MULTILINE)
    JSON_OBJECT = re.compile(r'\{[\s\S]*\}')

    # Dangerous prompt injection patterns
    INJECTION_PATTERNS = [
        (r"<\|im_start\|>.*?<\|im_end\|>", "[REDACTED_CONTROL_TOKEN]"),
        (r"<\|system\|>", "[REDACTED]"),
        (r"<\|assistant\|>", "[REDACTED]"),
        (r"<\|user\|>", "[REDACTED]"),
        (r"\bSYSTEM\s*:", "[REDACTED]:"),
        (r"\bASSISTANT\s*:", "[REDACTED]:"),
        (r"(?i)ignore\s+(all\s+)?previous\s+instructions?", "[INSTRUCTION_OVERRIDE_ATTEMPT]"),
        (r"(?i)you\s+are\s+now", "[ROLE_OVERRIDE_ATTEMPT]"),
        (r"(?i)forget\s+(all\s+)?prior", "[MEMORY_OVERRIDE_ATTEMPT]"),
        (r"(?i)disregard\s+(all\s+)?above", "[INSTRUCTION_OVERRIDE_ATTEMPT]"),
    ]

    # ─────────────────────────────────────────────────────
    # Code Blocks
    # ─────────────────────────────────────────────────────

    @classmethod
    def extract_code_blocks(cls, text: str, language_filter: Optional[str] = None) -> List[CodeBlock]:
        """
        Extract code blocks from text.

        Args:
            text: Text to parse
            language_filter: Optional language to filter (e.g., "python")

        Returns:
            List of CodeBlock objects

        Example:
            blocks = OutputParser.extract_code_blocks(output)
            python_blocks = OutputParser.extract_code_blocks(output, "python")
        """
        blocks = []

        for match in cls.CODE_BLOCK.finditer(text):
            filename = match.group(1)
            language = match.group(2) or "text"
            code = match.group(3).strip()

            # Apply language filter
            if language_filter:
                if language.lower() != language_filter.lower():
                    continue

            blocks.append(CodeBlock(
                code=code,
                language=language,
                filename=filename
            ))

        return blocks

    @classmethod
    def extract_first_code_block(cls, text: str, language: Optional[str] = None) -> Optional[str]:
        """
        Extract first code block, optionally filtered by language.

        Args:
            text: Text to parse
            language: Optional language filter

        Returns:
            Code string or None if not found

        Example:
            code = OutputParser.extract_first_code_block(output, "python")
        """
        blocks = cls.extract_code_blocks(text, language_filter=language)
        return blocks[0].code if blocks else None

    # ─────────────────────────────────────────────────────
    # Error Detection
    # ─────────────────────────────────────────────────────

    @classmethod
    def has_errors(cls, text: str) -> bool:
        """
        Check if output contains errors.

        Returns:
            True if errors detected
        """
        return bool(cls.ERROR_PATTERN.search(text))

    @classmethod
    def extract_errors(cls, text: str, context_lines: int = 3) -> List[str]:
        """
        Extract error messages with context.

        Args:
            text: Text to parse
            context_lines: Number of lines around error to include

        Returns:
            List of error excerpts
        """
        lines = text.split('\n')
        errors = []

        for i, line in enumerate(lines):
            if cls.ERROR_PATTERN.search(line):
                # Get context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                error_context = '\n'.join(lines[start:end])
                errors.append(error_context)

        return errors

    # ─────────────────────────────────────────────────────
    # File Paths
    # ─────────────────────────────────────────────────────

    @classmethod
    def extract_file_paths(cls, text: str) -> List[str]:
        """
        Extract file paths from output.

        Returns:
            List of unique file paths
        """
        matches = cls.FILE_PATH.findall(text)
        return list(set(matches))  # Deduplicate

    # ─────────────────────────────────────────────────────
    # Test Results
    # ─────────────────────────────────────────────────────

    @classmethod
    def parse_test_results(cls, text: str) -> Dict[str, int]:
        """
        Parse test results (pytest, jest, etc.).

        Returns:
            Dictionary with 'passed' and 'failed' counts

        Example:
            results = OutputParser.parse_test_results(output)
            print(f"{results['passed']} passed, {results['failed']} failed")
        """
        passed_match = cls.TEST_PASSED.search(text)
        failed_match = cls.TEST_FAILED.search(text)

        return {
            "passed": int(passed_match.group(1)) if passed_match else 0,
            "failed": int(failed_match.group(1)) if failed_match else 0,
        }

    # ─────────────────────────────────────────────────────
    # JSON Extraction
    # ─────────────────────────────────────────────────────

    @classmethod
    def extract_json(cls, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse JSON from text.

        Handles:
        - JSON in code blocks
        - Raw JSON objects
        - Common formatting issues

        Returns:
            Parsed JSON dict or None if not found/invalid

        Example:
            data = OutputParser.extract_json(output)
            if data:
                print(data["key"])
        """
        # Try code block first
        match = cls.JSON_BLOCK.search(text)
        if match:
            json_str = match.group(1).strip()
        else:
            # Try raw JSON object
            match = cls.JSON_OBJECT.search(text)
            if not match:
                return None
            json_str = match.group(0)

        # Clean up common issues
        json_str = cls._clean_json(json_str)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    @classmethod
    def _clean_json(cls, json_str: str) -> str:
        """Clean up common JSON formatting issues."""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)

        # Remove comments
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)

        return json_str

    # ─────────────────────────────────────────────────────
    # Sanitization (Security)
    # ─────────────────────────────────────────────────────

    @classmethod
    def sanitize_for_chaining(cls, text: str, max_length: int = 5000) -> str:
        """
        Sanitize LLM output before using in subsequent prompts.

        Removes potential prompt injection patterns that could hijack
        downstream agents.

        Args:
            text: Raw LLM output
            max_length: Maximum length (truncate longer outputs)

        Returns:
            Sanitized text safe to include in prompts

        Example:
            safe_text = OutputParser.sanitize_for_chaining(llm_output)
            next_prompt = f"Review this: {safe_text}"
        """
        sanitized = text

        for pattern, replacement in cls.INJECTION_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.MULTILINE | re.DOTALL)

        # Truncate to reasonable size
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "\n[... output truncated ...]"

        return sanitized

    @classmethod
    def summarize_output(cls, text: str, max_length: int = 500) -> str:
        """
        Create a summary of output for chaining.

        Includes:
        - Whether code was generated
        - Whether errors exist
        - Modified files
        - Truncated output

        Args:
            text: Text to summarize
            max_length: Maximum output length

        Returns:
            Summary string

        Example:
            summary = OutputParser.summarize_output(long_output)
        """
        # Sanitize first
        sanitized = cls.sanitize_for_chaining(text, max_length=5000)

        # Extract key information
        has_code = bool(cls.extract_code_blocks(sanitized))
        has_errors = cls.has_errors(sanitized)
        files = cls.extract_file_paths(sanitized)

        summary_parts = []

        if has_code:
            summary_parts.append("Generated code")
        if has_errors:
            summary_parts.append("Contains errors")
        if files:
            summary_parts.append(f"Modified files: {', '.join(files[:3])}")

        # Add truncated output
        if len(sanitized) > max_length:
            summary_parts.append(f"\n\nOutput preview:\n{sanitized[:max_length]}...")
        else:
            summary_parts.append(f"\n\nOutput:\n{sanitized}")

        return " | ".join(summary_parts) if summary_parts else sanitized[:max_length]

    # ─────────────────────────────────────────────────────
    # Comprehensive Parsing
    # ─────────────────────────────────────────────────────

    @classmethod
    def parse_all(cls, text: str) -> Dict[str, Any]:
        """
        Parse all available information from text.

        Returns:
            Dictionary with all parsed data:
            - code_blocks: List[CodeBlock]
            - has_errors: bool
            - errors: List[str]
            - file_paths: List[str]
            - test_results: Dict[str, int]
            - json_data: Optional[Dict]
            - summary: str

        Example:
            data = OutputParser.parse_all(output)
            if data['has_errors']:
                print("Errors found:", data['errors'])
        """
        return {
            "code_blocks": cls.extract_code_blocks(text),
            "has_errors": cls.has_errors(text),
            "errors": cls.extract_errors(text),
            "file_paths": cls.extract_file_paths(text),
            "test_results": cls.parse_test_results(text),
            "json_data": cls.extract_json(text),
            "summary": cls.summarize_output(text, max_length=200),
        }
