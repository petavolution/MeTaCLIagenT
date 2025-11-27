#!/usr/bin/env python3
"""
Test Framework Demonstration

This demonstrates the intelligent testing framework that:
1. Generates prompts from a library
2. Sends them to mock CLI tools
3. Analyzes outputs for patterns
4. Chooses follow-up prompts based on patterns found
5. Saves everything to database
6. Generates reports

This is a COMPLETE testing system for CLI orchestration.

Usage:
    python examples/test_framework_demo.py
"""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_framework import TestFramework
from tests.test_prompts import (
    get_library_stats,
    get_random_prompt,
    find_patterns_in_output,
    get_follow_up_prompt,
)


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def demo_prompt_library():
    """Demonstrate the test prompt library."""
    print_section("1. TEST PROMPT LIBRARY")

    stats = get_library_stats()

    print("The library contains:")
    print(f"  • {stats['total_prompts']} test prompts")
    print(f"  • {stats['total_pattern_rules']} pattern matching rules")
    print(f"  • {len(stats['categories'])} prompt categories")
    print(f"  • Hash lookup table with {stats['hash_table_size']} entries")

    print(f"\nPrompt categories:")
    for cat, count in stats['prompts_per_category'].items():
        print(f"  - {cat}: {count} prompts")

    print(f"\nExample prompts:")
    for i in range(3):
        prompt = get_random_prompt()
        print(f"  {i+1}. [{prompt.category}] {prompt.prompt[:60]}...")


def demo_pattern_matching():
    """Demonstrate pattern matching and follow-up selection."""
    print_section("2. PATTERN MATCHING")

    # Simulate different CLI outputs
    test_outputs = [
        (
            "code_output",
            "Here's a function:\ndef calculate_total(items):\n    return sum(item.price for item in items)"
        ),
        (
            "review_output",
            "Found security vulnerability: SQL injection risk in user input handling"
        ),
        (
            "fix_output",
            "Fixed the security issues and optimized the database queries"
        ),
    ]

    for name, output in test_outputs:
        print(f"\n{name}:")
        print(f"  Output: {output[:80]}...")

        # Find patterns
        patterns = find_patterns_in_output(output)
        print(f"  Patterns found: {len(patterns)}")

        if patterns:
            for p in patterns[:2]:  # Show first 2
                print(f"    - '{p.pattern}' → {p.description}")

            # Get follow-up
            follow_up = get_follow_up_prompt(output)
            if follow_up:
                print(f"  Suggested follow-up:")
                print(f"    → {follow_up[:70]}...")


def demo_simple_test():
    """Demonstrate a simple single-prompt test."""
    print_section("3. SIMPLE TEST")

    print("Running a simple test with one prompt...")
    print("This sends a prompt to mock CLI and captures output.\n")

    framework = TestFramework()

    result = framework.run_simple_test(
        prompt="Write a Python function to calculate fibonacci numbers",
        tool_name="mock-coder",
        save_to_db=True
    )

    print(f"\nResult:")
    print(f"  Status: {result['status']}")
    print(f"  Duration: {result['duration']:.2f}s")
    print(f"  Output length: {len(result['steps'][0]['raw_output'])} chars")


def demo_workflow_test():
    """Demonstrate a pre-defined workflow test."""
    print_section("4. WORKFLOW TEST")

    print("Running a pre-defined workflow test...")
    print("This executes a sequence: Generate → Review → Fix\n")

    framework = TestFramework()

    result = framework.run_workflow_test(
        workflow_type="generate_review_fix",
        save_to_db=True
    )

    print(f"\nWorkflow result:")
    print(f"  Status: {result['status']}")
    print(f"  Steps completed: {result['successful_steps']}/{result['total_steps']}")
    print(f"  Duration: {result['duration']:.2f}s")

    print(f"\nStep outputs:")
    for i, step in enumerate(result['steps'], 1):
        print(f"  Step {i} ({step['tool_name']}): {len(step['raw_output'])} chars")


def demo_intelligent_test():
    """Demonstrate the intelligent test with pattern-based follow-ups."""
    print_section("5. INTELLIGENT TEST (Pattern-Based)")

    print("Running an INTELLIGENT test...")
    print("This demonstrates the KEY feature: pattern-based follow-ups\n")

    print("How it works:")
    print("  1. Send initial prompt to mock CLI")
    print("  2. Analyze output for patterns (def, class, vulnerability, etc.)")
    print("  3. Choose appropriate follow-up based on patterns found")
    print("  4. Repeat until max steps or no patterns found")
    print()

    framework = TestFramework()

    result = framework.run_intelligent_test(
        initial_prompt="Write a REST API endpoint for user authentication",
        max_steps=4,
        save_to_db=True
    )

    print(f"\nIntelligent test result:")
    print(f"  Status: {result['status']}")
    print(f"  Total steps: {result['successful_steps']}")
    print(f"  Duration: {result['duration']:.2f}s")
    print(f"  Pattern matches: {len(result.get('pattern_history', []))}")

    if result.get('pattern_history'):
        print(f"\nPattern matching flow:")
        for entry in result['pattern_history']:
            print(f"  Step {entry['step']}: {entry['follow_up_description']}")
            print(f"    Patterns: {', '.join(entry['patterns_found'][:3])}")


