"""
MetaCLI Core Layer - Orchestration Patterns

The core user-facing API for CLI tool orchestration.

Components:
- CLISequence: Sequential tool execution with chaining
- Workflow: Advanced orchestration with conditionals, loops, sub-agents
- OutputParser: Extract code blocks, errors, files, JSON
- Persistence: Auto-save to files + SQLite with FTS
- DecisionEngine: Conditional routing and dynamic prompts
- Patterns: Pre-built workflow patterns

Examples:
    # Simple sequence
    from metacli.core import CLISequence
    seq = CLISequence("code-review")
    seq.add_step("claude-code", "Write API")
    seq.add_step("aider", "Fix bugs", use_previous=True)
    result = seq.run()

    # Advanced workflow with conditionals
    from metacli.core import Workflow
    from metacli.core.patterns import audit_refactor_cycle
    pattern = audit_refactor_cycle("src/api.py", max_iterations=3)
    workflow = Workflow.from_pattern(pattern)
    result = workflow.run()
"""

# Sequence orchestration (linear)
from .sequence import (
    CLISequence,
    SequenceStep,
    CLIToolConfig,
    run_sequence,
    quick_chain,
)

# Workflow orchestration (advanced: conditionals, loops, sub-agents)
from .workflow import (
    Workflow,
    WorkflowStep,
)

# Decision engine
from .decision import (
    Decision,
    DecisionType,
    DecisionEngine,
    PromptTemplate,
    Condition,
    # Built-in decision functions
    has_errors_decision,
    test_pass_decision,
    code_quality_decision,
    max_iterations_decision,
)

# Workflow patterns
from . import patterns

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
    # Sequence (linear)
    "CLISequence",
    "SequenceStep",
    "CLIToolConfig",
    "run_sequence",
    "quick_chain",

    # Workflow (advanced)
    "Workflow",
    "WorkflowStep",

    # Decision engine
    "Decision",
    "DecisionType",
    "DecisionEngine",
    "PromptTemplate",
    "Condition",
    "has_errors_decision",
    "test_pass_decision",
    "code_quality_decision",
    "max_iterations_decision",

    # Patterns
    "patterns",

    # Parser
    "OutputParser",
    "CodeBlock",

    # Persistence
    "Persistence",
    "get_persistence",
]

__version__ = "2.0.0-alpha"
