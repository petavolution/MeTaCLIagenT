# Transport Consolidation - Audit Report

**Date**: 2025-11-27
**Status**: Step 1 Complete - Ready for Step 2

---

## 🔍 EXECUTIVE SUMMARY

**Finding**: Transport layer is duplicated in TWO separate files within `eats_core/`:
- `eats_core/core.py` (lines 45-343): Transport + PTYTransport + TmuxTransport
- `eats_core/transport.py` (591 lines): Transport + PTYTransport + TmuxTransport

**Impact**:
- ❌ Code duplication (300+ lines duplicated)
- ❌ API incompatibility between implementations
- ❌ Import confusion (different files use different sources)
- ❌ Maintenance burden (changes must be applied twice)

**Recommendation**: Make `transport.py` canonical, remove Transport from `core.py`

---

## 📊 IMPORT USAGE ANALYSIS

### Files Importing from `eats_core/core.py`

| File | Line | What's Imported |
|------|------|-----------------|
| `eats_core/__init__.py` | 97-106 | Transport, PTYTransport, TmuxTransport, AgentDNA, Agent, Evolution |
| `eats_core/swarm.py` | 18 | Agent, AgentDNA, Transport, TmuxTransport, PTYTransport |
| `eats_core/async_core.py` | 20 | Agent, AgentDNA, Transport |

**Total: 3 files** using Transport from `core.py`

### Files Importing from `eats_core/transport.py`

| File | Line | What's Imported |
|------|------|-----------------|
| `validate_core.py` | 28 | PTYTransport, create_transport |
| `eats_core/cli_orchestrator.py` | 37 | Transport, PTYTransport, create_transport |

**Total: 2 files** using Transport from `transport.py`

### Files Importing from Legacy `eats/tmux_transport.py`

| File | Line | What's Imported |
|------|------|-----------------|
| `eats/__init__.py` | 35 | TmuxTransport |
| `eats/ghost_swarm.py` | 46 | (tmux_transport imports) |

**Total: 2 files** using legacy tmux_transport (GhostSwarm)

### Files Importing from Legacy `eats/transport_pty.py`

| File | Line | What's Imported |
|------|------|-----------------|
| `eats/agents.py` | 15 | PTYTransport |
| `eats/manager.py` | 15 | PTYTransport |

**Total: 2 files** using legacy transport_pty

---

## 🔬 API COMPATIBILITY ANALYSIS

### Base Transport Class

#### `core.py` Transport (ABC-based)

```python
from abc import ABC, abstractmethod

class Transport(ABC):
    @abstractmethod
    def start(self) -> None: pass

    @abstractmethod
    def send(self, text: str, newline: bool = True) -> None: pass

    @abstractmethod
    def recv(self, timeout: float = 0.1) -> str: pass

    @abstractmethod
    def is_alive(self) -> bool: pass

    @abstractmethod
    def terminate(self) -> None: pass

    def send_and_wait(self, text: str, wait_seconds: float = 2.0,
                      idle_threshold: float = 0.5) -> str:
        # Implementation provided
```

**Methods**: 6 total (5 abstract + 1 concrete helper)

#### `transport.py` Transport (NotImplementedError-based)

```python
class Transport:
    def start(self) -> None:
        raise NotImplementedError

    def send_line(self, text: str) -> None:
        raise NotImplementedError

    def send_raw(self, text: str) -> None:
        raise NotImplementedError

    def recv_now(self) -> str:
        raise NotImplementedError

    def terminate(self) -> None:
        raise NotImplementedError

    def is_alive(self) -> bool:
        raise NotImplementedError

    def get_full_log(self) -> str:
        raise NotImplementedError

    def send_and_wait(self, prompt: str, wait_seconds: float = 5.0,
                      idle_threshold: float = 0.5) -> str:
        # Implementation provided
```

**Methods**: 8 total (7 abstract + 1 concrete helper)

### ⚠️ API INCOMPATIBILITIES

| Feature | core.py | transport.py | Compatible? |
|---------|---------|--------------|-------------|
| `start()` | ✅ | ✅ | ✅ YES |
| `terminate()` | ✅ | ✅ | ✅ YES |
| `is_alive()` | ✅ | ✅ | ✅ YES |
| `send()` with newline param | ✅ | ❌ | ❌ NO - Different API |
| `send_line()` | ❌ | ✅ | ❌ NO - Missing in core.py |
| `send_raw()` | ❌ | ✅ | ❌ NO - Missing in core.py |
| `recv(timeout)` | ✅ | ❌ | ❌ NO - Different API |
| `recv_now()` | ❌ | ✅ | ❌ NO - Missing in core.py |
| `get_full_log()` | ❌ | ✅ | ❌ NO - Missing in core.py |
| `send_and_wait()` | ✅ | ✅ | ⚠️ PARTIAL - Different param names |

### Key Differences

