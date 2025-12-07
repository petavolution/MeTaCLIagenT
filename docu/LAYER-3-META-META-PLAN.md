# LAYER 3: META-META FRAMEWORK - IMPLEMENTATION PLAN

**Status**: 📋 PLANNED
**Goal**: Transform MetaCLI from meta-framework to meta-meta-framework
**Vision**: Workflows that evolve, optimize, and generate other workflows

---

## 🎯 EXECUTIVE SUMMARY

### Current State (Layers 0-2 Complete)
- ✅ **Layer 0 (Kernel)**: Process execution primitives
- ✅ **Layer 1 (Core)**: Workflow orchestration with conditionals, loops, decisions
- ✅ **Layer 2 (Meta)**: Declarative workflows, patterns, registry

### Next Level (Layer 3)
- 🎯 **Self-Aware Workflows**: Analyze and modify themselves
- 🎯 **Intelligent Optimization**: Learn from execution history
- 🎯 **Autonomous Generation**: Create workflows from goals
- 🎯 **Higher-Order Composition**: Abstract patterns and combinators

---

## 🔍 ANALYSIS HIGHLIGHTS

### Key Findings

**Strengths:**
- Clean 3-layer architecture (817 + 2,819 + 678 = 4,314 lines)
- Unified Workflow API with multiple constructors
- 6 pre-built patterns including `audit_refactor_cycle`
- Comprehensive persistence layer (SQLite + files)

**Gaps for Meta-Meta Level:**
1. **Static Workflows**: Can't modify themselves at runtime
2. **No Learning Loop**: Each execution is independent
3. **Manual Pattern Creation**: No auto-discovery from usage
4. **Simple Decisions**: No composition (AND/OR/NOT)
5. **No Performance Analysis**: Can't identify bottlenecks
6. **No Reflection**: Limited introspection capabilities

**Impact on User's Use Case:**
The `audit → load → refactor → genplan → continue → meta-refactor` cycle needs:
- Self-optimization (detect slow steps)
- Learning (remember what worked)
- Meta-refactoring (improve the workflow itself)

---

## 📋 IMPLEMENTATION ROADMAP

### PHASE 1: INTELLIGENT DECISIONS (Week 1-2) 🟢 HIGH PRIORITY

**Goal**: Compose complex decisions from simple ones

#### Feature 1.1: Decision Combinators

**File**: `metacli/core/decision_combinators.py` (new)

**Implementation**:
```python
class DecisionCombinator:
    """Compose decisions with boolean logic."""

    @staticmethod
    def AND(*decisions: DecisionFunc) -> DecisionFunc:
        """All decisions must agree to continue."""
        def combined(output: str, context: Dict[str, Any]) -> Decision:
            results = [d(output, context) for d in decisions]

            # If any says STOP, stop
            if any(r.type == DecisionType.STOP for r in results):
                reasons = [r.reason for r in results if r.type == DecisionType.STOP]
                return Decision(
                    type=DecisionType.STOP,
                    reason=f"Stopped by: {', '.join(reasons)}",
                    context=context
                )

            # If any says LOOP, loop
            if any(r.type == DecisionType.LOOP for r in results):
                loop_result = next(r for r in results if r.type == DecisionType.LOOP)
                return loop_result

            # All say CONTINUE
            return Decision(
                type=DecisionType.CONTINUE,
                reason="All conditions satisfied",
                context=context
            )

        combined.__name__ = f"AND({', '.join(d.__name__ for d in decisions)})"
        return combined

    @staticmethod
    def OR(*decisions: DecisionFunc) -> DecisionFunc:
        """At least one decision must pass."""
        def combined(output: str, context: Dict[str, Any]) -> Decision:
            results = [d(output, context) for d in decisions]

            # If any says CONTINUE, continue
            if any(r.type == DecisionType.CONTINUE for r in results):
                return Decision(
                    type=DecisionType.CONTINUE,
                    reason="At least one condition met",
                    context=context
                )

            # All failed, use first failure
            return results[0]

        combined.__name__ = f"OR({', '.join(d.__name__ for d in decisions)})"
        return combined

    @staticmethod
    def NOT(decision: DecisionFunc) -> DecisionFunc:
        """Invert decision."""
        def inverted(output: str, context: Dict[str, Any]) -> Decision:
            result = decision(output, context)

            if result.type == DecisionType.CONTINUE:
                return Decision(
                    type=DecisionType.STOP,
                    reason=f"NOT({result.reason})",
                    context=context
                )
            elif result.type == DecisionType.STOP:
                return Decision(
                    type=DecisionType.CONTINUE,
                    reason=f"NOT({result.reason})",
                    context=context
                )

            return result  # LOOP, DELEGATE unchanged

        inverted.__name__ = f"NOT({decision.__name__})"
        return inverted

    @staticmethod
    def IF_THEN_ELSE(
        condition: DecisionFunc,
        if_true: DecisionFunc,
        if_false: DecisionFunc
    ) -> DecisionFunc:
        """Conditional decision routing."""
        def conditional(output: str, context: Dict[str, Any]) -> Decision:
            cond_result = condition(output, context)

            if cond_result.type == DecisionType.CONTINUE:
                return if_true(output, context)
            else:
                return if_false(output, context)

        conditional.__name__ = f"IF({condition.__name__}) THEN {if_true.__name__} ELSE {if_false.__name__}"
        return conditional
```

