# EATS Project Vision - Optimized Edition

## Evolutionary Agent Tree System (Meta-CLI-Agent)

**Version:** 3.0 (Optimized)
**Status:** Production Roadmap
**Last Updated:** 2025-12-08

---

## Executive Summary

EATS is a **practical multi-agent orchestration framework** for terminal-driven LLM coding agents. It enables developers to chain AI coding CLI tools (claude-code, gemini, aider, ollama) in automated workflows with intelligent output parsing, security controls, and comprehensive persistence.

### Project Identity

| Aspect | Description |
|--------|-------------|
| **Full Name** | Evolutionary Agent Tree System (EATS) |
| **Tagline** | Easy AI Tool Sequencer |
| **Core Mission** | Orchestrate multiple AI coding CLIs through unified interface with evolutionary optimization |
| **Primary Users** | Individual developers and small teams on local hardware |
| **Platform** | Linux (Debian-based), terminal-native |

---

## 1. Vision Statement

> **Enable humans to orchestrate multiple LLM-based coding agents through a unified terminal interface, combining practical workflow automation with optional evolutionary optimization, while maintaining human supervision, security, and full auditability.**

### Design Principles

1. **Practical First**: Core functionality works for real-world CLI tool chaining before advanced features
2. **Minimal Dependencies**: Core runs on Python stdlib; optional integrations enhance but don't require
3. **Terminal-Native**: Leverage existing CLI ecosystem (aider, claude-code, gemini, interpreter)
4. **Human-in-the-Loop**: System amplifies human capability; humans supervise and make final decisions
5. **Observable & Secure**: Real-time logging, audit trails, and security controls at every layer

---

## 2. Problem Statement

### Current Pain Points

| Challenge | Impact | EATS Solution |
|-----------|--------|---------------|
| Manual CLI tool switching | Time waste, context loss | Sequential tool chaining with output passing |
| Inconsistent AI outputs | Unreliable results | Multi-LLM consensus, output validation |
| No workflow persistence | Lost work, no audit trail | Text files + SQLite with full-text search |
| Black-box agent behavior | Hard to debug/trust | Terminal visibility, comprehensive logging |
| Security risks | Command injection, resource exhaustion | Allowlists, bounded buffers, policy enforcement |
| Prompt optimization is manual | Suboptimal configurations | Evolutionary algorithm discovers optimal prompts |

### Target Use Cases

1. **CLI Tool Orchestration** (Primary)
   - Chain tools: claude-code -> gemini -> aider
   - Parse outputs, send follow-ups, save everything

2. **Code Review Pipelines**
   - Generate -> Review -> Fix workflows
   - Multi-perspective code analysis

3. **Prompt Engineering** (Advanced)
   - Evolve system prompts automatically
   - Tournament-style agent comparison

4. **Local Model Experimentation**
   - Test different Ollama models on same tasks
   - Compare cloud vs local performance

---

## 3. Architecture Overview

### Layered Design

```
+-----------------------------------------------------------------------+
|                         API/CLI Layer                                   |
|   eats_cli.py | FastAPI Server | Web Dashboard                         |
+-----------------------------------------------------------------------+
|                      Orchestration Layer                                |
|   CLISequence | WorkflowTemplates | ParallelExecutor                   |
+-----------------------------------------------------------------------+
|                        Agent Layer                                      |
|   Transport (PTY/Tmux) | OutputParser | SequenceStep                   |
+-----------------------------------------------------------------------+
|                      Security Layer                                     |
|   CommandValidator | PolicyGatekeeper | AuditLogger                    |
+-----------------------------------------------------------------------+
|                     Persistence Layer                                   |
|   Text Files | SQLite + FTS5 | StateManager                            |
+-----------------------------------------------------------------------+
|                      Provider Layer                                     |
|   OpenAI | Anthropic | Ollama | Mock                                   |
+-----------------------------------------------------------------------+
```

### Core Module Map

| Module | Purpose | Lines | Priority |
|--------|---------|-------|----------|
| `transport.py` | PTY/Tmux process control | ~600 | P0 Core |
| `cli_orchestrator.py` | Tool sequencing, output parsing | ~700 | P0 Core |
| `cli_persistence.py` | Text files + SQLite storage | ~400 | P0 Core |
| `audit.py` | Security logging | ~500 | P0 Core |
| `presets.py` | CLI tool configurations | ~400 | P0 Core |
| `swarm.py` | Hierarchical agent tree | ~600 | P1 Advanced |
| `core.py` | AgentDNA, Evolution | ~700 | P1 Advanced |
| `judge.py` | LLM-as-judge evaluation | ~400 | P1 Advanced |
| `conflict.py` | Contradiction resolution | ~350 | P1 Advanced |

---

## 4. Core Functionality

### 4.1 CLI Tool Orchestration (P0)

The primary use case: chain AI coding CLIs in sequences.

