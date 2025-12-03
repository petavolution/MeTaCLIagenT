# MetaCLI - Meta-Framework for CLI Agent Orchestration

**A powerful, unified meta-framework for orchestrating AI coding CLI tools with advanced workflow capabilities.**

Transform how you work with AI CLI tools (claude-code, gemini, aider) through a unified API that supports everything from simple sequences to complex workflows with conditionals, loops, and sub-agent delegation.

---

## 🌟 Key Features

- **🎯 Unified API**: One `Workflow` class for all orchestration needs
- **🔄 Advanced Workflows**: Conditionals, loops, sub-agent delegation
- **📄 Declarative YAML/JSON**: Define workflows as configuration
- **🎨 Pattern Library**: Pre-built workflows for common tasks
- **💾 Auto-Persistence**: Files + SQLite with full-text search
- **🔒 Security Hardening**: Command allowlists, sanitization, audit logs
- **0️⃣ Zero Dependencies**: Core requires only Python 3.8+

---

## 🚀 Quick Start

### Simple Workflow
```python
from metacli.core import Workflow

# Create and run a workflow
workflow = Workflow("code-review")
workflow.add_step("generate", "claude-code", "Write a REST API for auth")
workflow.add_step("review", "gemini", "Review for security", use_previous=True)
workflow.add_step("fix", "aider", "Fix issues", use_previous=True)

result = workflow.run()
workflow.cleanup()
```

### From YAML (Declarative)
```python
from metacli.core import Workflow

# Load workflow from YAML file
workflow = Workflow.from_yaml("workflows/audit-refactor.yaml", target="src/")
result = workflow.run()
```

### Using Patterns
```python
from metacli.core import Workflow
from metacli.core.patterns import audit_refactor_cycle

# Use pre-built pattern
pattern = audit_refactor_cycle("src/api.py", max_iterations=3)
workflow = Workflow.from_pattern(pattern)
result = workflow.run()
```

### From Registry
```python
from metacli.core import Workflow

# Load from workflow registry
workflow = Workflow.from_registry("audit-refactor", target="src/")
result = workflow.run()
```

**See:** [Examples](examples/) | [Consolidation Summary](docu/CONSOLIDATION-SUMMARY.md)

---

## 🎯 What Makes MetaCLI Unique

### 🎯 Unified Orchestration API
The `Workflow` class provides **one consistent API** for all orchestration needs:
- Direct instantiation for simple workflows
- YAML/JSON loading for declarative workflows
- Pattern library for common scenarios
- Registry for workflow reusability

### 🔄 Advanced Workflow Engine
- **Conditional Branching**: Execute steps based on output analysis
- **Iterative Loops**: Repeat steps until conditions are met
- **Sub-Agent Delegation**: Route to different tools based on decisions
- **Dynamic Prompts**: Generate prompts from context variables
- **Context Tracking**: Pass data between steps

### 📄 Declarative Workflows
Define workflows as YAML/JSON files:
```yaml
name: audit-refactor-cycle
steps:
  - name: audit
    agent: claude-code
    prompt: "Audit {{target}}"

  - name: refactor
    agent: aider
    prompt: "Fix issues"
    decision: max_iterations
    loop: back_to: verify
```

### 🎨 Pattern Library
Pre-built workflows for common tasks:
- **audit_refactor**: Iterative code auditing and refactoring
- **generate_review_fix**: Generate → Review → Fix cycle
- **tdd**: Test-driven development workflow
- **multi_agent_consensus**: Multiple agents, consensus decision

### 💾 Smart Persistence
- **Text files**: One per step (grep-able, human-readable)
- **SQLite**: Full-text search (FTS5), queryable metadata
- Auto-save with zero configuration
- Export/import for backups

### 🔒 Security First
- Command allowlist (block dangerous tools)
- Prompt injection detection & sanitization
- Buffer overflow protection (10MB limit)
- Comprehensive audit logging
- Shell escaping for all commands

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/petavolution/MeTaCLIagenT.git
cd MeTaCLIagenT

# No dependencies needed for core!
# Optional: For YAML support
pip install pyyaml

# Optional: Install AI CLI tools
# - claude-code: npm install -g @anthropic-ai/claude-cli
# - gemini: pip install google-generativeai
# - aider: pip install aider-chat
```

---

## 📚 Usage Examples

### 1. Simple Workflow
```python
from metacli.core import Workflow

workflow = Workflow("hello-world")
workflow.add_step("test", "python", "print('Hello from MetaCLI!')")
result = workflow.run()
workflow.cleanup()
```

### 2. Multi-Step with Chaining
```python
from metacli.core import Workflow

