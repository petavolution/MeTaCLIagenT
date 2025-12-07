# MetaCLI Testing Framework

**Simulate, test, and validate CLI workflows without running real tools.**

---

## 🎯 Overview

The MetaCLI Testing Framework provides a comprehensive solution for testing workflows that orchestrate CLI tools (AI coding assistants, POSIX utilities, etc.) without needing to run the actual tools.

### Key Features

- **CLI Simulation**: Mock CLI tools with hash-based response lookup
- **Response Templates**: Pattern-based intelligent routing
- **Test Database**: Store scenarios and execution history
- **Parallel Execution**: Run tests concurrently
- **Terminal Emulation**: Simulate keyboard input for interactive tools
- **YAML Configuration**: Define test scenarios declaratively

---

## 🚀 Quick Start

### Basic Example

```python
from metacli.testing import create_test_simulator, TestScenario, ParallelExecutor

# Create simulator with pre-configured tools
simulator = create_test_simulator(tools=["claude-code", "aider", "python"])

# Define test scenario
scenario = TestScenario(
    name="audit-refactor",
    description="Test audit → refactor workflow",
    steps=[
        {"tool": "claude-code", "prompt": "Audit src/", "expected_output": "Found"},
        {"tool": "aider", "prompt": "Fix issues", "expected_output": "Fixed"},
    ]
)

# Execute
executor = ParallelExecutor(simulator=simulator)
results = executor.run_sequential([scenario])

# Check results
for result in results:
    print(f"{result.workflow_name}: {result.status}")
```

---

## 📦 Components

### 1. CLI Simulator

Mock CLI tools using hash-based response lookup.

#### Features
- **Exact match**: Full prompt → specific response
- **Prefix match**: First 50 chars → similar responses
- **Keyword match**: Contains keyword → tagged response
- **Pattern match**: Regex → matched response

#### Usage

```python
from metacli.testing import CLISimulator

# Create simulator
simulator = CLISimulator()

# Register tool with responses
simulator.register_tool("claude-code", {
    "exact": {
        "Audit code": "Found 3 issues",
    },
    "keywords": {
        "error": "Error detected and logged",
    },
    "patterns": {
        r"fix.*bug": "Bug fixed successfully",
    }
})

# Spawn simulated process
process = simulator.spawn("claude-code")
process.start()

# Interact
process.write("Audit code")
response = process.read()  # "Found 3 issues"
```

#### Hash-Based Lookup

The simulator uses multiple hash strategies for fast matching:

```python
from metacli.testing.simulator import ResponseLookupTable

lookup = ResponseLookupTable()

# Add responses
lookup.add_response("Audit src/api.py", "Found 3 issues", keywords=["audit"])
lookup.add_pattern(r"fix.*error", "Error fixed")

# Lookup (priority: exact → prefix → keyword → pattern)
response = lookup.lookup("Audit src/api.py")  # Exact match
response = lookup.lookup("Audit src/")  # Prefix match
response = lookup.lookup("Please audit the code")  # Keyword match
```

---

### 2. Response Templates

Define patterns for matching outputs and generating follow-up commands.

#### Features
- Multiple match strategies (exact, contains, regex, fuzzy)
- Priority-based template selection
- Context variable substitution
- Template categories

#### Usage

```python
from metacli.testing import ResponseTemplate, TemplateLibrary, ResponseMatcher
from metacli.testing.templates import MatchStrategy

# Create template
template = ResponseTemplate(
    name="syntax_error",
    pattern=r"SyntaxError.*line (\d+)",
    response="Fix syntax error on line {match[1]}",
    strategy=MatchStrategy.REGEX,
    priority=10
)

# Create library
library = TemplateLibrary()
library.add_template(template, category="error_handling")

# Use matcher
matcher = ResponseMatcher(library)
next_command = matcher.match("SyntaxError on line 42", category="error_handling")
# Result: "Fix syntax error on line 42"
```

#### Pre-Built Templates

```python
from metacli.testing.templates import (
    create_coding_templates,
    create_audit_refactor_templates
)

# Coding templates (errors, reviews, tests)
library = create_coding_templates()

# Audit-refactor cycle templates
library = create_audit_refactor_templates()
```

---

### 3. Test Database

Store test scenarios and execution history in SQLite.

#### Features
- Test scenario storage
- Execution history tracking
- Template usage statistics
- Query and search capabilities

