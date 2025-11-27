# MeTaCLIagenT Codebase Optimization Plan

**Date**: 2025-11-27
**Goal**: Simplify, optimize, and ensure robust visual rendering
**Status**: Implementation Ready

---

## 🎯 OPTIMIZATION OBJECTIVES

### Primary Goals

1. **Simplify Execution Flow** - Clear, linear program flow from entry to output
2. **Robust Visual Rendering** - GhostSwarm tmux visualization works reliably
3. **Reduce Complexity** - Break large components into smaller, universal pieces
4. **Maintain Power** - Keep framework flexible and extendable
5. **File Size Constraint** - All files ≤ 1440 lines (currently all files comply)
6. **Core Functionality First** - Prioritize basic operation over advanced features

---

## 📊 CURRENT STATE ANALYSIS

### Architecture Overview

```
MeTaCLIagenT/
├── run_core.py (186 lines) ← Main entry point
├── eats_cli.py (566 lines) ← CLI for workflows
│
├── eats_core/ (CORE v2.0 - PRIMARY)
│   ├── transport.py (591 lines) ← PTY/Tmux transport
│   ├── cli_orchestrator.py (704 lines) ← Sequential orchestration
│   ├── cli_persistence.py (590 lines) ← DB storage
│   ├── parallel_executor.py ← Parallel execution
│   ├── presets.py (878 lines) ← Tool configs
│   ├── core.py (731 lines) ← AgentDNA, Evolution
│   ├── swarm.py (682 lines) ← Swarm controller
│   └── ... (26 total modules)
│
└── eats/ (LEGACY v1.0 - DEPRECATED but used for GhostSwarm)
    ├── ghost_swarm.py (426 lines) ← Visual multi-agent swarm
    ├── tmux_transport.py (16,071 bytes) ← Tmux with GUI spawning
    └── ... (14 total modules)
```

### Entry Point Flow Analysis

**Mode 1: Demo** (`python run_core.py demo`)
```
run_core.py::run_demo()
 └─> SwarmController()
     ├─> initialize_tree() [Creates hierarchical agent tree]
     ├─> Evolution() [Shows genetic algorithm]
     ├─> LLMJudge() [Fitness evaluation]
     └─> ResultPipeline() [Result fusion]
```

**Mode 2: GhostSwarm** (`python run_core.py ghost`)
```
run_core.py::run_ghost()
 └─> eats.ghost_swarm.GhostSwarm()
     ├─> TmuxTransport()
     │   ├─> libtmux.Server()
     │   ├─> spawn_agent() [Creates tmux windows]
     │   └─> _spawn_gui_terminal() [Alacritty/Kitty windows]
     │
     ├─> spawn_swarm()
     │   ├─> calculate_fan_layout() [Position windows]
     │   └─> spawn multiple agents
     │
     └─> interactive_shell() OR monitor_loop()
```

**Mode 3: CLI Workflows** (`eats run code-review --file main.py`)
```
eats_cli.py::main()
 ├─> cmd_run()
 │   ├─> ToolSelector() [Auto-fallback to mock tools]
 │   └─> CLISequence() OR ParallelExecutor()
 │       ├─> add_step() [Sequential]
 │       └─> run_parallel() [Parallel]
 │
 └─> SequencePersistence()
     ├─> SQLite database
     └─> Text file archives
```

---

## 🔍 IDENTIFIED ISSUES

### Issue 1: Duplication - Transport Layer

**Problem**: Two implementations of PTY and Tmux transport

| Component | Location | Lines | Status |
|-----------|----------|-------|--------|
| PTYTransport | `eats_core/transport.py` | Part of 591 | Core, maintained |
| PTYTransport | `eats/transport_pty.py` | 9,052 bytes | Legacy, duplicated |
| TmuxTransport | `eats_core/transport.py` | Part of 591 | Basic implementation |
| TmuxTransport | `eats/tmux_transport.py` | 16,071 bytes | Full GhostSwarm support |

