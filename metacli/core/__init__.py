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
- Orchestrator: Advanced iterative workflows with sub-agent decisions (NEW)
- UnifiedExecutor: Execute AI tools and POSIX commands (NEW)
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

Advanced Orchestration (NEW):
    from metacli.core import Orchestrator, create_audit_refactor_workflow

    # Create orchestrator
    orchestrator = Orchestrator(db_path="workflow.db")

    # Use pre-built workflow
    workflow = create_audit_refactor_workflow(orchestrator, target="src/")
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    # Or create custom workflow
    workflow = orchestrator.create_workflow("my-workflow")
    workflow.add_step("audit", "claude-code", "audit {target}")
    workflow.add_decision("route", lambda ctx: "refactor" if ctx.get_last_result().has_error else "done")
    workflow.add_step("refactor", "codex", "fix issues")
    context = orchestrator.execute(workflow, {"target": "src/"})

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

# Orchestration (NEW)
from .executor import (
    UnifiedExecutor,
    ExecutionResult,
    ExecutionConfig,
    ExecutionMode,
    ToolType,
    create_ai_executor,
    create_posix_executor,
)

from .orchestrator import (
    Orchestrator,
    Workflow as OrchestratorWorkflow,
    WorkflowStep as OrchestratorStep,
    WorkflowContext,
    StepType,
    create_audit_refactor_workflow,
    create_iterative_refactor_workflow,
)

from .workflow_loader import (
    WorkflowLoader,
    YAMLWorkflowDefinition,
    load_workflow,
    load_all_workflows,
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

    # Orchestration (NEW)
    "Orchestrator",
    "OrchestratorWorkflow",
    "OrchestratorStep",
    "WorkflowContext",
    "StepType",
    "UnifiedExecutor",
    "ExecutionResult",
    "ExecutionConfig",
    "ExecutionMode",
    "ToolType",
    "create_ai_executor",
    "create_posix_executor",
    "create_audit_refactor_workflow",
    "create_iterative_refactor_workflow",

    # Workflow Loader (NEW)
    "WorkflowLoader",
    "YAMLWorkflowDefinition",
    "load_workflow",
    "load_all_workflows",

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
