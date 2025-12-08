# Meta-Orchestration Enhancement Plan

## Hyperspace-Optimal Code Evolution Strategy

**Version:** 1.0
**Status:** Strategic Roadmap
**Date:** 2025-12-08

---

## Executive Summary

This document outlines the evolution of EATS from a linear CLI sequencer into a **full meta-orchestration framework** supporting:

- **Conditional workflows** with branching logic
- **Iterative patterns** with convergence detection
- **Hierarchical orchestration** with sub-agent delegation
- **Pattern-driven response selection** via hash lookup tables
- **Robust PTY/terminal control** for any text-based CLI
- **Complete persistence** with SQLite + FTS5

---

## 1. Current State Analysis

### What Exists

| Component | File | Status | Capability |
|-----------|------|--------|------------|
| Mock CLI | `tools/mock_ai_cli.py` | Basic | Random base64+hex output, interactive mode |
| Parallel Executor | `eats_core/parallel_executor.py` | Good | Thread pool, dependency graph, retries |
| Template Engine | `eats_core/template_engine.py` | Good | Pattern-action rules, callbacks |
| Test Framework | `tests/test_framework.py` | Good | Intelligent tests with pattern matching |
| Test Prompts | `tests/test_prompts.py` | Good | Hash lookup table, follow-up prompts |
| CLI Orchestrator | `eats_core/cli_orchestrator.py` | Good | Sequences, output parsing, security |
| Transport | `eats_core/transport.py` | Good | PTY, Tmux, bounded buffers |
| Persistence | `eats_core/cli_persistence.py` | Good | SQLite + text files + FTS5 |
| Workflows | `eats_core/workflow_templates.py` | Basic | Linear sequences only |

### Gaps to Fill

1. **Mock CLI lacks keywords** - Need `identified`, `error`, `complete`, `refactor`, `optimize`
2. **No conditional branching** - All workflows are linear sequences
3. **No iteration/loops** - Can't repeat until convergence
4. **No sub-agent delegation** - No hierarchical task decomposition
5. **Limited pattern-response** - Hash table exists but not integrated with orchestrator
6. **No expect-style control** - PTY doesn't handle prompts like "Continue? (y/N)"

---

## 2. Enhanced Mock CLI Design

### Output Format

The mock CLI should output two parts as specified:

```
Part 1: Base64-encoded 128-char random string (simulates text output)
Part 2: 256-char hex sequence (simulates hash/binary data)
```

### Keyword Injection

Randomly inject detection keywords that the controller looks for:

```python
DETECTION_KEYWORDS = [
    # Status indicators
    'identified', 'complete', 'error', 'warning', 'success', 'failed',
    # Action triggers
    'refactor', 'optimize', 'review', 'test', 'fix', 'implement',
    # Workflow signals
    'continue', 'abort', 'retry', 'pause', 'checkpoint',
    # Quality markers
    'vulnerability', 'performance', 'security', 'deprecated',
]
```

### Mock CLI Architecture

```python
class MockAICLI:
    """
    Enhanced mock CLI for testing orchestration.

    Output format (always 2 parts):
    1. Base64 encoded random 128-char string
    2. 256-char random hex string

    With randomly injected keywords for pattern detection.
    """

    def generate_response(self, mode: str) -> str:
        # Part 1: Base64 text
        random_bytes = secrets.token_bytes(96)
        part1 = base64.b64encode(random_bytes).decode('ascii')

        # Part 2: Hex data
        part2 = secrets.token_hex(128)

        # Inject keywords (30% chance per keyword)
        keywords = self._select_random_keywords(probability=0.3)

        return self._format_output(part1, part2, keywords, mode)

    def _select_random_keywords(self, probability: float) -> List[str]:
        return [kw for kw in DETECTION_KEYWORDS
                if random.random() < probability]
```

---

## 3. Pattern-Driven Response Selection

### Hash Lookup Table Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pattern Lookup System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CLI Output ──► Keyword Extractor ──► Hash Lookup ──► Response  │
│                        │                   │                     │
│                        ▼                   ▼                     │
│               "identified" ───► MD5 ───► Follow-up Prompt       │
│               "error"     ───► MD5 ───► Error Handler           │
│               "complete"  ───► MD5 ───► Next Phase              │
│               "refactor"  ───► MD5 ───► Refactor Workflow       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern Rule Database