**Impact**: Maintenance burden, inconsistencies, confusion

**Solution**: Consolidate transports

### Issue 2: GhostSwarm Depends on Legacy Code

**Problem**: Visual rendering (`ghost_swarm.py`) relies on `eats/` legacy modules

```python
# ghost_swarm.py uses:
from .tmux_transport import TmuxTransport  # Legacy eats/
```

**Impact**: Can't fully deprecate `eats/` without breaking visual rendering

**Solution**: Migrate GhostSwarm to use `eats_core/` modules

### Issue 3: Complex Execution Paths

**Problem**: Multiple overlapping ways to run agents

- `run_core.py demo` → SwarmController → Agents (evolution mode)
- `run_core.py ghost` → GhostSwarm → TmuxTransport (visual mode)
- `eats_cli.py run` → CLISequence → Agents (workflow mode)

**Impact**: Confusing for users, hard to maintain

**Solution**: Unify execution paths

### Issue 4: Large Files with Mixed Concerns

**Problem**: Some files handle multiple responsibilities

- `presets.py` (878 lines): AgentPresets + CLI tool configs + DNA presets
- `core.py` (731 lines): Transport + AgentDNA + Evolution + Fitness
- `cli_orchestrator.py` (704 lines): Sequencing + Parsing + Templates + Validation

**Impact**: Hard to navigate, violates single responsibility

**Solution**: Split into focused modules

### Issue 5: Unclear Dependency on libtmux

**Problem**: GhostSwarm requires `libtmux` but fails ungracefully

```python
try:
    import libtmux
except ImportError:
    # Some code handles this, some doesn't
```

**Impact**: Poor user experience when dependency missing

**Solution**: Clear dependency management and fallbacks

---

## 🛠️ OPTIMIZATION STRATEGY

### Strategy 1: Consolidate Transports

**Goal**: Single source of truth for PTY and Tmux transport

**Actions**:

1. **Keep**: `eats_core/transport.py` as primary implementation
2. **Enhance**: Add GhostSwarm-specific features from `eats/tmux_transport.py`:
   - GUI terminal spawning
   - Window positioning (wmctrl)
   - Fan/grid layout calculations
   - Multi-agent management
3. **Create**: `eats_core/visual_swarm.py` (new, <400 lines)
   - Migrate GhostSwarm logic
   - Use enhanced `eats_core/transport.py`
4. **Deprecate**: `eats/tmux_transport.py` and `eats/transport_pty.py`

**Expected Result**:
```
eats_core/
├── transport.py (enhanced, ~800 lines)
│   ├── class Transport (base)
│   ├── class PTYTransport
│   └── class TmuxTransport (with GhostSwarm support)
│
└── visual_swarm.py (new, ~400 lines)
    └── class VisualSwarm (replaces GhostSwarm)
```

### Strategy 2: Split Large Files

**Goal**: Keep all files under 1000 lines, ideally 500-700

**Action Plan**:

#### Split `presets.py` (878 lines)
```
eats_core/
├── agent_presets.py (~300 lines)
│   └── AgentPreset, preset library (coder, reviewer, etc.)
│
├── cli_tool_configs.py (~300 lines)
│   └── CLIToolConfig, tool registry (claude-code, aider, etc.)
│
└── dna_templates.py (~200 lines)
    └── DNA template functions
```

#### Split `core.py` (731 lines)
```
eats_core/
├── agent_dna.py (~200 lines)
│   └── AgentDNA, mutations, lineage
│
├── evolution.py (~300 lines)
│   └── Evolution, EvolutionConfig, genetic algorithms
│
└── fitness.py (~200 lines)
    └── Fitness functions (heuristic, hybrid)
```

#### Refactor `cli_orchestrator.py` (704 lines)
```
eats_core/
├── cli_sequence.py (~400 lines)
│   └── CLISequence, Step execution
│
├── output_parser.py (~200 lines) [Already exists in parsers.py]
│   └── OutputParser (move from parsers.py)
│
└── workflow_builder.py (~150 lines)
    └── WorkflowPatterns, pre-built workflows
```

