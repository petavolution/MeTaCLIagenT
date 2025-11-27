# Codebase Simplification Plan

**Date**: 2025-11-26
**Goal**: Simplify project structure to focus on core CLI orchestration functionality
**Status**: Analysis Complete → Implementation Pending

---

## Executive Summary

### Current State
- **Total lines**: 19,875 lines across 39+ Python files
- **Complexity**: High - includes genetic algorithms, swarm intelligence, evolution engines
- **Core functionality**: Buried under layers of advanced features
- **User's actual need**: Simple CLI tool orchestration (claude-code, gemini, aider)

### Target State
- **Focus**: Reliable CLI tool sequencing with output parsing and chaining
- **Architecture**: Minimal core + optional advanced modules
- **Persistence**: Text files + SQLite for orchestration history
- **Line count**: Keep core modules under 500 lines each

---

## Analysis: What User Actually Needs

### User's Explicit Requirements
> "running ai coding dev cli in terminal on debian linux, like codex cli, claude code cli,
> gemini cli, and have internal setup to call them in specific sequences, and parse the
> output, and then send custom follow up text inputs, buffering and saving everything in
> elaborate system of text files on local file system, and a small db to keep records of
> orchestration sequences and results"

### Core Workflow
```
1. Start CLI tool (claude-code, gemini, aider, etc.)
2. Send prompt
3. Read output
4. Parse output (extract code, errors, etc.)
5. Send follow-up based on output
6. Repeat
7. Save everything (text files + SQLite)
```

---

## Current Architecture Problems

### Problem 1: Feature Bloat

**Features That Exist But Aren't Needed for Core Use Case:**

1. **Evolution Engine** (`eats_core/core.py`, `eats/evolution_engine.py`)
   - Genetic algorithms for agent improvement
   - Fitness functions, mutations, generations
   - AgentDNA with lineage tracking
   - **Lines**: ~800+
   - **User need**: ❌ Not requested

2. **Swarm Intelligence** (`eats_core/swarm.py`, `eats/ghost_swarm.py`, `eats/hierarchical_tree.py`)
   - Hierarchical agent trees
   - Probability-fan spawning
   - Senescence tracking
   - Multi-terminal tmux visualization
   - **Lines**: ~1200+
   - **User need**: ❌ Not requested

3. **LLM Judge** (`eats_core/judge.py`, `eats/llm_judge.py`)
   - LLM-as-judge fitness evaluation
   - Pairwise comparison
   - Hybrid scoring
   - **Lines**: ~400+
   - **User need**: ❌ Not requested

4. **Conflict Resolution** (`eats_core/conflict.py`)
   - Contradiction detection
   - Meta-agent arbitration
   - **Lines**: ~300+
   - **User need**: ❌ Not requested

5. **Advanced Workflows** (`eats_core/workflows.py`)
   - DAG-based workflows
   - Complex dependency graphs
   - **Lines**: ~400+
   - **User need**: ⚠️ Simple sequences only

6. **LLM Providers** (`eats_core/providers.py`)
   - OpenAI, Anthropic, Ollama integration
   - **Lines**: ~500+
   - **User need**: ❌ Uses CLI tools directly, not API

### Problem 2: Code Duplication

**Duplicate Implementations:**

1. **PTY Transport**
   - `eats_core/core.py` - PTYTransport class (lines 50-200)
   - `eats/transport_pty.py` - PTYTransport class (264 lines)
   - **Impact**: Maintenance burden, confusion

2. **Tmux Transport**
   - `eats_core/core.py` - TmuxTransport class (lines 200-350)
   - `eats/tmux_transport.py` - TmuxTransport class
   - **Impact**: Bug fixes need to be applied twice

3. **Output Parsing**
   - `eats_core/cli_orchestrator.py` - OutputParser class
   - `eats_core/parsers.py` - Multiple parser classes
   - **Impact**: Overlapping functionality

### Problem 3: Unnecessary Abstraction Layers

**cli_orchestrator.py Current Flow:**
```python
CLISequence
  └─> creates AgentDNA (evolution-focused dataclass)
       └─> creates Agent (evolution-aware wrapper)
            └─> creates PTYTransport (actual I/O)
                 └─> spawns CLI process
```

