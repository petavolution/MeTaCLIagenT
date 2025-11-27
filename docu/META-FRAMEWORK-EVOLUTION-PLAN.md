# 🌟 MeTaCLIagenT - META-FRAMEWORK EVOLUTION PLAN

**VISION**: Transform into a Universal Meta-CLI Orchestration Framework
**STATUS**: Strategic Architectural Refactoring
**DATE**: 2025-11-27
**SCOPE**: Next-level abstraction for maximum power and flexibility

---

## 🎯 META-LEVEL INSIGHT

### **What We've Accomplished** ✅
1. **Phase 1**: Transport Consolidation (Single Source of Truth)
2. **Phase 2**: VisualSwarm Migration (95%+ Reliability)

### **What We NOW See** 👁️

The codebase has **THREE PARALLEL EXECUTION PATHS** that should be **ONE UNIFIED ORCHESTRATOR**:

```
Current State (FRAGMENTED):
├── SwarmController      → Evolution-based multi-agent (eats_core/swarm.py)
├── CLISequence          → Sequential tool chains (eats_core/cli_orchestrator.py)
├── ParallelExecutor     → Parallel tool execution (eats_core/parallel_executor.py)
├── VisualSwarm          → Visual terminal orchestration (eats_core/visual_swarm.py)
└── WorkflowTemplates    → Predefined patterns (eats_core/workflow_templates.py)

Problem: Each path is separate, no unified abstraction
```

```
Meta-Framework Vision (UNIFIED):
                    ┌─────────────────────────────────┐
                    │   UNIVERSAL ORCHESTRATOR        │
                    │   (Single Execution Engine)     │
                    └─────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌─────────┐  ┌─────────┐  ┌─────────┐
             │Sequential│  │Parallel │  │Adaptive │
             └─────────┘  └─────────┘  └─────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌─────────────────────────────────┐
                    │      PLAYBOOK ENGINE            │
                    │   (Declarative YAML Workflows)  │
                    └─────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌─────────┐  ┌─────────┐  ┌─────────┐
             │Evolution│  │Visual   │  │Template │
             │(AI)     │  │(Debug)  │  │(Rules)  │
             └─────────┘  └─────────┘  └─────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌─────────────────────────────────┐
                    │    UNIFIED TOOL ABSTRACTION     │
                    │  (AI Tools + POSIX + Custom)    │
                    └─────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌─────────┐  ┌─────────┐  ┌─────────┐
             │Transport│  │Persist  │  │Monitor  │
             │Layer ✅ │  │Layer    │  │Layer    │
             └─────────┘  └─────────┘  └─────────┘
```

---

## 🏗️ PROPOSED META-ARCHITECTURE

### **New Structure**: Fractal, Self-Similar, Universal