#### Usage

```python
from metacli.testing import TestDatabase, TestScenario

# Create database
db = TestDatabase(db_path="tests/test_database.db")

# Save scenario
scenario = TestScenario(
    name="audit-test",
    description="Audit workflow test",
    steps=[
        {"tool": "claude-code", "prompt": "Audit src/", "expected_output": "Found"},
    ],
    tags=["audit"],
    category="integration"
)
scenario_id = db.save_scenario(scenario)

# Load scenario
loaded = db.load_scenario(scenario_id)

# List scenarios
scenarios = db.list_scenarios(category="integration", tags=["audit"])

# Get statistics
stats = db.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
```

#### Schema

```sql
-- Test scenarios
CREATE TABLE test_scenarios (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    steps TEXT NOT NULL,  -- JSON array
    tags TEXT,  -- JSON array
    category TEXT,
    created_at REAL,
    updated_at REAL
);

-- Test executions
CREATE TABLE test_executions (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER NOT NULL,
    started_at REAL NOT NULL,
    duration REAL NOT NULL,
    status TEXT NOT NULL,  -- "passed", "failed", "error"
    steps_executed INTEGER,
    steps_passed INTEGER,
    steps_failed INTEGER,
    step_results TEXT,  -- JSON array
    FOREIGN KEY (scenario_id) REFERENCES test_scenarios(id)
);

-- Template usage statistics
CREATE TABLE template_usage (
    template_name TEXT NOT NULL,
    category TEXT,
    used_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_used REAL
);
```

---

### 4. Parallel Execution

Run multiple test scenarios concurrently.

#### Features
- Sequential execution (one after another)
- Parallel execution (concurrent)
- Thread pool management
- Result aggregation
- Execution statistics

#### Usage

```python
from metacli.testing import ParallelExecutor, TestScenario

# Create scenarios
scenarios = [
    TestScenario(name=f"test-{i}", description="Test", steps=[...])
    for i in range(10)
]

# Create executor
executor = ParallelExecutor(
    simulator=simulator,
    test_database=db,
    max_workers=4
)

# Sequential execution
results = executor.run_sequential(scenarios)

# Parallel execution (faster)
results = executor.run_parallel(scenarios)

# Get summary
for result in results:
    print(f"{result.workflow_name}: {result.status} ({result.duration:.2f}s)")

# Execution statistics
summary = executor.get_summary()
print(f"Success rate: {summary['success_rate']:.1f}%")
print(f"Avg duration: {summary['avg_duration']:.2f}s")
```

---

### 5. Terminal Emulator

Simulate keyboard input for interactive CLI tools.

#### Features
- PTY (pseudo-terminal) support
- Keyboard input simulation
- ANSI escape code handling
- stdin/stdout for simple tools
- Timeout management

#### Usage

```python
from metacli.testing import TerminalEmulator, KeyboardInput

# Create emulator
with TerminalEmulator() as term:
    # Spawn interactive process
    term.spawn(["python", "-i"])

    # Send text (simulates typing)
    term.send_text("print('hello')", press_enter=True)

    # Read output
    output = term.read(timeout=1.0)
    print(output)  # "hello"

    # Send special keys
    term.send_keys([
        KeyboardInput.from_string("2+2"),
        KeyboardInput.enter(),
    ])

    output = term.read(timeout=1.0)
    print(output)  # "4"
```

#### Keyboard Codes

```python
from metacli.testing.terminal import KeyCode

# Special keys
KeyCode.ENTER
KeyCode.TAB
KeyCode.BACKSPACE
KeyCode.ESCAPE
KeyCode.CTRL_C
KeyCode.CTRL_D

# Arrow keys
KeyCode.ARROW_UP
KeyCode.ARROW_DOWN
KeyCode.ARROW_LEFT
KeyCode.ARROW_RIGHT

# Function keys
KeyCode.F1
KeyCode.F2
KeyCode.F3
KeyCode.F4
```

---

## 📋 YAML Configuration

Define test scenarios and templates in YAML files.

### Example: test_scenarios.yaml

