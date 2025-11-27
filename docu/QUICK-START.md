# EATS Quick Start Guide

**Goal**: Run AI coding CLI tools in sequences, parse outputs, chain them, and save everything.

**Core workflow**: CLI tool → Parse output → Send follow-up → Repeat → Save (text files + SQLite)

---

## Installation

```bash
# Clone repository
git clone <repo-url>
cd CLIagentmngr

# No dependencies required for core functionality!
# Optional: Install AI CLI tools
# - claude-code: npm install -g @anthropic-ai/claude-cli
# - gemini: pip install google-generativeai
# - aider: pip install aider-chat
```

---

## 5-Minute Tutorial

### 1. Basic Sequence

```python
from eats_core import CLISequence

# Create sequence (auto-saves to text files + SQLite)
seq = CLISequence("my-first-workflow")

# Add step
seq.add_step("python", "print('Hello EATS!')")

# Run (automatically saved!)
result = seq.run()

# Cleanup
seq.cleanup()

print(f"Done! Saved to: {result['id']}")
```

**What happened:**
- Spawned Python CLI in a pseudo-terminal
- Sent the command
- Captured output
- Saved to `logs/sequences/YYYY-MM-DD/seq-xxxxx/step-1-python.txt`
- Saved to SQLite database

---

### 2. Multi-Step with Chaining

```python
seq = CLISequence("code-review-fix")

# Step 1: Generate code
seq.add_step("claude-code", "Write a REST API for user login")

# Step 2: Review (receives step 1 output)
seq.add_step("gemini", "Review for security issues", use_previous_output=True)

# Step 3: Fix (receives step 2 output)
seq.add_step("aider", "Fix any issues found", use_previous_output=True)

# Run all steps
result = seq.run()
seq.cleanup()

print(f"Completed {result['successful_steps']}/{result['total_steps']} steps")
```

**What happened:**
- Step 1 generates code
- Step 2 receives Step 1's output + your prompt
- Step 3 receives Step 2's output + your prompt
- All saved separately: `step-1-claude-code.txt`, `step-2-gemini.txt`, `step-3-aider.txt`

---

### 3. Query Saved Sequences

```python
from eats_core.cli_persistence import get_persistence

persistence = get_persistence()

# Find all completed sequences
sequences = persistence.query_sequences(status="completed")

for seq in sequences:
    print(f"{seq['id']}: {seq['name']} - {seq['total_steps']} steps")

# Full-text search across ALL outputs
results = persistence.search_outputs("authentication bug")

for result in results:
    print(f"Found in {result['sequence_id']}, step {result['step_number']}")
    print(f"Snippet: {result['snippet']}")

# Statistics
stats = persistence.get_statistics()
print(f"Total sequences: {stats['total_sequences']}")
print(f"Success rate: {stats['success_rate']}%")
```

---

### 4. Inspect Saved Files

Every sequence is saved in two places:

**1. Text Files** (grep-able, human-readable):
```
logs/sequences/
├── 2025-11-26/
│   ├── seq-abc123/
│   │   ├── metadata.json       # Sequence info
│   │   ├── step-1-claude-code.txt  # Full output
│   │   ├── step-2-gemini.txt       # Full output
│   │   └── step-3-aider.txt        # Full output
```

Each `.txt` file contains:
```
# Step 1: claude-code
# Prompt: Write a REST API for user login...
# Duration: 12.34s
# Status: success
# Timestamp: 2025-11-26T10:30:00
#======================================================================

[Full CLI output here - exactly what the tool printed]
```

**2. SQLite Database** (queryable, fast):
```bash
sqlite3 logs/sequences/sequences.db

# Query sequences
SELECT * FROM sequences WHERE status = 'completed';

# Full-text search
SELECT * FROM step_outputs_fts WHERE step_outputs_fts MATCH 'authentication';

# Stats
SELECT tool_name, COUNT(*) FROM steps GROUP BY tool_name;
```

---

## Common Patterns

### Pattern 1: Code Generation → Review → Fix

```python
def code_review_fix(task: str):
    seq = CLISequence("code-review-fix")
    seq.add_step("claude-code", f"Write code for: {task}")
    seq.add_step("gemini", "Review for bugs and security", use_previous_output=True)
    seq.add_step("aider", "Fix issues found", use_previous_output=True)
    return seq.run()

result = code_review_fix("user authentication system")
```

### Pattern 2: Multi-LLM Consensus

```python
def get_consensus(question: str):
    seq = CLISequence("consensus")
    for tool in ["claude-code", "gemini", "ollama"]:
        seq.add_step(tool, question)

    result = seq.run()

    # Compare outputs
    for i, step in enumerate(result['steps'], 1):
        print(f"\n{step['tool_name']} says:")
        print(step['raw_output'][:200])

    return result

result = get_consensus("Best way to implement LRU cache in Python?")
```

### Pattern 3: Iterative Refinement

```python
def refine(task: str, iterations: int = 3):
    seq = CLISequence("refinement")
    seq.add_step("claude-code", f"Initial design: {task}")

    for i in range(1, iterations):
        seq.add_step("claude-code", "Improve and refine this design", use_previous_output=True)

    return seq.run()

result = refine("microservices architecture for e-commerce", iterations=4)
```

### Pattern 4: Test-Driven Development

```python
def tdd_workflow(feature: str):
    seq = CLISequence("tdd-workflow")
    seq.add_step("claude-code", f"Write tests for: {feature}")
    seq.add_step("aider", "Implement code to pass these tests", use_previous_output=True)
    seq.add_step("python", "pytest tests/", use_previous_output=True)
    seq.add_step("aider", "Fix any failing tests", use_previous_output=True)
    return seq.run()

result = tdd_workflow("user registration endpoint")
```