**Usage Example**:
```python
from metacli.core import Workflow
from metacli.core.decision import has_errors_decision, test_pass_decision, max_iterations_decision
from metacli.core.decision_combinators import DecisionCombinator as DC

workflow = Workflow("smart-refactor")

# Complex decision: Continue only if tests pass AND no errors AND iterations < 3
workflow.add_step(
    "refactor",
    "aider",
    "Fix issues",
    decision=DC.AND(
        test_pass_decision,
        DC.NOT(has_errors_decision),
        max_iterations_decision(3)
    ),
    loop_back_to="test"
)
```

**Effort**: 1 day
**Impact**: Medium (enables complex decision logic)
**Dependencies**: None

---

### PHASE 2: WORKFLOW INTROSPECTION (Week 2-3) 🟢 HIGH PRIORITY

**Goal**: Workflows can analyze their own execution

#### Feature 2.1: Execution Tracer

**File**: `metacli/meta/tracer.py` (new)

**Implementation**:
```python
from dataclasses import dataclass
from typing import List, Dict, Any
import time

@dataclass
class ExecutionTrace:
    """Detailed execution trace for a workflow."""
    workflow_id: str
    workflow_name: str
    started_at: float
    completed_at: float
    total_duration: float

    # Execution path
    steps_executed: List[str]
    steps_skipped: List[str]

    # Decision points
    decisions_made: List[Dict[str, Any]]

    # Performance
    step_durations: Dict[str, float]
    slowest_step: str
    fastest_step: str

    # Loops
    loop_iterations: Dict[str, int]

    # Context evolution
    context_snapshots: List[Dict[str, Any]]


class WorkflowTracer:
    """Trace workflow execution for analysis."""

    def __init__(self, workflow):
        self.workflow = workflow
        self.trace_data = {
            "decisions": [],
            "step_order": [],
            "context_snapshots": [],
            "timings": {}
        }

    def record_step_start(self, step_name: str, context: Dict):
        """Record step execution start."""
        self.trace_data["step_order"].append(step_name)
        self.trace_data["context_snapshots"].append({
            "step": step_name,
            "time": time.time(),
            "context": dict(context)
        })

    def record_decision(self, step_name: str, decision: Decision, output: str):
        """Record decision made."""
        self.trace_data["decisions"].append({
            "step": step_name,
            "decision_type": decision.type.value,
            "reason": decision.reason,
            "next_step": decision.next_step,
            "output_preview": output[:200]
        })

    def record_step_end(self, step_name: str, duration: float):
        """Record step completion."""
        self.trace_data["timings"][step_name] = duration

    def build_trace(self) -> ExecutionTrace:
        """Build execution trace object."""
        # Identify loops
        loop_iterations = {}
        for step in self.trace_data["step_order"]:
            loop_iterations[step] = loop_iterations.get(step, 0) + 1

        # Find slowest/fastest
        if self.trace_data["timings"]:
            slowest = max(self.trace_data["timings"], key=self.trace_data["timings"].get)
            fastest = min(self.trace_data["timings"], key=self.trace_data["timings"].get)
        else:
            slowest = fastest = None

        return ExecutionTrace(
            workflow_id=self.workflow.workflow_id,
            workflow_name=self.workflow.name,
            started_at=self.workflow.started_at,
            completed_at=time.time(),
            total_duration=time.time() - self.workflow.started_at,
            steps_executed=list(set(self.trace_data["step_order"])),
            steps_skipped=[s.name for s in self.workflow.steps if s.name not in self.trace_data["step_order"]],
            decisions_made=self.trace_data["decisions"],
            step_durations=self.trace_data["timings"],
            slowest_step=slowest,
            fastest_step=fastest,
            loop_iterations=loop_iterations,
            context_snapshots=self.trace_data["context_snapshots"]
        )

    def visualize(self, trace: ExecutionTrace) -> str:
        """Generate Mermaid diagram of execution."""
        lines = ["```mermaid", "graph TD"]

        prev_step = None
        for i, step in enumerate(trace.steps_executed):
            # Add node
            duration = trace.step_durations.get(step, 0)
            lines.append(f'    {step}["{step}<br/>{duration:.2f}s"]')

            # Add edge from previous
            if prev_step:
                lines.append(f"    {prev_step} --> {step}")

            prev_step = step

        lines.append("```")
        return "\n".join(lines)