```python
PATTERN_RULES = {
    # Detection keyword → Response action
    'identified': PatternRule(
        pattern='identified',
        pattern_hash=md5('identified'),
        follow_up_prompt='Analyze the identified items and propose next steps',
        action_type='continue',
        category='status_change',
    ),
    'error': PatternRule(
        pattern='error',
        pattern_hash=md5('error'),
        follow_up_prompt='Explain the error and suggest fixes',
        action_type='diagnose',
        category='error_handling',
    ),
    'complete': PatternRule(
        pattern='complete',
        pattern_hash=md5('complete'),
        follow_up_prompt=None,  # Signals end of sequence
        action_type='finish',
        category='completion',
    ),
    'refactor': PatternRule(
        pattern='refactor',
        pattern_hash=md5('refactor'),
        follow_up_prompt='Apply the suggested refactoring',
        action_type='delegate',
        category='code_change',
    ),
    'optimize': PatternRule(
        pattern='optimize',
        pattern_hash=md5('optimize'),
        follow_up_prompt='Implement the suggested optimizations',
        action_type='delegate',
        category='code_change',
    ),
}
```

---

## 4. Conditional Workflow Architecture

### Workflow DAG Model

Replace linear sequences with Directed Acyclic Graphs:

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  audit_code │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ errors?  │   │ warnings?│   │  clean?  │
     └────┬─────┘   └────┬─────┘   └────┬─────┘
          │              │              │
          ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ fix_bugs │   │ refactor │   │ optimize │
     └────┬─────┘   └────┬─────┘   └────┬─────┘
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  ┌─────────────┐
                  │    merge    │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   genplan   │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  continue   │◄────────────┐
                  └──────┬──────┘             │
                         │                    │
                  (iterate if not converged)──┘
```

### Conditional Node Types

```python
class NodeType(Enum):
    """Types of workflow nodes."""
    EXECUTE = "execute"     # Run CLI tool
    CONDITION = "condition" # Branch based on output
    MERGE = "merge"         # Join parallel branches
    LOOP = "loop"           # Iterate until condition
    DELEGATE = "delegate"   # Spawn sub-workflow
    CHECKPOINT = "checkpoint" # Save state for resume

@dataclass
class WorkflowNode:
    """A node in the workflow DAG."""
    id: str
    node_type: NodeType
    tool_name: Optional[str] = None
    prompt: Optional[str] = None

    # Conditional routing
    condition: Optional[Callable[[str], bool]] = None
    true_branch: Optional[str] = None
    false_branch: Optional[str] = None

    # Iteration control
    max_iterations: int = 10
    convergence_check: Optional[Callable[[str, str], bool]] = None

    # Sub-workflow delegation
    sub_workflow: Optional[str] = None

    # Connections
    next_nodes: List[str] = field(default_factory=list)
```

---

## 5. Iterative Pattern Support

### Convergence Loop Architecture

```python
class ConvergenceLoop:
    """
    Run steps until output converges or max iterations.

    Detects convergence via:
    - Semantic similarity (optional)
    - Keyword presence ('complete', 'done', 'no changes')
    - Output stability (no change between iterations)
    """

    def __init__(
        self,
        steps: List[str],          # Sequence to repeat
        max_iterations: int = 10,
        convergence_keywords: List[str] = ['complete', 'done', 'no changes'],
        stability_threshold: float = 0.95,  # Similarity threshold
    ):
        self.steps = steps
        self.max_iterations = max_iterations
        self.convergence_keywords = convergence_keywords
        self.stability_threshold = stability_threshold

    def is_converged(self, current_output: str, previous_output: str) -> bool:
        # Check keywords
        for keyword in self.convergence_keywords:
            if keyword.lower() in current_output.lower():
                return True

        # Check stability (simple: exact match)
        if current_output == previous_output:
            return True

        return False