```
metacli/                              # Renamed from eats_core (more accurate)
│
├── core/                             # FUNDAMENTAL ABSTRACTIONS
│   ├── tool.py                       # ✨ Universal CLI tool abstraction
│   ├── executor.py                   # ✨ Unified execution engine
│   ├── session.py                    # ✨ Session lifecycle management
│   ├── result.py                     # ✨ Unified result representation
│   └── transport.py                  # ✅ KEEP (already excellent!)
│
├── orchestration/                    # EXECUTION STRATEGIES
│   ├── orchestrator.py               # ✨ Main universal orchestrator
│   ├── strategies/
│   │   ├── sequential.py             # Sequential execution
│   │   ├── parallel.py               # Parallel execution
│   │   ├── adaptive.py               # ✨ Adaptive routing (NEW!)
│   │   └── evolutionary.py           # Evolution-based selection
│   └── router.py                     # ✨ Strategy selection logic
│
├── playbooks/                        # DECLARATIVE WORKFLOWS
│   ├── parser.py                     # ✨ YAML playbook parser
│   ├── runner.py                     # ✨ Playbook execution engine
│   ├── validator.py                  # ✨ Schema validation
│   ├── templates.py                  # Template/variable engine
│   ├── artifacts.py                  # Artifact management
│   ├── guardrails.py                 # Safety constraints
│   └── diff_tracker.py               # Change budgets
│
├── intelligence/                     # AI-SPECIFIC CAPABILITIES
│   ├── evolution.py                  # Genetic algorithms (from core.py)
│   ├── agents.py                     # Agent DNA (from core.py)
│   ├── swarm.py                      # Multi-agent coordination
│   ├── judge.py                      # LLM-as-judge (KEEP)
│   └── prompts.py                    # Prompt library (KEEP)
│
├── visual/                           # VISUAL DEBUGGING
│   ├── swarm.py                      # ✅ VisualSwarm (keep as-is)
│   ├── monitor.py                    # Real-time monitoring
│   └── layouts.py                    # Window positioning
│
├── tools/                            # TOOL REGISTRY
│   ├── registry.py                   # ✨ Universal tool registry
│   ├── ai_tools.py                   # AI CLI tools (aider, claude-code)
│   ├── posix_tools.py                # POSIX utilities (grep, sed, awk)
│   ├── custom_tools.py               # User-defined tools
│   └── adapters/                     # Tool-specific adapters
│       ├── aider.py
│       ├── claude_code.py
│       └── generic.py
│
├── persistence/                      # DATA LAYER
│   ├── database.py                   # SQLite backend (KEEP, enhance)
│   ├── archive.py                    # File archives
│   ├── query.py                      # ✨ Rich query interface
│   └── replay.py                     # ✨ Session replay
│
├── templates/                        # TEMPLATE ENGINE
│   ├── engine.py                     # Template processing
│   ├── matchers.py                   # Pattern matching
│   ├── rules.py                      # Conditional logic
│   └── library/                      # Built-in templates
│       ├── code_review.yml
│       ├── refactor.yml
│       └── deploy.yml
│
├── config/                           # CONFIGURATION
│   ├── loader.py                     # Config loading (KEEP)
│   ├── validator.py                  # Config validation
│   └── defaults.py                   # Default settings
│
├── cli/                              # COMMAND-LINE INTERFACE
│   ├── main.py                       # ✨ Unified CLI entry point
│   ├── commands/
│   │   ├── run.py                    # Run playbooks
│   │   ├── list.py                   # List available workflows
│   │   ├── session.py                # Session management
│   │   ├── ghost.py                  # Visual swarm mode
│   │   └── server.py                 # API server
│   └── interactive.py                # Interactive REPL
│
└── utils/                            # UTILITIES
    ├── logging.py                    # Enhanced logging (KEEP)
    ├── metrics.py                    # Metrics collection (KEEP)
    ├── audit.py                      # Security audit (KEEP)
    └── helpers.py                    # Common utilities
```

---

## ✨ KEY INNOVATIONS

### 1. **Universal Tool Abstraction** (NEW!)

Every CLI tool - whether AI assistant, POSIX utility, or custom app - is treated uniformly:

```python
# metacli/core/tool.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ToolCapabilities:
    """What a tool can do."""
    supports_stdin: bool = True
    supports_interactive: bool = False
    needs_pty: bool = False
    async_capable: bool = False
    stateful: bool = False

class UniversalTool(ABC):
    """
    Universal abstraction for ANY CLI tool.

    Works with:
    - AI assistants (aider, claude-code, gemini)
    - POSIX utilities (grep, sed, awk, git)
    - Custom applications
    """

    def __init__(self, name: str, command: List[str], capabilities: ToolCapabilities):
        self.name = name
        self.command = command
        self.capabilities = capabilities

    @abstractmethod
    async def execute(self, input: str, context: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given input."""
        pass

    @abstractmethod
    def validate_input(self, input: str) -> bool:
        """Validate input before execution."""
        pass

# Example usage:
aider = UniversalTool(
    name="aider",
    command=["aider", "--no-auto-commit"],
    capabilities=ToolCapabilities(
        supports_stdin=False,
        supports_interactive=True,
        needs_pty=True,
        async_capable=True,
        stateful=True,
    )
)

grep = UniversalTool(
    name="grep",
    command=["grep", "-r"],
    capabilities=ToolCapabilities(
        supports_stdin=True,
        supports_interactive=False,
        needs_pty=False,
        async_capable=True,
        stateful=False,
    )
)
```

