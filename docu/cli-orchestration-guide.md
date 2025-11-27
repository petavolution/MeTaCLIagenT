# CLI Orchestration Quick Reference

**Focus**: Chain AI coding CLI tools (claude-code, gemini, aider) in sequences with intelligent output parsing.

---

## Core Concepts

### 1. CLISequence - Chain Tools

```python
from eats_core import CLISequence

# Create sequence
seq = CLISequence("my-workflow")

# Add steps
seq.add_step("claude-code", "Write a Python web scraper")
seq.add_step("gemini", "Review this code", use_previous_output=True)
seq.add_step("aider", "Fix any issues", use_previous_output=True)

# Execute
result = seq.run()

# Cleanup
seq.cleanup()
```

### 2. OutputParser - Extract Structured Data

```python
from eats_core import OutputParser

parser = OutputParser()

# Extract code blocks
code_blocks = parser.extract_code_blocks(output)
# Returns: [{"language": "python", "code": "..."}]

# Detect errors
has_errors = parser.has_errors(output)

# Extract file paths
files = parser.extract_file_paths(output)

# Parse test results
tests = parser.parse_test_results(output)
# Returns: {"passed": 5, "failed": 2}

# Get first code block
code = parser.extract_first_code_block(output, language="python")
```

### 3. WorkflowPatterns - Pre-Built Workflows

```python
from eats_core import WorkflowPatterns

# Code → Review → Fix
seq = WorkflowPatterns.code_review_fix("Create a REST API")

# Multi-LLM Consensus
seq = WorkflowPatterns.multi_llm_consensus("Best sorting algorithm?")

# Iterative Refinement
seq = WorkflowPatterns.iterative_refinement("Design microservices", iterations=4)

# Test-Driven Development
seq = WorkflowPatterns.test_driven_development("User authentication")
```

### 4. Quick Helpers

```python
from eats_core import run_sequence, quick_chain

# Quick sequence from tuples
result = run_sequence([
    ("claude-code", "Write binary search"),
    ("gemini", "Review this", True),  # True = use_previous_output
    ("aider", "Fix issues", True),
])

# Simple chaining
output = quick_chain(
    ["claude-code", "gemini", "aider"],
    "Write a web scraper"
)
```

---

## Common Workflows

### Workflow 1: Generate → Review → Fix

```python
from eats_core import CLISequence

seq = CLISequence("code-review-fix")

# Step 1: Generate code
seq.add_step("claude-code", "Create a FastAPI CRUD application for blog posts")

# Step 2: Review
seq.add_step("gemini", "Review for security, performance, and best practices",
            use_previous_output=True)

# Step 3: Fix
seq.add_step("aider", "Implement the suggested improvements",
            use_previous_output=True)

result = seq.run()

if result['successful_steps'] == 3:
    print("Success! Final code:")
    print(result['final_output'][:500])

seq.cleanup()
```

### Workflow 2: Multi-Tool Comparison

```python
from eats_core import CLISequence, OutputParser

seq = CLISequence("compare-llms")

question = "Implement an LRU cache in Python"

# Query multiple LLMs
for tool in ["claude-code", "gemini", "ollama"]:
    seq.add_step(tool, question)

result = seq.run()

# Compare outputs
parser = OutputParser()
for step in result['steps']:
    if step['success']:
        code = parser.extract_first_code_block(step['parsed_data']['summary'])
        print(f"\n{step['tool']} implementation:")
        print(code[:200] if code else "No code found")

seq.cleanup()
```

### Workflow 3: Iterative Refinement

```python
from eats_core import CLISequence

seq = CLISequence("refine")

# Initial
seq.add_step("claude-code", "Design a distributed caching system")

# Refine 3x
for i in range(3):
    seq.add_step("claude-code",
                f"Improve and refine (iteration {i+2}/4)",
                use_previous_output=True)

result = seq.run()

# Each iteration should be more refined
for i, step in enumerate(result['steps']):
    print(f"Iteration {i+1}: {len(step['parsed_data']['summary'])} chars")

seq.cleanup()
```

### Workflow 4: Parse and Act

```python
from eats_core import CLISequence, OutputParser

seq = CLISequence("parse-and-act")

# Generate code
seq.add_step("claude-code", "Write a Python data validation module")

result = seq.run()

# Parse output
if result['successful_steps'] > 0:
    parser = OutputParser()
    output = result['final_output']

    # Extract code
    code_blocks = parser.extract_code_blocks(output)

    # Check for issues
    if parser.has_errors(output):
        print("Errors detected, sending for review...")
        # Could spawn new sequence here

    # Get mentioned files
    files = parser.extract_file_paths(output)
    print(f"Files: {files}")

seq.cleanup()
```

---

## Advanced Features

### Custom Parsing Logic

```python
from eats_core import CLISequence, OutputParser
import re

class CustomParser(OutputParser):
    """Extend parser for domain-specific patterns."""

    # Add custom pattern
    API_ENDPOINT = re.compile(r'(GET|POST|PUT|DELETE)\s+(/[\w/]+)')

    @classmethod
    def extract_api_endpoints(cls, text):
        """Extract API endpoints from output."""
        return cls.API_ENDPOINT.findall(text)

# Use custom parser
seq = CLISequence("api-workflow")
seq.parser = CustomParser()  # Replace default parser

seq.add_step("claude-code", "Design REST API for user management")
result = seq.run()

# Use custom method
endpoints = CustomParser.extract_api_endpoints(result['final_output'])
print(f"Found {len(endpoints)} endpoints")

seq.cleanup()
```