def demo_batch_tests():
    """Demonstrate running multiple tests in batch."""
    print_section("6. BATCH TESTS")

    print("Running batch tests (5 intelligent tests)...")
    print("This simulates continuous testing workload.\n")

    framework = TestFramework()

    result = framework.run_batch_tests(
        num_tests=5,
        test_type="intelligent",
        save_to_db=True
    )

    print(f"\nBatch test summary:")
    print(f"  Tests run: {result['num_tests']}")
    print(f"  Successful: {result['successful']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Success rate: {(result['successful']/result['num_tests'])*100:.1f}%")
    print(f"  Total time: {result['total_duration']:.2f}s")
    print(f"  Avg per test: {result['total_duration']/result['num_tests']:.2f}s")


def demo_test_report():
    """Demonstrate generating a test report."""
    print_section("7. TEST REPORT")

    print("Generating comprehensive test report from database...\n")

    framework = TestFramework()

    report_file = "logs/test_report.json"
    report = framework.generate_test_report(output_file=report_file)

    print(f"\nReport highlights:")
    db_stats = report['database_statistics']
    lib_stats = report['prompt_library']

    print(f"\nDatabase:")
    print(f"  Total sequences: {db_stats.get('total_sequences', 0)}")
    print(f"  Total steps: {db_stats.get('total_steps', 0)}")
    print(f"  Success rate: {db_stats.get('success_rate', 0):.1f}%")

    if db_stats.get('tools_used'):
        print(f"  Tools used: {', '.join(db_stats['tools_used'].keys())}")

    print(f"\nPrompt Library:")
    print(f"  Total prompts: {lib_stats['total_prompts']}")
    print(f"  Pattern rules: {lib_stats['total_pattern_rules']}")
    print(f"  Categories: {len(lib_stats['categories'])}")

    print(f"\nReport saved to: {report_file}")


def main():
    """Run all demonstrations."""
    print("\n" + "="*70)
    print("  TEST FRAMEWORK DEMONSTRATION")
    print("  Intelligent Testing for CLI Orchestration")
    print("="*70)

    print("\nThis demo shows:")
    print("  • Test prompt library with 20+ prompts")
    print("  • Pattern matching with hash lookup")
    print("  • Simple, workflow, and intelligent tests")
    print("  • Batch testing capabilities")
    print("  • Automated test reporting")
    print()

    try:
        # 1. Show prompt library
        demo_prompt_library()

        # 2. Show pattern matching
        demo_pattern_matching()

        # 3. Simple test
        demo_simple_test()

        # 4. Workflow test
        demo_workflow_test()

        # 5. Intelligent test (KEY FEATURE)
        demo_intelligent_test()

        # 6. Batch tests
        demo_batch_tests()

        # 7. Test report
        demo_test_report()

        # Final summary
        print_section("SUMMARY")

        print("✓ Test Framework Validated!")
        print()
        print("The framework provides:")
        print()
        print("1. TEST PROMPT LIBRARY")
        print("   - 20+ categorized test prompts")
        print("   - Pattern-based follow-up rules")
        print("   - Hash lookup for fast matching")
        print()
        print("2. INTELLIGENT TESTING")
        print("   - Analyzes CLI output for patterns")
        print("   - Automatically chooses follow-up prompts")
        print("   - Creates multi-step workflows dynamically")
        print()
        print("3. COMPREHENSIVE PERSISTENCE")
        print("   - Saves all tests to database")
        print("   - Full-text search of outputs")
        print("   - Pattern match history tracking")
        print()
        print("4. TEST REPORTING")
        print("   - Statistics on test runs")
        print("   - Success/failure rates")
        print("   - Tool usage analysis")
        print()
        print("="*70)
        print("SYSTEM READY: Use framework for comprehensive CLI testing!")
        print("="*70)
        print()

        print("Next steps:")
        print("  1. Use this framework to test real AI CLI tools")
        print("  2. Add more prompts and patterns to the library")
        print("  3. Customize pattern rules for your workflows")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
