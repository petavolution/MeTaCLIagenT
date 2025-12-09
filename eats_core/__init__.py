# eats_core - Simplified EATS Implementation
"""
EATS Core: Evolutionary Agent Tree System

Production-ready version v2.3 with optimized architecture:

Transport (transport.py):
- PTY transport for interactive CLI control
- Tmux transport for visual debugging
- Buffer overflow protection

Core (core.py):
- Agent DNA/evolution
- Built-in fitness functions
- Uses transport.py (single source of truth)

Async (async_core.py):
- Concurrent agent execution
- Worker pools with rate limiting
- Orchestrator-worker pattern

Swarm (swarm.py):
- Hierarchical agent tree
- Probability-fan spawning
- Senescence tracking

Judge (judge.py):
- LLM-as-judge fitness
- Pairwise comparison
- Hybrid scoring

Pipeline (pipeline.py):
- DAG result trees
- Fusion methods
- Semantic caching

Conflict (conflict.py):
- Contradiction detection
- Meta-agent arbitration
- Multi-strategy resolution

CLI Orchestrator (cli_orchestrator.py):
- Sequence AI CLI tools
- Parse outputs intelligently
- Chain tools with context
- Pre-built workflow patterns

Events (events.py):
- Real-time pub/sub
- SSE streaming
- Event decorators

Workflows (workflows.py):
- DAG-based workflows
- Prompt chaining
- Parallel execution

Presets (presets.py):
- Agent archetypes
- Team configurations
- Optimized prompts

Persistence (persistence.py):
- State snapshots
- DNA library
- Export/import

Metrics (metrics.py):
- Performance tracking
- Cost estimation
- Observability

Providers (providers.py):
- LLM provider abstraction
- OpenAI, Anthropic, Ollama support
- Unified completion interface

Prompts (prompts.py):
- Prompt template system
- Prompt library
- Chain-of-thought support

Parsers (parsers.py):
- Output parsing
- JSON/code extraction
- Structured validation

Config (config.py):
- Configuration management
- Environment profiles
- Secrets handling

Server (server.py):
- FastAPI server
- Dashboard UI
- CLI interface
"""

__version__ = "2.3.0"

# Core components
from .core import (
    Transport,
    PTYTransport,
    TmuxTransport,
    AgentDNA,
    Agent,
    Evolution,
    EvolutionConfig,
    heuristic_fitness,
)

# Swarm management
from .swarm import (
    SwarmController,
    TreeNode,
    BranchType,
    AgentRole,
    fan_layout,
    grid_layout,
)

# Fitness evaluation
from .judge import (
    LLMJudge,
    Fitness,
    Criterion,
    create_fitness_fn,
    create_keyword_fitness,
    create_code_fitness,
)

# Result processing
from .pipeline import (
    ResultPipeline,
    FusedOutput,
    FusionMethod,
)

# Conflict resolution
from .conflict import (
    ConflictDetector,
    ConflictResolver,
    Conflict,
    ConflictType,
    detect_conflicts,
    resolve_conflict,
)

# CLI Orchestrator
from .cli_orchestrator import (
    CLISequence,
    SequenceStep,
    OutputParser,
    WorkflowPatterns,
    run_sequence,
    quick_chain,
)

# Project Context
from .project_context import (
    ProjectContext,
    ProjectInfo,
    ProjectLanguage,
    detect_project,
    get_context,
)

# Workflow Templates
from .workflow_templates import (
    WorkflowTemplates,
    quick_feature,
    quick_bugfix,
    quick_review,
)

# Async execution
from .async_core import (
    AsyncAgent,
    TaskResult,
    WorkerPool,
    AsyncEvolution,
    AsyncEvolutionConfig,
    OrchestratorWorker,
    run_parallel,
    run_with_taskgroup,
    run_first_wins,
    create_agent_pool,
    shutdown_agents,
)