**1. Send Methods**
- `core.py`: Single `send(text, newline=True)` method
- `transport.py`: Separate `send_line(text)` and `send_raw(text)` methods
- **Impact**: Code using `transport.send("foo", newline=False)` won't work with transport.py

**2. Receive Methods**
- `core.py`: `recv(timeout=0.1)` - takes timeout parameter
- `transport.py`: `recv_now()` - no timeout parameter
- **Impact**: Code using `transport.recv(timeout=2.0)` won't work with transport.py

**3. Extra Features**
- `transport.py` has `get_full_log()` for complete history
- `transport.py` has `get_exit_code()` for process status
- `core.py` lacks these features

---

## 📋 FEATURE COMPARISON

### PTYTransport

| Feature | core.py | transport.py | Notes |
|---------|---------|--------------|-------|
| Buffer overflow protection | ✅ | ✅ | Both have MAX_BUFFER_SIZE |
| Max buffer size | 10MB | 10MB | Same |
| Full log buffer | ❌ | ✅ | transport.py has ring buffer |
| Max log size | ❌ | 50MB | transport.py only |
| Audit logging | ✅ | ✅ | Both integrate with audit logger |
| Terminal size setting | ✅ | ✅ | Both set to 50x120 |
| Background reader thread | ✅ | ✅ | Both use threading |
| API methods | send/recv | send_line/send_raw/recv_now | Different APIs |

**Winner**: `transport.py` (better features, but incompatible API)

### TmuxTransport

| Feature | core.py | transport.py | Notes |
|---------|---------|--------------|-------|
| libtmux dependency | Required | Optional | transport.py uses subprocess |
| GUI terminal spawning | ✅ | ❌ | core.py has `_spawn_gui_window()` |
| Terminal choice | ✅ (4 options) | ❌ | core.py supports alacritty/kitty/gnome/xterm |
| Session management | libtmux API | tmux subprocess | Different approaches |
| Command escaping | shlex.quote | shlex.quote | Both secure |
| Pane capture | libtmux API | subprocess | Different approaches |

**Winner**: `core.py` (has GUI spawning needed for GhostSwarm)

---

## 🎯 MIGRATION REQUIREMENTS

### To Make `transport.py` Canonical

**1. Add Missing Features to `transport.py`**

Need to add from `core.py` TmuxTransport:
- GUI terminal spawning (`_spawn_gui_window()` method)
- Terminal selection (alacritty/kitty/gnome-terminal/xterm)
- `spawn_gui` parameter to constructor

**2. Provide Backward Compatibility Wrappers**

To support existing code that uses `send(text, newline=True)`:

```python
# Add to Transport base class
def send(self, text: str, newline: bool = True) -> None:
    """Backward compatibility wrapper for send_line/send_raw."""
    if newline:
        self.send_line(text)
    else:
        self.send_raw(text)

def recv(self, timeout: float = 0.1) -> str:
    """Backward compatibility wrapper for recv_now."""
    if timeout > 0:
        time.sleep(timeout)
    return self.recv_now()
```

**3. Files That Need Import Changes**

After enhancement, update these files:
- `eats_core/__init__.py` (lines 97-106) - Change from `.core` to `.transport`
- `eats_core/swarm.py` (line 18) - Change from `.core` to `.transport`
- `eats_core/async_core.py` (line 20) - Change from `.core` to `.transport`

**4. Files That Can Stay Unchanged**

These already import from transport.py:
- ✅ `validate_core.py`
- ✅ `eats_core/cli_orchestrator.py`

---

## 📐 SIZE COMPARISON

### Current State

| File | Lines | Content |
|------|-------|---------|
| `eats_core/core.py` | 731 | Transport (300) + AgentDNA (200) + Evolution (200) + Fitness (30) |
| `eats_core/transport.py` | 591 | Transport + PTYTransport + TmuxTransport + Helpers |

### After Consolidation

| File | Lines | Content |
|------|-------|---------|
| `eats_core/core.py` | ~430 | AgentDNA + Evolution + Fitness (imports Transport) |
| `eats_core/transport.py` | ~650 | Transport + PTYTransport + TmuxTransport + GUI spawning |

**Savings**: ~300 lines of duplicate code removed

---

## ✅ COMPATIBILITY MATRIX

### Can `transport.py` Replace `core.py` Transport?

| Use Case | Status | Notes |
|----------|--------|-------|
| Basic PTY usage | ⚠️ PARTIAL | Need compat wrappers for send/recv |
| Tmux usage | ❌ NO | Missing GUI spawning |
| GhostSwarm | ❌ NO | Needs GUI terminal support |
| CLI Orchestrator | ✅ YES | Already uses transport.py |
| Async agents | ⚠️ PARTIAL | Need compat wrappers |
| Swarm controller | ⚠️ PARTIAL | Need compat wrappers |

**Conclusion**: Need to enhance `transport.py` before it can fully replace `core.py` Transport

