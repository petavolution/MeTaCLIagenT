# FILELIST-MAIN.md

**MetaCLI Master File Index - Comprehensive Evolution Guide**

*Last Updated: 2025-12-07*
*Version: 2.0.0-alpha*
*Status: Post-Consolidation, Testing Framework Added*

---

## 📋 EXECUTIVE SUMMARY

**Total Codebase:** ~44,517 lines across 100+ files
**Active Core:** 4,200 lines (metacli/)
**Testing Framework:** 2,215 lines (NEW)
**Legacy Code:** 21,600 lines (eats_core/ - for future integration)
**Documentation:** 19,186 lines (27 markdown files)

**Architecture:** Clean 3-layer design (Kernel → Core → Meta) + Testing
**Dependencies:** Zero for core, YAML optional, pytest for testing
**Status:** Production-ready core, alpha testing framework, planned Layer 3

---

## 🎯 EVOLUTIONARY ROADMAP

### Current State (v2.0.0-alpha)
```
✅ Layer 0: Kernel (Execution) - COMPLETE
✅ Layer 1: Core (Orchestration) - COMPLETE
✅ Layer 2: Meta (Declarative) - COMPLETE
✅ Testing Framework - ALPHA
⏳ Layer 3: Meta-Meta (Self-Improvement) - PLANNED
⏳ Advanced Features Integration - PLANNED
```

### Future Evolution Path
```
Phase 1 (DONE): Kernel Extraction & Consolidation
Phase 2 (DONE): Core Orchestration & Patterns
Phase 3 (DONE): Meta-Level Declarative Workflows
Phase 4 (DONE): Testing Infrastructure
Phase 5 (NEXT): Layer 3 Meta-Meta Features      ← YOU ARE HERE
Phase 6 (FUTURE): Advanced Features Integration
Phase 7 (FUTURE): Autonomous Orchestration
```

---

## 📂 SECTION I: ACTIVE CORE FRAMEWORK

### Layer 0: KERNEL (Execution Primitives)

**Purpose:** Universal process abstraction with security enforcement
**Status:** ✅ STABLE - Production Ready
**Dependencies:** None (stdlib only)
**Lines:** 817

#### Files

| File | Lines | Purpose | Next Evolution |
|------|-------|---------|----------------|
| `metacli/kernel/__init__.py` | 64 | Kernel exports (Process, PTY, Security) | Add: ProcessPool for parallel execution |
| `metacli/kernel/process.py` | 479 | Universal process abstraction | Add: Streaming output support, checkpointing |
| `metacli/kernel/security.py` | 274 | Command validation & escaping | Add: Runtime monitoring, resource limits |

**Key Features:**
- ✅ PTY spawning for interactive tools (claude-code, aider)
- ✅ Subprocess for simple commands (ls, grep, python)
- ✅ Tmux for debugging and inspection
- ✅ Security allowlist/blocklist
- ✅ Buffer overflow protection (10MB)
- ✅ Timeout enforcement

**Future Enhancements:**
```python
# PLANNED: Process pooling for reuse
pool = ProcessPool(max_processes=4)
process = pool.get_or_create("claude-code")

# PLANNED: Streaming output
for chunk in process.stream_output():
    handle_chunk(chunk)

# PLANNED: Checkpointing
process.save_checkpoint()  # Save state
process.restore_checkpoint()  # Resume
```

---

### Layer 1: CORE (Orchestration Engine)

**Purpose:** Workflow orchestration with conditionals, loops, and patterns
**Status:** ✅ STABLE - Production Ready
**Dependencies:** None (YAML optional for persistence)
**Lines:** 2,691

#### Core Orchestration Files

| File | Lines | Purpose | Status | Next Evolution |
|------|-------|---------|--------|----------------|
| `metacli/core/__init__.py` | 128 | Unified API exports | Stable | Document best practices |
| **`metacli/core/workflow.py`** | 508 | **PRIMARY API** - Unified workflow engine | Stable | Add: Workflow.compile() for optimization |
| `metacli/core/sequence.py` | 391 | Legacy sequential execution | Legacy | Consider deprecation in v3.0 |
| `metacli/core/decision.py` | 339 | Conditional routing & decisions | Stable | Add: Decision combinators (AND/OR/NOT) |
| `metacli/core/parser.py` | 389 | Output parsing & extraction | Stable | Add: Semantic code analysis |
| `metacli/core/patterns.py` | 468 | Pre-built workflow patterns | Stable | Add: Auto-discovered patterns |
| `metacli/core/persistence.py` | 596 | Dual-layer storage (files+SQLite) | Stable | Add: Cloud sync, compression |