workflow = Workflow("iterative-refinement")
workflow.add_step("design", "claude-code", "Design microservices architecture")
workflow.add_step("refine", "claude-code", "Refine and improve", use_previous=True)
workflow.add_step("finalize", "claude-code", "Add deployment plan", use_previous=True)
result = workflow.run()
```

### 3. Advanced Workflow with Conditionals
```python
from metacli.core import Workflow, has_errors_decision

workflow = Workflow("test-fix-loop")
workflow.add_step("test", "python", "pytest tests/")
workflow.add_step(
    "fix",
    "aider",
    "Fix failing tests",
    decision=has_errors_decision,
    loop_back_to="test",
    max_iterations=3
)
result = workflow.run()
```

### 4. Declarative YAML Workflow
```yaml
# workflows/audit-refactor.yaml
name: audit-refactor-cycle
context:
  target: "src/"
  max_iterations: 3

steps:
  - name: audit
    agent: claude-code
    prompt: "Audit {{target}} for issues"

  - name: refactor
    agent: aider
    prompt: "Fix issues found"
    decision: max_iterations
    loop_back_to: audit
```

```python
from metacli.core import Workflow

workflow = Workflow.from_yaml("workflows/audit-refactor.yaml", target="src/api.py")
result = workflow.run()
```

### 5. Query Saved Workflows
```python
from metacli.core import get_persistence

persistence = get_persistence()

# Find all completed workflows
workflows = persistence.query(status="completed")

# Full-text search
results = persistence.search("authentication bug")

# Statistics
stats = persistence.stats()
print(f"Total workflows: {stats['total_sequences']}")
print(f"Success rate: {stats['success_rate']}%")
```

**More examples:** [examples/](examples/) directory

---

## 🏗️ Architecture

### Layered Architecture

MetaCLI follows a clean layered architecture:

```
┌─────────────────────────────────────────────────────┐
│ Layer 2: META (Declarative)                        │
│ - WorkflowLoader (YAML/JSON)                       │
│ - WorkflowRegistry (Library)                       │
│ - Patterns (Pre-built)                             │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Layer 1: CORE (Orchestration)                      │
│ - Workflow (UNIFIED API)                           │
│ - OutputParser (parsing)                           │
│ - DecisionEngine (routing)                         │
│ - Persistence (storage)                            │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│ Layer 0: KERNEL (Execution)                        │
│ - Process (execution primitives)                   │
│ - Security (validation)                            │
└─────────────────────────────────────────────────────┘
```

### Core Modules (~4,200 lines)

```
metacli/
├── kernel/
│   ├── process.py        - Process execution primitives
│   └── security.py       - Security validation
│
├── core/
│   ├── workflow.py       - Unified Workflow engine ⭐
│   ├── sequence.py       - Simple sequences (legacy)
│   ├── parser.py         - Output parsing
│   ├── decision.py       - Decision engine
│   ├── patterns.py       - Workflow patterns
│   └── persistence.py    - Storage (files + SQLite)
│
└── meta/
    ├── loader.py         - YAML/JSON loading
    └── registry.py       - Workflow library
```

### Workflow Execution Flow

```
┌──────────────────────────────────────────────────────┐
│ Workflow.from_yaml("audit-refactor.yaml")           │
│   ↓                                                  │
│ WorkflowLoader.from_yaml()                          │
│   ↓                                                  │
│ Workflow (with steps, decisions, context)           │
│   ↓                                                  │
│ workflow.run()                                       │
└──────────────────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌────────┐     ┌──────────┐    ┌──────────┐
│ Step 1 │ ──→ │ Decision │ ──→│ Step 2   │
│ Execute│     │ Evaluate │    │ Execute  │
└────────┘     └──────────┘    └──────────┘
    │                                │
    └────────────────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Persistence  │
              │ - Files      │
              │ - SQLite     │
              └──────────────┘
```

### Storage Layout

```
logs/
├── sequences/
│   ├── 2025-11-26/
│   │   ├── seq-abc123/
│   │   │   ├── metadata.json
│   │   │   ├── step-1-claude-code.txt
│   │   │   ├── step-2-gemini.txt
│   │   │   └── step-3-aider.txt
│   │   └── seq-def456/...
│   └── sequences.db (SQLite)
└── audit/
    └── audit_20251126.jsonl