### Conditional Steps

```python
from eats_core import CLISequence, OutputParser

seq = CLISequence("conditional")

# Generate code
seq.add_step("claude-code", "Write a sorting algorithm")

# Run manually to check output
result_1 = seq.run()

# Check if errors
parser = OutputParser()
if parser.has_errors(result_1['final_output']):
    # Add fix step
    seq.add_step("aider", "Fix the errors", use_previous_output=True)
    result_2 = seq.run()

seq.cleanup()
```

### Timeout and Error Handling

```python
from eats_core import CLISequence

seq = CLISequence("robust")

# Step with custom timeout
seq.add_step("claude-code", "Complex analysis task", timeout=120.0)

result = seq.run()

# Check each step
for step in result['steps']:
    if not step['success']:
        print(f"Step {step['tool']} failed: {step['error']}")
        print(f"Duration: {step['duration']:.1f}s")

seq.cleanup()
```

---

## Output Structure

### Sequence Result

```python
{
    "name": "sequence-name",
    "total_steps": 3,
    "successful_steps": 3,
    "duration": 45.2,
    "steps": [
        {
            "tool": "claude-code",
            "prompt": "Write...",
            "success": True,
            "duration": 15.3,
            "parsed_data": {
                "code_blocks": [...],
                "has_errors": False,
                "file_paths": ["main.py"],
                "test_results": {"passed": 0, "failed": 0},
                "summary": "..."
            },
            "error": None
        },
        # ... more steps
    ],
    "final_output": "..."  # Last successful step's output
}
```

### Parsed Data Structure

```python
{
    "code_blocks": [
        {"language": "python", "code": "def foo():\n    pass"}
    ],
    "has_errors": False,
    "file_paths": ["src/main.py", "tests/test_main.py"],
    "test_results": {"passed": 5, "failed": 0},
    "summary": "Generated code | Modified files: main.py\n\nOutput:\n..."
}
```

---

## CLI Tools Configuration

Tools defined in `eats_core/presets.py`:

| Tool | Command | Description |
|------|---------|-------------|
| claude-code | `claude` | Anthropic's Claude Code CLI |
| gemini | `gemini chat` | Google Gemini CLI |
| aider | `aider` | AI pair programming |
| open-interpreter | `interpreter` | Open Interpreter |
| ollama | `ollama run codellama` | Local LLM |
| python | `python3 -i -q` | Python REPL |
| ipython | `ipython` | Enhanced Python |
| bash | `bash` | Bash shell |

Install as needed:
```bash
# Claude Code
npm install -g @anthropic-ai/claude-cli

# Aider
pip install aider-chat

# Ollama
# Download from https://ollama.ai/download
```

---

## Best Practices

### 1. Always Cleanup

```python
seq = CLISequence("workflow")
try:
    seq.add_step(...)
    result = seq.run()
finally:
    seq.cleanup()  # Always cleanup agents
```

### 2. Use Meaningful Names

```python
# Good
seq = CLISequence("api-generation-review-fix")

# Bad
seq = CLISequence("seq1")
```

### 3. Parse Strategically

```python
# Only parse when needed
seq.add_step("claude-code", "Generate docs", parse_output=False)
seq.add_step("claude-code", "Generate code", parse_output=True)
```

### 4. Set Appropriate Timeouts

```python
# Quick task
seq.add_step("claude-code", "Write hello world", timeout=30.0)

# Complex analysis
seq.add_step("gemini", "Analyze large codebase", timeout=180.0)
```

### 5. Check Success

```python
result = seq.run()

if result['successful_steps'] != result['total_steps']:
    print("Some steps failed!")
    for step in result['steps']:
        if not step['success']:
            print(f"Failed: {step['tool']} - {step['error']}")
```

---

## Integration with EATS

### With SwarmController

```python
from eats_core import CLISequence, SwarmController

# Use sequence within swarm
swarm = SwarmController()
swarm.initialize_tree()

seq = CLISequence("swarm-task")
seq.add_step("claude-code", "Analyze requirements")
result = seq.run()

# Feed to swarm
swarm.broadcast(result['final_output'])

seq.cleanup()
swarm.shutdown()
```

### With ResultPipeline

```python
from eats_core import CLISequence, ResultPipeline, FusionMethod

pipeline = ResultPipeline()

# Run multiple sequences
for tool in ["claude-code", "gemini", "ollama"]:
    seq = CLISequence(f"seq-{tool}")
    seq.add_step(tool, "Best sorting algorithm?")
    result = seq.run()

    # Add to pipeline
    pipeline.add(tool, result['final_output'], fitness=8.0)
    seq.cleanup()

# Fuse results
fused = pipeline.fuse(["claude-code", "gemini", "ollama"],
                     method=FusionMethod.VOTE)
```

---

## Troubleshooting

### Tool Not Found

```python
# Error: Unknown tool: xyz
from eats_core.presets import CLI_TOOLS

# List available tools
print(list(CLI_TOOLS.keys()))
```

### Timeout Issues

```python
# Increase timeout for slow tools
seq.add_step("ollama", "Complex task", timeout=300.0)
```

### Parse Errors

```python
parser = OutputParser()

# Check what was extracted
code_blocks = parser.extract_code_blocks(output)
print(f"Found {len(code_blocks)} code blocks")

# Fallback to raw output
if not code_blocks:
    print("Raw output:", output)
```

---

## Examples Location

See `/examples/cli_orchestration_demo.py` for comprehensive examples.

Run demo:
```bash
python3 examples/cli_orchestration_demo.py
```