---

## Configuration

### Disable Auto-Save

```python
seq = CLISequence("no-save", auto_save=False)
seq.add_step("python", "print('Not saved')")
result = seq.run()  # Not saved to disk
```

### Custom Timeout

```python
seq.add_step("claude-code", "Complex task", timeout=120.0)  # 2 minutes
```

### Skip Output Parsing

```python
seq.add_step("python", "print('Hello')", parse_output=False)
```

---

## Storage Locations

| What | Where | Format |
|------|-------|--------|
| Sequence text files | `logs/sequences/YYYY-MM-DD/seq-*/` | `.txt` + `.json` |
| SQLite database | `logs/sequences/sequences.db` | SQLite 3 |
| Audit logs | `logs/audit/` | JSON-lines |

---

## Security Features

All sequences are automatically protected:

✅ **Command Allowlist**: Only approved CLI tools can run
```python
# Approved by default: python, claude-code, gemini, aider, git, node, bash
# Blocks: rm, dd, curl (unsafe patterns), etc.
```

✅ **Buffer Overflow Protection**: 10MB per process
```python
# If CLI tool outputs > 10MB, raises BufferOverflowError
```

✅ **Prompt Injection Detection**: Sanitizes chained outputs
```python
# Removes: "SYSTEM: Ignore previous instructions", control tokens, etc.
```

✅ **Audit Logging**: All commands, rejections, and errors logged
```python
# Query with: python -m eats_core.audit_query --severity CRITICAL
```

✅ **Shell Escaping**: All commands properly escaped
```python
# Uses shlex.quote() to prevent injection
```

---

## Advanced Features

### Custom Output Parsing

```python
from eats_core.cli_orchestrator import OutputParser

parser = OutputParser()

# Extract code blocks
code_blocks = parser.extract_code_blocks(output)
for block in code_blocks:
    print(f"Language: {block['language']}")
    print(f"Code: {block['code']}")

# Detect errors
has_errors = parser.has_errors(output)

# Find file paths
file_paths = parser.extract_file_paths(output)

# Parse test results
test_results = parser.parse_test_results(output)
```

### Export/Import Sequences

```python
persistence = get_persistence()

# Export single sequence
persistence.export_sequence("seq-abc123", "backup.json")

# Import
sequence_id = persistence.import_sequence("backup.json")
```

### Load and Replay

```python
# Load previous sequence
sequence = persistence.load_sequence("seq-abc123")

print(f"Name: {sequence['name']}")
print(f"Steps: {sequence['total_steps']}")

for step in sequence['steps']:
    print(f"Step {step['step_number']}: {step['tool_name']}")
    print(f"Output: {step['output'][:100]}...")
```

---

## Troubleshooting

### "Command rejected: tool not in allowlist"

Add your tool to the allowlist in `eats_core/cli_orchestrator.py`:
```python
APPROVED_COMMANDS = {
    "claude-code", "gemini", "aider", "python", "node",
    "your-custom-tool",  # Add here
}
```

### "BufferOverflowError: Buffer exceeded 10MB"

The CLI tool is generating too much output. Options:
1. Increase limit: `PTYTransport(cmd=..., max_buffer_size=50*1024*1024)`
2. Reduce output: Modify tool prompt
3. Process in chunks: Split into multiple steps

### "Transport not started"

Remember to call `.cleanup()` or the transport stays running:
```python
try:
    result = seq.run()
finally:
    seq.cleanup()  # Always cleanup!
```

### Database locked

Close other connections to `sequences.db`:
```python
# Good: Use context manager (auto-closes)
with sqlite3.connect("sequences.db") as conn:
    cursor = conn.cursor()
    # ...

# Bad: Leaves connection open
conn = sqlite3.connect("sequences.db")
```

---

## Examples

Run the included examples:
```bash
# Simple workflow (uses Python - always works)
python examples/simple_workflow.py

# Audit logging demo
python examples/audit_logging_demo.py

# CLI orchestration demo
python examples/cli_orchestration_demo.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ CLISequence                                         │
│  - add_step(tool, prompt, use_previous_output)      │
│  - run() → auto-saves to text files + SQLite        │
└─────────────────────────────────────────────────────┘
                    │
                    ├─→ Transport (PTY or Tmux)
                    │    - spawn CLI process
                    │    - send_and_wait(prompt)
                    │    - recv_now() → output
                    │
                    ├─→ OutputParser
                    │    - extract_code_blocks()
                    │    - sanitize_for_chaining()
                    │
                    └─→ SequencePersistence
                         - save_sequence() → text files + SQLite
                         - query_sequences()
                         - search_outputs()
```

**Core files** (only 3!):
- `eats_core/transport.py` - Run CLI tools
- `eats_core/cli_orchestrator.py` - Sequence and chain
- `eats_core/cli_persistence.py` - Save and query

Total: ~1,800 lines of simple, focused code.

---

## Next Steps

1. **Try the examples**: `python examples/simple_workflow.py`
2. **Install AI tools**: claude-code, gemini, aider
3. **Create your workflow**: Copy a pattern from above
4. **Query your data**: Use `get_persistence()` to analyze
5. **Grep your logs**: `grep -r "error" logs/sequences/`

---

## Learn More

- **Full Plan**: `docu/CODEBASE-SIMPLIFICATION-PLAN.md`
- **Security Audit**: `docu/SECURITY-AUDIT-FINDINGS.md`
- **Architecture**: `docu/mpc-architecture-plan.md` (advanced)

---

**That's it!** You now have:
- ✅ CLI tools running in sequences
- ✅ Output parsing and chaining
- ✅ Everything saved (text files + SQLite)
- ✅ Full-text search
- ✅ Security hardening

Simple. Focused. Reliable.