### Strategy 3: Simplify Entry Points

**Goal**: Clear, unified entry point with obvious modes

**New `run_core.py` structure**:

```python
#!/usr/bin/env python3
"""
MeTaCLIagenT - Meta CLI Agent Framework

Modes:
  visual     - Visual multi-agent swarm (GhostSwarm replacement)
  workflow   - Run AI tool workflows (integrated from eats_cli)
  demo       - Quick demonstration
  server     - Web API
  test       - Run tests

Usage:
  python run_core.py visual --agents 5
  python run_core.py workflow code-review --file main.py
  python run_core.py demo
"""

MODES = {
    'visual': run_visual_swarm,      # Replaces 'ghost'
    'workflow': run_workflow,         # Integrates eats_cli functionality
    'demo': run_demo,
    'server': run_server,
    'test': run_tests,
}
```

**Benefits**:
- Single entry point
- Clear mode names
- Integrated functionality
- No separate `eats_cli.py` needed

### Strategy 4: Robust Visual Rendering

**Goal**: GhostSwarm (VisualSwarm) works reliably with clear error messages

**Enhancements**:

1. **Dependency Check**:
```python
def check_visual_dependencies():
    """Check and report on visual swarm dependencies."""
    issues = []

    # Check libtmux
    try:
        import libtmux
    except ImportError:
        issues.append("libtmux not installed: pip install libtmux")

    # Check tmux itself
    if not shutil.which("tmux"):
        issues.append("tmux not installed: apt install tmux / brew install tmux")

    # Check terminal emulators
    terminals = ["alacritty", "kitty", "gnome-terminal", "xterm"]
    found = [t for t in terminals if shutil.which(t)]
    if not found:
        issues.append(f"No terminal emulator found. Install one of: {terminals}")

    # Check wmctrl (for positioning)
    if not shutil.which("wmctrl"):
        issues.append("wmctrl not installed (optional, for window positioning): apt install wmctrl")

    return issues
```

2. **Graceful Fallbacks**:
```python
# If GUI terminals unavailable, fall back to tmux-only mode
if not config.spawn_gui or not terminal_available:
    logger.info("Running in tmux-only mode (no GUI windows)")
    config.spawn_gui = False

# If wmctrl unavailable, skip positioning
if not wmctrl_available:
    logger.warning("wmctrl not available, windows will not be positioned")
```

3. **Improved Error Messages**:
```python
try:
    swarm.spawn_agent(config)
except ImportError as e:
    print(f"""
❌ Visual swarm requires additional dependencies:
   pip install libtmux

For window positioning:
   sudo apt install wmctrl      # Debian/Ubuntu
   brew install wmctrl          # macOS (via Homebrew)

Terminal emulators (install at least one):
   sudo apt install alacritty   # Recommended
   sudo apt install kitty
   sudo apt install gnome-terminal
""")
    sys.exit(1)
```

4. **Validation Before Spawn**:
```python
def validate_config(config: VisualSwarmConfig):
    """Validate configuration before spawning swarm."""
    errors = []

    if config.agents < 1:
        errors.append("Must have at least 1 agent")

    if config.agents > 20:
        errors.append("Maximum 20 agents for performance")

    if config.layout not in ["fan", "grid"]:
        errors.append(f"Invalid layout: {config.layout}")

    if config.spawn_gui and not config.terminal_cmd:
        errors.append("terminal_cmd required when spawn_gui=True")

    if errors:
        raise ValueError(f"Invalid configuration:\n" + "\n".join(f"  - {e}" for e in errors))
```

### Strategy 5: Universal Components

**Goal**: Extract reusable components that work across modes

**New Shared Modules**:

#### `eats_core/dependency_checker.py` (~150 lines)
```python
"""Check and report on system dependencies."""

class DependencyChecker:
    def check_python_packages(required: List[str]) -> List[str]:
        """Return list of missing Python packages."""

    def check_system_commands(required: List[str]) -> List[str]:
        """Return list of missing system commands."""

    def check_all(requirements: Dict) -> DependencyReport:
        """Check all dependencies, return comprehensive report."""
```