**Workflow.py - The Heart of MetaCLI:**
```python
# CURRENT: Multiple construction methods (UNIFIED API)
workflow = Workflow("name")                          # Direct
workflow = Workflow.from_yaml("file.yaml")          # Declarative
workflow = Workflow.from_pattern(pattern)           # Pre-built
workflow = Workflow.from_registry("name")           # Library

# FUTURE: Compilation and optimization
compiled = workflow.compile()  # Optimize execution plan
compiled.run()  # 40% faster (planned)
```

**Evolution Priority: HIGH**
- ✅ **DONE:** Unified API consolidation
- ⏳ **NEXT:** Decision combinators (AND/OR/NOT logic)
- ⏳ **NEXT:** Workflow compilation/optimization
- ⏳ **NEXT:** Performance profiling hooks
- ⏳ **FUTURE:** Self-modification capabilities

---

### Layer 2: META (Declarative Workflows)

**Purpose:** Transform imperative code to declarative configuration
**Status:** ✅ STABLE - Production Ready
**Dependencies:** pyyaml (optional)
**Lines:** 678

#### Meta Layer Files

| File | Lines | Purpose | Status | Next Evolution |
|------|-------|---------|--------|----------------|
| `metacli/meta/__init__.py` | 52 | Meta layer exports | Stable | Add: WorkflowTemplate class |
| `metacli/meta/loader.py` | 347 | YAML/JSON workflow loading | Stable | Add: Schema validation, linting |
| `metacli/meta/registry.py` | 279 | Workflow library management | Stable | Add: Remote registry, versioning |

**Current YAML Support:**
```yaml
# workflows/audit-refactor.yaml
name: audit-refactor-cycle
context:
  target: "{{target}}"
  max_iterations: 3

steps:
  - name: audit
    agent: claude-code
    prompt: "Audit {{target}}"

  - name: refactor
    agent: aider
    prompt: "Fix issues"
    decision: max_iterations
    loop_back_to: audit
```

**Future Enhancements:**
```yaml
# PLANNED: Workflow composition
workflows:
  audit-refactor:
    extends: base-audit
    overrides:
      max_iterations: 5

# PLANNED: Conditional workflows
  - name: deploy
    when:
      - tests_pass
      - approved_by: senior-dev
```

**Evolution Priority: MEDIUM**
- ✅ **DONE:** YAML/JSON loading
- ✅ **DONE:** Context variables
- ⏳ **NEXT:** Schema validation & linting
- ⏳ **NEXT:** Workflow composition (extends, includes)
- ⏳ **FUTURE:** Remote workflow registry

---

## 📂 SECTION II: TESTING FRAMEWORK

### Testing Infrastructure (NEW - Alpha)

**Purpose:** Simulate CLI tools for workflow testing without real execution
**Status:** 🆕 ALPHA - Active Development
**Dependencies:** None (stdlib only)
**Lines:** 2,215

#### Testing Framework Files

| File | Lines | Purpose | Status | Next Evolution |
|------|-------|---------|--------|----------------|
| `metacli/testing/__init__.py` | 56 | Testing exports | Alpha | Add: Quick start helpers |
| **`metacli/testing/simulator.py`** | 367 | CLI tool simulator | Alpha | Add: Semantic response matching |
| `metacli/testing/templates.py` | 491 | Response templates | Alpha | Add: Template learning |
| `metacli/testing/database.py` | 441 | Test scenario storage | Alpha | Add: Result analytics |
| `metacli/testing/terminal.py` | 421 | Terminal emulation | Alpha | Add: VT100 full support |
| `metacli/testing/parallel.py` | 439 | Parallel test execution | Alpha | Add: Distributed testing |