---

## 🚧 BLOCKERS AND RISKS

### Blocker 1: API Incompatibility

**Issue**: Different method signatures
- `core.py`: `send(text, newline=True)`, `recv(timeout=0.1)`
- `transport.py`: `send_line(text)`, `send_raw(text)`, `recv_now()`

**Solution**: Add backward compatibility wrappers to `transport.py`

### Blocker 2: Missing GUI Terminal Spawning

**Issue**: GhostSwarm requires GUI terminal spawning (from `core.py` TmuxTransport)

**Solution**: Port `_spawn_gui_window()` from core.py to transport.py

### Risk 1: Import Errors During Migration

**Mitigation**: Update `__init__.py` first, then individual files

### Risk 2: Test Failures

**Mitigation**: Run tests after each file is updated, rollback if needed

---

## 📝 RECOMMENDED IMPLEMENTATION SEQUENCE

### Step 2: Enhance `transport.py` (NEXT)

**Tasks**:
1. Add backward compatibility wrappers (`send()`, `recv()`)
2. Port GUI terminal spawning from `core.py` TmuxTransport
3. Add tests for new features
4. Verify compatibility with existing code

**Estimated Time**: 45 minutes

### Step 3: Refactor `core.py`

**Tasks**:
1. Remove Transport class definitions (lines 45-343)
2. Add import: `from .transport import Transport, PTYTransport, TmuxTransport, BufferOverflowError`
3. Update module docstring
4. Verify core.py focuses only on AgentDNA/Evolution

**Estimated Time**: 30 minutes

### Step 4: Update `__init__.py`

**Tasks**:
1. Change Transport exports from `.core` to `.transport`
2. Keep AgentDNA/Evolution exports from `.core`
3. Test that public API still works

**Estimated Time**: 15 minutes

### Step 5: Update Import Statements

**Tasks**:
1. Update `swarm.py` (line 18)
2. Update `async_core.py` (line 20)
3. Verify no circular dependencies

**Estimated Time**: 15 minutes

### Step 6: Run Tests

**Tasks**:
1. Run test suite: `python run_core.py test`
2. Run demo: `python run_core.py demo`
3. Test CLI orchestrator
4. Test GhostSwarm (visual mode)

**Estimated Time**: 20 minutes

### Step 7: Documentation

**Tasks**:
1. Update file headers
2. Update ARCHITECTURE.md
3. Mark legacy code deprecated

**Estimated Time**: 15 minutes

---

## 📊 METRICS

### Code Duplication

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Transport implementations | 4 | 1 | -75% |
| Total Transport LOC | ~1200 | ~650 | -46% |
| Import confusion points | 3 | 0 | -100% |
| Maintenance burden | High | Low | Significant |

### File Organization

| Metric | Before | After |
|--------|--------|-------|
| core.py lines | 731 | ~430 |
| core.py concerns | 3 (Transport + DNA + Evolution) | 2 (DNA + Evolution) |
| transport.py completeness | 85% | 100% |

---

## 🎯 ACCEPTANCE CRITERIA FOR STEP 1

✅ **COMPLETE** - All import usage documented
✅ **COMPLETE** - API compatibility analyzed
✅ **COMPLETE** - Feature comparison documented
✅ **COMPLETE** - Migration requirements identified
✅ **COMPLETE** - Blockers and risks identified
✅ **COMPLETE** - Implementation sequence planned

**Status**: Step 1 COMPLETE - Ready to proceed with Step 2 (Enhance transport.py)

---

## 📎 APPENDICES

### Appendix A: Full Import List

```bash
# From core.py
eats_core/__init__.py:97:from .core import (Transport, PTYTransport, TmuxTransport, ...)
eats_core/swarm.py:18:from .core import Agent, AgentDNA, Transport, TmuxTransport, PTYTransport
eats_core/async_core.py:20:from .core import Agent, AgentDNA, Transport

# From transport.py
validate_core.py:28:from eats_core.transport import PTYTransport, create_transport
eats_core/cli_orchestrator.py:37:from .transport import Transport, PTYTransport, create_transport

# Legacy
eats/__init__.py:35:from .tmux_transport import TmuxTransport
eats/ghost_swarm.py:46:from .tmux_transport import (...)
eats/agents.py:15:from .transport_pty import PTYTransport
eats/manager.py:15:from .transport_pty import PTYTransport
```

### Appendix B: API Decision

**Chosen Direction**: Keep both APIs
- Primary API: `send_line()`, `send_raw()`, `recv_now()`
- Backward compatibility: `send(newline=True)`, `recv(timeout=0.1)`

**Rationale**:
1. `send_line`/`send_raw` is more explicit and safer
2. Backward compatibility prevents breaking existing code
3. Gradual migration path available

---

**Next Action**: Proceed to Step 2 - Enhance `transport.py` with missing features