```yaml
# Tool response templates
tools:
  claude-code:
    responses:
      exact:
        "Audit src/api.py": "Audit complete. Found 3 issues."
        "Fix issues": "Fixed successfully."

      keywords:
        audit: "Audit complete."
        refactor: "Refactored code."

      patterns:
        ".*error.*": "Error found and fixed."

# Response templates
templates:
  error_handling:
    - name: syntax_error
      pattern: "SyntaxError.*line (\\d+)"
      response: "Fix syntax error on line {match[1]}"
      strategy: regex
      priority: 10

  audit:
    - name: found_issues
      pattern: "Found (\\d+) issue"
      response: "Load context about the {match[1]} issues"
      strategy: regex
      priority: 10

# Test scenarios
scenarios:
  - name: audit-refactor-cycle
    description: Complete audit → refactor → verify cycle
    category: integration
    tags: [audit, refactor]
    steps:
      - tool: claude-code
        prompt: "Audit src/api.py"
        expected_output: "Found 3"
        category: audit

      - tool: aider
        prompt: "Fix issues"
        expected_output: "Fixed"
        category: refactor
```

### Loading from YAML

```python
from metacli.testing import CLISimulator, TemplateLibrary

# Load simulator
simulator = CLISimulator.from_templates("tests/test_scenarios.yaml")

# Load template library
library = TemplateLibrary.from_yaml("tests/test_scenarios.yaml")
```

---

## 🔄 Workflow Integration

Use the testing framework with actual workflows.

### Example: Test Workflow with Simulator

```python
from metacli.core import Workflow
from metacli.testing import create_test_simulator

# Create workflow
workflow = Workflow("code-review")
workflow.add_step("audit", "claude-code", "Audit src/")
workflow.add_step("review", "gemini", "Review findings", use_previous=True)

# Create simulator
simulator = create_test_simulator()

# Run workflow with simulator (no real tools needed!)
result = workflow.run(simulator=simulator)

print(f"Status: {result['status']}")
print(f"Steps: {len(result['steps'])}")
```

### Example: Audit-Refactor Cycle

```python
from metacli.core import Workflow
from metacli.core.patterns import audit_refactor_cycle
from metacli.testing import create_test_simulator, create_audit_refactor_templates

# Create workflow from pattern
pattern = audit_refactor_cycle("src/api.py", max_iterations=3)
workflow = Workflow.from_pattern(pattern)

# Create simulator with realistic responses
simulator = create_test_simulator(tools=["claude-code", "aider"])

# Add custom responses for audit cycle
simulator.register_tool("claude-code", {
    "exact": {
        "Audit src/api.py": "Audit complete. Found 3 issues:\n1. SQL injection\n2. Missing validation\n3. Performance issue"
    }
})

# Run with simulator
result = workflow.run(simulator=simulator)
```

---

## 📊 Use Cases

### 1. Unit Testing Workflows

Test workflow logic without running real CLI tools:

```python
def test_audit_refactor_workflow():
    """Test that audit → refactor workflow executes correctly."""
    simulator = create_test_simulator()
    workflow = Workflow.from_yaml("workflows/audit-refactor.yaml")

    result = workflow.run(simulator=simulator)

    assert result["status"] == "completed"
    assert len(result["steps"]) == 4
    assert result["steps"][0]["tool_name"] == "claude-code"
```

### 2. Integration Testing

Test complete workflows end-to-end:

```python
scenarios = [
    TestScenario(name="audit-cycle", steps=[...]),
    TestScenario(name="refactor-cycle", steps=[...]),
    TestScenario(name="test-cycle", steps=[...]),
]

executor = ParallelExecutor(simulator=simulator, test_database=db)
results = executor.run_parallel(scenarios, max_workers=3)

# All scenarios pass?
assert all(r.status == "success" for r in results)
```

### 3. Performance Testing

Measure workflow execution time:

```python
import time

scenarios = [TestScenario(...) for _ in range(100)]

start = time.time()
results = executor.run_parallel(scenarios, max_workers=8)
duration = time.time() - start

print(f"Executed {len(scenarios)} scenarios in {duration:.2f}s")
print(f"Throughput: {len(scenarios)/duration:.1f} scenarios/sec")
```

### 4. Template Validation

Test that response templates work correctly:

```python
library = create_coding_templates()
matcher = ResponseMatcher(library)

# Test error template
output = "SyntaxError on line 42"
next_cmd = matcher.match(output, category="error_handling")
assert "line 42" in next_cmd

# Test audit template
output = "Found 5 issues"
next_cmd = matcher.match(output, category="audit")
assert "5 issues" in next_cmd
```

---

## 🎓 Best Practices

### 1. Use YAML for Configuration

