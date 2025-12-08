#!/usr/bin/env python3
"""
Progressive Orchestration Examples - Simple to Complex

4 Simple Examples:
1. Single AI tool execution
2. Two-step sequence (audit → fix)
3. Three-step with decision point
4. Four-step with context passing

3 Complex Examples:
5. Multi-layered parallel + sequential
6. Iterative loop with sub-agents
7. Full hyperspace optimization

Run: python examples/08_progressive_examples.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.core import (
    Orchestrator,
    UnifiedExecutor,
    WorkflowContext,
    OrchestratorStep as WorkflowStep,
    StepType,
    create_ai_executor,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIMPLE EXAMPLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_1_single_tool():
    """
    Example 1: Single AI Tool Execution

    Simplest possible: Execute one AI tool, parse output, done.

    Flow: claude-code (audit) → done
    """
    print("=" * 70)
    print("Example 1: Single AI Tool Execution")
    print("=" * 70)

    executor = create_ai_executor()

    # Single execution
    result = executor.execute(
        tool="mock-ai",
        prompt="audit src/api.py for security issues"
    )

    print(f"\n  Tool: {result.tool}")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Success: {result.success}")

    if result.parsed_output:
        print(f"  Keywords: {result.parsed_output.detected_keywords}")
        print(f"  Text: {result.parsed_output.decoded_text[:80]}...")

    print("\n✓ Example 1 complete\n")


def example_2_two_step_sequence():
    """
    Example 2: Two-Step Sequence

    Basic sequence: First tool analyzes, second tool fixes.
    No decisions, just linear execution.

    Flow: claude-code (audit) → codex (fix) → done
    """
    print("=" * 70)
    print("Example 2: Two-Step Sequence (audit → fix)")
    print("=" * 70)

    orchestrator = Orchestrator()

    # Create simple two-step workflow
    workflow = orchestrator.create_workflow(
        "simple-audit-fix",
        "Audit then fix"
    )

    workflow.add_step("audit", "mock-ai", "audit {target}")
    workflow.add_step("fix", "mock-ai", "fix issues in {target}")

    print("\n  Workflow steps:")
    print(f"    1. audit: Analyze code")
    print(f"    2. fix: Apply fixes")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"\n  Results:")
    for name, result in context.results.items():
        status = "✓" if result.success else "✗"
        duration = result.duration
        print(f"    {status} {name}: {duration:.2f}s")

    print("\n✓ Example 2 complete\n")


def example_3_three_step_with_decision():
    """
    Example 3: Three-Step with Decision Point

    Add intelligence: Check audit output, decide whether to fix or skip.
    Demonstrates sub-agent decision making.

    Flow: audit → [has errors?] → fix or skip → done
    """
    print("=" * 70)
    print("Example 3: Three-Step with Decision Point")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "audit-decide-fix",
        "Audit with intelligent routing"
    )

    # Step 1: Audit
    workflow.add_step("audit", "mock-ai", "audit {target}")

    # Decision: Should we fix?
    def decide_if_fix_needed(ctx: WorkflowContext) -> str:
        """Sub-agent decision: analyze output and route."""
        last = ctx.get_last_result()

        if last and last.parsed_output:
            keywords = last.parsed_output.detected_keywords

            if 'error' in keywords or 'identified' in keywords:
                print("    → Decision: Issues found, routing to 'fix'")
                return "fix"
            elif 'complete' in keywords:
                print("    → Decision: No issues, routing to 'skip'")
                return "skip"

        print("    → Decision: Unclear, routing to 'skip'")
        return "skip"

    workflow.add_decision("decide_fix", decide_if_fix_needed)

    # Step 2a: Fix (if needed)
    workflow.add_step("fix", "mock-ai", "fix issues in {target}")

    # Step 2b: Skip (if not needed)
    workflow.add_step("skip", "mock-ai", "no action needed for {target}")

    print("\n  Workflow structure:")
    print("    audit → decision → fix or skip")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/auth.py"})

    print(f"\n  Execution path:")
    for i, name in enumerate(context.results.keys(), 1):
        print(f"    {i}. {name}")

    print("\n✓ Example 3 complete\n")


def example_4_four_step_context_passing():
    """
    Example 4: Four-Step with Context Passing

    More sophisticated: Pass information between steps via context.
    Each step uses outputs from previous steps.

    Flow: audit → load context → refactor → verify → done
    """
    print("=" * 70)
    print("Example 4: Four-Step with Context Passing")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "context-passing",
        "Pass context between steps"
    )

    # Step 1: Audit (find issues)
    workflow.add_step("audit", "mock-ai", "audit {target}")

    # Step 2: Load context (gather details)
    workflow.add_step(
        "load_context",
        "mock-ai",
        "load detailed context for issues in {target}"
    )

    # Step 3: Refactor (apply fixes)
    workflow.add_step(
        "refactor",
        "mock-ai",
        "refactor {target} based on context"
    )

    # Step 4: Verify (check results)
    workflow.add_step(
        "verify",
        "mock-ai",
        "verify changes to {target}"
    )

    print("\n  Workflow pipeline:")
    print("    audit → load_context → refactor → verify")
    print("\n  Context flow:")
    print("    {target} passed to all steps")
    print("    Each step uses previous outputs")

    # Execute
    context = orchestrator.execute(workflow, {
        "target": "src/payment.py"
    })

    print(f"\n  Execution summary:")
    total_time = sum(r.duration for r in context.results.values())
    print(f"    Steps: {len(context.results)}")
    print(f"    Total time: {total_time:.2f}s")
    print(f"    All succeeded: {all(r.success for r in context.results.values())}")

    print("\n✓ Example 4 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPLEX EXAMPLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_5_parallel_then_sequential():
    """
    Example 5: Multi-Layered Parallel + Sequential

    Complex: Parallel analysis by multiple agents, then sequential refinement.
    Demonstrates coordinated multi-agent orchestration.

    Flow:
        ┌─ claude (security) ─┐
        ├─ codex (performance) ┤→ merge → decide → refactor → verify
        └─ gemini (architecture)┘
    """
    print("=" * 70)
    print("Example 5: Multi-Layered Parallel + Sequential")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "parallel-sequential",
        "Parallel analysis then sequential refinement"
    )

    # Layer 1: Parallel analysis by 3 specialized agents
    parallel_steps = [
        WorkflowStep(
            name="security_audit",
            step_type=StepType.EXECUTE,
            tool="mock-ai",
            prompt_template="audit security of {target}"
        ),
        WorkflowStep(
            name="performance_audit",
            step_type=StepType.EXECUTE,
            tool="mock-ai",
            prompt_template="analyze performance of {target}"
        ),
        WorkflowStep(
            name="architecture_audit",
            step_type=StepType.EXECUTE,
            tool="mock-ai",
            prompt_template="review architecture of {target}"
        ),
    ]

    workflow.add_parallel("parallel_analysis", parallel_steps)

    # Layer 2: Merge results
    workflow.add_step(
        "merge",
        "mock-ai",
        "merge analysis results for {target}"
    )

    # Layer 3: Decision point
    def decide_priority(ctx: WorkflowContext) -> str:
        """Analyze all parallel results and prioritize."""
        print("\n    Sub-agent decision: Analyzing parallel results...")

        # Check what each agent found
        security_result = ctx.results.get("security_audit")
        performance_result = ctx.results.get("performance_audit")

        if security_result and security_result.has_error:
            print("    → Priority: SECURITY (critical)")
            ctx.set("priority", "security")
            return "refactor"
        elif performance_result and 'optimize' in performance_result.parsed_output.detected_keywords:
            print("    → Priority: PERFORMANCE (important)")
            ctx.set("priority", "performance")
            return "refactor"
        else:
            print("    → Priority: ARCHITECTURE (low)")
            ctx.set("priority", "architecture")
            return "refactor"

    workflow.add_decision("prioritize", decide_priority)

    # Layer 4: Sequential refinement
    workflow.add_step(
        "refactor",
        "mock-ai",
        "refactor {target} focusing on {priority}"
    )

    workflow.add_step(
        "verify",
        "mock-ai",
        "verify {priority} improvements in {target}"
    )

    print("\n  Architecture:")
    print("    Layer 1: Parallel (3 agents)")
    print("    Layer 2: Merge")
    print("    Layer 3: Decision")
    print("    Layer 4: Sequential refinement")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/core/"})

    print(f"\n  Results:")
    print(f"    Parallel steps: 3")
    print(f"    Priority chosen: {context.get('priority')}")
    print(f"    Total steps: {len(context.results)}")

    print("\n✓ Example 5 complete\n")


def example_6_iterative_loop_with_subagents():
    """
    Example 6: Iterative Loop with Sub-Agents

    Advanced: Loop with multiple sub-agents making decisions at each iteration.
    Demonstrates iterative refinement with meta-analysis.

    Flow:
        test → [passed?] → done
         ↓ failed
        analyze → fix → meta-check → [continue?] → test (loop)
    """
    print("=" * 70)
    print("Example 6: Iterative Loop with Sub-Agents")
    print("=" * 70)

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "iterative-subagents",
        "Test-fix loop with sub-agent decisions"
    )
    workflow.max_iterations = 5

    # Layer 1: Test
    workflow.add_step("test", "mock-ai", "run tests for {target}")

    # Sub-agent 1: Analyze test results
    def analyze_test_results(ctx: WorkflowContext) -> str:
        """Sub-agent: Determine what failed."""
        last = ctx.get_last_result()

        if last and last.parsed_output:
            if 'error' in last.parsed_output.detected_keywords:
                print(f"    → Sub-agent 1: Tests failed, analyzing...")
                ctx.set("failure_type", "error")
                return "analyze_failures"
            elif 'complete' in last.parsed_output.detected_keywords:
                print(f"    → Sub-agent 1: All tests passed!")
                return "done"

        return "done"

    workflow.add_decision("check_tests", analyze_test_results)

    # Layer 2: Analyze failures
    workflow.add_step(
        "analyze_failures",
        "mock-ai",
        "analyze test failures in {target}"
    )

    # Layer 3: Fix
    workflow.add_step(
        "fix",
        "mock-ai",
        "fix {failure_type} in {target}"
    )

    # Sub-agent 2: Meta-check if we should continue
    def meta_check_continue(ctx: WorkflowContext) -> str:
        """Sub-agent: Meta-analysis of progress."""
        iteration = ctx.iteration_count

        print(f"    → Sub-agent 2: Meta-check at iteration {iteration}")

        if iteration >= 5:
            print(f"      Meta-decision: Max iterations reached, stop")
            return "done"

        # Check if we're making progress
        fix_result = ctx.get_last_result()
        if fix_result and fix_result.is_complete:
            print(f"      Meta-decision: Fix complete, retest")
            return "loop_to_test"

        print(f"      Meta-decision: Continue iteration")
        return "loop_to_test"

    workflow.add_decision("meta_check", meta_check_continue)

    # Loop back to test
    def should_loop(ctx: WorkflowContext) -> bool:
        return ctx.iteration_count < 5

    workflow.add_loop("loop_to_test", "test", should_loop)

    # Done
    workflow.add_step("done", "mock-ai", "all tests passed for {target}")

    print("\n  Multi-layered loop structure:")
    print("    test")
    print("    ↓")
    print("    sub-agent 1 (analyze results)")
    print("    ↓")
    print("    analyze failures → fix")
    print("    ↓")
    print("    sub-agent 2 (meta-check)")
    print("    ↓")
    print("    loop or done")

    # Execute
    context = orchestrator.execute(workflow, {
        "target": "tests/",
        "failure_type": "unknown"
    })

    print(f"\n  Execution summary:")
    print(f"    Total iterations: {context.iteration_count}")
    print(f"    Steps executed: {len(context.results)}")
    print(f"    Sub-agents called: 2 per iteration")

    print("\n✓ Example 6 complete\n")


def example_7_full_hyperspace_optimization():
    """
    Example 7: Full Hyperspace Optimization

    Most complex: Multi-dimensional parallel optimization with conflict resolution,
    iterative improvement, and meta-learning.

    Demonstrates the complete "dimension hyperspace" vision.

    Flow:
        ┌─ security dimension agent ─┐
        ├─ performance dimension ────┤→ conflict resolver → iterative improver → meta-learner
        └─ architecture dimension ───┘
              ↓ (loop until optimal)
        measure → [pareto optimal?] → done or continue
    """
    print("=" * 70)
    print("Example 7: Full Hyperspace Optimization")
    print("=" * 70)
    print("\n  🌌 Navigating the dimension hyperspace of optimal code...")

    orchestrator = Orchestrator()
    workflow = orchestrator.create_workflow(
        "hyperspace-optimization",
        "Multi-dimensional code optimization"
    )
    workflow.max_iterations = 3

    # ═══════════════════════════════════════════════════════════
    # Layer 1: Parallel Multi-Dimensional Analysis
    # ═══════════════════════════════════════════════════════════

    dimension_agents = [
        WorkflowStep(
            name="security_dimension",
            step_type=StepType.EXECUTE,
            tool="mock-ai",
            prompt_template="optimize {target} for SECURITY dimension"
        ),
        WorkflowStep(
            name="performance_dimension",
            step_type=StepType.EXECUTE,
            tool="mock-ai",
            prompt_template="optimize {target} for PERFORMANCE dimension"
        ),
        WorkflowStep(
            name="architecture_dimension",
            step_type=StepType.EXECUTE,
            tool="mock-ai",
            prompt_template="optimize {target} for ARCHITECTURE dimension"
        ),
    ]

    workflow.add_parallel("dimension_analysis", dimension_agents)

    # ═══════════════════════════════════════════════════════════
    # Layer 2: Conflict Resolution Sub-Agent
    # ═══════════════════════════════════════════════════════════

    def resolve_conflicts(ctx: WorkflowContext) -> str:
        """Sub-agent: Resolve conflicts between dimension optimizations."""
        print("\n    🤖 Conflict Resolution Sub-Agent:")

        # Get all dimension results
        security = ctx.results.get("security_dimension")
        performance = ctx.results.get("performance_dimension")
        architecture = ctx.results.get("architecture_dimension")

        conflicts = []

        # Check for conflicts
        if security and performance:
            if 'optimize' in security.parsed_output.detected_keywords and \
               'optimize' in performance.parsed_output.detected_keywords:
                conflicts.append("security-performance")
                print("      ⚠ Detected: Security vs Performance trade-off")

        if conflicts:
            ctx.set("conflicts", conflicts)
            ctx.set("resolution_strategy", "weighted-priority")
            print(f"      → Resolving {len(conflicts)} conflict(s)")
            return "conflict_resolver"
        else:
            print("      ✓ No conflicts detected")
            return "apply_improvements"

    workflow.add_decision("check_conflicts", resolve_conflicts)

    # Conflict resolver step
    workflow.add_step(
        "conflict_resolver",
        "mock-ai",
        "resolve conflicts: {conflicts} using {resolution_strategy}"
    )

    # ═══════════════════════════════════════════════════════════
    # Layer 3: Apply Improvements
    # ═══════════════════════════════════════════════════════════

    workflow.add_step(
        "apply_improvements",
        "mock-ai",
        "apply multi-dimensional improvements to {target}"
    )

    # ═══════════════════════════════════════════════════════════
    # Layer 4: Measure Progress
    # ═══════════════════════════════════════════════════════════

    workflow.add_step(
        "measure",
        "mock-ai",
        "measure code quality across all dimensions for {target}"
    )

    # ═══════════════════════════════════════════════════════════
    # Layer 5: Meta-Learning Sub-Agent
    # ═══════════════════════════════════════════════════════════

    def meta_learning_decision(ctx: WorkflowContext) -> str:
        """Sub-agent: Learn from iteration and decide if we've reached optimum."""
        print("\n    🧠 Meta-Learning Sub-Agent:")

        iteration = ctx.iteration_count
        measure_result = ctx.get_last_result()

        # Simulate quality measurement
        quality_score = 60 + (iteration * 15)  # Improves each iteration
        ctx.set(f"quality_iter_{iteration}", quality_score)

        print(f"      Iteration {iteration}: Quality score = {quality_score}")

        # Check if we've reached Pareto optimality
        if quality_score >= 90:
            print("      ✓ Pareto optimal point reached!")
            ctx.set("optimization_complete", True)
            return "meta_analyze"
        elif iteration >= 3:
            print("      ⚠ Max iterations reached")
            ctx.set("optimization_complete", False)
            return "meta_analyze"
        else:
            print(f"      → Continue optimization (target: 90)")
            return "loop_to_dimensions"

    workflow.add_decision("meta_learning", meta_learning_decision)

    # Loop back to dimension analysis
    def should_optimize_more(ctx: WorkflowContext) -> bool:
        return ctx.iteration_count < 3 and not ctx.get("optimization_complete", False)

    workflow.add_loop("loop_to_dimensions", "dimension_analysis", should_optimize_more)

    # ═══════════════════════════════════════════════════════════
    # Layer 6: Final Meta-Analysis
    # ═══════════════════════════════════════════════════════════

    workflow.add_step(
        "meta_analyze",
        "mock-ai",
        "meta-analyze optimization journey for {target}"
    )

    print("\n  Architecture Layers:")
    print("    Layer 1: Parallel dimension agents (security, performance, architecture)")
    print("    Layer 2: Conflict resolution sub-agent")
    print("    Layer 3: Apply improvements")
    print("    Layer 4: Measure quality")
    print("    Layer 5: Meta-learning sub-agent (Pareto check)")
    print("    Layer 6: Final meta-analysis")
    print("\n  Optimization loop continues until Pareto optimal or max iterations")

    # Execute
    context = orchestrator.execute(workflow, {
        "target": "src/",
        "conflicts": [],
        "resolution_strategy": "none"
    })

    print(f"\n  🎯 Optimization Results:")
    print(f"    Total iterations: {context.iteration_count}")
    print(f"    Dimension agents invoked: {context.iteration_count * 3}")
    print(f"    Sub-agents called: 2 per iteration")
    print(f"    Conflicts resolved: {len(context.get('conflicts', []))}")
    print(f"    Optimization complete: {context.get('optimization_complete', False)}")
    print(f"    Final quality scores:")

    for i in range(context.iteration_count + 1):
        score = context.get(f"quality_iter_{i}")
        if score:
            bar = "█" * int(score / 10)
            print(f"      Iteration {i}: {bar} {score}")

    print("\n  🌟 Hyperspace navigation complete!")
    print("\n✓ Example 7 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    """Run all examples in sequence."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Progressive Orchestration Examples".center(68) + "║")
    print("║" + "  From Simple to Multi-Layered".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    examples = [
        # Simple
        ("SIMPLE", example_1_single_tool),
        ("SIMPLE", example_2_two_step_sequence),
        ("SIMPLE", example_3_three_step_with_decision),
        ("SIMPLE", example_4_four_step_context_passing),

        # Complex
        ("COMPLEX", example_5_parallel_then_sequential),
        ("COMPLEX", example_6_iterative_loop_with_subagents),
        ("COMPLEX", example_7_full_hyperspace_optimization),
    ]

    for category, example in examples:
        try:
            if category == "COMPLEX":
                print("\n" + "▼" * 70)
                print("  ENTERING COMPLEX TERRITORY")
                print("▼" * 70 + "\n")

            example()
        except Exception as e:
            print(f"✗ Example failed: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("\n")
    print("=" * 70)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\n📊 Summary:")
    print("\n  Simple Examples (4):")
    print("    1. Single tool execution")
    print("    2. Two-step sequence")
    print("    3. Three-step with decision")
    print("    4. Four-step with context passing")
    print("\n  Complex Examples (3):")
    print("    5. Multi-layered parallel + sequential")
    print("    6. Iterative loop with sub-agents")
    print("    7. Full hyperspace optimization")
    print("\n🎓 Key Concepts Demonstrated:")
    print("    ✓ Single → Sequential → Parallel execution")
    print("    ✓ Simple routing → Sub-agent decisions → Meta-learning")
    print("    ✓ Context passing → Conflict resolution → Iterative refinement")
    print("    ✓ Linear flow → Loops → Multi-dimensional optimization")
    print("\n🚀 Progression Pattern:")
    print("    Level 1: Execute tools")
    print("    Level 2: Chain tools sequentially")
    print("    Level 3: Add decision points")
    print("    Level 4: Pass context between steps")
    print("    Level 5: Parallel multi-agent coordination")
    print("    Level 6: Iterative refinement with meta-analysis")
    print("    Level 7: Multi-dimensional hyperspace optimization")
    print("\n" + "=" * 70)
    print()


if __name__ == "__main__":
    main()