**What's Actually Needed:**
```python
CLISequence
  └─> creates CLIProcess (simple wrapper)
       └─> spawns CLI process
```

**Lines Saved**: AgentDNA (100 lines) + Agent evolution logic (200 lines) = ~300 lines

---

## Proposed Simplified Architecture

### Core Modules (REQUIRED)

```
eats_core/
├── transport.py          (~300 lines) - PTY + Tmux transport only
├── cli_orchestrator.py   (~500 lines) - Sequence, parse, chain (KEEP AS IS, mostly)
├── cli_persistence.py    (~400 lines) - Save sequences to files + SQLite (NEW)
├── audit.py              (~500 lines) - Security logging (KEEP - already done)
├── audit_query.py        (~300 lines) - Query audit logs (KEEP - already done)
└── logging.py            (~100 lines) - Basic logging (KEEP)
```

**Total Core**: ~2,100 lines (down from 19,875)

### Optional/Advanced Modules (Move to `eats_advanced/`)

```
eats_advanced/
├── evolution.py          - Genetic algorithms, fitness, mutations
├── swarm.py              - Hierarchical agent trees
├── judge.py              - LLM-as-judge evaluation
├── conflict.py           - Conflict detection/resolution
├── providers.py          - Direct LLM API access
├── ghost_swarm.py        - Visual multi-terminal mode
└── workflows.py          - Complex DAG workflows
```

### Legacy Compatibility (`eats/` - deprecated)

Keep for backward compatibility but mark as deprecated.

---

## Detailed Refactoring Plan

### Step 1: Create Minimal Transport Layer

**File**: `eats_core/transport.py` (NEW - consolidate from duplicates)

```python
"""
Minimal transport layer for CLI processes.

Supports:
- PTY (pseudo-terminal for interactive CLIs)
- Tmux (for visual multi-pane debugging)
"""

class Transport:
    """Base transport interface."""
    def start(self) -> None: ...
    def send(self, text: str) -> None: ...
    def recv(self) -> str: ...
    def terminate(self) -> None: ...

class PTYTransport(Transport):
    """PTY-based transport with buffer overflow protection."""
    # Merge best code from:
    # - eats/transport_pty.py (has BufferOverflowError - keep this)
    # - eats_core/core.py (has audit integration - keep this)

class TmuxTransport(Transport):
    """Tmux-based transport for visual debugging."""
    # Merge from:
    # - eats/tmux_transport.py (has shlex.quote - keep this)
    # - eats_core/core.py
```

**Actions**:
- [x] Audit logging integrated in transport_pty.py
- [x] Buffer overflow protection added
- [x] Shell escaping with shlex.quote added
- [ ] Consolidate into single transport.py module
- [ ] Remove evolution-specific code (AgentDNA, mutations, fitness)

### Step 2: Simplify CLI Orchestrator

**File**: `eats_core/cli_orchestrator.py` (REFACTOR)

**Current dependencies**:
```python
from .core import Agent, AgentDNA  # ❌ Brings in evolution baggage
from .presets import get_cli_tool, CLI_TOOLS  # ✅ Keep
from .logging import get_logger  # ✅ Keep
from .audit import get_audit_logger  # ✅ Keep
```

**New dependencies**:
```python
from .transport import PTYTransport  # ✅ Direct, minimal
from .presets import get_cli_tool, CLI_TOOLS  # ✅ Keep
from .logging import get_logger  # ✅ Keep
from .audit import get_audit_logger  # ✅ Keep
```

**Refactor**:
```python
# OLD (lines 451-459):
dna = AgentDNA(
    role=tool_config.name,
    system_prompt=f"You are {tool_config.description}",
    cmd=tool_config.cmd,
)
agent = Agent(dna)
agent.start()

# NEW:
transport = PTYTransport(
    cmd=tool_config.cmd,
    name=tool_config.name
)
transport.start()
```

**Impact**: Remove 300+ lines of unused evolution machinery

### Step 3: Add Persistence Layer

**File**: `eats_core/cli_persistence.py` (NEW)