```

**Integration with Workflow**:
```python
# In workflow.py
class Workflow:
    def run(self, enable_tracing: bool = False) -> Dict[str, Any]:
        """Execute workflow with optional tracing."""
        tracer = WorkflowTracer(self) if enable_tracing else None

        # ... execution logic with tracer.record_*() calls ...

        result = self._build_result(total_duration)

        if tracer:
            result["trace"] = tracer.build_trace()
            result["trace_diagram"] = tracer.visualize(result["trace"])

        return result
```

**Usage Example**:
```python
workflow = Workflow.from_yaml("audit-refactor.yaml")
result = workflow.run(enable_tracing=True)

trace = result["trace"]
print(f"Slowest step: {trace.slowest_step} ({trace.step_durations[trace.slowest_step]:.2f}s)")
print(f"Loop iterations: {trace.loop_iterations}")
print(f"\nExecution diagram:\n{result['trace_diagram']}")
```

**Effort**: 2 days
**Impact**: High (enables performance analysis)
**Dependencies**: None

---

### PHASE 3: PERFORMANCE OPTIMIZATION (Week 3-4) 🟡 MEDIUM PRIORITY

**Goal**: Automatically identify and fix workflow bottlenecks

#### Feature 3.1: Workflow Optimizer

**File**: `metacli/meta/optimizer.py` (new)

**Implementation**:
```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class OptimizationSuggestion:
    """A suggested workflow optimization."""
    category: str  # "cache", "parallel", "reorder", "remove"
    description: str
    impact: str  # "high", "medium", "low"
    confidence: float  # 0.0-1.0

    # How to apply
    step_name: str
    modification: Dict[str, Any]