```

### Common Iterative Patterns

```python
ITERATIVE_SEQUENCES = {
    'audit_refactor_loop': [
        'audit code',
        'load context',
        'refactor',
        'genplan',
        'continue',  # Check convergence here
    ],

    'review_fix_loop': [
        'review code',
        'identify issues',
        'fix issues',
        'verify fixes',  # Check convergence here
    ],

    'optimize_benchmark_loop': [
        'profile code',
        'identify bottlenecks',
        'optimize',
        'benchmark',  # Check convergence here
    ],
}
```

---

## 6. Hierarchical Orchestration

### Meta-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    META-ORCHESTRATOR                             │
│                    (Strategic Level)                             │
├─────────────────────────────────────────────────────────────────┤
│  • Decomposes high-level tasks                                   │
│  • Allocates to sub-orchestrators                                │
│  • Monitors progress and conflicts                               │
│  • Makes strategic decisions                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  SUB-ORCH #1    │  │  SUB-ORCH #2    │  │  SUB-ORCH #3    │
│  (Code Gen)     │  │  (Review)       │  │  (Testing)      │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ claude-code     │  │ gemini          │  │ pytest          │
│ aider           │  │ claude-code     │  │ coverage        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Sub-Agent Delegation Protocol

```python
@dataclass
class DelegationTask:
    """A task delegated to a sub-agent."""
    task_id: str
    parent_id: str

    # Task definition
    objective: str
    constraints: List[str]
    input_context: str

    # Sub-workflow
    workflow_name: str
    tools: List[str]
    max_steps: int
    timeout: int

    # Return contract
    expected_output_format: str
    success_criteria: List[str]

class SubAgentOrchestrator:
    """
    Manages sub-agent execution.

    Features:
    - Spawns isolated sub-workflows
    - Monitors progress
    - Aggregates results
    - Handles failures
    """

    async def delegate(self, task: DelegationTask) -> DelegationResult:
        # Create isolated context
        context = self._create_context(task)

        # Run sub-workflow
        workflow = self._load_workflow(task.workflow_name)
        result = await workflow.run_with_context(context)

        # Validate result against contract
        if not self._validate_result(result, task):
            return DelegationResult(
                success=False,
                error="Result did not meet success criteria"
            )

        return DelegationResult(
            success=True,
            output=result['final_output'],
            steps_taken=len(result['steps']),
        )
```

---

## 7. Enhanced PTY Control

### Expect-Style Pattern Matching

For CLIs that prompt for confirmation (e.g., "Proceed? [y/N]"):

```python
class RobustDriver:
    """
    Expect-style driver for interactive CLIs.

    Handles:
    - Confirmation prompts (y/n)
    - Password prompts
    - Multi-choice menus
    - Pagination (--MORE--)
    """

    EXPECT_RULES = [
        ExpectRule(
            pattern=r'\[y/N\]|\(yes/no\)',
            response='y\n',
            description='Auto-confirm prompts',
        ),
        ExpectRule(
            pattern=r'--More--|Press .* to continue',
            response=' ',  # Space to continue
            description='Handle pagination',
        ),
        ExpectRule(
            pattern=r'Password:|Enter passphrase:',
            response=None,  # Block - don't auto-respond
            description='Block password prompts',
        ),
    ]

    def send_and_expect(
        self,
        input_text: str,
        expect_patterns: List[str],
        timeout: float = 30.0,
    ) -> Tuple[str, str]:
        """
        Send input and wait for expected pattern.

        Returns:
            (output, matched_pattern)
        """
        self.transport.send_line(input_text)

        start = time.time()
        accumulated = ""

        while time.time() - start < timeout:
            output = self.transport.recv_now()
            accumulated += output

            # Check expect patterns
            for pattern in expect_patterns:
                if re.search(pattern, accumulated):
                    return (accumulated, pattern)

            # Check auto-response rules
            self._handle_auto_responses(accumulated)

            time.sleep(0.1)

        raise TimeoutError(f"Expected patterns not found: {expect_patterns}")
```

---

## 8. Database Schema Enhancement

### Full Persistence Schema

```sql
-- Workflows (top-level)
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'sequential', 'parallel', 'conditional', 'iterative'
    status TEXT NOT NULL,
    parent_id TEXT,      -- For sub-workflows
    started_at REAL,
    completed_at REAL,
    total_steps INTEGER,
    successful_steps INTEGER,
    config_json TEXT,    -- Workflow configuration
    context_json TEXT,   -- Execution context
    FOREIGN KEY (parent_id) REFERENCES workflows(id)
);

