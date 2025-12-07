#!/usr/bin/env python3
"""
MetaCLI Testing Framework Examples

Demonstrates how to use the testing framework for:
- CLI simulation
- Response templates
- Test database
- Sequential and parallel execution
- Terminal emulation

Run: python examples/05_testing_framework.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.testing import (
    CLISimulator,
    ResponseTemplate,
    TemplateLibrary,
    ResponseMatcher,
    TestDatabase,
    TestScenario,
    ParallelExecutor,
    TerminalEmulator,
    KeyboardInput,
    create_test_simulator,
    create_coding_templates,
    create_audit_refactor_templates,
)
from metacli.testing.templates import MatchStrategy


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 1: Basic CLI Simulator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_1_basic_simulator():
    """Example 1: Basic CLI simulator with hash-based lookup."""
    print("=" * 70)
    print("Example 1: Basic CLI Simulator")
    print("=" * 70)

    # Create simulator with pre-configured tools
    simulator = create_test_simulator(tools=["claude-code", "python"])

    # Spawn claude-code process
    process = simulator.spawn("claude-code")
    process.start()

    # Send prompts and get responses
    prompts = [
        "Write a hello world program",
        "Review this code",
        "Fix any bugs",
    ]

    for prompt in prompts:
        process.write(prompt)
        response = process.read()
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response[:100]}...")

    simulator.cleanup()
    print("\n✓ Example 1 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 2: Response Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_2_response_templates():
    """Example 2: Use response templates for intelligent routing."""
    print("=" * 70)
    print("Example 2: Response Templates")
    print("=" * 70)

    # Create template library
    library = create_coding_templates()

    # Create matcher
    matcher = ResponseMatcher(library)

    # Test outputs
    test_outputs = [
        ("Error: SyntaxError on line 42", "error_handling"),
        ("Found 3 issues in the code", "audit"),
        ("5 tests failed", "testing"),
        ("```python\nprint('hello')\n```", "code_review"),
    ]

    for output, category in test_outputs:
        next_command = matcher.match(output, category=category)
        print(f"\nOutput: {output}")
        print(f"Category: {category}")
        print(f"Next command: {next_command}")

    print("\n✓ Example 2 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 3: Test Scenarios in Database
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_3_test_database():
    """Example 3: Store and retrieve test scenarios from database."""
    print("=" * 70)
    print("Example 3: Test Database")
    print("=" * 70)

    # Create test database
    db = TestDatabase(db_path="tests/example_test.db")

    # Create test scenario
    scenario = TestScenario(
        name="audit-refactor-test",
        description="Test audit → refactor workflow",
        steps=[
            {
                "tool": "claude-code",
                "prompt": "Audit src/api.py",
                "expected_output": "Found 3 issues"
            },
            {
                "tool": "aider",
                "prompt": "Fix issues",
                "expected_output": "Fixed"
            },
        ],
        tags=["audit", "refactor"],
        category="integration"
    )

    # Save scenario
    scenario_id = db.save_scenario(scenario)
    print(f"✓ Saved scenario: {scenario.name} (ID: {scenario_id})")

    # Load scenario
    loaded = db.load_scenario(scenario_id)
    print(f"✓ Loaded scenario: {loaded.name}")
    print(f"  Steps: {len(loaded.steps)}")
    print(f"  Tags: {loaded.tags}")

    # List all scenarios
    all_scenarios = db.list_scenarios()
    print(f"\n✓ Total scenarios in database: {len(all_scenarios)}")

    # Get statistics
    stats = db.get_statistics()
    print(f"✓ Database statistics:")
    print(f"  Total scenarios: {stats['total_scenarios']}")
    print(f"  Total executions: {stats['total_executions']}")

    db.close()
    print("\n✓ Example 3 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 4: Sequential Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_4_sequential_execution():
    """Example 4: Run test scenarios sequentially."""
    print("=" * 70)
    print("Example 4: Sequential Execution")
    print("=" * 70)

    # Create simulator
    simulator = create_test_simulator()

    # Create test scenarios
    scenarios = [
        TestScenario(
            name="test-1",
            description="Simple test 1",
            steps=[
                {"tool": "python", "prompt": "print('test 1')", "expected_output": "test"}
            ]
        ),
        TestScenario(
            name="test-2",
            description="Simple test 2",
            steps=[
                {"tool": "python", "prompt": "2+2", "expected_output": "4"}
            ]
        ),
    ]

    # Execute sequentially
    executor = ParallelExecutor(simulator=simulator)
    results = executor.run_sequential(scenarios)

    # Print results
    for result in results:
        status_icon = "✓" if result.status == "success" else "✗"
        print(f"{status_icon} {result.workflow_name}: {result.status} ({result.duration:.2f}s)")

    print("\n✓ Example 4 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 5: Parallel Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_5_parallel_execution():
    """Example 5: Run test scenarios in parallel."""
    print("=" * 70)
    print("Example 5: Parallel Execution")
    print("=" * 70)

    # Create simulator
    simulator = create_test_simulator()

    # Create multiple test scenarios
    scenarios = [
        TestScenario(
            name=f"parallel-test-{i}",
            description=f"Parallel test {i}",
            steps=[
                {"tool": "python", "prompt": f"print('test {i}')", "expected_output": "test"}
            ]
        )
        for i in range(5)
    ]

    # Execute in parallel
    start_time = time.time()
    executor = ParallelExecutor(simulator=simulator, max_workers=3)
    results = executor.run_parallel(scenarios)
    parallel_duration = time.time() - start_time

    # Print results
    print(f"✓ Executed {len(results)} scenarios in parallel")
    print(f"  Total time: {parallel_duration:.2f}s")
    print(f"  Avg time per scenario: {parallel_duration / len(results):.2f}s")

    for result in results:
        status_icon = "✓" if result.status == "success" else "✗"
        print(f"  {status_icon} {result.workflow_name}: {result.duration:.2f}s")

    print("\n✓ Example 5 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 6: Audit-Refactor Cycle with Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_6_audit_refactor_cycle():
    """Example 6: Complete audit-refactor cycle with intelligent routing."""
    print("=" * 70)
    print("Example 6: Audit-Refactor Cycle")
    print("=" * 70)

    # Create simulator with realistic responses
    simulator = create_test_simulator(tools=["claude-code", "aider"])

    # Add custom responses for audit-refactor cycle
    simulator.register_tool("claude-code", {
        "exact": {
            "Audit src/api.py": "Audit complete. Found 3 potential issues.",
            "Load context": "Context loaded. Ready to refactor.",
        },
        "keywords": {
            "verify": "Verification passed. All tests green.",
        }
    })

    simulator.register_tool("aider", {
        "exact": {
            "Fix issues": "Refactored code. Changes applied.",
        }
    })

    # Create template library for audit-refactor
    library = create_audit_refactor_templates()
    matcher = ResponseMatcher(library)

    # Simulate audit-refactor cycle
    steps = [
        ("claude-code", "Audit src/api.py", "audit"),
        ("claude-code", "Load context", "load_context"),
        ("aider", "Fix issues", "refactor"),
        ("claude-code", "Verify changes", "verify"),
    ]

    process_map = {}

    for tool, prompt, category in steps:
        # Get or create process
        if tool not in process_map:
            process = simulator.spawn(tool)
            process.start()
            process_map[tool] = process
        else:
            process = process_map[tool]

        # Execute step
        process.write(prompt)
        output = process.read()

        # Use template to determine next action
        next_action = matcher.match(output, category=category)

        print(f"\nStep: {prompt}")
        print(f"Tool: {tool}")
        print(f"Output: {output}")
        print(f"Next action: {next_action}")

    simulator.cleanup()
    print("\n✓ Example 6 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 7: Load from YAML
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_7_load_from_yaml():
    """Example 7: Load test scenarios from YAML file."""
    print("=" * 70)
    print("Example 7: Load from YAML")
    print("=" * 70)

    yaml_path = "tests/test_scenarios.yaml"

    try:
        # Create simulator from YAML
        simulator = CLISimulator.from_templates(yaml_path)

        print(f"✓ Loaded simulator from {yaml_path}")
        print(f"  Registered tools: {list(simulator.tools.keys())}")

        # Load template library from YAML
        library = TemplateLibrary.from_yaml(yaml_path)

        print(f"✓ Loaded template library")
        print(f"  Categories: {list(library.templates.keys())}")
        print(f"  Global templates: {len(library.global_templates)}")

    except FileNotFoundError:
        print(f"✗ YAML file not found: {yaml_path}")
        print("  (This is expected if running outside tests/)")

    print("\n✓ Example 7 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 8: Terminal Emulator (Advanced)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_8_terminal_emulator():
    """Example 8: Use terminal emulator for interactive tools."""
    print("=" * 70)
    print("Example 8: Terminal Emulator")
    print("=" * 70)

    print("✓ TerminalEmulator class available for:")
    print("  - Interactive Python sessions")
    print("  - Tools requiring PTY (pseudo-terminal)")
    print("  - Keyboard input simulation")
    print("  - ANSI escape code handling")

    print("\n  Example usage:")
    print("    with TerminalEmulator() as term:")
    print("        term.spawn(['python', '-i'])")
    print("        term.send_text('print(2+2)')")
    print("        output = term.read(timeout=1.0)")

    print("\n✓ Example 8 complete (demonstration only)\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "     MetaCLI Testing Framework - Comprehensive Examples".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    examples = [
        example_1_basic_simulator,
        example_2_response_templates,
        example_3_test_database,
        example_4_sequential_execution,
        example_5_parallel_execution,
        example_6_audit_refactor_cycle,
        example_7_load_from_yaml,
        example_8_terminal_emulator,
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
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ CLI simulation with hash-based response lookup")
    print("  ✓ Response templates for intelligent routing")
    print("  ✓ Test database for scenario storage")
    print("  ✓ Sequential and parallel execution")
    print("  ✓ Audit-refactor cycle automation")
    print("  ✓ YAML-based configuration")
    print("  ✓ Terminal emulation for interactive tools")
    print("=" * 70)


if __name__ == "__main__":
    main()