**Hash-Based Response Lookup:**
```python
# CURRENT: Fast O(1) lookup with 5 strategies
lookup = ResponseLookupTable()
lookup.add_response("Audit code", "Found 3 issues")
response = lookup.lookup("Audit code")  # Exact match
response = lookup.lookup("Audit src/")  # Prefix match (first 50 chars)
response = lookup.lookup("Please audit") # Keyword match

# FUTURE: Semantic similarity
response = lookup.semantic_lookup("Review the code")  # Same intent
```

**Evolution Priority: HIGH**
- ✅ **DONE:** Basic CLI simulation
- ✅ **DONE:** Hash-based lookup
- ✅ **DONE:** Parallel execution
- ⏳ **NEXT:** Integration tests with real tools
- ⏳ **NEXT:** Performance benchmarking
- ⏳ **FUTURE:** Semantic similarity matching
- ⏳ **FUTURE:** ML-based response prediction

---

## 📂 SECTION III: EXAMPLES & DOCUMENTATION

### Examples (12 files, 3,900 lines)

**Purpose:** Demonstrate framework capabilities
**Status:** ✅ STABLE - Up to date

#### Core Examples (Production Ready)

| File | Lines | Demonstrates | Status |
|------|-------|--------------|--------|
| `examples/01_kernel_basics.py` | 173 | Process spawning, security | Stable |
| `examples/02_core_sequence.py` | 300 | Sequential workflows | Stable |
| `examples/03_advanced_workflows.py` | 378 | Conditionals, loops, decisions | Stable |
| `examples/04_declarative_workflows.py` | 348 | YAML/JSON, registry | Stable |
| **`examples/05_testing_framework.py`** | 426 | Testing framework usage | NEW |

#### Advanced Examples

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `examples/complete_workflow_demo.py` | 258 | Full workflow example | Stable |
| `examples/production_framework_demo.py` | 452 | Production patterns | Stable |
| `examples/headless_execution_demo.py` | 298 | Background execution | Stable |
| `examples/audit_logging_demo.py` | 191 | Security audit logs | Stable |

**Missing Examples (TODO):**
- [ ] Layer 3 meta-meta features
- [ ] Decision combinators (AND/OR/NOT)
- [ ] Workflow compilation
- [ ] Performance profiling
- [ ] Cloud deployment

---

### Documentation (27 files, 19,186 lines)

**Purpose:** Comprehensive guides, plans, and architecture docs
**Status:** ✅ COMPREHENSIVE - Well maintained

#### Architecture Documents (CRITICAL)

| File | Lines | Purpose | Audience | Status |
|------|-------|---------|----------|--------|
| **`docu/project-vision.md`** | 421 | Overall vision & goals | All | Stable |
| **`docu/CONSOLIDATION-SUMMARY.md`** | 347 | v2.0 consolidation results | Developers | Current |
| **`docu/LAYER-3-META-META-PLAN.md`** | 938 | Layer 3 implementation plan | Developers | Planning |
| **`docu/META-LEVEL-VISION.md`** | 660 | Meta-framework vision | Architects | Planning |
| `docu/mpc-architecture-plan.md` | 984 | Meta-Program-Controller design | Advanced | Future |

#### Implementation Guides (ACTIVE)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| **`docu/TESTING-FRAMEWORK.md`** | 766 | Testing framework guide | NEW ✨ |
| `docu/QUICK-START.md` | 459 | Getting started guide | Stable |
| `docu/cli-orchestration-guide.md` | 505 | Orchestration patterns | Stable |
| `docu/HEADLESS-EXECUTION-ARCHITECTURE.md` | 1,001 | Background execution | Stable |

#### Historical/Reference Documents

| File | Lines | Purpose | Use |
|------|-------|---------|-----|
| `docu/PHASE-1-KERNEL-EXTRACTION-EXECUTE.md` | 895 | Kernel extraction plan | Reference |
| `docu/CONSOLIDATION-PLAN.md` | 385 | Consolidation strategy | Reference |
| `docu/TRANSPORT-CONSOLIDATION-COMPLETE.md` | 335 | Transport consolidation | Reference |

**Documentation Priorities:**
- ✅ **DONE:** Testing framework guide
- ⏳ **NEXT:** Layer 3 implementation guide
- ⏳ **NEXT:** Decision combinator examples
- ⏳ **NEXT:** Production deployment guide
- ⏳ **FUTURE:** Performance tuning guide