-- Steps (individual executions)
CREATE TABLE steps (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    node_id TEXT,        -- For DAG workflows
    tool_name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    raw_output TEXT,
    parsed_output_json TEXT,
    patterns_found TEXT, -- Comma-separated keywords
    status TEXT NOT NULL,
    duration REAL,
    iteration INTEGER DEFAULT 0,
    timestamp REAL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Pattern matches (for analysis)
CREATE TABLE pattern_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id TEXT NOT NULL,
    pattern TEXT NOT NULL,
    pattern_hash TEXT NOT NULL,
    follow_up_prompt TEXT,
    action_taken TEXT,
    timestamp REAL,
    FOREIGN KEY (step_id) REFERENCES steps(id)
);

-- Full-text search
CREATE VIRTUAL TABLE steps_fts USING fts5(
    prompt,
    raw_output,
    content='steps',
    content_rowid='rowid'
);

-- Indexes
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_parent ON workflows(parent_id);
CREATE INDEX idx_steps_workflow ON steps(workflow_id);
CREATE INDEX idx_steps_patterns ON steps(patterns_found);
CREATE INDEX idx_patterns_hash ON pattern_matches(pattern_hash);
```

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal:** Enhanced mock CLI + integrated pattern matching

- [ ] Enhance `mock_ai_cli.py` with keyword injection
- [ ] Integrate pattern hash lookup with orchestrator
- [ ] Add pattern match logging to DB
- [ ] Unit tests for pattern detection

**Deliverables:**
- Enhanced mock CLI with configurable keywords
- Pattern-response integration in CLISequence
- DB schema migration

### Phase 2: Conditional Workflows (Week 3-4)

**Goal:** DAG-based workflow execution

- [ ] Implement `WorkflowNode` and `WorkflowDAG` classes
- [ ] Add condition nodes with branching
- [ ] Add merge nodes for parallel branches
- [ ] Implement checkpoint/resume

**Deliverables:**
- DAG workflow builder
- Conditional routing
- Visual workflow representation

### Phase 3: Iteration Support (Week 5-6)

**Goal:** Convergence loops and iterative patterns

- [ ] Implement `ConvergenceLoop` class
- [ ] Add iteration tracking to DB
- [ ] Implement stability detection
- [ ] Add max-iteration safeguards

**Deliverables:**
- Loop nodes in workflows
- Convergence detection
- Iteration metrics

### Phase 4: Hierarchical Orchestration (Week 7-8)

**Goal:** Sub-agent delegation

- [ ] Implement `SubAgentOrchestrator`
- [ ] Add delegation protocol
- [ ] Implement result aggregation
- [ ] Add conflict resolution for sub-agents

**Deliverables:**
- Sub-workflow spawning
- Result aggregation
- Hierarchical monitoring

### Phase 5: Robust PTY Control (Week 9-10)

**Goal:** Expect-style automation

- [ ] Implement `RobustDriver` with expect rules
- [ ] Add auto-response configuration
- [ ] Handle edge cases (timeouts, hangs)
- [ ] Add recovery mechanisms

**Deliverables:**
- Expect-style PTY control
- Auto-response rules
- Recovery from failures

---

## 10. API Design

### High-Level API

```python
from eats_core import (
    MetaOrchestrator,
    ConditionalWorkflow,
    ConvergenceLoop,
    SubAgentTask,
)

# Create meta-orchestrator
orchestrator = MetaOrchestrator()

# Define conditional workflow
workflow = ConditionalWorkflow('audit-and-fix')

# Add nodes
workflow.add_node('audit', tool='claude-code', prompt='Audit the codebase')
workflow.add_condition(
    'check_errors',
    condition=lambda output: 'error' in output.lower(),
    true_branch='fix_errors',
    false_branch='optimize',
)
workflow.add_node('fix_errors', tool='aider', prompt='Fix identified errors')
workflow.add_node('optimize', tool='gemini', prompt='Suggest optimizations')
workflow.add_merge('combine_results')

# Add iteration
workflow.add_loop(
    'refine',
    steps=['review', 'improve'],
    convergence_check=lambda curr, prev: 'complete' in curr,
    max_iterations=5,
)

