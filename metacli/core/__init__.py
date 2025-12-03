"""
MetaCLI Core Layer - Unified Orchestration API

The Workflow class is the unified API for all orchestration needs:
- Simple sequences
- Advanced workflows with conditionals, loops, sub-agents
- Declarative YAML/JSON workflows
- Pre-built patterns
- Registry-based workflows

Components:
- Workflow: Unified orchestration API (PRIMARY)
- CLISequence: Lightweight sequential execution (LEGACY)
- OutputParser: Extract code blocks, errors, files, JSON
- Persistence: Auto-save to files + SQLite with FTS
- DecisionEngine: Conditional routing and dynamic prompts
- Patterns: Pre-built workflow patterns

The Unified Way (Recommended):
    from metacli.core import Workflow

    # Simple workflow
    workflow = Workflow("code-review")
    workflow.add_step("generate", "claude-code", "Write API")
    workflow.add_step("review", "gemini", "Review", use_previous=True)
    result = workflow.run()

    # From YAML
    workflow = Workflow.from_yaml("workflows/audit-refactor.yaml", target="src/")
    result = workflow.run()

    # From pattern
    from metacli.core.patterns import audit_refactor_cycle
    pattern = audit_refactor_cycle("src/api.py", max_iterations=3)
    workflow = Workflow.from_pattern(pattern)
    result = workflow.run()

    # From registry
    workflow = Workflow.from_registry("audit-refactor", target="src/")
    result = workflow.run()

Legacy API (Still Supported):
    from metacli.core import CLISequence
    seq = CLISequence("code-review")
    seq.add_step("claude-code", "Write API")
    result = seq.run()
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