---

## 📂 SECTION IV: WORKFLOWS & CONFIGURATION

### Workflow Definitions (7 files, 428 lines YAML)

**Purpose:** Declarative workflow definitions
**Status:** ✅ STABLE - Example workflows

#### Registry Workflows (.metacli/workflows/)

| File | Lines | Purpose | Pattern |
|------|-------|---------|---------|
| `index.json` | 43 | Registry index | Metadata |
| `simple.yaml` | 20 | Simple workflow | Basic |
| `iterative.yaml` | 27 | Iterative refinement | Loop |
| `audit.yaml` | 57 | Audit-refactor cycle | Conditional loop |

#### Template Workflows (workflows/)

| File | Lines | Purpose | Use Case |
|------|-------|---------|----------|
| **`workflows/audit-refactor.yaml`** | 57 | Audit → refactor → verify | Code improvement |
| `workflows/iterative-refinement.yaml` | 27 | Progressive enhancement | Iterative development |
| `workflows/simple-python.yaml` | 20 | Basic Python workflow | Getting started |

**Example: Audit-Refactor Cycle**
```yaml
name: audit-refactor-cycle
description: Iterative code audit and refactoring workflow
context:
  target: "{{target}}"
  max_iterations: 3

steps:
  - name: audit
    agent: claude-code
    prompt: "Audit {{target}} for issues"
    category: audit

  - name: load_context
    agent: claude-code
    prompt: "Load context about issues"
    use_previous: true

  - name: refactor
    agent: aider
    prompt: "Fix issues found"
    decision: max_iterations
    loop_back_to: audit

  - name: verify
    agent: claude-code
    prompt: "Verify changes"

  - name: meta_refactor
    agent: claude-code
    prompt: "Analyze workflow performance"
```

**Future Workflow Features:**
```yaml
# PLANNED: Workflow composition
workflows:
  - name: advanced-audit
    extends: audit-refactor
    includes:
      - security-scan
      - performance-test

# PLANNED: Parallel steps
  - name: parallel-review
    parallel:
      - step: security-review
      - step: code-review
      - step: performance-review
```

---

## 📂 SECTION V: TEST INFRASTRUCTURE

### Test Files (4 files, 1,800 lines)

**Purpose:** Automated testing and validation
**Status:** ⚠️ NEEDS EXPANSION

#### Current Tests

| File | Lines | Coverage | Status |
|------|-------|----------|--------|
| `tests/test_core.py` | 675 | Core functionality | Stable |
| `tests/test_framework.py` | 484 | Testing framework | Alpha |
| `tests/test_prompts.py` | 444 | Prompt patterns | Active |
| `tests/test_scenarios.yaml` | 200 | YAML test cases | Active |

**Missing Tests (CRITICAL):**
- [ ] Integration tests with real CLI tools
- [ ] Performance benchmarks
- [ ] Stress tests (1000+ concurrent workflows)
- [ ] Security validation tests
- [ ] Edge case coverage

**Next Actions:**
```python
# TODO: Add integration tests
@pytest.mark.integration
def test_with_real_claude_code():
    """Test with actual claude-code CLI."""
    workflow = Workflow("real-audit")
    result = workflow.run()  # Real execution
    assert result["status"] == "completed"

# TODO: Add performance tests
@pytest.mark.benchmark
def test_parallel_performance():
    """Benchmark parallel execution."""
    scenarios = [TestScenario(...) for _ in range(100)]
    start = time.time()
    executor.run_parallel(scenarios, max_workers=8)
    duration = time.time() - start
    assert duration < 10.0  # Should complete in 10s
```

---

## 📂 SECTION VI: LEGACY CODE (For Future Integration)

### EATS Core (eats_core/ - 21,600 lines)

**Purpose:** Original implementation with advanced features
**Status:** 🔄 DEPRECATED but contains valuable features for integration

#### High-Value Modules for Migration