```python
from eats_core import CLISequence

# Create sequence
seq = CLISequence("feature-implementation")

# Add steps
seq.add_step("claude-code", "Write a REST API for user authentication")
seq.add_step("gemini", "Review for security issues", use_previous_output=True)
seq.add_step("aider", "Fix any issues found", use_previous_output=True)

# Execute (auto-saves to text files + SQLite)
result = seq.run()
seq.cleanup()
```

**Supported Tools:**

| Tool | Command | Use Case |
|------|---------|----------|
| `claude-code` | `claude` | Code generation, complex reasoning |
| `gemini` | `gemini chat` | Fast review, multi-perspective |
| `aider` | `aider` | AI pair programming, file editing |
| `ollama` | `ollama run codellama` | Local LLM, free, fast iteration |
| `python` | `python3 -i` | Test execution, REPL |

### 4.2 Output Parsing

Intelligent extraction from CLI outputs:

```python
from eats_core import OutputParser

parser = OutputParser()

# Extract code blocks
blocks = parser.extract_code_blocks(output)  # [{"language": "python", "code": "..."}]

# Detect errors
has_errors = parser.has_errors(output)

# Parse test results
results = parser.parse_test_results(output)  # {"passed": 5, "failed": 2}

# Sanitize for chaining (prevents prompt injection)
safe_output = parser.sanitize_for_chaining(output)
```

### 4.3 Persistence

Dual-layer storage for all executions:

**Text Files** (grep-able, human-readable):
```
logs/sequences/
+-- 2025-12-08/
    +-- seq-abc123/
        +-- metadata.json
        +-- step-1-claude-code.txt
        +-- step-2-gemini.txt
        +-- step-3-aider.txt
```

**SQLite** (queryable, fast):
```sql
SELECT * FROM sequences WHERE status = 'completed';
SELECT * FROM step_outputs_fts WHERE step_outputs_fts MATCH 'authentication';
```

---

## 5. Security Architecture

### Current Implementation

| Control | Status | Description |
|---------|--------|-------------|
| Command Allowlist | Implemented | Only approved CLIs can execute |
| Buffer Limits | Implemented | 10MB max buffer prevents OOM |
| Prompt Sanitization | Implemented | Removes injection patterns |
| Shell Escaping | Implemented | shlex.quote() for all commands |
| Audit Logging | Implemented | All actions logged with timestamps |

### Critical Security Fixes Required

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| C1 | CRITICAL | Command injection via tool config | Strict allowlist validation |
| C2 | CRITICAL | Unbounded buffer growth | Ring buffer for full_log |
| C3 | CRITICAL | Prompt injection in chaining | Sanitize all outputs |
| C6 | HIGH | No hard timeout enforcement | Signal-based timeout |
| C7 | CRITICAL | Tmux send-keys injection | shlex.quote() all args |

### Security Roadmap

1. **Immediate**: Fix C1, C2, C3, C7 (command/prompt injection)
2. **Short-term**: Implement PolicyGatekeeper with capability budgets
3. **Long-term**: Workspace isolation via containers/bwrap

---

## 6. Advanced Features (Optional)

### 6.1 Evolutionary Optimization

Genetic algorithm for agent configuration:

```python
from eats_core import Evolution, EvolutionConfig, AgentDNA, heuristic_fitness

config = EvolutionConfig(population_size=4, generations=3)
base_dna = AgentDNA(role="coder", system_prompt="Write Python code.")

evo = Evolution(config)
best_dna = evo.run(base_dna, heuristic_fitness)
```

**Evolution Cycle:**
1. Initialize population via mutation
2. Evaluate fitness (heuristic or LLM-as-judge)
3. Select top performers
4. Reproduce with mutation
5. Repeat for N generations

### 6.2 Hierarchical Agent Tree

Swarm organization for complex tasks:

```
Meta-Orchestrator (Root)
+-- Research Branch
|   +-- Planner (task decomposition)
|   +-- Searcher (information gathering)
+-- Creative Branch
|   +-- Generator (solution exploration)
|   +-- Critic (quality evaluation)
+-- Execution Branch
    +-- Coder (implementation)
    +-- Tester (test design)
    +-- Reviewer (code review)
```

### 6.3 Result Fusion

Combine outputs from multiple agents:

| Method | Description |
|--------|-------------|
| `VOTE` | Select highest fitness output |
| `SYNTHESIZE` | Weighted combination by fitness |
| `ROLLUP` | Hierarchical consolidation |
| `ARBITRATION` | Meta-agent resolves conflicts |

---

## 7. Implementation Roadmap

### Phase 1: Core Stability (Immediate)

**Goal:** Reliable CLI tool orchestration

- [ ] Fix all CRITICAL security issues (C1, C2, C3, C7)
- [ ] Consolidate transport.py (merge PTY/Tmux implementations)
- [ ] Complete cli_persistence.py (text files + SQLite + FTS)
- [ ] 100% test coverage for core modules
- [ ] Documentation: QUICK-START.md, API reference

**Success Metrics:**
- Basic sequence workflow works 100%
- Zero security regressions
- All outputs persisted automatically

### Phase 2: Production Hardening (Short-term)

