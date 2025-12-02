#!/usr/bin/env python3
"""
Example 03: Advanced Workflows - Conditionals, Loops, Sub-Agents

Demonstrates advanced orchestration features:
- Conditional execution (if/else)
- Loops (repeat until condition)
- Sub-agent delegation
- Dynamic prompt generation
- Pre-built workflow patterns
- Iterative refinement

Prerequisites:
- Python 3.8+
- metacli package installed

Usage:
    python examples/03_advanced_workflows.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.core import (
    Workflow,
    DecisionEngine,
    PromptTemplate,
    has_errors_decision,
    test_pass_decision,
    max_iterations_decision,
    patterns,
)


def example_1_conditional_execution():
    """Example 1: Conditional execution based on output."""
    print("=" * 70)
    print("Example 1: Conditional Execution")
    print("=" * 70)

    workflow = Workflow("conditional-test", auto_save=False)

    # Step 1: Generate code
    workflow.add_step(
        name="generate",
        tool_name="python",
        prompt="print('x = 42')",
        timeout=5.0,
    )

    # Step 2: Only execute if previous step had code
    workflow.add_step(
        name="validate",
        tool_name="python",
        prompt="print('Code validated')",
        condition="has_code",  # Built-in condition
        timeout=5.0,
    )

    print("\n▸ Running conditional workflow...")
    result = workflow.run()

    print(f"\n✓ Workflow completed")
    print(f"  Status: {result['status']}")
    print(f"  Steps executed: {result['successful_steps']}/{result['total_steps']}")

    workflow.cleanup()
    print("\n✓ Example 1 complete\n")


def example_2_loop_with_max_iterations():
    """Example 2: Loop until max iterations."""
    print("=" * 70)
    print("Example 2: Loop with Max Iterations")
    print("=" * 70)

    workflow = Workflow("loop-test", auto_save=False)

    # Step that loops back to itself
    workflow.add_step(
        name="iterate",
        tool_name="python",
        prompt=PromptTemplate("print('Iteration {{iteration}}')"),
        decision=max_iterations_decision(3),  # Loop max 3 times
        loop_back_to="iterate",  # Loop to self
        timeout=5.0,
    )

    print("\n▸ Running loop workflow...")
    result = workflow.run()

    print(f"\n✓ Workflow completed")
    print(f"  Status: {result['status']}")
    print(f"  Iterations: {result['steps'][0]['iterations']}")

    workflow.cleanup()
    print("\n✓ Example 2 complete\n")


def example_3_dynamic_prompts():
    """Example 3: Dynamic prompt generation."""
    print("=" * 70)
    print("Example 3: Dynamic Prompt Generation")
    print("=" * 70)

    workflow = Workflow("dynamic-prompts", auto_save=False)

    # Initialize context
    workflow.context["feature"] = "user authentication"
    workflow.context["max_attempts"] = 2

    # Step with template
    workflow.add_step(
        name="implement",
        tool_name="python",
        prompt=PromptTemplate(
            "print('Implementing {{feature}} - attempt {{iteration}}/{{max_attempts}}')"
        ),
        decision=max_iterations_decision(2),
        loop_to="implement",
        timeout=5.0,
    )

    print("\n▸ Running workflow with dynamic prompts...")
    result = workflow.run()

    print(f"\n✓ Workflow completed")
    print(f"  Status: {result['status']}")

    for step in result['steps']:
        print(f"  Step {step['name']}: {step['iterations']} iterations")

    workflow.cleanup()
    print("\n✓ Example 3 complete\n")


def example_4_pre_built_pattern():
    """Example 4: Use pre-built workflow pattern."""
    print("=" * 70)
    print("Example 4: Pre-built Workflow Pattern")
    print("=" * 70)

    # Get iterative refinement pattern
    pattern = patterns.iterative_refinement_pattern(
        initial_task="print('Initial version')",
        tool="python",
        refinement_prompt="print('Refined version')",
        iterations=2,
    )

    print(f"\n▸ Using pattern: {pattern['name']}")
    print(f"  Description: {pattern['description']}")
    print(f"  Steps: {len(pattern['steps'])}")

    workflow = Workflow.from_pattern(pattern)
    workflow.auto_save = False

    print("\n▸ Running pattern workflow...")
    result = workflow.run()

    print(f"\n✓ Workflow completed")
    print(f"  Status: {result['status']}")
    print(f"  Steps: {result['successful_steps']}/{result['total_steps']}")

    workflow.cleanup()
    print("\n✓ Example 4 complete\n")


def example_5_list_patterns():
    """Example 5: List available patterns."""
    print("=" * 70)
    print("Example 5: Available Workflow Patterns")
    print("=" * 70)

    available_patterns = patterns.list_patterns()

    print(f"\n▸ {len(available_patterns)} patterns available:\n")

    for pattern_name in available_patterns:
        print(f"  • {pattern_name}")

    print("\n▸ Pattern details:")

    # Get audit_refactor pattern
    pattern = patterns.get_pattern(
        "audit_refactor",
        target="example.py",
        max_iterations=2
    )

    if pattern:
        print(f"\n  Name: {pattern['name']}")
        print(f"  Description: {pattern['description']}")
        print(f"  Steps: {len(pattern['steps'])}")
        print(f"  Step names:")
        for step in pattern['steps']:
            print(f"    - {step['name']}: {step['tool']}")

    print("\n✓ Example 5 complete\n")


def example_6_custom_decision_function():
    """Example 6: Custom decision function."""
    print("=" * 70)
    print("Example 6: Custom Decision Function")
    print("=" * 70)

    def custom_decision(output: str, context: dict):
        """Custom decision: Stop after 2 iterations."""
        from metacli.core import Decision, DecisionType

        iteration = context.get("iteration", 0) + 1
        context["iteration"] = iteration

        if iteration >= 2:
            return Decision(
                type=DecisionType.STOP,
                reason=f"Custom stop at iteration {iteration}",
                context=context
            )
        else:
            return Decision(
                type=DecisionType.CONTINUE,
                reason=f"Continue to iteration {iteration + 1}",
                context=context
            )

    workflow = Workflow("custom-decision", auto_save=False)

    workflow.add_step(
        name="custom_loop",
        tool_name="python",
        prompt="print('Custom decision loop')",
        decision=custom_decision,
        loop_to="custom_loop",
        timeout=5.0,
    )

    print("\n▸ Running workflow with custom decision...")
    result = workflow.run()

    print(f"\n✓ Workflow completed")
    print(f"  Status: {result['status']}")

    if result['steps']:
        decision = result['steps'][0].get('decision', {})
        print(f"  Final decision: {decision.get('reason', 'N/A')}")

    workflow.cleanup()
    print("\n✓ Example 6 complete\n")


def example_7_complex_workflow():
    """Example 7: Complex workflow with multiple patterns."""
    print("=" * 70)
    print("Example 7: Complex Multi-Pattern Workflow")
    print("=" * 70)

    workflow = Workflow("complex", auto_save=False)

    # Step 1: Initial generation
    workflow.add_step(
        name="generate",
        tool_name="python",
        prompt="print('def hello(): return \"Hello\"')",
        timeout=5.0,
    )

    # Step 2: Validate (conditional)
    workflow.add_step(
        name="validate",
        tool_name="python",
        prompt="print('Validation passed')",
        condition="has_code",
        timeout=5.0,
    )

    # Step 3: Refine (with loop)
    workflow.add_step(
        name="refine",
        tool_name="python",
        prompt=PromptTemplate("print('Refinement {{iteration}}/2')"),
        use_previous=True,
        decision=max_iterations_decision(2),
        loop_to="refine",
        timeout=5.0,
    )

    # Step 4: Final check
    workflow.add_step(
        name="final",
        tool_name="python",
        prompt="print('Complete!')",
        timeout=5.0,
    )

    print("\n▸ Running complex workflow...")
    print("  Steps: generate → validate → refine (loop) → final")

    result = workflow.run()

    print(f"\n✓ Workflow completed")
    print(f"  Status: {result['status']}")
    print(f"  Total steps: {result['total_steps']}")
    print(f"  Steps executed: {result['successful_steps']}")

    print(f"\n▸ Execution path:")
    for step in result['steps']:
        iterations = step['iterations']
        iter_str = f" ({iterations}x)" if iterations > 1 else ""
        print(f"  • {step['name']}: {step['tool_name']}{iter_str}")

    workflow.cleanup()
    print("\n✓ Example 7 complete\n")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  MetaCLI Advanced Workflows - Conditionals, Loops, Patterns".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    try:
        # Run all examples
        example_1_conditional_execution()
        time.sleep(0.5)

        example_2_loop_with_max_iterations()
        time.sleep(0.5)

        example_3_dynamic_prompts()
        time.sleep(0.5)

        example_4_pre_built_pattern()
        time.sleep(0.5)

        example_5_list_patterns()
        time.sleep(0.5)

        example_6_custom_decision_function()
        time.sleep(0.5)

        example_7_complex_workflow()

        print("=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nAdvanced orchestration features demonstrated:")
        print("  ✓ Conditional execution (if/else)")
        print("  ✓ Loops with max iterations")
        print("  ✓ Dynamic prompt generation")
        print("  ✓ Pre-built workflow patterns")
        print("  ✓ Custom decision functions")
        print("  ✓ Complex multi-pattern workflows")
        print("\nYour use case: audit → load → refactor → continue → meta-refactor")
        print("  → Use patterns.audit_refactor_cycle() for this!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