| Module | Lines | Feature | Priority | Integration Status |
|--------|-------|---------|----------|-------------------|
| **`swarm.py`** | 683 | Swarm intelligence | HIGH | Not started |
| **`judge.py`** | 601 | LLM-based quality judgment | HIGH | Not started |
| **`evolution_engine.py`** | 562 | Genetic algorithm optimization | MEDIUM | Not started |
| `parallel_executor.py` | 425 | Advanced parallel execution | MEDIUM | Partially done |
| `metrics.py` | 460 | Performance metrics | MEDIUM | Not started |
| `events.py` | 443 | Event system | MEDIUM | Not started |
| `pipeline.py` | 526 | Pipeline abstraction | LOW | Not started |
| `project_context.py` | 562 | Project context management | LOW | Not started |
| `server.py` | 691 | FastAPI web server | LOW | Future |
| `visual_swarm.py` | 650 | Visual swarm UI | LOW | Future |

**Migration Roadmap:**

**Phase 1 (Next 2-4 weeks):**
- [ ] Extract swarm intelligence → Layer 3
- [ ] Migrate LLM judge → decision.py enhancement
- [ ] Port metrics system → persistence.py

**Phase 2 (1-2 months):**
- [ ] Integrate evolution engine → workflow optimization
- [ ] Add event system → workflow lifecycle hooks
- [ ] Enhance parallel execution → workflow.py

**Phase 3 (Future):**
- [ ] Web server → modern dashboard
- [ ] Visual swarm → workflow visualization

---

## 📂 SECTION VII: STORAGE & RUNTIME

### Logs Directory (logs/)

**Purpose:** Persistent storage for workflow executions
**Status:** ✅ AUTO-CREATED - Works well

**Structure:**
```
logs/
├── sequences/
│   ├── 2025-12-07/              # Date-based organization
│   │   ├── seq-abc123/          # Individual workflow execution
│   │   │   ├── metadata.json    # Workflow metadata
│   │   │   ├── step-1-claude-code.txt
│   │   │   ├── step-2-aider.txt
│   │   │   └── ...
│   └── sequences.db             # SQLite with FTS5 search
└── audit/
    └── audit_20251207.jsonl     # Security audit logs
```

**Features:**
- ✅ Date-based organization
- ✅ One text file per step (grep-able)
- ✅ SQLite for structured queries
- ✅ Full-text search (FTS5)
- ✅ Auto-cleanup (configurable retention)

**Future Enhancements:**
- [ ] Compression for old logs
- [ ] Cloud sync (S3, GCS)
- [ ] Log rotation policies
- [ ] Export to different formats (Parquet, CSV)

---

## 📂 SECTION VIII: ROOT-LEVEL FILES

### Entry Points & Utilities

| File | Lines | Purpose | Status | Usage |
|------|-------|---------|--------|-------|
| `eats_cli.py` | 566 | Main CLI application | Active | Primary interface |
| `run_core.py` | 187 | Multi-mode runner | Active | Testing, demo, server |
| `run_tests.py` | 24 | Test runner | Active | `python run_tests.py` |
| `validate_core.py` | 402 | Installation validator | Active | Post-install check |
| `example_meta_framework.py` | 260 | Advanced example | Active | Reference implementation |

### Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `requirements.txt` | Python dependencies | Stable |
| `.gitignore` | Git ignore patterns | Stable |
| `README.md` | Project overview | Needs update |

**README.md Status:** ⚠️ OUTDATED
- Current version shows old EATS branding
- Needs update to reflect MetaCLI v2.0
- Should showcase new unified API
- Priority: HIGH

---

## 🎯 SECTION IX: EVOLUTION GUIDANCE

### Immediate Priorities (Next 2 Weeks)

#### 1. Complete Testing Framework (Priority: CRITICAL)
**Status:** Alpha → Stable

**Tasks:**
- [ ] Add integration tests with real tools
- [ ] Performance benchmarks (100+ concurrent workflows)
- [ ] Stress testing (find breaking points)
- [ ] Documentation examples

**Files to Update:**
- `tests/test_integration.py` (NEW)
- `tests/test_performance.py` (NEW)
- `docu/TESTING-FRAMEWORK.md` (UPDATE)

---

#### 2. Implement Decision Combinators (Priority: HIGH)
**Status:** Planned → Implementation

**Why:** Enable complex decision logic (AND/OR/NOT)