**Goal:** Meta-Program-Controller capabilities

- [ ] Implement RobustDriver (expect-style prompt handling)
- [ ] Add PolicyGatekeeper (capability budgets)
- [ ] Create ActionProtocol (structured output format)
- [ ] Implement ConvergenceLoop (retry with feedback)
- [ ] Hard timeout enforcement via signals

**Success Metrics:**
- CLI tools run without manual intervention
- Automatic "Proceed? (y/N)" handling
- Dangerous commands blocked

### Phase 3: Advanced Features (Long-term)

**Goal:** Full evolutionary optimization

- [ ] Declarative runbook format (YAML workflows)
- [ ] Workspace isolation (git worktrees, containers)
- [ ] Visual dashboard enhancements
- [ ] SSH remote transport
- [ ] Vector embeddings for semantic similarity

---

## 8. Simplification Strategy

### Current State

- **~20,000 lines** across 58+ Python files
- High complexity: evolution, swarms, judge, conflict resolution
- Core functionality buried under advanced features

### Target State

- **~3,000 lines** in focused core modules
- Clear separation: `eats_core/` (required) vs `eats_advanced/` (optional)
- Single entry point for basic use

### Module Organization

```
eats_core/           # Required for basic orchestration (~3k lines)
+-- transport.py     # PTY + Tmux transports
+-- cli_orchestrator.py  # Sequence, parse, chain
+-- cli_persistence.py   # Save to files + SQLite
+-- presets.py       # CLI tool configurations
+-- audit.py         # Security logging
+-- logging.py       # Basic logging

eats_advanced/       # Optional advanced features
+-- evolution.py     # Genetic algorithms
+-- swarm.py         # Hierarchical trees
+-- judge.py         # LLM-as-judge
+-- conflict.py      # Contradiction resolution
+-- providers.py     # Direct LLM API access
```

---

## 9. Technical Constraints

### Hardware Profile (Target)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores (parallelism) |
| RAM | 8 GB | 32+ GB (large contexts) |
| Storage | 50 GB | 500+ GB NVMe (model storage) |
| GPU | Optional | RTX 3090+ (local LLMs) |

### Platform Requirements

- **OS:** Linux (Debian/Ubuntu tested)
- **Python:** 3.10+
- **Optional:** tmux (visual debugging), libtmux

### Dependency Philosophy

| Category | Dependencies | Notes |
|----------|--------------|-------|
| Core | None (stdlib only) | Pure Python |
| Server | FastAPI, uvicorn | Optional web interface |
| Terminal | libtmux | Optional visual mode |
| Display | rich | Optional pretty output |
| LLM API | httpx | Optional provider support |

---

## 10. Success Metrics

### Technical

| Metric | Target |
|--------|--------|
| Agent spawn time | < 500ms |
| Step execution overhead | < 100ms |
| Memory per transport | < 50MB |
| Core module test coverage | > 90% |
| Security vulnerabilities | 0 critical |

### User Experience

| Metric | Target |
|--------|--------|
| Time to first workflow | < 5 minutes |
| Documentation clarity | Self-explanatory examples |
| Error message quality | Actionable, clear |

### Reliability

| Metric | Target |
|--------|--------|
| Sequence success rate | > 95% |
| Data persistence | 100% (all outputs saved) |
| Recovery from failures | Auto-retry with backoff |

---

## 11. Key Differentiators

1. **Terminal-Native**: Works with any CLI tool that accepts text input
2. **Zero Lock-in**: Use cloud LLMs, local models, or both
3. **Full Persistence**: Every output saved, searchable, grep-able
4. **Security-First**: Allowlists, sanitization, audit logging
5. **Progressive Enhancement**: Start simple, add complexity as needed
6. **Human Control**: Supervision at all levels, no black boxes

---

## 12. Conclusion

EATS provides a practical framework for orchestrating AI coding CLI tools with optional evolutionary optimization. The key insight is that **most users need reliable tool chaining first**, with advanced features available when needed.

**Priority Order:**
1. Make CLI orchestration bulletproof (security, persistence, reliability)
2. Add production hardening (expect rules, convergence loops)
3. Enable advanced features (evolution, swarms, judge)

The framework is designed for **prosumer hardware**, enabling individual developers to leverage multi-agent AI workflows without cloud dependencies or complex infrastructure.

---

## Quick Reference

### Start a Simple Workflow
```python
from eats_core import CLISequence

seq = CLISequence("my-task")
seq.add_step("claude-code", "Write a sorting function")
seq.add_step("gemini", "Review this code", use_previous_output=True)
result = seq.run()
seq.cleanup()
```

### Query Past Executions
```python
from eats_core.cli_persistence import get_persistence

p = get_persistence()
sequences = p.query_sequences(status="completed")
results = p.search_outputs("authentication")
```

### CLI Usage
```bash
./setup_eats.sh
eats list workflows
eats run code-review --file mycode.py
eats status
```

---

*Document optimized from project documentation audit. Prioritizes practical implementation over aspirational features.*
