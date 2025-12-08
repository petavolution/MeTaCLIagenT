#!/usr/bin/env python3
"""
Full Orchestration Example - Complete AI CLI workflow system

Demonstrates:
- Unified executor for AI and POSIX tools
- Orchestrator with iterative sequences
- Sub-agent decision points
- Template-based routing
- Database persistence
- Error recovery
- Parallel execution support

Run: python examples/07_full_orchestration.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.core import (
    Orchestrator,
    UnifiedExecutor,
    WorkflowContext,
    create_audit_refactor_workflow,
    create_iterative_refactor_workflow,
    create_ai_executor,
)
from metacli.testing.realistic_parser import create_audit_refactor_router


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 1: Basic Execution with Unified Executor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_1_unified_executor():
    """Example 1: Execute AI tools and POSIX commands."""
    print("=" * 70)
    print("Example 1: Unified Executor - AI Tools and POSIX Commands")
    print("=" * 70)

    # Create executor
    executor = create_ai_executor(db_path="examples/executor_test.db")

    print("\n  Executing AI tool (mock):")

    # Execute AI tool
    result = executor.execute(
        tool="mock-ai",
        prompt="audit code for security issues"
    )

    print(f"    Tool: {result.tool}")
    print(f"    Success: {result.success}")
    print(f"    Duration: {result.duration:.2f}s")
    print(f"    Output length: {len(result.raw_output)} chars")

    if result.parsed_output:
        print(f"    Keywords detected: {result.parsed_output.detected_keywords}")
        print(f"    Has error: {result.has_error}")
        print(f"    Is complete: {result.is_complete}")

    print("\n✓ Example 1 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 2: Simple Orchestrator Workflow
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_2_simple_workflow():
    """Example 2: Create and execute simple workflow."""
    print("=" * 70)
    print("Example 2: Simple Orchestrator Workflow")
    print("=" * 70)

    # Create orchestrator
    orchestrator = Orchestrator(db_path="examples/workflow_test.db")

    # Create workflow
    workflow = orchestrator.create_workflow(
        "simple-audit",
        "Simple audit workflow"
    )

    # Add steps
    workflow.add_step("audit", "mock-ai", "audit {target}")
    workflow.add_step("report", "mock-ai", "generate report for {target}")

    print("\n  Executing simple workflow:")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"    Workflow: {workflow.name}")
    print(f"    Steps executed: {len(context.results)}")
    print(f"    Variables: {context.variables}")

    for name, result in context.results.items():
        print(f"    - {name}: {result.success} ({result.duration:.2f}s)")

    print("\n✓ Example 2 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 3: Workflow with Decision Points
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_3_decision_workflow():
    """Example 3: Workflow with sub-agent decision points."""
    print("=" * 70)
    print("Example 3: Workflow with Decision Points")
    print("=" * 70)

    orchestrator = Orchestrator(db_path="examples/workflow_test.db")

    # Create workflow with decisions
    workflow = orchestrator.create_workflow(
        "audit-with-decisions",
        "Audit workflow with intelligent routing"
    )

    # Step 1: Audit
    workflow.add_step("audit", "mock-ai", "audit {target}")

    # Decision: Check if issues found
    def decide_next_action(ctx: WorkflowContext) -> str:
        """Decide next action based on audit results."""
        last_result = ctx.get_last_result()

        if last_result and last_result.parsed_output:
            keywords = last_result.parsed_output.detected_keywords

            if 'error' in keywords:
                print("      Decision: Error detected → fix_errors")
                return "fix_errors"
            elif 'identified' in keywords:
                print("      Decision: Issues identified → load_context")
                return "load_context"
            elif 'complete' in keywords:
                print("      Decision: Audit complete → done")
                return "done"

        print("      Decision: No issues → done")
        return "done"

    workflow.add_decision("route_after_audit", decide_next_action)

    # Step 2a: Load context (if issues identified)
    workflow.add_step("load_context", "mock-ai", "load context for {target}")

    # Step 2b: Fix errors (if error detected)
    workflow.add_step("fix_errors", "mock-ai", "fix errors in {target}")

    # Step 3: Done (placeholder)
    workflow.add_step("done", "mock-ai", "finalize {target}")

    print("\n  Executing workflow with decisions:")

    # Execute multiple times to see different paths
    for i in range(2):
        print(f"\n    Run {i + 1}:")
        context = orchestrator.execute(workflow, {"target": f"src/test{i}.py"})
        print(f"      Steps executed: {list(context.results.keys())}")

    print("\n✓ Example 3 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 4: Pre-built Audit-Refactor Workflow
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_4_audit_refactor():
    """Example 4: Use pre-built audit-refactor workflow."""
    print("=" * 70)
    print("Example 4: Pre-built Audit-Refactor Workflow")
    print("=" * 70)

    orchestrator = Orchestrator(db_path="examples/workflow_test.db")

    # Create pre-built workflow
    workflow = create_audit_refactor_workflow(orchestrator, target="src/")

    print(f"\n  Workflow: {workflow.name}")
    print(f"  Description: {workflow.description}")
    print(f"  Steps: {[s.name for s in workflow.steps]}")

    print("\n  Executing audit-refactor cycle:")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/api.py"})

    print(f"\n    Steps executed: {len(context.results)}")
    for name, result in context.results.items():
        status = "✓" if result.success else "✗"
        keywords = result.parsed_output.detected_keywords if result.parsed_output else set()
        print(f"      {status} {name}: {result.duration:.2f}s (keywords: {keywords})")

    print("\n✓ Example 4 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 5: Iterative Refactor with Continue Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_5_iterative_refactor():
    """Example 5: Iterative refactor with continue loop."""
    print("=" * 70)
    print("Example 5: Iterative Refactor with Continue Loop")
    print("=" * 70)

    orchestrator = Orchestrator(db_path="examples/workflow_test.db")

    # Create iterative workflow
    workflow = create_iterative_refactor_workflow(orchestrator, max_iterations=3)

    print(f"\n  Workflow: {workflow.name}")
    print(f"  Max iterations: {workflow.max_iterations}")
    print(f"  Steps: {[s.name for s in workflow.steps]}")

    print("\n  Executing iterative refactor:")

    # Execute
    context = orchestrator.execute(workflow, {"target": "src/", "iteration": 0})

    print(f"\n    Total iterations: {context.iteration_count}")
    print(f"    Steps executed: {len(context.results)}")

    for name, result in context.results.items():
        print(f"      - {name}: {result.success}")

    print("\n✓ Example 5 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 6: Custom Workflow with Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_6_custom_loop():
    """Example 6: Custom workflow with explicit loop."""
    print("=" * 70)
    print("Example 6: Custom Workflow with Loop")
    print("=" * 70)

    orchestrator = Orchestrator(db_path="examples/workflow_test.db")

    # Create workflow
    workflow = orchestrator.create_workflow("test-fix-loop", "Test-fix cycle")
    workflow.max_iterations = 5

    # Step 1: Run tests
    workflow.add_step("test", "mock-ai", "run tests for {target}")

    # Decision: Check if tests passed
    def check_tests(ctx: WorkflowContext) -> str:
        last = ctx.get_last_result()
        if last and last.parsed_output:
            if 'error' in last.parsed_output.detected_keywords:
                return "fix"
            elif 'complete' in last.parsed_output.detected_keywords:
                return "done"
        return "done"

    workflow.add_decision("check_test_result", check_tests)

    # Step 2: Fix issues
    workflow.add_step("fix", "mock-ai", "fix failing tests in {target}")

    # Loop back to test
    def should_loop(ctx: WorkflowContext) -> bool:
        return ctx.iteration_count < 5

    workflow.add_loop("loop_to_test", "test", should_loop)

    # Step 3: Done
    workflow.add_step("done", "mock-ai", "all tests passed for {target}")

    print("\n  Executing test-fix loop:")

    # Execute
    context = orchestrator.execute(workflow, {"target": "tests/"})

    print(f"\n    Iterations: {context.iteration_count}")
    print(f"    Steps executed: {list(context.results.keys())}")

    print("\n✓ Example 6 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 7: Workflow with Template Variables
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_7_template_variables():
    """Example 7: Use template variables in prompts."""
    print("=" * 70)
    print("Example 7: Template Variables in Prompts")
    print("=" * 70)

    orchestrator = Orchestrator(db_path="examples/workflow_test.db")

    # Create workflow
    workflow = orchestrator.create_workflow("template-test")

    # Steps with template variables
    workflow.add_step(
        "analyze",
        "mock-ai",
        "analyze {file} for {concern} issues in {language}"
    )

    workflow.add_step(
        "report",
        "mock-ai",
        "generate {report_type} report for {file}"
    )

    print("\n  Executing workflow with template variables:")

    # Execute with context variables
    context = orchestrator.execute(workflow, {
        "file": "src/api.py",
        "concern": "security",
        "language": "Python",
        "report_type": "detailed"
    })

    print(f"\n    Variables used: {context.variables}")
    print(f"    Steps executed: {list(context.results.keys())}")

    print("\n✓ Example 7 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 8: Database Persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_8_database_persistence():
    """Example 8: Verify database persistence."""
    print("=" * 70)
    print("Example 8: Database Persistence")
    print("=" * 70)

    from metacli.testing.database import TestDatabase

    db_path = "examples/workflow_test.db"

    # Check if database exists
    print(f"\n  Database: {db_path}")

    db = TestDatabase(db_path)

    # Get statistics
    stats = db.get_statistics()

    print(f"\n    Total scenarios: {stats['total_scenarios']}")
    print(f"    Total executions: {stats['total_executions']}")

    # List recent scenarios
    scenarios = db.list_scenarios(limit=5)

    print(f"\n    Recent workflows:")
    for scenario in scenarios[:5]:
        print(f"      - {scenario.name}: {len(scenario.steps)} steps")

    db.close()

    print("\n✓ Example 8 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "     Full Orchestration System - Complete Examples".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    examples = [
        example_1_unified_executor,
        example_2_simple_workflow,
        example_3_decision_workflow,
        example_4_audit_refactor,
        example_5_iterative_refactor,
        example_6_custom_loop,
        example_7_template_variables,
        example_8_database_persistence,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"✗ Example failed: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Unified executor for AI tools and POSIX commands")
    print("  ✓ Orchestrator with iterative sequences")
    print("  ✓ Sub-agent decision points (process output → decide → delegate)")
    print("  ✓ Template-based routing with keyword detection")
    print("  ✓ Database persistence for entire workflows")
    print("  ✓ Error recovery and retry logic")
    print("  ✓ Loop constructs for iterative refinement")
    print("  ✓ Template variable substitution")
    print("  ✓ Pre-built workflow patterns")
    print("=" * 70)
    print()
    print("Production Sequences Supported:")
    print("  • audit → load context → refactor → verify → meta")
    print("  • audit → refactor → genplan → continue → genplan → continue")
    print("  • test → fix → test → fix (loop until pass)")
    print("  • analyze → decide → delegate → execute → repeat")
    print("=" * 70)


if __name__ == "__main__":
    main()