### 2. **Unified Orchestrator** (NEW!)

One execution engine that adapts based on requirements:

```python
# metacli/orchestration/orchestrator.py

class UniversalOrchestrator:
    """
    Unified orchestration engine.

    Automatically selects execution strategy based on:
    - Tool capabilities
    - Workflow requirements
    - Resource constraints
    - Performance goals
    """

    def __init__(self, session: Session):
        self.session = session
        self.strategies = {
            'sequential': SequentialStrategy(),
            'parallel': ParallelStrategy(),
            'adaptive': AdaptiveStrategy(),
            'evolutionary': EvolutionaryStrategy(),
        }

    async def execute(self, playbook: Playbook) -> SessionResult:
        """Execute a playbook with optimal strategy."""

        # Analyze playbook requirements
        strategy_name = self._select_strategy(playbook)
        strategy = self.strategies[strategy_name]

        # Execute with selected strategy
        result = await strategy.execute(
            playbook=playbook,
            session=self.session,
            orchestrator=self,
        )

        return result

    def _select_strategy(self, playbook: Playbook) -> str:
        """Intelligently select execution strategy."""

        if playbook.requires_evolution:
            return 'evolutionary'
        elif playbook.has_parallel_steps:
            return 'parallel'
        elif playbook.is_adaptive:
            return 'adaptive'
        else:
            return 'sequential'
```

### 3. **Declarative Playbook System** (NEW!)

Everything is a playbook - from simple commands to complex workflows:

```yaml
# .ai/workflows/feature-development.yml

metadata:
  name: feature-development
  version: 3.0.0
  description: AI-assisted feature development with guardrails
  tags: [development, ai-assisted, production-ready]

# Required variables
variables:
  required:
    - FEATURE         # Feature description
    - MODULE          # Module/component name
  optional:
    - BRANCH: "feature/{{MODULE}}"
    - AI_TOOL: "aider"
    - REVIEWER: "claude-code"

# Guardrails
guardrails:
  diff_budget:
    max_files: 25
    max_lines: 1500
  allowed_paths:
    - "src/**"
    - "tests/**"
  forbidden_paths:
    - ".env"
    - "secrets/**"

# Workflow steps
steps:
  - id: scan
    name: "Scan codebase context"
    tool: "{{AI_TOOL}}"
    strategy: sequential
    input:
      type: prompt_file
      path: .ai/prompts/scan.md
      variables:
        MODULE: "{{MODULE}}"
    outputs:
      artifacts:
        - CONTEXT.md
    checks:
      - type: file_exists
        path: CONTEXT.md
      - type: max_size
        bytes: 100000

  - id: plan
    name: "Generate implementation plan"
    tool: "{{AI_TOOL}}"
    depends_on: [scan]
    strategy: sequential
    input:
      type: prompt_file
      path: .ai/prompts/plan.md
      variables:
        FEATURE: "{{FEATURE}}"
        CONTEXT: "{{artifacts.CONTEXT.md}}"
    outputs:
      artifacts:
        - PLAN.md
    checks:
      - type: contains
        pattern: "## Implementation Steps"

  - id: implement
    name: "Implement feature"
    tool: "{{AI_TOOL}}"
    depends_on: [plan]
    strategy: adaptive
    input:
      type: prompt_file
      path: .ai/prompts/implement.md
      variables:
        PLAN: "{{artifacts.PLAN.md}}"
    outputs:
      diff: true
    guardrails:
      diff_budget:
        max_files: 15
        max_lines: 800
    checks:
      - type: tests_pass
        command: "pytest tests/"
      - type: lint_pass
        command: "ruff check ."

  - id: review
    name: "Code review"
    tool: "{{REVIEWER}}"
    depends_on: [implement]
    strategy: parallel
    input:
      type: prompt_file
      path: .ai/prompts/review.md
      variables:
        DIFF: "{{step.implement.diff}}"
    outputs:
      artifacts:
        - REVIEW.md
    checks:
      - type: no_critical_issues

  - id: verify
    name: "Verify implementation"
    tool: "pytest"
    depends_on: [implement]
    strategy: sequential
    input:
      command: ["pytest", "tests/", "-v"]
    checks:
      - type: exit_code
        value: 0
```