**Implementation:**
```python
# NEW FILE: metacli/core/decision_combinators.py
class DecisionCombinator:
    @staticmethod
    def AND(*decisions):
        """All must pass."""

    @staticmethod
    def OR(*decisions):
        """At least one must pass."""

    @staticmethod
    def NOT(decision):
        """Invert decision."""

# Usage:
workflow.add_step(
    decision=AND(
        test_pass_decision,
        NOT(has_errors_decision),
        max_iterations_decision(3)
    )
)
```

**Files to Create:**
- `metacli/core/decision_combinators.py` (~200 lines)
- `examples/06_decision_combinators.py` (~150 lines)
- `tests/test_decision_combinators.py` (~100 lines)

**Estimated Effort:** 2 days

---

#### 3. Update README.md (Priority: HIGH)
**Status:** Outdated → Current

**Tasks:**
- [ ] Update branding (EATS → MetaCLI)
- [ ] Showcase unified Workflow API
- [ ] Add quick start with new examples
- [ ] Update architecture diagram
- [ ] Add badges (tests, coverage, version)

**Template:**
```markdown
# MetaCLI - Meta-Framework for CLI Agent Orchestration

**Unified API for orchestrating AI coding tools and POSIX utilities**

## Quick Start

\`\`\`python
from metacli.core import Workflow

# Create workflow
workflow = Workflow("code-review")
workflow.add_step("audit", "claude-code", "Audit src/")
workflow.add_step("fix", "aider", "Fix issues", use_previous=True)

# Run
result = workflow.run()
\`\`\`

## Features

- ✅ Unified API (one way to do orchestration)
- ✅ Conditional branching & loops
- ✅ Declarative YAML workflows
- ✅ Built-in patterns (audit-refactor, TDD, etc.)
- ✅ Comprehensive testing framework
- ✅ Zero dependencies (core)
```

**Estimated Effort:** 1 day

---

### Medium-Term Goals (1-2 Months)

#### 4. Layer 3: Meta-Meta Features (Priority: MEDIUM)
**Status:** Planned → Design → Implementation

**Reference:** `docu/LAYER-3-META-META-PLAN.md`

**Phase 1: Workflow Introspection**
- [ ] ExecutionTracer for performance analysis
- [ ] WorkflowOptimizer for bottleneck detection
- [ ] Visualization (Mermaid diagrams)

**Files to Create:**
- `metacli/meta/tracer.py` (~300 lines)
- `metacli/meta/optimizer.py` (~400 lines)
- `metacli/meta/visualizer.py` (~200 lines)

**Phase 2: Pattern Mining**
- [ ] Discover patterns from execution history
- [ ] Auto-suggest workflows
- [ ] Template extraction

**Files to Create:**
- `metacli/meta/pattern_miner.py` (~500 lines)

**Estimated Effort:** 3-4 weeks

---

#### 5. Migrate High-Value Features from eats_core (Priority: MEDIUM)

**Swarm Intelligence:**
```python
# MIGRATION TARGET: eats_core/swarm.py → metacli/advanced/swarm.py
# Feature: Multi-agent swarm orchestration
# Lines: 683
# Dependencies: None (refactor to use metacli.core.Workflow)

# Future usage:
from metacli.advanced import SwarmOrchestrator

swarm = SwarmOrchestrator(agents=["claude-code", "gemini", "aider"])
swarm.consensus_decision("Refactor src/api.py")
```

**LLM Judge:**
```python
# MIGRATION TARGET: eats_core/judge.py → metacli/core/decision.py
# Feature: LLM-based output quality judgment
# Lines: 601
# Integration: Extend DecisionEngine

# Future usage:
workflow.add_step(
    decision=llm_judge_decision(
        criteria=["correctness", "security", "performance"]
    )
)
```

**Files to Migrate:**
- `metacli/advanced/swarm.py` (from eats_core/swarm.py)
- Enhance `metacli/core/decision.py` (add LLM judge)
- `metacli/metrics/` (new module from eats_core/metrics.py)

**Estimated Effort:** 4-6 weeks

---

### Long-Term Vision (3-6 Months)

#### 6. Autonomous Orchestration (Priority: FUTURE)

**Goal:** Workflows that optimize themselves

**Features:**
- Self-modifying workflows
- Evolutionary optimization
- Goal-directed synthesis
- Learning from history