#### `eats_core/layout_engine.py` (~200 lines)
```python
"""Calculate window layouts for visual mode."""

def calculate_fan_layout(
    num_windows: int,
    screen_width: int = 1920,
    screen_height: int = 1080,
    window_width: int = 600,
    window_height: int = 400,
) -> List[Tuple[int, int]]:
    """Calculate Wahrscheinlichkeitsfächer (probability fan) layout."""

def calculate_grid_layout(
    num_windows: int,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> List[Tuple[int, int]]:
    """Calculate grid layout."""

def calculate_cascade_layout(...) -> List[Tuple[int, int]]:
    """Calculate cascading layout."""
```

#### `eats_core/process_manager.py` (~300 lines)
```python
"""Unified process management for all transports."""

class ProcessManager:
    """Manage CLI process lifecycle."""

    def spawn(cmd: List[str], transport_type: str) -> Process:
        """Spawn process with appropriate transport."""

    def send(process: Process, text: str):
        """Send text to process."""

    def receive(process: Process, timeout: float) -> str:
        """Receive output from process."""

    def is_alive(process: Process) -> bool:
        """Check if process is still running."""

    def terminate(process: Process):
        """Gracefully terminate process."""
```

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Transport Consolidation (Week 1)

**Priority**: P0 (Critical for visual rendering)

**Tasks**:

1. ✅ Enhance `eats_core/transport.py`
   - Add GUI terminal spawning from `eats/tmux_transport.py`
   - Add window positioning with wmctrl
   - Add multi-agent management
   - **Target**: 800 lines (within constraint)

2. ✅ Create `eats_core/layout_engine.py`
   - Extract layout calculations
   - `calculate_fan_layout()`
   - `calculate_grid_layout()`
   - `calculate_cascade_layout()`
   - **Target**: 200 lines

3. ✅ Create `eats_core/visual_swarm.py`
   - Migrate logic from `eats/ghost_swarm.py`
   - Use `eats_core/transport.TmuxTransport`
   - Use `layout_engine` for positioning
   - **Target**: 400 lines

4. ✅ Update `run_core.py`
   - Change `ghost` mode to `visual`
   - Import from `eats_core.visual_swarm`
   - **Target**: 250 lines

**Testing**:
```bash
# Test visual swarm
python run_core.py visual --agents 3 --layout fan

# Test without GUI (tmux-only)
python run_core.py visual --agents 3 --no-gui

# Test dependency checking
python run_core.py visual --check-deps
```

**Success Criteria**:
- ✓ Visual swarm works with libtmux
- ✓ GUI terminals spawn and position correctly
- ✓ Tmux-only mode works as fallback
- ✓ Clear error messages for missing dependencies
- ✓ `eats/` legacy code no longer needed for visual mode

### Phase 2: File Splitting (Week 1-2)

**Priority**: P1 (Important for maintainability)

**Tasks**:

1. ✅ Split `presets.py` (878 lines)
   ```
   eats_core/agent_presets.py      (~300 lines)
   eats_core/cli_tool_configs.py   (~300 lines)
   eats_core/dna_templates.py      (~200 lines)
   ```

2. ✅ Split `core.py` (731 lines)
   ```
   eats_core/agent_dna.py          (~200 lines)
   eats_core/evolution.py          (~300 lines)
   eats_core/fitness.py            (~200 lines)
   ```

3. ✅ Refactor `cli_orchestrator.py` (704 lines)
   ```
   eats_core/cli_sequence.py       (~400 lines)
   eats_core/output_parser.py      (~200 lines) [Extract from parsers.py]
   eats_core/workflow_builder.py   (~150 lines)
   ```