### 4. **Self-Orchestrating** (META! 🌟)

The framework can orchestrate ITSELF:

```yaml
# .ai/workflows/optimize-itself.yml

metadata:
  name: self-optimization
  description: Framework optimizes its own codebase
  self_referential: true

steps:
  - id: scan_self
    tool: aider
    input:
      prompt: |
        Analyze the MeTaCLIagenT codebase in metacli/ directory.
        Identify:
        - Code duplication
        - Architectural improvements
        - Performance bottlenecks
        - Missing abstractions
    outputs:
      artifacts: [SELF_ANALYSIS.md]

  - id: plan_improvements
    tool: claude-code
    depends_on: [scan_self]
    input:
      prompt: |
        Based on this analysis: {{artifacts.SELF_ANALYSIS.md}}
        Create a detailed refactoring plan.
    outputs:
      artifacts: [IMPROVEMENT_PLAN.md]

  - id: implement_improvements
    tool: aider
    depends_on: [plan_improvements]
    input:
      prompt: |
        Implement this plan: {{artifacts.IMPROVEMENT_PLAN.md}}
        Preserve all existing functionality.
    guardrails:
      diff_budget:
        max_files: 10
        max_lines: 500
```

### 5. **Fractal Architecture** (SELF-SIMILAR 📐)

Every level follows the same pattern:

```
Tool → Execute → Result
  ↓
Step → Execute → Result
  ↓
Playbook → Execute → Result
  ↓
Session → Execute → Result
  ↓
Strategy → Execute → Result

ALL use the same interface!
```

---

## 🎯 MIGRATION STRATEGY

### Phase 1: Foundation (Week 1-2) ✅ **COMPLETE**
- [x] Transport consolidation
- [x] VisualSwarm migration
- [x] Clear architecture boundaries

### Phase 2: Core Abstractions (Week 3-4) 📍 **NEXT**
- [ ] Create `metacli/core/tool.py` - Universal tool abstraction
- [ ] Create `metacli/core/executor.py` - Unified execution engine
- [ ] Create `metacli/core/session.py` - Session management
- [ ] Create `metacli/core/result.py` - Result representation

### Phase 3: Orchestration Layer (Week 5-6)
- [ ] Create `metacli/orchestration/orchestrator.py`
- [ ] Implement sequential strategy
- [ ] Implement parallel strategy
- [ ] Implement adaptive strategy
- [ ] Implement evolutionary strategy

### Phase 4: Playbook Engine (Week 7-9)
- [ ] Create `metacli/playbooks/parser.py`
- [ ] Create `metacli/playbooks/runner.py`
- [ ] Create `metacli/playbooks/templates.py`
- [ ] Create `metacli/playbooks/artifacts.py`
- [ ] Create `metacli/playbooks/guardrails.py`

### Phase 5: Tool Registry (Week 10-11)
- [ ] Create `metacli/tools/registry.py`
- [ ] Implement AI tool adapters (aider, claude-code)
- [ ] Implement POSIX tool adapters
- [ ] Create tool discovery system

