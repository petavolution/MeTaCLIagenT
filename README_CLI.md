# EATS - Easy AI Tool Sequencer

**Production-ready CLI for orchestrating AI coding assistants** (Ollama, Claude Code, Codex) in powerful automated workflows.

## ⚡ Quick Start

```bash
# 1. Setup (creates config, creates 'eats' command)
./setup_eats.sh

# 2. List available workflows
eats list workflows

# 3. Run a workflow
eats run code-review --file mycode.py
```

## 🎯 What It Does

EATS lets you combine multiple AI coding assistants in sequences:

```bash
# Example: Code review with two AIs
eats run code-review --file main.py
# → Ollama (fast local review)
# → Claude Code (deep analysis)
# → Results saved to database

# Example: Generate code with refinement
eats run code-generate --input "Create a REST API"
# → Ollama generates code
# → Claude Code reviews and improves
# → Final code returned

# Example: Get 3 AI perspectives (runs in parallel!)
eats run explain-code --file complex.py
# → Ollama + Claude Code + Codex (all at once)
```

## 📦 Pre-built Workflows

| Workflow | Description | Execution |
|----------|-------------|-----------|
| `code-review` | Ollama → Claude Code review | Sequential |
| `code-generate` | Generate → Review → Refine | Sequential |
| `explain-code` | 3 AIs explain simultaneously | **Parallel** |
| `refactor` | Suggest → Apply improvements | Sequential |
| `debug` | Find bugs → Suggest fixes | Sequential |

## 🔧 Supported Tools

**Primary (optimized for):**
- **Ollama** - Local LLM (CodeLlama, DeepSeek, etc.) - Fast & Free
- **Claude Code CLI** - Anthropic's AI assistant - Best quality
- **Codex CLI** - OpenAI's code generator - Creative

**Plus 25+ POSIX tools:**
- Text: grep, awk, sed, jq
- VCS: git
- Build: npm, pip, make
- Test: pytest, jest
- Analysis: pylint, eslint, black

## 🚀 Installation

### Prerequisites

```bash
# Install Ollama (local AI - recommended)
curl https://ollama.ai/install.sh | sh
ollama pull codellama

# Install Claude Code CLI (optional)
pip install anthropic-cli

# Install Codex CLI (optional)
pip install openai-cli
```

### Setup EATS

```bash
# Run setup script
./setup_eats.sh

# Or manually:
python3 eats_cli.py config init
```

### Configure API Keys

```bash
# For Claude Code
eats config set api_keys.anthropic sk-ant-...

# For Codex
eats config set api_keys.openai sk-...

# Or use environment variables
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

## 📖 Usage Examples

### Code Review

```bash
# Review a file
eats run code-review --file src/main.py

# Review with input
eats run code-review --input "def foo(): return bar"
```

### Code Generation

```bash
# Generate code
eats run code-generate --input "Write a function to calculate Fibonacci numbers"

# From file prompt
eats run code-generate --file requirements.txt
```

### Get Explanations (Parallel)

```bash
# 3 AIs explain simultaneously
eats run explain-code --file complex_algorithm.py
```

### Debugging

```bash
# Find and fix bugs
eats run debug --file broken_code.py
```

### Refactoring

```bash
# Improve code quality
eats run refactor --file legacy.py
```

## 🔍 View Results

```bash
# List recent executions
eats status

# View specific execution
eats status seq-19ac1cb662a
```

**All executions saved to:**
- SQLite database: `logs/sequences.db`
- Text files: `logs/sequences/<date>/<id>/`

## 📊 Features

### ✅ Sequential Execution
Steps run one after another, each using previous output:
```
Ollama generates → Claude Code reviews → Final output
```

### ✅ Parallel Execution
Independent steps run simultaneously:
```
Ollama ┐
Claude Code ├─→ All run at once → Combined results
Codex ┘
```

### ✅ Template-Based Automation
Patterns in output trigger follow-up actions:
```
Output contains "vulnerability" → Auto-send "Fix security issues"
Output contains "tests passed" → Auto-exit workflow
```

### ✅ Robust Error Handling
- Automatic retries (exponential backoff)
- Timeout management
- Graceful failure handling

### ✅ Complete Persistence
- Every step saved to database
- Full-text search (FTS5)
- Grep-able text logs

## 🛠️ Configuration

Config file: `~/.eats/config.yaml`

```yaml
api_keys:
  anthropic: sk-ant-...
  openai: sk-...

tools:
  ollama:
    model: codellama  # Or: deepseek-coder, llama2
    host: http://localhost:11434

defaults:
  max_workers: 4      # Parallel execution limit
  timeout: 300        # Per-step timeout (seconds)
  save_to_db: true    # Save all executions
  auto_retry: true    # Retry failed steps
  max_retries: 2      # Retry attempts
```

## 📚 Documentation

- **CLI Guide**: [docs/CLI_GUIDE.md](docs/CLI_GUIDE.md)
- **Framework Demo**: [examples/production_framework_demo.py](examples/production_framework_demo.py)
- **Testing Guide**: [examples/test_framework_demo.py](examples/test_framework_demo.py)

## 🎯 Use Cases

### Local-First Development
```bash
# Quick iteration with Ollama (local, free)
eats run code-generate --input "Create user model"

# Final review with Claude Code (cloud, quality)
eats run code-review --file src/models/user.py
```

### Multi-AI Consensus
```bash
# Get 3 perspectives on complex code
eats run explain-code --file algorithm.py
```

### Automated Pipelines
```bash
# Build → Review → Fix workflow
eats run code-generate --input "REST API"
eats run code-review --file generated.py
eats run refactor --file generated.py
```

## 🧪 Testing

```bash
# Test with mock tools (no external dependencies)
cd examples/
python production_framework_demo.py

# Test parallel execution
python test_framework_demo.py
```

## 🏗️ Architecture

```
eats_cli.py              # Main CLI
├── eats_core/
│   ├── cli_orchestrator.py      # Sequence execution
│   ├── parallel_executor.py     # Parallel/sequential runner
│   ├── template_engine.py       # Pattern-based automation
│   ├── cli_persistence.py       # Database & logging
│   └── presets.py               # Tool registry (29 tools)
├── workflows/                    # Custom workflows
└── logs/                         # All execution data
```

## 🔜 Roadmap

- [ ] Custom workflow builder (interactive)
- [ ] Web UI for monitoring
- [ ] Resume failed workflows
- [ ] More pre-built workflows
- [ ] Real-time progress display
- [ ] Workflow templates library

## 📄 License

MIT

## 🙏 Credits

Built on top of:
- Ollama - Local LLM runtime
- Anthropic Claude - AI assistant
- OpenAI Codex - Code generation

---

**Made for developers who want AI-powered automation without complexity.**

```bash
# Get started in 3 commands:
./setup_eats.sh
eats list workflows
eats run code-review --file mycode.py
```