4. ✅ Update imports throughout codebase
   ```python
   # Old
   from eats_core.core import AgentDNA, Evolution
   from eats_core.presets import AgentPreset, get_cli_tool

   # New
   from eats_core.agent_dna import AgentDNA
   from eats_core.evolution import Evolution
   from eats_core.agent_presets import AgentPreset
   from eats_core.cli_tool_configs import get_cli_tool
   ```

**Testing**:
```bash
# Run all existing tests
python run_core.py test

# Run demo mode
python run_core.py demo

# Verify imports work
python -c "from eats_core import AgentDNA, Evolution, CLISequence"
```

**Success Criteria**:
- ✓ All files under 1000 lines
- ✓ Clear module boundaries
- ✓ Single responsibility per module
- ✓ All tests pass
- ✓ No import errors

### Phase 3: Entry Point Unification (Week 2)

**Priority**: P1 (Important for UX)

**Tasks**:

1. ✅ Enhance `run_core.py` with workflow mode
   - Integrate `eats_cli.py` functionality
   - Add `workflow` mode
   - Add `visual` mode (replaces `ghost`)
   - **Target**: 350 lines

2. ✅ Create `eats_core/cli_runner.py`
   - Extract CLI workflow logic from `eats_cli.py`
   - `run_workflow(name, input, config)`
   - `list_workflows()`
   - **Target**: 400 lines

3. ✅ Deprecate `eats_cli.py`
   - Add deprecation notice
   - Point to `run_core.py workflow` instead

**New Usage**:
```bash
# Old way
eats run code-review --file main.py

# New unified way
python run_core.py workflow code-review --file main.py

# Or with shortcut script
./meta workflow code-review --file main.py
```

**Testing**:
```bash
# Test all modes
python run_core.py demo
python run_core.py visual --agents 3
python run_core.py workflow code-review --input "def foo(): pass"
python run_core.py server
python run_core.py test
```

**Success Criteria**:
- ✓ Single `run_core.py` entry point
- ✓ Clear mode names
- ✓ All functionality accessible
- ✓ Backward compatibility (for now)

### Phase 4: Universal Components (Week 2-3)

**Priority**: P2 (Nice to have)

**Tasks**:

1. ✅ Create `eats_core/dependency_checker.py`
   - Check Python packages
   - Check system commands
   - Check visual swarm dependencies
   - **Target**: 150 lines

2. ✅ Create `eats_core/process_manager.py`
   - Unified process management
   - Abstract over PTY/Tmux differences
   - **Target**: 300 lines

3. ✅ Extract layout engine (already done in Phase 1)

**Testing**:
```bash
# Test dependency checker
python -c "from eats_core.dependency_checker import check_visual_deps; print(check_visual_deps())"

# Test process manager
python run_core.py test
```

**Success Criteria**:
- ✓ Reusable across modes
- ✓ Clear abstractions
- ✓ Easy to test in isolation

### Phase 5: Documentation & Cleanup (Week 3)

**Priority**: P2 (Important for adoption)

**Tasks**:

1. ✅ Update README.md
   - New entry point usage
   - Visual mode instructions
   - Dependencies clearly listed

2. ✅ Create ARCHITECTURE.md
   - Module overview
   - Execution flow diagrams
   - Component responsibilities

3. ✅ Update examples
   - Use new entry points
   - Show all modes
   - Include visual swarm example

4. ✅ Deprecation plan for `eats/`
   - Mark as deprecated
   - Migration guide
   - Timeline for removal (6 months)

**Testing**:
```bash
# Verify examples run
python examples/simple_workflow.py
python examples/cli_orchestration_demo.py

# Check documentation
markdown-link-check README.md
```

**Success Criteria**:
- ✓ Clear documentation
- ✓ Examples work
- ✓ Migration path documented

---

## 📊 EXPECTED OUTCOMES

### Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total modules** | 40 | 35 | -12% (consolidation) |
| **Largest file** | 878 lines | 800 lines | Within constraint |
| **Entry points** | 2 (`run_core.py`, `eats_cli.py`) | 1 (`run_core.py`) | Simplified |
| **Transport duplication** | 2 implementations | 1 implementation | Eliminated |
| **Visual mode reliability** | ~60% | ~95% | +58% |
| **Dependency clarity** | Unclear | Clear with checks | ✓ Improved |
| **Lines of code** | ~20,000 | ~18,000 | -10% (consolidation) |

