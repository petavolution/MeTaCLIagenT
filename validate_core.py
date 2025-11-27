#!/usr/bin/env python3
"""
Core Functionality Validation Script

Tests that the core orchestration workflow actually works:
1. Transport layer (PTY)
2. CLI sequencing
3. Output parsing
4. Persistence (text files + SQLite)
5. Querying

This is NOT a comprehensive test suite - it's a smoke test to ensure
basic functionality works before building more features.

Usage:
    python validate_core.py
"""

import sys
import os
import time
import sqlite3
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from eats_core.transport import PTYTransport, create_transport
from eats_core.cli_orchestrator import CLISequence, OutputParser
from eats_core.cli_persistence import SequencePersistence, get_persistence


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Utilities
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def test(name: str):
    """Test decorator."""
    def decorator(func):
        func._test_name = name
        return func
    return decorator


def run_test(func):
    """Run a single test and report result."""
    test_name = getattr(func, '_test_name', func.__name__)
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")

    try:
        func()
        print(f"✓ PASS: {test_name}")
        return True
    except AssertionError as e:
        print(f"✗ FAIL: {test_name}")
        print(f"  Assertion: {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {test_name}")
        print(f"  Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 1: Transport Layer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("Transport Layer - PTY spawn and basic I/O")
def test_transport_basic():
    """Test that PTYTransport can spawn a process and send/receive."""
    print("Creating PTYTransport with Python...")
    transport = create_transport(["python3", "-i"], transport_type="pty", name="test-python")

    print("Starting transport...")
    transport.start()

    assert transport.is_alive(), "Transport should be alive after start"

    print("Sending command...")
    transport.send_line("print('VALIDATION_TEST_OUTPUT')")

    print("Waiting for output...")
    time.sleep(0.5)

    output = transport.recv_now()
    print(f"Received {len(output)} bytes of output")

    assert len(output) > 0, "Should receive output"
    assert "VALIDATION_TEST_OUTPUT" in output, f"Output should contain test string. Got: {output[:200]}"

    print("Terminating transport...")
    transport.terminate()

    print("✓ Transport layer works!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 2: Output Parser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("Output Parser - Extract code blocks")
def test_output_parser():
    """Test that OutputParser can extract code blocks."""
    parser = OutputParser()

    test_output = """
Here's a Python function:

```python
def hello():
    print("Hello, World!")
```

And some JavaScript:

```javascript
console.log("Hello");
```
"""

    print("Parsing output...")
    code_blocks = parser.extract_code_blocks(test_output)

    print(f"Found {len(code_blocks)} code blocks")
    assert len(code_blocks) == 2, f"Should find 2 code blocks, found {len(code_blocks)}"

    assert code_blocks[0]['language'] == 'python', "First block should be Python"
    assert 'hello()' in code_blocks[0]['code'], "Python code should contain function"

    assert code_blocks[1]['language'] == 'javascript', "Second block should be JavaScript"
    assert 'console.log' in code_blocks[1]['code'], "JS code should contain console.log"

    print("✓ Output parser works!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 3: CLI Sequence (no auto-save)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("CLI Sequence - Basic execution")
def test_cli_sequence_basic():
    """Test that CLISequence can run a simple workflow."""
    print("Creating sequence (auto_save=False for testing)...")
    seq = CLISequence("validation-test", auto_save=False)

    print("Adding step...")
    seq.add_step("python", "print('Step 1 output')\nprint('2 + 2 =', 2 + 2)")

    print("Running sequence...")
    result = seq.run()

    print(f"Sequence result: {result['status']}")
    assert result['status'] == 'completed', f"Sequence should complete, got: {result['status']}"
    assert result['successful_steps'] == 1, f"Should have 1 successful step, got: {result['successful_steps']}"

    print("Checking step output...")
    step = result['steps'][0]
    assert step['success'], "Step should succeed"
    assert 'Step 1 output' in step['raw_output'], f"Output should contain expected text. Got: {step['raw_output'][:200]}"

    print("Cleaning up...")
    seq.cleanup()

    print("✓ CLI sequence works!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 4: Multi-Step with Chaining
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("CLI Sequence - Multi-step with output chaining")
def test_cli_sequence_chaining():
    """Test that output chaining works."""
    print("Creating 2-step sequence...")
    seq = CLISequence("chaining-test", auto_save=False)

    seq.add_step("python", "print('FIRST_STEP_MARKER')")
    seq.add_step("python", "print('Received previous output')", use_previous_output=True)

    print("Running sequence...")
    result = seq.run()

    assert result['successful_steps'] == 2, f"Should have 2 successful steps, got: {result['successful_steps']}"

    print("Verifying output chaining...")
    step1_output = result['steps'][0]['raw_output']
    step2_output = result['steps'][1]['raw_output']

    assert 'FIRST_STEP_MARKER' in step1_output, "Step 1 should have marker"
    assert 'Received previous output' in step2_output, "Step 2 should acknowledge"

    seq.cleanup()

    print("✓ Output chaining works!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 5: Persistence - Text Files
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("Persistence - Text file storage")
def test_persistence_text_files():
    """Test that sequences are saved to text files."""
    print("Creating sequence with auto_save=True...")
    seq = CLISequence("persistence-test", auto_save=True)

    seq.add_step("python", "print('PERSISTENCE_TEST_MARKER')")

    print("Running sequence (should auto-save)...")
    result = seq.run()

    seq_id = result['id']
    print(f"Sequence ID: {seq_id}")

    # Find the saved directory
    base_dir = Path("logs/sequences")
    seq_dirs = list(base_dir.glob(f"*/{seq_id}"))

    assert len(seq_dirs) > 0, f"Should find sequence directory for {seq_id}"

    seq_dir = seq_dirs[0]
    print(f"Found sequence directory: {seq_dir}")

    # Check for files
    metadata_file = seq_dir / "metadata.json"
    step_file = seq_dir / "step-1-python.txt"

    assert metadata_file.exists(), f"metadata.json should exist at {metadata_file}"
    assert step_file.exists(), f"step-1-python.txt should exist at {step_file}"

    # Verify content
    with open(step_file) as f:
        content = f.read()
        assert 'PERSISTENCE_TEST_MARKER' in content, "Step file should contain output"

    print(f"✓ Text files saved correctly to {seq_dir}")

    seq.cleanup()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 6: Persistence - SQLite Database
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("Persistence - SQLite database")
def test_persistence_sqlite():
    """Test that sequences are saved to SQLite."""
    print("Creating sequence with auto_save=True...")
    seq = CLISequence("sqlite-test", auto_save=True)

    seq.add_step("python", "print('DATABASE_TEST_MARKER')")

    print("Running sequence...")
    result = seq.run()

    seq_id = result['id']
    print(f"Sequence ID: {seq_id}")

    # Check SQLite database
    db_path = Path("logs/sequences/sequences.db")
    assert db_path.exists(), f"Database should exist at {db_path}"

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check sequences table
    cursor.execute("SELECT * FROM sequences WHERE id = ?", (seq_id,))
    seq_row = cursor.fetchone()
    assert seq_row is not None, f"Sequence {seq_id} should be in database"

    print(f"Found sequence in database: {seq_row[0]}")

    # Check steps table
    cursor.execute("SELECT * FROM steps WHERE sequence_id = ?", (seq_id,))
    steps = cursor.fetchall()
    assert len(steps) > 0, "Should have at least one step"

    print(f"Found {len(steps)} step(s) in database")

    # Check FTS using the persistence API (not direct SQL)
    print("Testing FTS via persistence API...")
    persistence = SequencePersistence()
    fts_results = persistence.search_outputs("DATABASE_TEST_MARKER", limit=10)
    assert len(fts_results) > 0, "FTS should find the marker"

    print(f"✓ FTS found marker in {len(fts_results)} result(s)")

    conn.close()
    seq.cleanup()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test 7: Query Persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@test("Persistence - Query sequences")
def test_persistence_query():
    """Test querying saved sequences."""
    print("Getting persistence instance...")
    persistence = get_persistence()

    print("Querying all sequences...")
    sequences = persistence.query_sequences(limit=10)

    print(f"Found {len(sequences)} sequences")
    assert len(sequences) > 0, "Should have at least one saved sequence from previous tests"

    # Test search
    print("Testing full-text search...")
    results = persistence.search_outputs("MARKER", limit=10)

    print(f"Search found {len(results)} matching steps")
    # Should find results from previous tests
    assert len(results) > 0, "Search should find marker from previous tests"

    # Test statistics
    print("Getting statistics...")
    stats = persistence.get_statistics()

    print(f"Statistics:")
    print(f"  Total sequences: {stats.get('total_sequences', 0)}")
    print(f"  Total steps: {stats.get('total_steps', 0)}")
    print(f"  Success rate: {stats.get('success_rate', 0)}%")

    assert stats['total_sequences'] > 0, "Should have sequences"
    assert stats['total_steps'] > 0, "Should have steps"

    print("✓ Query functionality works!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Test Runner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("EATS CORE VALIDATION")
    print("="*60)
    print("\nValidating core functionality...")
    print("This will create test sequences in logs/sequences/")
    print()

    # Collect all test functions
    tests = [
        test_transport_basic,
        test_output_parser,
        test_cli_sequence_basic,
        test_cli_sequence_chaining,
        test_persistence_text_files,
        test_persistence_sqlite,
        test_persistence_query,
    ]

    # Run tests
    results = []
    for test_func in tests:
        passed = run_test(test_func)
        results.append((test_func._test_name, passed))

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed

    for name, passed_flag in results:
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED - Core functionality validated!")
        print("\nNext steps:")
        print("  1. Run real AI CLI tools: python examples/simple_workflow.py")
        print("  2. Build your own workflows")
        print("  3. Add more tests as needed")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED - Fix issues before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())