### Phase 6: Integration & Migration (Week 12-14)
- [ ] Migrate existing code to new structure
- [ ] Update all entry points
- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Performance benchmarks

---

## 🔮 FUTURE CAPABILITIES (Post-Refactor)

Once the meta-framework is in place:

### 1. **Distributed Execution**
```yaml
deployment:
  strategy: distributed
  workers:
    - host: server1
      tools: [aider, claude-code]
    - host: server2
      tools: [pytest, ruff]
```

### 2. **Cloud Integration**
```yaml
cloud:
  provider: aws
  resources:
    - type: lambda
      for_tools: [grep, sed, awk]
    - type: ec2
      for_tools: [aider, claude-code]
```

### 3. **Plugin System**
```python
@metacli.plugin
class CustomTool(UniversalTool):
    """User-defined tool plugin."""
    pass
```

### 4. **Multi-Project Orchestration**
```yaml
projects:
  - path: ./frontend
    playbook: .ai/workflows/frontend-test.yml
  - path: ./backend
    playbook: .ai/workflows/backend-test.yml
  - path: ./infra
    playbook: .ai/workflows/deploy.yml
```

---

## 📊 METRICS & SUCCESS CRITERIA

### Architecture Quality
- ✅ Single unified orchestrator (instead of 3+)
- ✅ All tools use same abstraction
- ✅ 100% declarative workflows (YAML)
- ✅ Fractal self-similarity at all levels

### Performance
- ✅ <100ms orchestration overhead
- ✅ Parallel execution when possible
- ✅ Efficient resource utilization

### User Experience
- ✅ Simple CLI: `metacli run feature --var FEATURE="auth"`
- ✅ Clear error messages
- ✅ Comprehensive documentation
- ✅ Rich interactive mode

### Power & Flexibility
- ✅ Works with ANY CLI tool
- ✅ Sequential, parallel, adaptive, evolutionary modes
- ✅ Self-orchestrating capability
- ✅ Extensible plugin system

---

## 🚀 IMMEDIATE NEXT STEPS

### Option A: Start Core Abstractions (RECOMMENDED)
1. Create `metacli/core/tool.py` - Universal tool abstraction
2. Create `metacli/core/executor.py` - Execution engine
3. Create `metacli/core/session.py` - Session management
4. Test with simple example (grep → sed pipeline)

### Option B: Start Playbook Engine
1. Create `metacli/playbooks/parser.py` - YAML parser
2. Create `metacli/playbooks/runner.py` - Execution
3. Create example playbook
4. Test end-to-end

### Option C: Gradual Migration
1. Keep existing code working
2. Build new meta-framework alongside
3. Migrate piece by piece
4. Deprecate old code gradually

---

## 🎨 PHILOSOPHICAL PRINCIPLES

### 1. **Universal Applicability**
> "If it runs in a terminal, we can orchestrate it"

### 2. **Declarative Power**
> "Configuration over code, but with full programmability"

### 3. **Self-Similar Patterns**
> "The same abstraction works at every level"

### 4. **Radical Transparency**
> "Every action is logged, queryable, and replayable"

### 5. **Intelligent Defaults, Maximum Control**
> "Works out of the box, customizable to infinity"

### 6. **Meta-Circular**
> "The framework can improve itself"

---

## 🌟 THE ULTIMATE VISION

**MeTaCLIagenT becomes the universal substrate for terminal automation:**

- Students use it to automate homework
- Developers use it to orchestrate AI coding tools
- DevOps use it to automate deployments
- Researchers use it to chain data processing
- Security teams use it for automated audits
- **The framework itself uses it to evolve**

**It's not just a framework - it's a META-FRAMEWORK for building automation frameworks.**

---

**Next Decision Point**: Which option (A, B, or C) should we pursue?

I recommend **Option A** (Core Abstractions) because:
- Establishes the foundation
- Enables all other work
- Can be tested incrementally
- Provides immediate value

Ready to build the future? 🚀