```

---

## 🔒 Security Features

All sequences are automatically protected:

| Feature | Description |
|---------|-------------|
| **Command Allowlist** | Only approved CLI tools can run (python, claude-code, gemini, aider, etc.) |
| **Buffer Overflow Protection** | 10MB limit per process, raises `BufferOverflowError` if exceeded |
| **Prompt Injection Detection** | Removes control tokens, instruction overrides from chained outputs |
| **Shell Escaping** | All commands properly escaped with `shlex.quote()` |
| **Audit Logging** | All commands, rejections, errors logged to `logs/audit/*.jsonl` |

**See:** [Security Audit Findings](docu/SECURITY-AUDIT-FINDINGS.md)

---

## 🔍 Querying & Analysis

### Python API
```python
from eats_core.cli_persistence import get_persistence

p = get_persistence()

# Filter sequences
recent = p.query_sequences(status="completed", since=time.time()-86400)

# Full-text search (FTS5)
matches = p.search_outputs("authentication", tool="claude-code")

# Statistics
stats = p.get_statistics()
```

### Command Line
```bash
# Query audit logs
python -m eats_core.audit_query --severity CRITICAL --last 24h

# SQLite queries
sqlite3 logs/sequences/sequences.db << EOF
  SELECT tool_name, COUNT(*)
  FROM steps
  GROUP BY tool_name;
EOF

# Grep text files
grep -r "error" logs/sequences/
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docu/QUICK-START.md) | 5-minute tutorial + common patterns |
| [Simplification Plan](docu/CODEBASE-SIMPLIFICATION-PLAN.md) | Architecture analysis & roadmap |
| [Security Audit](docu/SECURITY-AUDIT-FINDINGS.md) | Vulnerability assessment & fixes |
| [MPC Architecture](docu/mpc-architecture-plan.md) | Advanced: Meta-Program-Controller design |

---

## 🎮 Advanced Features (Optional)

The project includes advanced features for power users:

- **Evolution Engine**: Genetic algorithms for agent optimization
- **Swarm Intelligence**: Hierarchical agent trees
- **LLM Judge**: AI-based fitness evaluation
- **GhostSwarm**: Visual multi-terminal tmux mode
- **Conflict Resolution**: Contradiction detection & arbitration
- **Web UI**: FastAPI dashboard (run with `python run_core.py server`)

**See:** [run_core.py](run_core.py) for all modes

---

## 🧪 Testing

```bash
# Run simple workflow examples (uses Python - always works)
python examples/simple_workflow.py

# Run audit logging demo
python examples/audit_logging_demo.py

# Run full test suite
python run_core.py test

# Run evolution demo (advanced)
python run_core.py demo
```

---

## 🗺️ Roadmap

- [x] Core CLI orchestration
- [x] Text file + SQLite persistence
- [x] Security hardening (audit, validation, sanitization)
- [x] Output parsing & chaining
- [x] Full-text search (FTS5)
- [ ] Move advanced features to `eats_advanced/`
- [ ] Replay capability (re-run saved sequences)
- [ ] Streaming outputs (real-time display)
- [ ] Custom tool adapters
- [ ] Integration tests with real AI CLIs

---

## 📊 Project Stats

- **Core code**: ~1,800 lines (3 main files)
- **Total code**: ~20,000 lines (including advanced features)
- **Dependencies**: 0 (core), 3 (web UI), 1 (tmux mode)
- **Language**: Python 3.8+
- **License**: MIT (TODO: Add LICENSE file)

---

## 🤝 Contributing

Contributions welcome! Focus areas:

1. **Core simplification**: Make the basic workflow even simpler
2. **Adapters**: Support for more AI CLI tools
3. **Testing**: Integration tests with real tools
4. **Documentation**: More examples and patterns
5. **Performance**: Optimize persistence layer

---

## 💡 Use Cases

- **Code generation workflows**: Generate → Review → Fix → Test
- **Multi-LLM consensus**: Query multiple LLMs, compare outputs
- **Iterative refinement**: Progressively improve outputs
- **TDD workflows**: Tests → Implementation → Validation
- **Security review**: Generate → Scan → Fix vulnerabilities
- **Documentation**: Code → Analysis → Docs generation

---

## 📝 License

TODO: Add LICENSE file (suggest MIT)

---

## 🙏 Acknowledgments

Built with focus on:
- **Simplicity**: Core functionality in ~1,800 lines
- **Security**: Defense-in-depth hardening
- **Reliability**: Robust error handling & persistence
- **Usability**: Simple API, clear documentation

Inspired by the need for simple, reliable CLI tool orchestration with comprehensive logging and querying capabilities.

---

**Get Started:** [Quick Start Guide](docu/QUICK-START.md) | [Examples](examples/simple_workflow.py)

**Questions?** Check [documentation](docu/) or open an issue.