```python
"""
Persistence for CLI orchestration sequences.

Dual-layer storage:
1. Text files: Complete outputs (grep-able, diff-able)
2. SQLite: Metadata, structured queries, FTS
"""

class SequencePersistence:
    """
    Save/load CLI orchestration sequences.

    Storage layout:
        logs/sequences/
        ├── 2025-11-26/
        │   ├── seq-12345/
        │   │   ├── metadata.json
        │   │   ├── step-1-claude-code.txt
        │   │   ├── step-2-gemini.txt
        │   │   └── step-3-aider.txt
        └── sequences.db
    """

    def save_sequence(self, sequence: CLISequence):
        """Save complete sequence to files + DB."""

    def load_sequence(self, sequence_id: str):
        """Load sequence from storage."""

    def search_outputs(self, query: str):
        """Full-text search across all outputs."""

    def query_sequences(self, **filters):
        """Query by tool, date, status, etc."""
```

**Schema**:
```sql
CREATE TABLE sequences (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,  -- 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_steps INTEGER,
    successful_steps INTEGER,
    error_message TEXT
);

CREATE TABLE steps (
    id TEXT PRIMARY KEY,
    sequence_id TEXT,
    step_number INTEGER,
    tool_name TEXT,
    prompt TEXT,
    output TEXT,
    duration_seconds REAL,
    status TEXT,
    error_message TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY (sequence_id) REFERENCES sequences(id)
);

-- Full-text search
CREATE VIRTUAL TABLE step_outputs_fts USING fts5(
    step_id,
    output,
    content='steps',
    content_rowid='rowid'
);
```

### Step 4: Update Entry Points

**File**: `run_core.py` (UPDATE)

```python
# Add new mode for simple CLI orchestration
def run_cli_orchestrator():
    """Interactive CLI orchestrator for sequencing AI tools."""
    from eats_core.cli_orchestrator import CLISequence
    from eats_core.cli_persistence import SequencePersistence

    print("EATS CLI Orchestrator")
    print("Available tools: claude-code, gemini, aider, python")

    seq = CLISequence("interactive-session")
    persistence = SequencePersistence()

    # Interactive prompt loop...

# Update help
"""
Usage:
    python run_core.py orchestrate  # Simple CLI orchestration (NEW!)
    python run_core.py demo         # Feature demo (evolution, swarms)
    python run_core.py server       # Full web UI
"""
```

### Step 5: Organize Advanced Features

**Directory structure**:
```
eats_core/          # Core (required for basic orchestration)
eats_advanced/      # Advanced features (optional)
eats/               # Legacy v1.0 (deprecated, backward compat)
examples/           # Usage examples
tests/              # Test suite
docu/               # Documentation
```

**Mark advanced features**:
```python
# eats_core/__init__.py (UPDATE)
"""
EATS Core: Simple CLI Orchestration

Basic Import (Minimal):
    from eats_core import CLISequence, OutputParser, WorkflowPatterns

Advanced Import (Full Features):
    from eats_core import SwarmController, Evolution, LLMJudge
    # Or: import eats_advanced
"""

# Basic exports (always available)
__all__ = [
    "CLISequence",
    "OutputParser",
    "WorkflowPatterns",
    "SequencePersistence",
    # ... other core items
]

# Advanced exports (marked as such)
__all_advanced__ = [
    "SwarmController",
    "Evolution",
    "LLMJudge",
    "ConflictResolver",
    # ... other advanced items
]
```

---

## File-by-File Actions

### Files to KEEP (Core)

| File | Lines | Action | Priority |
|------|-------|--------|----------|
| `eats_core/cli_orchestrator.py` | 678 | Refactor (remove Agent/DNA deps) | P0 |
| `eats_core/audit.py` | 532 | Keep as-is ✅ | P0 |
| `eats_core/audit_query.py` | 328 | Keep as-is ✅ | P0 |
| `eats_core/logging.py` | ~100 | Keep as-is | P0 |
| `eats_core/presets.py` | ~400 | Keep CLI_TOOLS section only | P1 |
| `eats_core/parsers.py` | 801 | Keep (useful for output parsing) | P1 |

### Files to REFACTOR

| File | Lines | Action | New File |
|------|-------|--------|----------|
| `eats_core/core.py` | 731 | Extract transports only | `eats_core/transport.py` |
| `eats/transport_pty.py` | 191 | Merge into transport.py | (deleted) |
| `eats/tmux_transport.py` | ~150 | Merge into transport.py | (deleted) |

### Files to MOVE (Advanced)

