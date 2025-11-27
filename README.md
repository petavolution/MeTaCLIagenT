# EATS - CLI Agent Orchestration Framework

**Simple, secure orchestration for AI coding CLI tools.**

Run AI CLI tools (claude-code, gemini, aider) in sequences, parse outputs, chain them with follow-ups, and save everything to text files + SQLite.

---

## 🚀 Quick Start

```python
from eats_core import CLISequence

# Create sequence (auto-saves to text files + SQLite)
seq = CLISequence("code-review-fix")

# Add steps with output chaining
seq.add_step("claude-code", "Write a REST API for user authentication")
seq.add_step("gemini", "Review for security issues", use_previous_output=True)
seq.add_step("aider", "Fix any issues found", use_previous_output=True)

# Run (automatically saved!)
result = seq.run()
seq.cleanup()

print(f"Done! Saved to: logs/sequences/*/{result['id']}/")
```

**What happens:**
1. Spawns each CLI tool in a pseudo-terminal
2. Sends prompts, captures outputs
3. Chains outputs between steps
4. Saves everything to:
   - **Text files**: `logs/sequences/2025-11-26/seq-xxxxx/step-1-claude-code.txt`
   - **SQLite DB**: `logs/sequences/sequences.db` (queryable, full-text search)

**See:** [Quick Start Guide](docu/QUICK-START.md) | [Examples](examples/)

---

## 🎯 Core Features

### ✅ CLI Tool Orchestration
- Run AI coding CLIs: **claude-code**, **gemini**, **aider**, **python**, etc.
- Spawn in pseudo-terminals (PTY) or tmux sessions
- Simple API: `add_step()` → `run()` → auto-saved

### ✅ Output Parsing & Chaining
- Parse code blocks, errors, file paths, test results
- Chain outputs: Step 2 receives Step 1's output
- Prompt injection detection & sanitization

### ✅ Dual-Layer Persistence
- **Text files**: One `.txt` per step (grep-able, diff-able, human-readable)
- **SQLite**: Metadata + full-text search (FTS5)
- Query sequences by status, tool, date
- Export/import for backups

### ✅ Security Hardening
- Command allowlist (blocks dangerous tools)
- Buffer overflow protection (10MB limit)
- Shell escaping (`shlex.quote()`)
- Comprehensive audit logging
- Prompt injection sanitization

### ✅ Zero Dependencies
Core functionality requires **only Python 3.8+** (no external packages!)

---

## 📦 Installation

```bash
# Clone repository
git clone <repo-url>
cd CLIagentmngr

# No dependencies needed for core!
# Optional: Install AI CLI tools
# - claude-code: npm install -g @anthropic-ai/claude-cli
# - gemini: pip install google-generativeai
# - aider: pip install aider-chat
```

---

## 📚 Usage Examples

### Basic Sequence
```python
from eats_core import CLISequence

seq = CLISequence("hello-world")
seq.add_step("python", "print('Hello from EATS!')")
result = seq.run()
seq.cleanup()
```

### Multi-Step with Chaining
```python
seq = CLISequence("iterative-refinement")
seq.add_step("claude-code", "Design a microservices architecture")
seq.add_step("claude-code", "Refine and improve", use_previous_output=True)
seq.add_step("claude-code", "Finalize with deployment plan", use_previous_output=True)
result = seq.run()
```

### Query Saved Sequences
```python
from eats_core.cli_persistence import get_persistence

persistence = get_persistence()

# Find all completed sequences
sequences = persistence.query_sequences(status="completed")

# Full-text search
results = persistence.search_outputs("authentication bug")

# Statistics
stats = persistence.get_statistics()
print(f"Total sequences: {stats['total_sequences']}")
print(f"Success rate: {stats['success_rate']}%")
```

### Inspect Saved Files
```bash
# Text files (one per step)
$ cat logs/sequences/2025-11-26/seq-abc123/step-1-claude-code.txt
# Step 1: claude-code
# Prompt: Write a REST API...
# Duration: 12.34s
# Status: success
#======================================================================
[Full CLI output here]

# SQLite database
$ sqlite3 logs/sequences/sequences.db
sqlite> SELECT * FROM sequences WHERE status = 'completed';
sqlite> SELECT * FROM step_outputs_fts WHERE step_outputs_fts MATCH 'authentication';
```

**More examples:** [examples/simple_workflow.py](examples/simple_workflow.py)

---

## 🏗️ Architecture

### Core Modules (1,800 lines total)

```
eats_core/
├── transport.py          (580 lines) - PTY + Tmux transports
├── cli_orchestrator.py   (678 lines) - Sequencing + parsing
├── cli_persistence.py    (550 lines) - Text files + SQLite
├── audit.py              (532 lines) - Security audit logging
└── audit_query.py        (328 lines) - Query audit logs
```

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│ CLISequence                                         │
│  - add_step(tool, prompt, use_previous_output)      │
│  - run() → auto-saves                               │
└─────────────────────────────────────────────────────┘
                    │
                    ├─→ Transport (PTY/Tmux)
                    │    - spawn CLI process
                    │    - send_and_wait(prompt)
                    │    - recv_now() → output
                    │
                    ├─→ OutputParser
                    │    - extract_code_blocks()
                    │    - sanitize_for_chaining()
                    │
                    └─→ SequencePersistence
                         ├─→ Text files (grep-able)
                         └─→ SQLite (queryable)
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