# Run workflow
result = orchestrator.run(workflow)
```

### Declarative YAML Format

```yaml
workflow: audit-refactor-optimize
version: "1.0"

nodes:
  - id: audit
    type: execute
    tool: claude-code
    prompt: "Audit codebase for issues"
    next: [check_severity]

  - id: check_severity
    type: condition
    condition:
      pattern: "critical|error"
      match_type: regex
    true_branch: fix_critical
    false_branch: check_warnings

  - id: fix_critical
    type: delegate
    sub_workflow: critical-fix-workflow
    next: [verify_fixes]

  - id: refine_loop
    type: loop
    steps: [review, improve, verify]
    convergence:
      keywords: [complete, stable, "no changes"]
      max_iterations: 5
    next: [finalize]

  - id: finalize
    type: execute
    tool: claude-code
    prompt: "Generate final report"

parallel_groups:
  - nodes: [static_analysis, security_scan, perf_check]
    merge_at: combine_analysis
```

---

## 11. Success Metrics

### Functional

| Metric | Target |
|--------|--------|
| Conditional branch accuracy | 100% (deterministic) |
| Loop convergence detection | > 95% |
| Sub-workflow completion rate | > 99% |
| Pattern detection accuracy | > 99% |

### Performance

| Metric | Target |
|--------|--------|
| Workflow DAG traversal | < 10ms |
| Pattern hash lookup | < 1ms |
| DB write per step | < 50ms |
| Sub-workflow spawn time | < 500ms |

### Reliability

| Metric | Target |
|--------|--------|
| Workflow resume success | > 99% |
| PTY auto-response accuracy | > 95% |
| Graceful failure handling | 100% |

---

## 12. Testing Strategy

### Mock CLI Testing

```python
def test_mock_cli_keyword_injection():
    """Verify mock CLI injects detection keywords."""
    cli = MockAICLI()

    # Run multiple times to verify probabilistic injection
    outputs = [cli.generate_response('test') for _ in range(100)]

    # Should see keywords in some outputs
    keyword_counts = {kw: 0 for kw in DETECTION_KEYWORDS}
    for output in outputs:
        for kw in DETECTION_KEYWORDS:
            if kw in output.lower():
                keyword_counts[kw] += 1

    # Each keyword should appear in ~30% of outputs (with tolerance)
    for kw, count in keyword_counts.items():
        assert 10 < count < 50, f"Keyword '{kw}' appeared {count} times"
```

### Workflow DAG Testing

```python
def test_conditional_workflow():
    """Test conditional branching in workflow."""
    workflow = ConditionalWorkflow('test')

    # Setup: audit -> condition -> (fix OR optimize)
    workflow.add_node('audit', tool='mock', prompt='audit')
    workflow.add_condition(
        'check',
        condition=lambda out: 'error' in out,
        true_branch='fix',
        false_branch='optimize',
    )
    workflow.add_node('fix', tool='mock', prompt='fix')
    workflow.add_node('optimize', tool='mock', prompt='optimize')

    # Test with error output
    mock_output = "Found 3 errors in code"
    result = workflow.run(initial_output=mock_output)
    assert 'fix' in result['nodes_executed']
    assert 'optimize' not in result['nodes_executed']
```

### Convergence Testing

```python
def test_convergence_loop():
    """Test iteration until convergence."""
    loop = ConvergenceLoop(
        steps=['review', 'improve'],
        convergence_keywords=['complete'],
        max_iterations=10,
    )

    # Mock outputs that converge on iteration 3
    mock_outputs = [
        "Found issues to fix",
        "Still improving",
        "Refinement complete",
    ]

    result = loop.run(mock_output_sequence=mock_outputs)

    assert result['iterations'] == 3
    assert result['converged'] == True
```

---

## Conclusion

This plan transforms EATS from a linear CLI sequencer into a **full meta-orchestration framework** capable of:

1. **Conditional execution** based on pattern detection
2. **Iterative refinement** with convergence detection
3. **Hierarchical delegation** to sub-workflows
4. **Robust terminal control** via expect-style automation
5. **Complete persistence** for audit and resume

The implementation follows a phased approach, building each capability on the previous foundation, with comprehensive testing at each stage.

---

*Document prepared as part of the hyperspace optimization initiative.*