# Event system
from .events import (
    Event,
    EventType,
    EventBus,
    EventStream,
    EventEmitter,
    get_event_bus,
    emit,
    on_event,
    emits,
)

# Workflows
from .workflows import (
    Workflow,
    WorkflowBuilder,
    WorkflowNode,
    NodeType,
    NodeStatus,
    create_chain_workflow,
    create_parallel_workflow,
)

# Agent presets
from .presets import (
    AgentPreset,
    PresetCategory,
    get_preset,
    list_presets,
    search_presets,
    create_dna,
    get_team,
    create_team_dna,
    ALL_PRESETS,
    TEAMS,
    # Individual presets
    CODER,
    REVIEWER,
    TESTER,
    DEBUGGER,
    PLANNER,
    ORCHESTRATOR,
    # CLI Tools
    CLIToolConfig,
    CLI_TOOLS,
    get_cli_tool,
    list_cli_tools,
    create_cli_agent,
)

# Easy API
from .easy import (
    AgentHandle,
    TaskResult,
    spawn_agent,
    spawn_multiple,
    stop_all,
    run_task,
    run_parallel,
    save_result,
    load_result,
    list_results,
    quick_run,
    compare_tools,
)

# Persistence
from .persistence import (
    Storage,
    MemoryStorage,
    FileStorage,
    StateManager,
    Snapshot,
    get_state_manager,
    save,
    load,
)

# Metrics
from .metrics import (
    MetricsRegistry,
    EATSMetrics,
    Counter,
    Gauge,
    Histogram,
    Timer,
    get_metrics,
)

# Logging
from .logging import (
    init_logging,
    get_logger,
    debug,
    info,
    warning,
    error,
    critical,
    exception,
    track_error,
    get_error_tracker,
    ErrorTracker,
    ErrorRecord,
    timer,
    timed,
)

# Server
from .server import (
    create_app,
    run_server,
    run_cli,
)

# Providers
from .providers import (
    LLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    MockProvider,
    Message as ProviderMessage,
    CompletionResponse,
    get_provider,
    list_providers,
)

# Prompts
from .prompts import (
    PromptTemplate,
    PromptBuilder,
    PromptLibrary,
    PromptStyle,
    Message as PromptMessage,
    Example,
    AgentPromptConfig,
    AGENT_PROMPTS,
    get_agent_prompt,
    get_prompt_library,
    get_template,
    chain_prompts,
    code_review,
    bug_fix,
    explain,
)

# Parsers
from .parsers import (
    OutputParser,
    ParseResult,
    JSONParser,
    CodeBlockParser,
    CodeBlock,
    RegexParser,
    ListParser,
    StructuredParser,
    FieldSpec,
    ChoiceParser,
    BooleanParser,
    ScoreParser,
    Score,
    CompositeParser,
    parse_json,
    parse_code,
    parse_list,
    parse_bool,
    parse_score,
    parse_choice,
)

