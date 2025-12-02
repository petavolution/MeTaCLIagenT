"""
MetaCLI Core Layer - Orchestration Patterns

The core user-facing API for CLI tool orchestration.

Components:
- CLISequence: Sequential tool execution with chaining
- OutputParser: Extract code blocks, errors, files, JSON
- Persistence: Auto-save to files + SQLite with FTS

Example:
    from metacli.core import CLISequence

    seq = CLISequence("code-review")
    seq.add_step("claude-code", "Write API")
    seq.add_step("aider", "Fix bugs", use_previous=True)
    result = seq.run()  # Auto-saved
    seq.cleanup()
"""

# Sequence orchestration
from .sequence import (
    CLISequence,
    SequenceStep,
    CLIToolConfig,
    run_sequence,
    quick_chain,
)

# Output parsing
from .parser import (
    OutputParser,
    CodeBlock,
)

# Persistence
from .persistence import (
    Persistence,
    get_persistence,
)

__all__ = [
    # Sequence
    "CLISequence",
    "SequenceStep",
    "CLIToolConfig",
    "run_sequence",
    "quick_chain",

    # Parser
    "OutputParser",
    "CodeBlock",

    # Persistence
    "Persistence",
    "get_persistence",
]

__version__ = "2.0.0-alpha"