class WorkflowOptimizer:
    """Analyze workflow execution and suggest optimizations."""

    def __init__(self, persistence):
        self.persistence = persistence

    def analyze_workflow(self, workflow_name: str, runs: int = 10) -> List[OptimizationSuggestion]:
        """Analyze recent runs of a workflow."""
        suggestions = []

        # Get recent executions
        recent_runs = self.persistence.query(name=workflow_name, limit=runs)

        # Analyze for patterns
        suggestions.extend(self._detect_slow_steps(recent_runs))
        suggestions.extend(self._detect_redundant_steps(recent_runs))
        suggestions.extend(self._detect_cacheable_outputs(recent_runs))
        suggestions.extend(self._detect_parallelizable_steps(recent_runs))

        # Sort by impact
        return sorted(suggestions, key=lambda s: (s.impact, s.confidence), reverse=True)

    def _detect_slow_steps(self, runs: List[Dict]) -> List[OptimizationSuggestion]:
        """Find consistently slow steps."""
        suggestions = []

        # Calculate average duration per step
        step_durations = {}
        for run in runs:
            for step in run["steps"]:
                if step["step_name"] not in step_durations:
                    step_durations[step["step_name"]] = []
                step_durations[step["step_name"]].append(step["duration"])

        # Find outliers
        for step_name, durations in step_durations.items():
            avg_duration = sum(durations) / len(durations)

            # If step takes >50% of total workflow time
            if avg_duration > 30:  # seconds
                suggestions.append(OptimizationSuggestion(
                    category="cache",
                    description=f"Step '{step_name}' is slow ({avg_duration:.1f}s avg). Consider caching outputs.",
                    impact="high",
                    confidence=0.9,
                    step_name=step_name,
                    modification={"add_cache": True}
                ))

        return suggestions

    def _detect_redundant_steps(self, runs: List[Dict]) -> List[OptimizationSuggestion]:
        """Find steps that always produce same output."""
        suggestions = []

        # Group outputs by step
        step_outputs = {}
        for run in runs:
            for step in run["steps"]:
                if step["step_name"] not in step_outputs:
                    step_outputs[step["step_name"]] = []
                step_outputs[step["step_name"]].append(step["raw_output"])

        # Check for identical outputs
        for step_name, outputs in step_outputs.items():
            unique_outputs = set(outputs)
            if len(unique_outputs) == 1 and len(outputs) >= 5:
                suggestions.append(OptimizationSuggestion(
                    category="remove",
                    description=f"Step '{step_name}' always produces same output. Consider making it conditional or removing.",
                    impact="medium",
                    confidence=0.8,
                    step_name=step_name,
                    modification={"make_conditional": True}
                ))

        return suggestions

    def _detect_cacheable_outputs(self, runs: List[Dict]) -> List[OptimizationSuggestion]:
        """Find steps with repetitive prompts but different context."""
        suggestions = []

        # Analyze prompt patterns
        step_prompts = {}
        for run in runs:
            for step in run["steps"]:
                if step["step_name"] not in step_prompts:
                    step_prompts[step["step_name"]] = []
                step_prompts[step["step_name"]].append(step["prompt"])

        # Find similar prompts
        for step_name, prompts in step_prompts.items():
            # Simple similarity check (in production, use semantic similarity)
            if len(set(prompts)) < len(prompts) * 0.3:  # 70%+ similar
                suggestions.append(OptimizationSuggestion(
                    category="cache",
                    description=f"Step '{step_name}' has repetitive prompts. Semantic caching could help.",
                    impact="medium",
                    confidence=0.7,
                    step_name=step_name,
                    modification={"enable_semantic_cache": True}
                ))

        return suggestions

    def _detect_parallelizable_steps(self, runs: List[Dict]) -> List[OptimizationSuggestion]:
        """Find steps that could run in parallel."""
        suggestions = []

        # Analyze step dependencies
        for run in runs:
            steps = run["steps"]
            for i, step in enumerate(steps[:-1]):
                next_step = steps[i + 1]

                # If next step doesn't use previous output, they could be parallel
                if not next_step.get("use_previous", False):
                    suggestions.append(OptimizationSuggestion(
                        category="parallel",
                        description=f"Steps '{step['step_name']}' and '{next_step['step_name']}' could run in parallel.",
                        impact="high",
                        confidence=0.6,
                        step_name=step["step_name"],
                        modification={
                            "parallelize_with": next_step["step_name"]
                        }
                    ))

        return suggestions

    def apply_optimization(self, workflow: Workflow, suggestion: OptimizationSuggestion) -> Workflow:
        """Apply an optimization suggestion to a workflow."""
        # Clone workflow
        optimized = Workflow(workflow.name + "_optimized", workflow.auto_save)
        optimized.steps = workflow.steps.copy()
        optimized.context = workflow.context.copy()

        # Apply modification
        if suggestion.category == "cache":
            # Add caching wrapper
            pass  # Implementation depends on caching strategy

        elif suggestion.category == "remove":
            # Remove step
            optimized.steps = [s for s in optimized.steps if s.name != suggestion.step_name]

        elif suggestion.category == "parallel":
            # Mark steps for parallel execution
            pass  # Requires parallel execution support

        return optimized
```

**Usage Example**:
```python
from metacli.core import Workflow, get_persistence
from metacli.meta.optimizer import WorkflowOptimizer

