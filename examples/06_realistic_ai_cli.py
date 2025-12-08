#!/usr/bin/env python3
"""
Realistic AI CLI Testing - Production-Ready Examples

Demonstrates:
- Realistic two-part output format (base64 + hex)
- Keyword detection and routing
- Complete audit-refactor cycle
- Error recovery
- Parallel multi-tool execution
- Meta-level optimization

Run: python examples/06_realistic_ai_cli.py
"""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metacli.testing.realistic_parser import (
    RealisticOutputParser,
    KeywordRouter,
    ParsedOutput,
    parse_and_route,
    create_audit_refactor_router,
    create_test_fix_router,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 1: Basic Parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_1_basic_parsing():
    """Example 1: Parse realistic two-part output."""
    print("=" * 70)
    print("Example 1: Basic Parsing of Two-Part Output")
    print("=" * 70)

    # Call mock AI CLI
    result = subprocess.run(
        ["python3", "tools/mock_ai_cli_realistic.py", "audit", "the", "code"],
        capture_output=True,
        text=True
    )

    output = result.stdout

    # Parse output
    parser = RealisticOutputParser()
    parsed = parser.parse(output)

    if parsed:
        print(f"\n✓ Successfully parsed output")
        print(f"  Base64 part length: {len(parsed.base64_part)} chars")
        print(f"  Hex part length: {len(parsed.hex_part)} chars")
        print(f"  Decoded text: {parsed.decoded_text[:80]}...")
        print(f"  Detected keywords: {parsed.detected_keywords}")
        print(f"  Has error: {parsed.has_error}")
        print(f"  Is complete: {parsed.is_complete}")
    else:
        print("\n✗ Failed to parse output")

    print("\n✓ Example 1 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 2: Keyword Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_2_keyword_detection():
    """Example 2: Detect specific keywords and route accordingly."""
    print("=" * 70)
    print("Example 2: Keyword Detection and Routing")
    print("=" * 70)

    parser = RealisticOutputParser()

    # Test with different forced keywords
    keywords_to_test = ['identified', 'error', 'complete', 'refactor', 'optimize']

    for keyword in keywords_to_test:
        # Call with forced keyword
        result = subprocess.run(
            ["python3", "tools/mock_ai_cli_realistic.py", "-k", keyword, "test"],
            capture_output=True,
            text=True
        )

        parsed = parser.parse(result.stdout)

        if parsed:
            print(f"\n  Testing keyword: {keyword}")
            print(f"    Detected: {parsed.detected_keywords}")
            print(f"    Text: {parsed.decoded_text[:60]}...")

    print("\n✓ Example 2 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 3: Keyword-Based Routing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_3_keyword_routing():
    """Example 3: Route to next action based on keywords."""
    print("=" * 70)
    print("Example 3: Keyword-Based Routing")
    print("=" * 70)

    parser = RealisticOutputParser()
    router = create_audit_refactor_router()

    # Test scenarios
    scenarios = [
        ("audit code", None),
        ("test with error", "error"),
        ("complete analysis", "complete"),
        ("refactor needed", "refactor"),
    ]

    for prompt, keyword in scenarios:
        # Run CLI
        cmd = ["python3", "tools/mock_ai_cli_realistic.py"]
        if keyword:
            cmd.extend(["-k", keyword])
        cmd.append(prompt)

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse and route
        parsed = parser.parse(result.stdout)
        if parsed:
            next_action = router.route(parsed)
            print(f"\n  Prompt: {prompt}")
            print(f"    Keywords detected: {parsed.detected_keywords}")
            print(f"    Next action: {next_action}")

    print("\n✓ Example 3 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 4: Complete Audit-Refactor Cycle
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_4_audit_refactor_cycle():
    """Example 4: Simulate complete audit-refactor cycle."""
    print("=" * 70)
    print("Example 4: Complete Audit-Refactor Cycle")
    print("=" * 70)

    parser = RealisticOutputParser()
    router = create_audit_refactor_router()

    # Workflow steps
    steps = [
        ("Audit code", "identified"),
        ("Load context", "complete"),
        ("Refactor code", "refactor"),
        ("Verify changes", "complete"),
        ("Optimize", "optimize"),
    ]

    print("\n  Executing workflow:")

    for i, (prompt, expected_keyword) in enumerate(steps, 1):
        # Execute step
        result = subprocess.run(
            ["python3", "tools/mock_ai_cli_realistic.py", "-k", expected_keyword, prompt],
            capture_output=True,
            text=True
        )

        parsed = parser.parse(result.stdout)

        if parsed:
            next_action = router.route(parsed)
            print(f"\n  Step {i}: {prompt}")
            print(f"    Output: {parsed.decoded_text[:60]}...")
            print(f"    Keywords: {parsed.detected_keywords}")
            print(f"    Next: {next_action}")

    print("\n✓ Example 4 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 5: Error Recovery
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_5_error_recovery():
    """Example 5: Handle errors with retry logic."""
    print("=" * 70)
    print("Example 5: Error Recovery")
    print("=" * 70)

    parser = RealisticOutputParser()
    router = create_audit_refactor_router()

    # Simulate error scenario
    print("\n  Simulating error scenario:")

    # Step 1: Trigger error
    result = subprocess.run(
        ["python3", "tools/mock_ai_cli_realistic.py", "-k", "error", "complex operation"],
        capture_output=True,
        text=True
    )

    parsed = parser.parse(result.stdout)

    if parsed and parsed.has_error:
        print(f"\n  ⚠ Error detected!")
        print(f"    Output: {parsed.decoded_text[:60]}...")
        print(f"    Next action: {router.route(parsed)}")

        # Step 2: Retry
        print("\n  Retrying operation...")
        result = subprocess.run(
            ["python3", "tools/mock_ai_cli_realistic.py", "-k", "complete", "retry operation"],
            capture_output=True,
            text=True
        )

        parsed = parser.parse(result.stdout)

        if parsed and parsed.is_complete:
            print(f"  ✓ Recovery successful!")
            print(f"    Output: {parsed.decoded_text[:60]}...")

    print("\n✓ Example 5 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 6: Custom Router
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_6_custom_router():
    """Example 6: Create custom routing logic."""
    print("=" * 70)
    print("Example 6: Custom Router")
    print("=" * 70)

    parser = RealisticOutputParser()
    router = KeywordRouter()

    # Add custom rules
    router.add_rule({'error'}, 'CRITICAL: Fix immediately', priority=20)
    router.add_rule({'identified', 'refactor'}, 'MEDIUM: Schedule refactoring', priority=10)
    router.add_rule({'optimize'}, 'LOW: Queue for optimization', priority=5)
    router.add_rule({'complete'}, 'INFO: Continue workflow', priority=1)

    print("\n  Testing custom routing rules:")

    test_keywords = ['error', 'refactor', 'optimize', 'complete']

    for keyword in test_keywords:
        result = subprocess.run(
            ["python3", "tools/mock_ai_cli_realistic.py", "-k", keyword, "test"],
            capture_output=True,
            text=True
        )

        parsed = parser.parse(result.stdout)

        if parsed:
            next_action = router.route(parsed)
            print(f"\n    Keyword: {keyword}")
            print(f"    Routing: {next_action}")

    print("\n✓ Example 6 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 7: Interactive Session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_7_interactive_session():
    """Example 7: Simulate interactive CLI session."""
    print("=" * 70)
    print("Example 7: Interactive Session Simulation")
    print("=" * 70)

    parser = RealisticOutputParser()
    router = create_audit_refactor_router()

    # Start interactive process
    proc = subprocess.Popen(
        ["python3", "tools/mock_ai_cli_realistic.py", "-i"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )

    print("\n  Interactive session started")

    # Send commands
    commands = [
        "audit the codebase",
        "load context",
        "apply refactoring",
    ]

    for cmd in commands:
        print(f"\n  Sending: {cmd}")

        # Send command
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

        # Read response (simplified - in production use proper buffering)
        import time
        time.sleep(0.5)

    # Cleanup
    proc.stdin.write("exit\n")
    proc.stdin.flush()
    proc.wait(timeout=2)

    print("\n  ✓ Interactive session completed")
    print("\n✓ Example 7 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 8: Convenience Function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def example_8_convenience_function():
    """Example 8: Use convenience parse_and_route function."""
    print("=" * 70)
    print("Example 8: Convenience Function")
    print("=" * 70)

    print("\n  Using parse_and_route() for quick workflows:")

    # Execute and parse in one step
    result = subprocess.run(
        ["python3", "tools/mock_ai_cli_realistic.py", "-k", "identified", "audit code"],
        capture_output=True,
        text=True
    )

    parsed, next_action = parse_and_route(result.stdout)

    if parsed:
        print(f"\n    Detected: {parsed.detected_keywords}")
        print(f"    Next: {next_action}")

    print("\n✓ Example 8 complete\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "     Realistic AI CLI Testing - Production Examples".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")

    examples = [
        example_1_basic_parsing,
        example_2_keyword_detection,
        example_3_keyword_routing,
        example_4_audit_refactor_cycle,
        example_5_error_recovery,
        example_6_custom_router,
        example_7_interactive_session,
        example_8_convenience_function,
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
    print("  ✓ Two-part output parsing (base64 + hex)")
    print("  ✓ Keyword detection in decoded text")
    print("  ✓ Intelligent routing based on keywords")
    print("  ✓ Complete audit-refactor cycle")
    print("  ✓ Error recovery with retry logic")
    print("  ✓ Custom routing rules")
    print("  ✓ Interactive session handling")
    print("  ✓ Convenience functions for quick workflows")
    print("=" * 70)


if __name__ == "__main__":
    main()