| File | Lines | Action | New Location |
|------|-------|--------|--------------|
| `eats_core/swarm.py` | ~600 | Move | `eats_advanced/swarm.py` |
| `eats_core/judge.py` | ~400 | Move | `eats_advanced/judge.py` |
| `eats_core/conflict.py` | ~300 | Move | `eats_advanced/conflict.py` |
| `eats_core/async_core.py` | ~500 | Move | `eats_advanced/async_core.py` |
| `eats_core/workflows.py` | ~400 | Move | `eats_advanced/workflows.py` |
| `eats_core/providers.py` | ~500 | Move | `eats_advanced/providers.py` |
| `eats_core/prompts.py` | 838 | Move | `eats_advanced/prompts.py` |
| `eats/evolution_engine.py` | ~400 | Move | `eats_advanced/evolution_engine.py` |
| `eats/ghost_swarm.py` | ~300 | Move | `eats_advanced/ghost_swarm.py` |

### Files to CREATE (New)

| File | Lines | Purpose |
|------|-------|---------|
| `eats_core/transport.py` | ~300 | Consolidated transport layer |
| `eats_core/cli_persistence.py` | ~400 | Sequence persistence (files + SQLite) |
| `examples/simple_orchestration.py` | ~100 | Simple usage example |
| `docu/QUICK-START.md` | - | Getting started guide |

---

## Implementation Phases

### Phase 1: Core Refactoring (Week 1)
- [x] Create CODEBASE-SIMPLIFICATION-PLAN.md (this file)
- [ ] Create eats_core/transport.py (consolidate PTY + Tmux)
- [ ] Refactor cli_orchestrator.py (remove Agent/DNA deps)
- [ ] Test basic sequence execution
- [ ] Update examples/cli_orchestration_demo.py

### Phase 2: Persistence (Week 1)
- [ ] Create eats_core/cli_persistence.py
- [ ] Implement file-based storage
- [ ] Implement SQLite storage with FTS
- [ ] Add auto-save to CLISequence
- [ ] Create query/replay tools

### Phase 3: Organization (Week 2)
- [ ] Create eats_advanced/ directory
- [ ] Move advanced features
- [ ] Update imports throughout
- [ ] Update __init__.py exports
- [ ] Mark eats/ as deprecated

### Phase 4: Documentation (Week 2)
- [ ] Write QUICK-START.md
- [ ] Update README.md
- [ ] Create ARCHITECTURE.md (new simplified version)
- [ ] Add docstring examples
- [ ] Update run_core.py help text

### Phase 5: Testing (Week 2)
- [ ] Test core orchestration workflows
- [ ] Test persistence layer
- [ ] Test backward compatibility
- [ ] Integration tests
- [ ] Performance benchmarks

---

## Success Metrics

### Simplicity
- ✅ Core under 3,000 lines (currently ~2,100 planned)
- ✅ No file over 600 lines in core
- ✅ Zero circular dependencies
- ✅ Single clear entry point for basic use

### Reliability
- ✅ Basic sequence workflow works 100%
- ✅ All security fixes preserved
- ✅ Audit logging complete
- ✅ Error handling comprehensive

### Persistence
- ✅ All outputs saved automatically
- ✅ Full-text search working
- ✅ Replay capability functional
- ✅ Export/import working

### User Experience
- ✅ Can run example in < 5 minutes
- ✅ Clear "basic" vs "advanced" separation
- ✅ Documentation up to date
- ✅ Backward compatibility maintained

---

## Risks and Mitigations

### Risk 1: Breaking Changes
**Mitigation**: Keep eats/ for backward compatibility, provide migration guide

### Risk 2: Loss of Features
**Mitigation**: Move to eats_advanced/, don't delete

### Risk 3: Incomplete Testing
**Mitigation**: Maintain comprehensive test suite, test before/after

### Risk 4: Documentation Drift
**Mitigation**: Update docs in same commit as code changes

---

## Next Steps

1. ✅ Complete this analysis document
2. ⏳ Create eats_core/transport.py (consolidate PTY/Tmux)
3. ⏳ Refactor cli_orchestrator.py (remove evolution deps)
4. ⏳ Implement cli_persistence.py
5. ⏳ Update documentation
6. ⏳ Test end-to-end

**Current Task**: Create transport.py module (Phase 1, Step 1)