# Run workflow multiple times
workflow = Workflow.from_yaml("audit-refactor.yaml")
for i in range(10):
    workflow.run()

# Analyze and optimize
optimizer = WorkflowOptimizer(get_persistence())
suggestions = optimizer.analyze_workflow("audit-refactor-cycle")

print("🔍 Optimization Suggestions:")
for s in suggestions:
    print(f"  [{s.impact.upper()}] {s.description}")

# Apply best suggestion
if suggestions:
    optimized_workflow = optimizer.apply_optimization(workflow, suggestions[0])
    print(f"\n✅ Created optimized workflow: {optimized_workflow.name}")
```

**Effort**: 3 days
**Impact**: High (automatic performance improvements)
**Dependencies**: Phase 2 (tracer for detailed metrics)

---

### PHASE 4: PATTERN MINING (Week 5-7) 🟡 MEDIUM PRIORITY

**Goal**: Automatically discover workflow patterns from usage

#### Feature 4.1: Pattern Discovery Engine

**File**: `metacli/meta/pattern_miner.py` (new)

**Implementation**:
```python
from typing import List, Dict, Any, Tuple
from collections import Counter
from dataclasses import dataclass

@dataclass
class DiscoveredPattern:
    """Auto-discovered workflow pattern."""
    name: str
    description: str
    frequency: float  # 0.0-1.0 (how often this pattern appears)
    avg_success_rate: float
    avg_duration: float

    # Pattern definition
    step_sequence: List[str]
    decision_types: List[str]
    common_prompts: Dict[str, str]

    # Evidence
    example_workflow_ids: List[str]
    total_occurrences: int


class PatternMiner:
    """Discover common workflow patterns from execution history."""

    def __init__(self, persistence):
        self.persistence = persistence

    def mine_patterns(self, min_occurrences: int = 5, min_frequency: float = 0.3) -> List[DiscoveredPattern]:
        """Find common patterns across all workflows."""
        all_workflows = self.persistence.query(limit=1000)

        # Extract step sequences
        sequences = []
        for wf in all_workflows:
            sequence = tuple(step["step_name"] for step in wf["steps"])
            sequences.append((sequence, wf))

        # Count sequences
        sequence_counts = Counter(seq for seq, _ in sequences)

        # Extract patterns
        patterns = []
        for sequence, count in sequence_counts.items():
            if count >= min_occurrences:
                frequency = count / len(sequences)

                if frequency >= min_frequency:
                    # Get example workflows with this pattern
                    examples = [wf for seq, wf in sequences if seq == sequence]

                    pattern = self._build_pattern(sequence, examples)
                    patterns.append(pattern)

        return sorted(patterns, key=lambda p: p.frequency, reverse=True)

    def _build_pattern(self, sequence: Tuple[str], examples: List[Dict]) -> DiscoveredPattern:
        """Build pattern from examples."""
        # Calculate statistics
        success_rate = sum(1 for ex in examples if ex["status"] == "completed") / len(examples)
        avg_duration = sum(ex["duration"] for ex in examples) / len(examples)

        # Extract common prompts
        common_prompts = {}
        for step_name in sequence:
            prompts = []
            for ex in examples:
                step = next((s for s in ex["steps"] if s["step_name"] == step_name), None)
                if step:
                    prompts.append(step["prompt"])

            # Find most common prompt
            if prompts:
                common_prompts[step_name] = Counter(prompts).most_common(1)[0][0]

        # Generate name and description
        name = f"auto_{'_'.join(sequence[:3])}"  # Use first 3 steps
        description = f"Pattern: {' → '.join(sequence)}"

        return DiscoveredPattern(
            name=name,
            description=description,
            frequency=len(examples) / 100,  # Approximate
            avg_success_rate=success_rate,
            avg_duration=avg_duration,
            step_sequence=list(sequence),
            decision_types=[],  # TODO: Extract from examples
            common_prompts=common_prompts,
            example_workflow_ids=[ex["id"] for ex in examples[:5]],
            total_occurrences=len(examples)
        )

    def suggest_pattern_for_workflow(self, workflow_steps: List[str]) -> List[DiscoveredPattern]:
        """Suggest patterns similar to given workflow."""
        all_patterns = self.mine_patterns()

        # Find patterns with overlapping steps
        suggestions = []
        workflow_set = set(workflow_steps)

        for pattern in all_patterns:
            pattern_set = set(pattern.step_sequence)
            overlap = len(workflow_set & pattern_set) / len(workflow_set)

            if overlap > 0.5:  # 50%+ overlap
                suggestions.append(pattern)

        return suggestions

    def register_pattern(self, pattern: DiscoveredPattern, registry) -> None:
        """Register discovered pattern in workflow registry."""
        # Create pattern definition
        pattern_def = {
            "name": pattern.name,
            "description": pattern.description,
            "steps": [
                {
                    "name": step_name,
                    "tool": "claude-code",  # Default, should be extracted
                    "prompt": pattern.common_prompts.get(step_name, "")
                }
                for step_name in pattern.step_sequence
            ]
        }

        # Save as YAML
        import yaml
        yaml_path = f".metacli/discovered/{pattern.name}.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(pattern_def, f)

        # Register
        registry.register(
            pattern.name,
            yaml_path,
            version="auto-discovered",
            description=f"{pattern.description} (Auto-discovered, {pattern.total_occurrences} occurrences)"
        )