# Config
from .config import (
    EATSConfig,
    LLMConfig,
    SwarmConfig,
    EvolutionConfig as EvolutionConfigFull,
    TransportConfig,
    PersistenceConfig,
    MetricsConfig,
    ServerConfig,
    ConfigLoader,
    ConfigValue,
    ConfigValidator,
    ValidationError,
    SecretsManager,
    Environment,
    get_config,
    set_config,
    load_config,
    reset_config,
    get_llm_config,
    get_swarm_config,
    get_evolution_config,
    get_environment,
    is_production,
    is_development,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "Transport",
    "PTYTransport",
    "TmuxTransport",
    "AgentDNA",
    "Agent",
    "Evolution",
    "EvolutionConfig",
    "heuristic_fitness",
    # Swarm
    "SwarmController",
    "TreeNode",
    "BranchType",
    "AgentRole",
    "fan_layout",
    "grid_layout",
    # Judge
    "LLMJudge",
    "Fitness",
    "Criterion",
    "create_fitness_fn",
    "create_keyword_fitness",
    "create_code_fitness",
    # Pipeline
    "ResultPipeline",
    "FusedOutput",
    "FusionMethod",
    # Conflict Resolution
    "ConflictDetector",
    "ConflictResolver",
    "Conflict",
    "ConflictType",
    "detect_conflicts",
    "resolve_conflict",
    # CLI Orchestrator
    "CLISequence",
    "SequenceStep",
    "OutputParser",
    "WorkflowPatterns",
    "run_sequence",
    "quick_chain",
    # Project Context
    "ProjectContext",
    "ProjectInfo",
    "ProjectLanguage",
    "detect_project",
    "get_context",
    # Workflow Templates
    "WorkflowTemplates",
    "quick_feature",
    "quick_bugfix",
    "quick_review",
    # Async
    "AsyncAgent",
    "TaskResult",
    "WorkerPool",
    "AsyncEvolution",
    "AsyncEvolutionConfig",
    "OrchestratorWorker",
    "run_parallel",
    "run_with_taskgroup",
    "run_first_wins",
    "create_agent_pool",
    "shutdown_agents",
    # Events
    "Event",
    "EventType",
    "EventBus",
    "EventStream",
    "EventEmitter",
    "get_event_bus",
    "emit",
    "on_event",
    "emits",
    # Workflows
    "Workflow",
    "WorkflowBuilder",
    "WorkflowNode",
    "NodeType",
    "NodeStatus",
    "create_chain_workflow",
    "create_parallel_workflow",
    # Presets
    "AgentPreset",
    "PresetCategory",
    "get_preset",
    "list_presets",
    "search_presets",
    "create_dna",
    "get_team",
    "create_team_dna",
    "ALL_PRESETS",
    "TEAMS",
    "CODER",
    "REVIEWER",
    "TESTER",
    "DEBUGGER",
    "PLANNER",
    "ORCHESTRATOR",
    # Persistence
    "Storage",
    "MemoryStorage",
    "FileStorage",
    "StateManager",
    "Snapshot",
    "get_state_manager",
    "save",
    "load",
    # Metrics
    "MetricsRegistry",
    "EATSMetrics",
    "Counter",
    "Gauge",
    "Histogram",
    "Timer",
    "get_metrics",
    # Server
    "create_app",
    "run_server",
    "run_cli",
    # Providers
    "LLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "MockProvider",
    "ProviderMessage",
    "CompletionResponse",
    "get_provider",
    "list_providers",
    # Prompts
    "PromptTemplate",
    "PromptBuilder",
    "PromptLibrary",
    "PromptStyle",
    "PromptMessage",
    "Example",
    "AgentPromptConfig",
    "AGENT_PROMPTS",
    "get_agent_prompt",
    "get_prompt_library",
    "get_template",
    "chain_prompts",
    "code_review",
    "bug_fix",
    "explain",
    # Parsers
    "OutputParser",
    "ParseResult",
    "JSONParser",
    "CodeBlockParser",
    "CodeBlock",
    "RegexParser",
    "ListParser",
    "StructuredParser",
    "FieldSpec",
    "ChoiceParser",
    "BooleanParser",
    "ScoreParser",
    "Score",
    "CompositeParser",
    "parse_json",
    "parse_code",
    "parse_list",
    "parse_bool",
    "parse_score",
    "parse_choice",
    # Config
    "EATSConfig",
    "LLMConfig",
    "SwarmConfig",
    "EvolutionConfigFull",
    "TransportConfig",
    "PersistenceConfig",
    "MetricsConfig",
    "ServerConfig",
    "ConfigLoader",
    "ConfigValue",
    "ConfigValidator",
    "ValidationError",
    "SecretsManager",
    "Environment",
    "get_config",
    "set_config",
    "load_config",
    "reset_config",
    "get_llm_config",
    "get_swarm_config",
    "get_evolution_config",
    "get_environment",
    "is_production",
    "is_development",
]