Define test scenarios in YAML for better maintainability:

```yaml
# tests/scenarios/audit_tests.yaml
scenarios:
  - name: audit-security
    steps:
      - tool: claude-code
        prompt: "Audit for security issues"
        expected_output: "Found"
```

### 2. Use Response Templates

Don't hardcode responses - use templates for flexibility:

```python
# BAD: Hardcoded
if "error" in output:
    next_command = "Fix the error"

# GOOD: Template-based
next_command = matcher.match(output, category="error_handling")
```

### 3. Store Results in Database

Track execution history for analysis:

```python
executor = ParallelExecutor(
    simulator=simulator,
    test_database=db  # Automatically saves results
)
```

### 4. Run Tests in Parallel

Use parallel execution for faster testing:

```python
# Sequential: 10 scenarios × 2s = 20s
results = executor.run_sequential(scenarios)

# Parallel: 10 scenarios / 4 workers × 2s = 5s
results = executor.run_parallel(scenarios, max_workers=4)
```

### 5. Validate Expected Outputs

Always define expected outputs:

```python
scenario = TestScenario(
    name="test",
    steps=[{
        "tool": "claude-code",
        "prompt": "Audit code",
        "expected_output": "Found 3 issues"  # ← Important!
    }]
)
```

---

## 🔧 Advanced Features

### Custom Simulators

Create custom simulators for specific tools:

```python
def create_custom_tool_simulator():
    simulator = CLISimulator()

    simulator.register_tool("my-tool", {
        "exact": {
            "command1": "response1",
            "command2": "response2",
        },
        "patterns": {
            r"analyze\s+(.*)": "Analyzed {match[1]} successfully",
        }
    })

    return simulator
```

### Custom Response Templates

Create domain-specific templates:

```python
template = ResponseTemplate(
    name="deployment_success",
    pattern=r"Deployed version ([\d.]+)",
    response="Verify deployment of version {match[1]}",
    strategy=MatchStrategy.REGEX,
    conditions=[
        lambda output, ctx: "success" in output.lower(),
        lambda output, ctx: ctx.get("environment") == "production"
    ]
)
```

### Fuzzy Matching

Use fuzzy matching for similar prompts:

```python
template = ResponseTemplate(
    name="audit_request",
    pattern="audit the code for issues",
    response="Running comprehensive audit",
    strategy=MatchStrategy.FUZZY  # 80% word overlap
)
```

---

## 📚 Examples

See `examples/05_testing_framework.py` for comprehensive examples:

- Basic CLI simulation
- Response templates
- Test database usage
- Sequential execution
- Parallel execution
- Audit-refactor cycle
- YAML configuration
- Terminal emulation

Run: `python examples/05_testing_framework.py`

---

## 🐛 Troubleshooting

### Issue: "Terminal not spawned"

**Cause**: Trying to use terminal emulator without spawning process

**Fix**:
```python
with TerminalEmulator() as term:
    term.spawn(["python", "-i"])  # Must spawn first
    term.send_text("print('hello')")
```

### Issue: Template not matching

**Cause**: Wrong match strategy or pattern

**Fix**: Check pattern and strategy:
```python
# For exact matches
strategy=MatchStrategy.EXACT

# For substring matches
strategy=MatchStrategy.CONTAINS

# For regex
strategy=MatchStrategy.REGEX
```

### Issue: Parallel tests interfere with each other

**Cause**: Shared state between tests

**Fix**: Create fresh simulator for each scenario:
```python
def workflow_factory(scenario):
    simulator = create_test_simulator()  # Fresh simulator
    workflow = Workflow.from_scenario(scenario)
    return workflow

results = executor.run_parallel(scenarios, workflow_factory=workflow_factory)
```

---

## 🚀 Next Steps

1. **Explore Examples**: Run `python examples/05_testing_framework.py`
2. **Create Test Scenarios**: Define in `tests/test_scenarios.yaml`
3. **Run Tests**: Use `ParallelExecutor` for workflow validation
4. **Analyze Results**: Query test database for insights
5. **Iterate**: Refine templates based on execution patterns

---

## 📖 API Reference

Full API documentation:

- `CLISimulator` - Mock CLI tools
- `ResponseTemplate` - Pattern matching
- `TestDatabase` - Scenario storage
- `ParallelExecutor` - Concurrent execution
- `TerminalEmulator` - Interactive tools

See source code for detailed docstrings.
