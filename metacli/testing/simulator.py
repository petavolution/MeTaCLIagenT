"""
CLI Simulator - Mock CLI tools for testing

Simulates CLI tool behavior using hash-based response lookup.
"""

from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hash-Based Response Lookup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResponseLookupTable:
    """
    Fast hash-based lookup for matching prompts to responses.

    Uses multiple hash sizes for fuzzy matching:
    - Full hash: Exact match
    - Prefix hash (first 50 chars): Similar prompts
    - Keyword hash: Contains specific keywords
    """

    def __init__(self):
        self.exact_matches: Dict[str, str] = {}  # full_hash → response
        self.prefix_matches: Dict[str, List[str]] = defaultdict(list)  # prefix_hash → [responses]
        self.keyword_matches: Dict[str, List[str]] = defaultdict(list)  # keyword_hash → [responses]
        self.patterns: List[tuple] = []  # (regex, response) pairs

    def add_response(
        self,
        prompt: str,
        response: str,
        keywords: Optional[List[str]] = None
    ):
        """Add a prompt-response mapping."""
        # Exact match
        full_hash = self._hash(prompt)
        self.exact_matches[full_hash] = response

        # Prefix match (first 50 chars)
        prefix = prompt[:50].lower().strip()
        prefix_hash = self._hash(prefix)
        self.prefix_matches[prefix_hash].append(response)

        # Keyword matches
        if keywords:
            for keyword in keywords:
                kw_hash = self._hash(keyword.lower())
                self.keyword_matches[kw_hash].append(response)

    def lookup(self, prompt: str, fallback: str = "OK") -> str:
        """
        Find best matching response.

        Priority:
        1. Exact match (full hash)
        2. Prefix match (first 50 chars)
        3. Keyword match
        4. Pattern match
        5. Fallback
        """
        # Try exact match
        full_hash = self._hash(prompt)
        if full_hash in self.exact_matches:
            return self.exact_matches[full_hash]

        # Try prefix match
        prefix = prompt[:50].lower().strip()
        prefix_hash = self._hash(prefix)
        if prefix_hash in self.prefix_matches:
            return self.prefix_matches[prefix_hash][0]

        # Try keyword matches
        words = prompt.lower().split()
        for word in words:
            word_hash = self._hash(word)
            if word_hash in self.keyword_matches:
                return self.keyword_matches[word_hash][0]

        # Try patterns
        for pattern, response in self.patterns:
            if pattern.search(prompt):
                return response

        # Fallback
        return fallback

    def add_pattern(self, pattern, response: str):
        """Add regex pattern for matching."""
        import re
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re.IGNORECASE)
        self.patterns.append((pattern, response))

    @staticmethod
    def _hash(text: str) -> str:
        """Generate hash for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Simulated Process
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SimulatedProcess:
    """
    Simulates a CLI process with stdin/stdout.

    Mimics behavior of real Process class but uses lookup table
    for responses instead of actual process execution.
    """
    name: str
    lookup_table: ResponseLookupTable
    delay: float = 0.1  # Simulated execution delay

    # State
    running: bool = False
    history: List[Dict[str, str]] = field(default_factory=list)

    def start(self):
        """Start simulated process."""
        self.running = True

    def write(self, prompt: str):
        """Send input to simulated process."""
        if not self.running:
            raise RuntimeError(f"Process {self.name} not running")

        # Simulate processing time
        time.sleep(self.delay)

        # Lookup response
        response = self.lookup_table.lookup(prompt)

        # Record interaction
        self.history.append({
            "prompt": prompt,
            "response": response,
            "timestamp": time.time()
        })

    def read(self, timeout: float = 5.0) -> str:
        """Read output from simulated process."""
        if not self.history:
            return ""

        # Return last response
        return self.history[-1]["response"]

    def terminate(self):
        """Stop simulated process."""
        self.running = False

    def get_history(self) -> List[Dict[str, str]]:
        """Get full interaction history."""
        return self.history


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Simulator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CLISimulator:
    """
    Main simulator for CLI tools.

    Supports:
    - AI coding tools (claude-code, codex, aider)
    - Standard POSIX tools (ls, grep, python)
    - Custom tool definitions
    """

    def __init__(self):
        self.tools: Dict[str, ResponseLookupTable] = {}
        self.processes: Dict[str, SimulatedProcess] = {}

    @classmethod
    def from_templates(cls, template_path: str) -> CLISimulator:
        """Load simulator from template file (YAML/JSON)."""
        simulator = cls()

        # Load templates
        import yaml
        with open(template_path, 'r') as f:
            templates = yaml.safe_load(f)

        # Register tools
        for tool_name, config in templates.get("tools", {}).items():
            simulator.register_tool(tool_name, config.get("responses", {}))

        return simulator

    def register_tool(self, tool_name: str, responses: Dict[str, Any]):
        """
        Register a tool with response mappings.

        Args:
            tool_name: Tool identifier (e.g., "claude-code")
            responses: Dict of prompt patterns → responses
        """
        lookup_table = ResponseLookupTable()

        # Add exact matches
        for prompt, response in responses.get("exact", {}).items():
            lookup_table.add_response(prompt, response)

        # Add keyword matches
        for keyword, response in responses.get("keywords", {}).items():
            lookup_table.add_response("", response, keywords=[keyword])

        # Add pattern matches
        for pattern, response in responses.get("patterns", {}).items():
            lookup_table.add_pattern(pattern, response)

        self.tools[tool_name] = lookup_table

    def spawn(self, tool_name: str, **kwargs) -> SimulatedProcess:
        """Spawn a simulated process for a tool."""
        if tool_name not in self.tools:
            # Create default lookup table
            self.register_tool(tool_name, {
                "exact": {},
                "keywords": {},
                "patterns": {}
            })

        lookup_table = self.tools[tool_name]
        process = SimulatedProcess(
            name=tool_name,
            lookup_table=lookup_table,
            delay=kwargs.get("delay", 0.1)
        )

        self.processes[tool_name] = process
        return process

    def get_process(self, tool_name: str) -> Optional[SimulatedProcess]:
        """Get existing simulated process."""
        return self.processes.get(tool_name)

    def cleanup(self):
        """Terminate all simulated processes."""
        for process in self.processes.values():
            process.terminate()
        self.processes.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-Built Tool Simulators
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_claude_code_simulator() -> CLISimulator:
    """Create simulator for claude-code with realistic responses."""
    simulator = CLISimulator()

    claude_responses = {
        "exact": {
            "Write a hello world program": "```python\nprint('Hello, World!')\n```",
            "Review this code": "The code looks good. No issues found.",
            "Fix any bugs": "I've fixed the bugs in the code.",
        },
        "keywords": {
            "audit": "Audit complete. Found 3 potential issues:\n1. Variable naming\n2. Missing error handling\n3. Performance concern",
            "refactor": "Refactored code for better readability and performance.",
            "test": "Running tests...\n5 passed, 0 failed",
            "error": "Error: Syntax error on line 42",
        },
        "patterns": {
            r"write.*function": "```python\ndef new_function(arg1, arg2):\n    return arg1 + arg2\n```",
            r"fix.*error": "Fixed the error. The issue was a missing import statement.",
            r"optimize": "Optimized the code. Performance improved by 30%.",
        }
    }

    simulator.register_tool("claude-code", claude_responses)
    return simulator


def create_posix_simulator() -> CLISimulator:
    """Create simulator for common POSIX tools."""
    simulator = CLISimulator()

    # Python simulator
    python_responses = {
        "exact": {
            "print('hello')": "hello",
            "2+2": "4",
        },
        "patterns": {
            r"print\(": "output",
            r"import": "",
            r"\d+\s*[\+\-\*\/]\s*\d+": "42",
        }
    }
    simulator.register_tool("python", python_responses)

    # ls simulator
    ls_responses = {
        "exact": {
            "-la": "total 24\ndrwxr-xr-x  6 user  staff  192 Dec  7 10:00 .\ndrwxr-xr-x  8 user  staff  256 Dec  7 09:00 ..\n-rw-r--r--  1 user  staff  100 Dec  7 10:00 file.txt",
        }
    }
    simulator.register_tool("ls", ls_responses)

    # grep simulator
    grep_responses = {
        "patterns": {
            r"error": "file.txt:42:Error: something failed",
            r"TODO": "src/main.py:10:# TODO: implement this",
        }
    }
    simulator.register_tool("grep", grep_responses)

    return simulator


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_test_simulator(tools: List[str] = None) -> CLISimulator:
    """
    Create a simulator with common tools pre-configured.

    Args:
        tools: List of tools to include (default: all common tools)

    Returns:
        Configured CLISimulator
    """
    if tools is None:
        tools = ["claude-code", "aider", "python", "ls", "grep"]

    simulator = CLISimulator()

    # Add AI coding tools
    if "claude-code" in tools:
        claude_sim = create_claude_code_simulator()
        simulator.tools["claude-code"] = claude_sim.tools["claude-code"]

    if "aider" in tools:
        # Aider responses
        simulator.register_tool("aider", {
            "exact": {
                "Fix the bug": "Fixed bug in file.py",
            },
            "keywords": {
                "refactor": "Refactored 3 files",
            }
        })

    # Add POSIX tools
    posix_tools = ["python", "ls", "grep"]
    for tool in posix_tools:
        if tool in tools:
            posix_sim = create_posix_simulator()
            if tool in posix_sim.tools:
                simulator.tools[tool] = posix_sim.tools[tool]

    return simulator