**Reference:** `docu/META-LEVEL-VISION.md` (Levels 2-4)

---

#### 7. Production Deployment Features (Priority: FUTURE)

**Features:**
- Cloud deployment (AWS, GCP, Azure)
- Distributed execution
- Web dashboard
- API server
- Monitoring & alerting

**Migration from:**
- `eats_core/server.py` → Modern FastAPI server
- `eats_core/visual_swarm.py` → React dashboard

---

## 🔧 SECTION X: MAINTENANCE GUIDELINES

### Code Quality Standards

**All new code must:**
1. ✅ Have comprehensive docstrings
2. ✅ Include type hints
3. ✅ Pass pylint/flake8
4. ✅ Have 80%+ test coverage
5. ✅ Include examples in docstring
6. ✅ Update this file list

**Example:**
```python
def my_function(arg1: str, arg2: int) -> Dict[str, Any]:
    """
    Brief description.

    Args:
        arg1: Description
        arg2: Description

    Returns:
        Dictionary with results

    Example:
        >>> result = my_function("test", 42)
        >>> print(result["status"])
        "success"
    """
    pass
```

---

### Documentation Standards

**All new features must include:**
1. ✅ Docstring in code
2. ✅ Example in `examples/`
3. ✅ Test in `tests/`
4. ✅ Entry in this file list
5. ✅ Update to relevant `docu/*.md`

---

### Deprecation Policy

**Before deprecating:**
1. Mark as `@deprecated` with version
2. Add warning in docstring
3. Provide migration path
4. Keep for 2 major versions
5. Document in `CHANGELOG.md`

**Example:**
```python
@deprecated("2.0.0", "Use Workflow.from_yaml() instead")
def load_workflow_from_yaml(path: str):
    """
    DEPRECATED: Use Workflow.from_yaml() instead.

    Will be removed in v3.0.0.

    Migration:
        OLD: load_workflow_from_yaml("file.yaml")
        NEW: Workflow.from_yaml("file.yaml")
    """
    return Workflow.from_yaml(path)
```

---

## 📊 SECTION XI: METRICS & HEALTH

### Current Codebase Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Core Lines** | 4,200 | < 5,000 | ✅ Good |
| **Test Coverage** | ~60% | > 80% | ⚠️ Needs improvement |
| **Documentation** | 19,186 lines | Comprehensive | ✅ Excellent |
| **Code Duplication** | 0% | < 5% | ✅ Excellent |
| **Complexity** | Low | Low | ✅ Good |
| **Dependencies (core)** | 0 | 0 | ✅ Perfect |
| **Dependencies (full)** | 6 | < 10 | ✅ Good |

### Technical Debt

**Low Priority:**
- [ ] Remove duplicate archived code (eats_deprecated, eats_BACKUP)
- [ ] Consolidate overlapping examples
- [ ] Improve test coverage to 80%+

**Medium Priority:**
- [ ] CLISequence deprecation path
- [ ] Update all examples to use unified API
- [ ] Migrate remaining eats_core utilities

**High Priority:**
- [ ] None currently

---

## 🎓 SECTION XII: LEARNING PATH

### For New Developers

**Day 1: Understand Architecture**
1. Read `README.md` (to be updated)
2. Read `docu/project-vision.md`
3. Read `docu/CONSOLIDATION-SUMMARY.md`
4. Run `examples/01_kernel_basics.py`

**Day 2: Core Concepts**
1. Read `docu/QUICK-START.md`
2. Read `metacli/core/workflow.py` docstrings
3. Run `examples/02_core_sequence.py`
4. Run `examples/03_advanced_workflows.py`

**Day 3: Advanced Features**
1. Read `docu/TESTING-FRAMEWORK.md`
2. Run `examples/05_testing_framework.py`
3. Explore `workflows/*.yaml` files

**Week 1: First Contribution**
1. Pick a TODO from this file
2. Write tests first
3. Implement feature
4. Add example
5. Update documentation
6. Submit PR

---

### For Advanced Development

**Layer 3 Implementation:**
1. Read `docu/LAYER-3-META-META-PLAN.md`
2. Study `metacli/core/decision.py`
3. Review `metacli/meta/` modules
4. Implement decision combinators (good first task)

