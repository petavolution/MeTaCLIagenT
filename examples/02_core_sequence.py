#!/usr/bin/env python3
"""
Example 02: Core Layer - CLI Orchestration

Demonstrates Layer 1 (Core) functionality:
- CLISequence for orchestrating tools
- OutputParser for extracting structured data
- Persistence for auto-saving results
- Built on clean kernel.Process layer

Prerequisites:
- Python 3.8+
- metacli package installed

Usage:
    python examples/02_core_sequence.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.core import (
    CLISequence,
    OutputParser,
    Persistence,
    get_persistence,
    run_sequence,
    quick_chain,
)


def example_1_basic_sequence():
    """Example 1: Basic sequence with Python"""
    print("=" * 70)
    print("Example 1: Basic Sequence")
    print("=" * 70)

    seq = CLISequence("python-hello", auto_save=False)

    # Add a simple Python step
    seq.add_step("python", "print('Hello from MetaCLI Core!')", timeout=5.0)

    print("\n▸ Running sequence...")
    result = seq.run()

    print(f"\n✓ Sequence completed")
    print(f"  Status: {result['status']}")
    print(f"  Duration: {result['duration']:.2f}s")
    print(f"  Steps: {result['successful_steps']}/{result['total_steps']}")

    if result['final_output']:
        print(f"\n▸ Output:")
        print(result['final_output'][:200])

    seq.cleanup()
    print("\n✓ Example 1 complete\n")


def example_2_output_parsing():
    """Example 2: Output parsing"""
    print("=" * 70)
    print("Example 2: Output Parsing")
    print("=" * 70)

    # Simulate tool output with code blocks
    sample_output = """
    Here's the code:

    ```python
    def greet(name):
        return f"Hello, {name}!"

    # Test
    print(greet("World"))
    ```

    Modified files: ./test.py, ./utils.py

    5 tests passed, 0 failed
    """

    parser = OutputParser()

    print("\n▸ Parsing sample output...")

    # Extract code blocks
    code_blocks = parser.extract_code_blocks(sample_output)
    print(f"\n✓ Code blocks found: {len(code_blocks)}")
    for block in code_blocks:
        print(f"  - Language: {block.language}")
        print(f"    Lines: {len(block.code.split(chr(10)))}")

    # Extract file paths
    files = parser.extract_file_paths(sample_output)
    print(f"\n✓ File paths found: {len(files)}")
    for f in files:
        print(f"  - {f}")

    # Parse test results
    test_results = parser.parse_test_results(sample_output)
    print(f"\n✓ Test results:")
    print(f"  - Passed: {test_results['passed']}")
    print(f"  - Failed: {test_results['failed']}")

    # Check for errors
    has_errors = parser.has_errors(sample_output)
    print(f"\n✓ Has errors: {has_errors}")

    # Extract JSON (if any)
    json_data = parser.extract_json(sample_output)
    print(f"\n✓ JSON data: {json_data}")

    print("\n✓ Example 2 complete\n")


def example_3_persistence():
    """Example 3: Persistence layer"""
    print("=" * 70)
    print("Example 3: Persistence")
    print("=" * 70)

    persistence = get_persistence()

    # Create a mock sequence result
    seq_id = f"test-seq-{int(time.time())}"
    mock_result = {
        'id': seq_id,
        'name': 'test-sequence',
        'status': 'completed',
        'started_at': time.time(),
        'completed_at': time.time() + 10,
        'total_steps': 2,
        'successful_steps': 2,
        'duration': 10.5,
        'error_message': None,
        'tags': ['test', 'demo'],
        'steps': [
            {
                'tool_name': 'python',
                'prompt': 'print("step 1")',
                'raw_output': 'step 1\n',
                'success': True,
                'duration': 5.0,
                'parsed_data': {},
                'error_message': None,
                'timestamp': time.time(),
                'status': 'success',
            },
            {
                'tool_name': 'python',
                'prompt': 'print("step 2")',
                'raw_output': 'step 2\n',
                'success': True,
                'duration': 5.5,
                'parsed_data': {},
                'error_message': None,
                'timestamp': time.time() + 5,
                'status': 'success',
            },
        ],
        'final_output': 'step 2\n',
    }

    print("\n▸ Saving sequence...")
    saved_id = persistence.save(mock_result)
    print(f"✓ Saved with ID: {saved_id}")

    print("\n▸ Loading sequence...")
    loaded = persistence.load(saved_id)
    print(f"✓ Loaded: {loaded['name']}")
    print(f"  Status: {loaded['status']}")
    print(f"  Steps: {len(loaded['steps'])}")

    print("\n▸ Querying sequences...")
    recent = persistence.query(status="completed", limit=5)
    print(f"✓ Found {len(recent)} completed sequences")
    for seq in recent[:3]:
        print(f"  - {seq['id']}: {seq['name']} ({seq['total_steps']} steps)")

    print("\n▸ Searching outputs...")
    results = persistence.search("step", limit=5)
    print(f"✓ Found {len(results)} matching steps")
    for result in results[:3]:
        print(f"  - {result['tool_name']}: {result['prompt'][:40]}...")

    print("\n▸ Statistics...")
    stats = persistence.stats()
    print(f"✓ Total sequences: {stats['total_sequences']}")
    print(f"✓ Total steps: {stats['total_steps']}")
    print(f"✓ Success rate: {stats['success_rate']}%")
    if stats['tools_used']:
        print(f"✓ Tools used:")
        for tool, count in list(stats['tools_used'].items())[:3]:
            print(f"  - {tool}: {count}")

    print("\n✓ Example 3 complete\n")


def example_4_convenience_functions():
    """Example 4: Convenience functions"""
    print("=" * 70)
    print("Example 4: Convenience Functions")
    print("=" * 70)

    print("\n▸ Using run_sequence() helper...")

    result = run_sequence([
        ("python", "print('Step 1')"),
        ("python", "print('Step 2')"),
    ], name="quick-test")

    print(f"✓ Sequence completed: {result['status']}")
    print(f"  Duration: {result['duration']:.2f}s")

    print("\n✓ Example 4 complete\n")


def example_5_error_handling():
    """Example 5: Error handling"""
    print("=" * 70)
    print("Example 5: Error Handling")
    print("=" * 70)

    seq = CLISequence("error-test", auto_save=False)

    # Add a step that will succeed
    seq.add_step("python", "print('This works')", timeout=5.0)

    # Add a step that will fail (invalid tool)
    try:
        seq.add_step("nonexistent-tool", "Some prompt", timeout=5.0)
        print("\n▸ Running sequence with invalid tool...")
        result = seq.run()

        print(f"\n✓ Sequence status: {result['status']}")
        if result['error_message']:
            print(f"  Error: {result['error_message'][:100]}")

    except Exception as e:
        print(f"\n✓ Caught expected error: {type(e).__name__}")
        print(f"  Message: {str(e)[:100]}")

    seq.cleanup()
    print("\n✓ Example 5 complete\n")


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  MetaCLI Layer 1 (Core) - CLI Orchestration Examples".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    try:
        # Run all examples
        example_1_basic_sequence()
        time.sleep(0.5)

        example_2_output_parsing()
        time.sleep(0.5)

        example_3_persistence()
        time.sleep(0.5)

        example_4_convenience_functions()
        time.sleep(0.5)

        example_5_error_handling()

        print("=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)
        print("\nLayer 1 (Core) features demonstrated:")
        print("  ✓ CLI orchestration with CLISequence")
        print("  ✓ Output parsing (code, errors, files, tests)")
        print("  ✓ Persistence (files + SQLite + FTS)")
        print("  ✓ Convenience functions")
        print("  ✓ Error handling")
        print("\nNext: Layer 2 (Meta) - Declarative workflows")
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