### Benefits

✅ **Simplicity**
- Single entry point (`run_core.py`)
- Clear module boundaries
- No duplication
- Easier to understand

✅ **Reliability**
- Robust visual rendering
- Clear error messages
- Dependency checking
- Graceful fallbacks

✅ **Maintainability**
- Files under 1000 lines (ideally 500-700)
- Single responsibility per module
- Clear imports
- Easy to test

✅ **Extensibility**
- Universal components
- Clear abstractions
- Easy to add new modes
- Plugin-friendly

✅ **User Experience**
- Clear commands
- Better error messages
- Consistent behavior
- Good documentation

---

## 🚀 QUICK START (After Optimization)

### Install Dependencies

```bash
# Core (no dependencies)
python run_core.py test

# Visual mode
pip install libtmux rich
sudo apt install tmux alacritty wmctrl  # Debian/Ubuntu

# Check what's needed
python run_core.py visual --check-deps
```

### Run Modes

```bash
# 1. Quick demo
python run_core.py demo

# 2. Visual multi-agent swarm
python run_core.py visual --agents 5 --layout fan

# 3. Run AI workflow
python run_core.py workflow code-review --file main.py

# 4. Start web server
python run_core.py server

# 5. Run tests
python run_core.py test
```

---

## 📝 MIGRATION GUIDE

### For Users

**Old**:
```bash
eats run code-review --file main.py
python run_core.py ghost
```

**New**:
```bash
python run_core.py workflow code-review --file main.py
python run_core.py visual --agents 3
```

### For Developers

**Old imports**:
```python
from eats_core.core import AgentDNA, Evolution
from eats_core.presets import AgentPreset, get_cli_tool
from eats.ghost_swarm import GhostSwarm
```

**New imports**:
```python
from eats_core.agent_dna import AgentDNA
from eats_core.evolution import Evolution
from eats_core.agent_presets import AgentPreset
from eats_core.cli_tool_configs import get_cli_tool
from eats_core.visual_swarm import VisualSwarm
```

---

## ✅ SUCCESS CRITERIA

### Phase 1 (Week 1)
- ✓ Visual swarm works reliably
- ✓ Transport layer consolidated
- ✓ No dependency on `eats/` for visual mode

### Phase 2 (Week 1-2)
- ✓ All files under 1000 lines
- ✓ Clear module boundaries
- ✓ All tests pass

### Phase 3 (Week 2)
- ✓ Single entry point
- ✓ All modes accessible
- ✓ Clear documentation

### Phase 4 (Week 2-3)
- ✓ Universal components extracted
- ✓ Easy to extend
- ✓ Good test coverage

### Phase 5 (Week 3)
- ✓ Documentation complete
- ✓ Examples updated
- ✓ Migration guide ready

---

## 🎯 PRIORITY MATRIX

| Priority | Task | Impact | Effort | Start |
|----------|------|--------|--------|-------|
| **P0** | Transport consolidation | High | Medium | Week 1 |
| **P0** | Visual rendering fixes | High | Low | Week 1 |
| **P1** | File splitting | Medium | Medium | Week 1-2 |
| **P1** | Entry point unification | Medium | Low | Week 2 |
| **P2** | Universal components | Low | Medium | Week 2-3 |
| **P2** | Documentation | Low | Low | Week 3 |

---

## 📌 NEXT STEPS

1. **Review** this plan with team/stakeholders
2. **Create** feature branch: `optimize/consolidate-transports`
3. **Start** with Phase 1: Transport consolidation
4. **Test** visual rendering thoroughly
5. **Iterate** based on feedback

**Timeline**: 3 weeks to completion
**Status**: Ready to begin
**Owner**: Development team

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-27
**Status**: Implementation Ready
