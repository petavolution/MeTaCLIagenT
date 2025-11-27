# EATS CLI - User Guide

**EATS** (Easy AI Tool Sequencer) is a command-line tool for orchestrating AI coding assistants and traditional CLI tools in powerful workflows.

## 🎯 Optimized for These Tools

- **Ollama** - Local LLM (CodeLlama, DeepSeek, etc.)
- **Claude Code CLI** - Anthropic's AI coding assistant
- **Codex CLI** - OpenAI's code generation tool

Plus support for 25+ POSIX tools (grep, git, awk, sed, etc.)

---

## 📦 Installation

### 1. Install Prerequisites

```bash
# Install Ollama (for local AI)
curl https://ollama.ai/install.sh | sh
ollama pull codellama

# Install Claude Code CLI (requires Anthropic API key)
pip install anthropic-cli
# or
npm install -g @anthropic-ai/claude-code-cli

# Install Codex CLI (requires OpenAI API key)
pip install openai-cli
```

### 2. Initialize EATS Configuration

```bash
python eats_cli.py config init
```

This creates `~/.eats/config.yaml` with default settings.

### 3. Configure API Keys

```bash
# For Claude Code CLI
python eats_cli.py config set api_keys.anthropic sk-ant-...

# For Codex CLI
python eats_cli.py config set api_keys.openai sk-...
```

Or export environment variables:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

---

## 🚀 Quick Start

### List Available Workflows

```bash
python eats_cli.py list workflows
```

**Output:**
```
code-review     - AI-powered code review with Ollama → Claude Code
code-generate   - Generate code with Ollama, review with Claude Code
explain-code    - Get multiple AI perspectives (parallel execution)
refactor        - Refactor code with AI assistance
debug           - Debug code with AI help
```

### Run a Workflow

#### Code Review
```bash
python eats_cli.py run code-review --file mycode.py
```

**What happens:**
1. Ollama does quick initial review (local, fast)
2. Claude Code does deep security/architecture review
3. Results saved to database and logs

#### Code Generation
```bash
python eats_cli.py run code-generate --input "Create a REST API for user authentication"
```

**What happens:**
1. Ollama generates initial code
2. Claude Code reviews and improves it
3. Final code returned

#### Explain Code (Parallel)
```bash
python eats_cli.py run explain-code --file complex_code.py
```

**What happens:**
1. **Runs in parallel**: Ollama, Claude Code, and Codex all explain the code simultaneously
2. Get 3 different perspectives quickly
3. Compare and synthesize insights

---

## 📋 Commands Reference

### `eats run <workflow>`

Run a pre-built workflow.

**Options:**
- `--input`, `-i`: Provide input text directly
- `--file`, `-f`: Read input from file
- `--config`: Use custom config file

**Examples:**
```bash
# Review code from file
eats run code-review --file src/main.py

# Generate code from prompt
eats run code-generate --input "Write a binary search function"

# Debug with file input
eats run debug --file broken_code.py

# Refactor code
eats run refactor --file legacy.py
```

---

### `eats list [tools|workflows]`

List available tools or workflows.

**Examples:**
```bash
# List workflows
eats list workflows

# List tools
eats list tools
```

---

### `eats config <action>`

Manage configuration.

**Actions:**
- `init` - Create default config file
- `get [key]` - Get config value (or show all)
- `set <key> <value>` - Set config value
- `path` - Show config file path

**Examples:**
```bash
# Initialize config
eats config init

# Set API key
eats config set api_keys.anthropic sk-ant-...

# Get specific value
eats config get defaults.max_workers

# Show all config
eats config get

# Find config file
eats config path
```

---

### `eats status [sequence-id]`

View execution status and history.

**Examples:**
```bash
# Show recent executions
eats status

# Show specific execution
eats status seq-19ac1cb662a
```

**Output:**
```
Sequence: seq-19ac1cb662a
Name: workflow-code-review
Status: completed
Steps: 2/2
Duration: 5.23s
```

---

### `eats interactive`

Interactive workflow builder (coming soon).

---

## 🔧 Configuration

Default config location: `~/.eats/config.yaml`

### Full Configuration Example

```yaml
api_keys:
  anthropic: sk-ant-...  # For Claude Code CLI
  openai: sk-...         # For Codex CLI

tools:
  ollama:
    model: codellama      # Or: deepseek-coder, llama2, etc.
    host: http://localhost:11434

  claude-code:
    enabled: true

  codex:
    enabled: true

defaults:
  max_workers: 4          # Parallel execution limit
  timeout: 300            # Per-step timeout (seconds)
  save_to_db: true        # Save all executions to database
  auto_retry: true        # Retry failed steps
  max_retries: 2          # Retry attempts

paths:
  logs: ./logs
  db: ./logs/sequences.db
  workflows: ./workflows
```

### Configuring Ollama

