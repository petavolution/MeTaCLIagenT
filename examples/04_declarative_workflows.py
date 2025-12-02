#!/usr/bin/env python3
"""
Example 04: Declarative Workflows - YAML/JSON Loading

Demonstrates Meta-Level 1: Declarative workflow transformation.

FROM (Imperative - Python code):
    workflow = Workflow("my-workflow")
    workflow.add_step("step1", "python", "print('hi')")
    workflow.run()

TO (Declarative - YAML/JSON files):
    workflow = WorkflowLoader.from_yaml("my-workflow.yaml")
    workflow.run()

Features:
- Load workflows from YAML/JSON files
- Context variable substitution
- Workflow registry for reusable patterns
- Shareable, versionable workflows

Prerequisites:
- Python 3.8+
- metacli package installed
- pyyaml (pip install pyyaml)

Usage:
    python examples/04_declarative_workflows.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from metacli.meta import WorkflowLoader, get_registry, load_workflow
    META_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Meta layer not available: {e}")
    META_AVAILABLE = False
    sys.exit(1)


def example_1_load_yaml():
    """Example 1: Load workflow from YAML."""
    print("=" * 70)
    print("Example 1: Load Workflow from YAML")
    print("=" * 70)

    yaml_file = "workflows/simple-python.yaml"
    print(f"\n▸ Loading workflow from: {yaml_file}")

    try:
        workflow = WorkflowLoader.from_yaml(yaml_file)

        print(f"✓ Workflow loaded: {workflow.name}")
        print(f"  Steps: {len(workflow.steps)}")

        print("\n▸ Running workflow...")
        result = workflow.run()

        print(f"\n✓ Workflow completed")
        print(f"  Status: {result['status']}")
        print(f"  Duration: {result['duration']:.2f}s")

        workflow.cleanup()

    except FileNotFoundError:
        print(f"⚠ Workflow file not found: {yaml_file}")
        print("  (This is expected if running outside project root)")

    print("\n✓ Example 1 complete\n")


def example_2_context_variables():
    """Example 2: Context variable substitution."""
    print("=" * 70)
    print("Example 2: Context Variable Substitution")
    print("=" * 70)

    yaml_file = "workflows/simple-python.yaml"
    print(f"\n▸ Loading workflow with custom context")

    try:
        # Override context variables
        workflow = WorkflowLoader.from_yaml(
            yaml_file,
            message="Hello from CUSTOM context!"
        )

        print(f"✓ Workflow loaded: {workflow.name}")
        print(f"  Context: {workflow.context}")

        print("\n▸ Running workflow with custom context...")
        result = workflow.run()

        print(f"\n✓ Workflow completed")
        print(f"  Status: {result['status']}")

        workflow.cleanup()

    except FileNotFoundError:
        print(f"⚠ Workflow file not found: {yaml_file}")

    print("\n✓ Example 2 complete\n")


def example_3_iterative_workflow():
    """Example 3: Iterative workflow with loops."""
    print("=" * 70)
    print("Example 3: Iterative Workflow (Loops)")
    print("=" * 70)

    yaml_file = "workflows/iterative-refinement.yaml"
    print(f"\n▸ Loading iterative workflow: {yaml_file}")

    try:
        workflow = WorkflowLoader.from_yaml(yaml_file)

        print(f"✓ Workflow loaded: {workflow.name}")
        print(f"  Description: {workflow.metadata.get('description', 'N/A')}")
        print(f"  Max iterations: {workflow.context.get('max_iterations')}")

        print("\n▸ Running iterative workflow...")
        result = workflow.run()

        print(f"\n✓ Workflow completed")
        print(f"  Status: {result['status']}")
        print(f"  Total steps: {result['total_steps']}")

        # Show iterations
        for step in result['steps']:
            if step['iterations'] > 1:
                print(f"  {step['name']}: {step['iterations']} iterations")

        workflow.cleanup()

    except FileNotFoundError:
        print(f"⚠ Workflow file not found: {yaml_file}")

    print("\n✓ Example 3 complete\n")


def example_4_audit_refactor_cycle():
    """Example 4: Audit-refactor cycle (user's use case)."""
    print("=" * 70)
    print("Example 4: Audit-Refactor Cycle (Your Use Case!)")
    print("=" * 70)

    yaml_file = "workflows/audit-refactor.yaml"
    print(f"\n▸ Loading audit-refactor workflow: {yaml_file}")
    print("  This demonstrates your exact use case:")
    print("  audit → load → refactor → verify → meta-refactor")

    try:
        workflow = WorkflowLoader.from_yaml(
            yaml_file,
            target="src/api.py"  # Custom target
        )

        print(f"\n✓ Workflow loaded: {workflow.name}")
        print(f"  Description: {workflow.metadata.get('description', 'N/A')}")
        print(f"  Target: {workflow.context.get('target')}")
        print(f"  Max iterations: {workflow.context.get('max_iterations')}")

        print("\n▸ Running audit-refactor cycle...")
        result = workflow.run()

        print(f"\n✓ Workflow completed")
        print(f"  Status: {result['status']}")
        print(f"  Steps executed: {result['successful_steps']}/{result['total_steps']}")

        print(f"\n▸ Execution path:")
        for step in result['steps']:
            print(f"  • {step['name']}")

        workflow.cleanup()

    except FileNotFoundError:
        print(f"⚠ Workflow file not found: {yaml_file}")

    print("\n✓ Example 4 complete\n")


def example_5_workflow_registry():
    """Example 5: Workflow registry."""
    print("=" * 70)
    print("Example 5: Workflow Registry")
    print("=" * 70)

    print("\n▸ Creating workflow registry...")
    registry = get_registry()

    # Register workflows
    workflows_to_register = [
        ("simple", "workflows/simple-python.yaml", "Simple Python workflow"),
        ("iterative", "workflows/iterative-refinement.yaml", "Iterative refinement"),
        ("audit", "workflows/audit-refactor.yaml", "Audit-refactor cycle"),
    ]

    print(f"\n▸ Registering {len(workflows_to_register)} workflows...")

    for name, path, description in workflows_to_register:
        try:
            registry.register(
                name=name,
                source=path,
                version="1.0.0",
                description=description,
                tags=["example", "python"]
            )
            print(f"  ✓ Registered: {name}")
        except FileNotFoundError:
            print(f"  ⚠ Skipped: {name} (file not found)")
        except Exception as e:
            print(f"  ⚠ Skipped: {name} ({e})")

    # List workflows
    print(f"\n▸ Listing registered workflows...")
    all_workflows = registry.list()
    print(f"✓ Found {len(all_workflows)} workflows:")
    for w in all_workflows:
        print(f"  • {w['name']} (v{w['version']}): {w['description']}")

    # Search workflows
    print(f"\n▸ Searching for 'audit' workflows...")
    results = registry.search("audit")
    print(f"✓ Found {len(results)} matching workflows:")
    for w in results:
        print(f"  • {w['name']}: {w['description']}")

    # Load by name
    print(f"\n▸ Loading workflow by name...")
    try:
        workflow = registry.get("simple", message="Hello from registry!")
        print(f"✓ Loaded: {workflow.name}")

        print("\n▸ Running workflow from registry...")
        result = workflow.run()
        print(f"✓ Completed: {result['status']}")

        workflow.cleanup()
    except (KeyError, FileNotFoundError) as e:
        print(f"⚠ Could not load workflow: {e}")

    print("\n✓ Example 5 complete\n")


def example_6_convenience_function():
    """Example 6: Convenience load_workflow function."""
    print("=" * 70)
    print("Example 6: Convenience Function")
    print("=" * 70)

    yaml_file = "workflows/simple-python.yaml"
    print(f"\n▸ Using load_workflow() convenience function")
    print(f"  File: {yaml_file}")

    try:
        # Auto-detects format from extension
        workflow = load_workflow(yaml_file, message="Convenient!")

        print(f"✓ Workflow loaded: {workflow.name}")

        print("\n▸ Running workflow...")
        result = workflow.run()

        print(f"✓ Completed: {result['status']}")

        workflow.cleanup()

    except FileNotFoundError:
        print(f"⚠ Workflow file not found: {yaml_file}")

    print("\n✓ Example 6 complete\n")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  MetaCLI Declarative Workflows - YAML/JSON Loading".center(68) + "║")
    print("║" + "  Meta-Level 1: From Code to Configuration".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    if not META_AVAILABLE:
        print("❌ Meta layer not available")
        print("   Install: pip install pyyaml")
        return

    try:
        # Run all examples
        example_1_load_yaml()
        time.sleep(0.5)

        example_2_context_variables()
        time.sleep(0.5)

        example_3_iterative_workflow()
        time.sleep(0.5)

        example_4_audit_refactor_cycle()
        time.sleep(0.5)

        example_5_workflow_registry()
        time.sleep(0.5)

        example_6_convenience_function()

        print("=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nDeclarative workflow features demonstrated:")
        print("  ✓ Load workflows from YAML files")
        print("  ✓ Context variable substitution")
        print("  ✓ Iterative workflows with loops")
        print("  ✓ Audit-refactor cycle (your use case)")
        print("  ✓ Workflow registry for reusable patterns")
        print("  ✓ Convenience functions")
        print("\nMeta-Level Transformation:")
        print("  FROM: Python code (imperative)")
        print("  TO:   YAML/JSON files (declarative)")
        print("\nBenefits:")
        print("  • Shareable workflows (just share YAML)")
        print("  • Version controllable (git track)")
        print("  • Non-programmers can create workflows")
        print("  • Composable and reusable")
        print("  • Foundation for AI-generated workflows")
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