```

**Usage Example**:
```python
from metacli.core import get_persistence
from metacli.meta import get_registry
from metacli.meta.pattern_miner import PatternMiner

# Mine patterns from history
miner = PatternMiner(get_persistence())
patterns = miner.mine_patterns(min_occurrences=5)

print("🔍 Discovered Patterns:")
for p in patterns:
    print(f"\n  {p.name}")
    print(f"  Sequence: {' → '.join(p.step_sequence)}")
    print(f"  Frequency: {p.frequency*100:.1f}%")
    print(f"  Success Rate: {p.avg_success_rate*100:.1f}%")
    print(f"  Avg Duration: {p.avg_duration:.1f}s")

# Register patterns
registry = get_registry()
for pattern in patterns[:3]:  # Register top 3
    miner.register_pattern(pattern, registry)
    print(f"✅ Registered: {pattern.name}")
```

**Effort**: 5 days
**Impact**: High (automatic pattern discovery)
**Dependencies**: Persistence layer

---

### PHASE 5: SELF-MODIFYING WORKFLOWS (Week 8-10) 🔴 LOW PRIORITY (FUTURE)

**Goal**: Workflows that can modify themselves

#### Feature 5.1: Workflow Self-Modification API

**File**: `metacli/meta/self_modifying.py` (new)

**Concept** (detailed implementation in future):
```python
class SelfModifyingWorkflow(Workflow):
    """Workflow that can analyze and modify itself."""

    def enable_self_optimization(self):
        """Enable automatic self-optimization."""
        self.auto_optimize = True

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze own execution performance."""
        return {
            "bottlenecks": self._find_bottlenecks(),
            "redundancies": self._find_redundancies(),
            "optimization_opportunities": self._suggest_optimizations()
        }

    def optimize_self(self):
        """Apply optimizations to self."""
        analysis = self.analyze_performance()

        for opt in analysis["optimization_opportunities"]:
            self._apply_optimization(opt)

    def _apply_optimization(self, opt: Dict):
        """Apply single optimization."""
        if opt["type"] == "remove_redundant_step":
            self.remove_step(opt["step_name"])
        elif opt["type"] == "add_caching":
            self.add_caching_to_step(opt["step_name"])
        elif opt["type"] == "reorder_steps":
            self.reorder_steps(opt["new_order"])
```

**Effort**: 8 days
**Impact**: Very High (autonomous workflows)
**Dependencies**: All previous phases

---

## 🎯 RECOMMENDED IMPLEMENTATION ORDER

### Sprint 1 (Week 1-2): Foundations
1. ✅ Decision Combinators (1 day)
2. ✅ Execution Tracer (2 days)
3. ✅ Basic testing and integration

**Deliverable**: Complex decision logic + execution visibility

### Sprint 2 (Week 3-4): Intelligence
1. ✅ Workflow Optimizer (3 days)
2. ✅ Integration with existing workflows
3. ✅ Documentation and examples

**Deliverable**: Automatic performance analysis

### Sprint 3 (Week 5-7): Autonomy
1. ✅ Pattern Miner (5 days)
2. ✅ Pattern registration automation
3. ✅ User-facing pattern suggestions

**Deliverable**: Auto-discovered patterns

### Sprint 4 (Week 8+): Future
- Self-modifying workflows
- Goal-directed synthesis
- Evolutionary optimization

---

## 📊 SUCCESS METRICS

### Phase 1 Success:
- [ ] Can compose 3+ decisions with AND/OR/NOT
- [ ] Decision logic is clear and maintainable
- [ ] All existing examples still work

### Phase 2 Success:
- [ ] Can visualize workflow execution paths
- [ ] Can identify slowest step in workflow
- [ ] Can detect loop iterations

### Phase 3 Success:
- [ ] Can suggest 3+ optimizations per workflow
- [ ] Optimizations reduce execution time by 20%+
- [ ] Suggestions have 80%+ user acceptance rate

### Phase 4 Success:
- [ ] Can discover patterns from 100+ workflow runs
- [ ] Discovered patterns match manually-created ones
- [ ] Auto-registration works smoothly

---

## 🚀 ALIGNMENT WITH USER'S USE CASE

### The Audit → Meta-Refactor Cycle

**Current Support:**
✅ `audit → load → refactor → verify` works via `audit_refactor_cycle` pattern
✅ Conditionals and loops supported
✅ Sub-agent delegation via decision routing

**After Phase 1:**
✅ Complex decisions: "Continue only if tests pass AND no errors AND iteration < max"

**After Phase 2:**
✅ Can analyze which steps are slow in the cycle
✅ Can visualize execution path through the cycle
✅ Can detect infinite loops and stop gracefully

**After Phase 3:**
✅ System suggests: "load_context is slow, add caching"
✅ Automatically generates optimized variant
✅ Measures improvement: "40% faster with cache"

**After Phase 4:**
✅ After 20 runs, system says: "I notice you always do audit→load→refactor→verify→meta-refactor"
✅ Offers to create pattern: "auto_audit_load_refactor"
✅ Pattern available in registry for reuse

**Future (Phase 5):**
✅ Workflow modifies itself: adds error handling after repeated failures
✅ Meta-refactors itself: reorders steps for efficiency
✅ Evolves: tries variations, keeps best performing

---

## 💡 ARCHITECTURAL PRINCIPLES

### 1. Backward Compatibility
All new features must work with existing workflows without modification.

### 2. Opt-In Complexity
Advanced features are opt-in:
```python
workflow.run()  # Simple, no changes
workflow.run(enable_tracing=True)  # Advanced feature
```

### 3. Composability
Features should compose:
```python
workflow.run(
    enable_tracing=True,
    enable_optimization=True,
    enable_pattern_mining=True
)
```

### 4. Clear Separation
Layer 3 builds on Layers 1-2 without modifying them.

---

## 📝 NEXT STEPS

### Immediate Actions:
1. **Review this plan** - Validate approach
2. **Choose starting point** - Phase 1 recommended
3. **Create feature branch** - `feature/layer-3-meta-meta`
4. **Implement Phase 1** - Decision combinators (1 week)
5. **Iterate** - Build, test, refine

### Questions to Answer:
- [ ] Priority: Which phases are most valuable?
- [ ] Scope: Should we start smaller or go full Layer 3?
- [ ] Timeline: How fast to move?
- [ ] Resources: Solo or team effort?

---

## 🎉 VISION

**From**: Static workflows defined in YAML
**To**: Intelligent, self-optimizing, evolving meta-framework

**Impact**:
- 🚀 **Performance**: 20-40% faster through auto-optimization
- 🧠 **Intelligence**: Learns from every execution
- 🔄 **Evolution**: Workflows improve themselves over time
- 💡 **Discovery**: Patterns emerge from usage
- 🎯 **Autonomy**: Workflows achieve goals, not just execute steps

**The Ultimate Meta-Framework**: Workflows that write, optimize, and evolve other workflows.

---

**Status**: 📋 PLANNED - Ready for Implementation
**Next**: Choose phase and begin development
**Contact**: Ready for questions and refinement