```bash
# Pull different models
ollama pull codellama
ollama pull deepseek-coder
ollama pull llama2

# Set default model
eats config set tools.ollama.model deepseek-coder

# Set custom host
eats config set tools.ollama.host http://192.168.1.100:11434
```

---

## 📊 Workflows Deep Dive

### `code-review`
**Purpose**: Multi-stage AI code review

**Steps:**
1. **Ollama** (local, fast): Quick initial scan for obvious issues
2. **Claude Code** (cloud, thorough): Deep security and architecture review

**Use when:**
- You want comprehensive code review
- Security is important
- Need both speed and thoroughness

---

### `code-generate`
**Purpose**: Generate and refine code

**Steps:**
1. **Ollama**: Generate initial code quickly
2. **Claude Code**: Review and improve the code

**Use when:**
- Generating new code
- Want AI refinement
- Need production-quality output

---

### `explain-code` (Parallel)
**Purpose**: Get multiple AI perspectives

**Steps** (run in parallel):
1. **Ollama**: Explain code
2. **Claude Code**: Explain code
3. **Codex**: Explain code

**Use when:**
- Code is complex/unclear
- Want multiple viewpoints
- Need comprehensive understanding

**Performance**: ~3x faster than sequential (all run simultaneously)

---

### `refactor`
**Purpose**: Improve code quality

**Steps:**
1. **Claude Code**: Suggest refactoring improvements
2. **Ollama**: Apply refactorings to code

**Use when:**
- Legacy code needs improvement
- Want AI-suggested refactorings
- Improving code quality

---

### `debug`
**Purpose**: Find and fix bugs

**Steps:**
1. **Ollama**: Identify potential bugs
2. **Claude Code**: Suggest specific fixes

**Use when:**
- Code has bugs
- Need debugging assistance
- Want fix suggestions

---

## 💡 Usage Patterns

### Pattern 1: Local-First Development

Use Ollama for fast iteration, Claude Code for final review:

```bash
# Quick local iterations
eats run code-generate --input "Create user model"
# Uses Ollama → Claude Code

# Final review before commit
eats run code-review --file src/models/user.py
# Ollama → Claude Code review
```

### Pattern 2: Parallel Insights

Get multiple perspectives quickly:

```bash
eats run explain-code --file complex_algorithm.py
# Ollama + Claude Code + Codex run in parallel
```

### Pattern 3: Sequential Refinement

Build → Review → Fix pipeline:

```bash
# 1. Generate
eats run code-generate --input "REST API for todos"

# 2. Review (use output file from step 1)
eats run code-review --file generated_code.py

# 3. Apply fixes
eats run refactor --file generated_code.py
```

---

## 🗄️ Database & Logging

### All Executions Are Saved

Every workflow execution is automatically:
- ✅ Saved to SQLite database (`logs/sequences.db`)
- ✅ Logged to text files (`logs/sequences/`)
- ✅ Searchable with full-text search

### View History

```bash
# Recent executions
eats status

# Specific execution
eats status seq-19ac1cb662a
```

### Query Database Directly

```bash
sqlite3 logs/sequences.db

# Find all code reviews
SELECT * FROM sequences WHERE name LIKE '%code-review%';

# Search outputs for "security"
SELECT * FROM sequence_steps_fts WHERE raw_output MATCH 'security';
```

---

## 🐛 Troubleshooting

### Ollama Not Found

```bash
# Check if Ollama is running
ollama list

# Start Ollama server
ollama serve

# Pull model if needed
ollama pull codellama
```

### API Key Errors

```bash
# Verify API keys are set
eats config get api_keys

# Set if missing
eats config set api_keys.anthropic sk-ant-...
eats config set api_keys.openai sk-...
```

### Tool Not Found

```bash
# List available tools
eats list tools

# Check if tool is installed
which claude-code
which ollama
```

### Workflow Fails

```bash
# Check status
eats status <sequence-id>

# Review logs
cat logs/sequences/<date>/<sequence-id>/step-1-*.txt
```

---

## 🔜 Coming Soon

- ✅ Custom workflow creation from CLI
- ✅ Web UI for monitoring
- ✅ Resume failed workflows
- ✅ Workflow templates library
- ✅ Real-time progress display

---

## 📚 Examples

See `examples/` directory for:
- `production_framework_demo.py` - Complete framework demonstration
- `test_framework_demo.py` - Testing framework examples
- `complete_workflow_demo.py` - End-to-end workflows

---

## 🎓 Best Practices

1. **Start with Ollama** - Fast, local, free
2. **Use Claude Code for quality** - Best for production code
3. **Parallel for exploration** - `explain-code` workflow
4. **Sequential for refinement** - Generate → Review → Fix
5. **Check status** - All executions are logged
6. **Configure once** - API keys stored securely

---

## 📞 Support

- Issues: https://github.com/petavolution/CLIagentMngR/issues
- Documentation: `docs/` directory
- Examples: `examples/` directory