**Feature Migration:**
1. Study `eats_core/swarm.py`
2. Design integration with `metacli.core.Workflow`
3. Write migration plan
4. Implement incrementally
5. Test thoroughly

---

## 🚀 SECTION XIII: QUICK REFERENCE

### Most Important Files

**For Understanding the Framework:**
1. `metacli/core/workflow.py` - Heart of the system
2. `docu/CONSOLIDATION-SUMMARY.md` - What we built
3. `examples/03_advanced_workflows.py` - Advanced usage

**For Contributing:**
1. This file (`docu/fileLIST-MAIN.md`)
2. `docu/LAYER-3-META-META-PLAN.md` - Next features
3. `tests/test_core.py` - Test patterns

**For Deployment:**
1. `docu/QUICK-START.md`
2. `requirements.txt`
3. `validate_core.py`

---

### Command Cheat Sheet

```bash
# Run all examples
python examples/01_kernel_basics.py
python examples/02_core_sequence.py
python examples/03_advanced_workflows.py
python examples/04_declarative_workflows.py
python examples/05_testing_framework.py

# Run tests
python run_tests.py
pytest tests/

# Validate installation
python validate_core.py

# Run with specific tool
python eats_cli.py --tool claude-code "Audit code"

# Load workflow from YAML
python -c "from metacli.core import Workflow; \
  w = Workflow.from_yaml('workflows/audit-refactor.yaml'); \
  w.run()"
```

---

## ✅ SECTION XIV: NEXT ACTIONS CHECKLIST

### This Week
- [ ] Update README.md (1 day)
- [ ] Add integration tests (2 days)
- [ ] Implement decision combinators (2 days)

### Next Week
- [ ] Add performance benchmarks (1 day)
- [ ] Update all examples to unified API (2 days)
- [ ] Write Layer 3 implementation guide (2 days)

### This Month
- [ ] Implement ExecutionTracer (1 week)
- [ ] Implement WorkflowOptimizer (1 week)
- [ ] Start swarm intelligence migration (2 weeks)

### This Quarter
- [ ] Complete Layer 3 Phase 1 (1 month)
- [ ] Migrate LLM judge (2 weeks)
- [ ] Add metrics system (2 weeks)
- [ ] Launch v2.1.0 with Layer 3 features (Q1 2026)

---

## 📝 SECTION XV: VERSION HISTORY

### v2.0.0-alpha (Current)
- ✅ Kernel extraction complete
- ✅ Core consolidation complete
- ✅ Unified Workflow API
- ✅ Testing framework alpha
- ✅ 0% code duplication
- ✅ Comprehensive documentation

### v2.1.0 (Planned - Q1 2026)
- Decision combinators
- Workflow introspection
- Performance optimization
- Integration tests

### v2.2.0 (Planned - Q2 2026)
- Pattern mining
- Swarm intelligence
- LLM judge integration

### v3.0.0 (Planned - Q3 2026)
- Autonomous orchestration
- Self-modifying workflows
- CLISequence removal (breaking change)

---

## 🎯 CONCLUSION

**Current State:** Solid foundation with clean architecture
**Next Steps:** Decision combinators → Layer 3 → Advanced features
**Long-term Vision:** Autonomous, self-optimizing meta-framework

**Key Strengths:**
- ✅ Clean layered architecture
- ✅ Zero dependencies (core)
- ✅ Unified API
- ✅ Comprehensive testing framework
- ✅ Excellent documentation

**Areas for Improvement:**
- ⚠️ Test coverage (60% → 80%)
- ⚠️ README outdated
- ⚠️ Legacy code cleanup
- ⚠️ Production deployment guides

**The Path Forward:**
```
Week 1:  Decision combinators + README update
Week 2:  Integration tests + Layer 3 design
Month 1: ExecutionTracer + WorkflowOptimizer
Month 2: Pattern mining + Swarm migration
Month 3: v2.1.0 release
```

---

**Maintained by:** MetaCLI Development Team
**Last Updated:** 2025-12-07
**Next Review:** 2026-01-07
**Contact:** See project repository

---

*This file is the single source of truth for MetaCLI project structure and evolution.*
*All new features, files, and changes must be documented here.*
