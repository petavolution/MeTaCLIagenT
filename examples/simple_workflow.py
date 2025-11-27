#!/usr/bin/env python3
"""
Simple CLI Orchestration Workflow - Minimal Example

Demonstrates the core functionality:
1. Run AI coding CLI tools in sequences
2. Parse outputs
3. Chain with follow-up inputs
4. Save everything to text files + SQLite

This is the simplest possible usage - no complexity, just core features.

Requirements:
- Python 3.8+
- At least one CLI tool: python (built-in) for testing
- Optional: claude-code, gemini, aider for real workflows

Usage:
    python examples/simple_workflow.py
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eats_core.cli_orchestrator import CLISequence, OutputParser
from eats_core.cli_persistence import get_persistence


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 1: Basic Python Execution (No external tools needed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_basic_python():
    """
    Simplest possible example using built-in Python.

    Shows:
    - Create sequence
    - Add steps
    - Run sequence
    - Outputs auto-saved to text files + SQLite
    """
    print("\n" + "="*60)
    print("Example 1: Basic Python Execution")
    print("="*60)

    # Create sequence (auto_save=True by default)
    seq = CLISequence("basic-python-test")

    # Add a simple Python step
    seq.add_step(
        "python",
        "print('Hello from EATS CLI orchestrator!')\nprint('2 + 2 =', 2 + 2)"
    )

    # Run the sequence
    print("\nRunning sequence...")
    result = seq.run()

    # Cleanup
    seq.cleanup()

    # Show results
    print(f"\n✓ Sequence completed!")
    print(f"  Steps: {result['successful_steps']}/{result['total_steps']}")
    print(f"  Duration: {result['duration']:.2f}s")
    print(f"  Sequence ID: {result['id']}")
    print(f"\n  Saved to:")
    print(f"    - Text files: logs/sequences/*/{result['id']}/")
    print(f"    - Database: logs/sequences/sequences.db")

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 2: Multi-Step with Output Chaining
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_chained_python():
    """
    Multi-step sequence with output chaining.

    Shows:
    - Multiple steps
    - use_previous_output=True for chaining
    - Output parsing
    """
    print("\n" + "="*60)
    print("Example 2: Multi-Step with Output Chaining")
    print("="*60)

    seq = CLISequence("python-chaining-test")

    # Step 1: Generate some data
    seq.add_step(
        "python",
        "data = [1, 2, 3, 4, 5]\nprint('Generated data:', data)\nprint('Sum:', sum(data))"
    )

    # Step 2: Process the output (simulated follow-up)
    seq.add_step(
        "python",
        "# This step receives previous output\nprint('Processing previous output...')\nprint('Done!')",
        use_previous_output=True  # Previous output will be prepended to prompt
    )

    print("\nRunning 2-step sequence...")
    result = seq.run()

    seq.cleanup()

    print(f"\n✓ Sequence completed!")
    print(f"  Steps: {result['successful_steps']}/{result['total_steps']}")
    print(f"  Sequence ID: {result['id']}")

    # Show parsed output
    if result['steps']:
        step1 = result['steps'][0]
        if step1.get('parsed_data'):
            print(f"\n  Step 1 parsed data:")
            print(f"    Code blocks: {len(step1['parsed_data'].get('code_blocks', []))}")
            print(f"    Errors: {step1['parsed_data'].get('has_errors', False)}")

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 3: Query Saved Sequences
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_query_persistence():
    """
    Query and search previously saved sequences.

    Shows:
    - Query sequences by status
    - Full-text search
    - Load specific sequence
    - Statistics
    """
    print("\n" + "="*60)
    print("Example 3: Query Saved Sequences")
    print("="*60)

    persistence = get_persistence()

    # Get all completed sequences
    print("\n1. All completed sequences:")
    completed = persistence.query_sequences(status="completed", limit=5)
    for seq in completed:
        print(f"   - {seq['id']}: {seq['name']} ({seq['total_steps']} steps)")

    # Full-text search
    print("\n2. Full-text search for 'Hello':")
    results = persistence.search_outputs("Hello", limit=3)
    for result in results:
        print(f"   - Step {result['step_number']} in {result['sequence_id']}: {result['tool_name']}")
        if result.get('snippet'):
            print(f"     {result['snippet'][:100]}...")

    # Statistics
    print("\n3. Overall statistics:")
    stats = persistence.get_statistics()
    print(f"   Total sequences: {stats.get('total_sequences', 0)}")
    print(f"   Total steps: {stats.get('total_steps', 0)}")
    print(f"   Success rate: {stats.get('success_rate', 0)}%")

    if stats.get('tools_used'):
        print(f"\n   Tools used:")
        for tool, count in stats['tools_used'].items():
            print(f"     - {tool}: {count} times")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 4: Inspect Saved Files
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_inspect_files(sequence_id: str):
    """
    Show what files were created.

    Shows:
    - Directory structure
    - Text file contents
    - metadata.json
    """
    print("\n" + "="*60)
    print(f"Example 4: Inspect Saved Files for {sequence_id}")
    print("="*60)

    base_dir = Path("logs/sequences")

    # Find sequence directory
    seq_dir = None
    for date_dir in base_dir.glob("*/"):
        potential = date_dir / sequence_id
        if potential.exists():
            seq_dir = potential
            break

    if not seq_dir:
        print(f"Sequence directory not found for {sequence_id}")
        return

    print(f"\nSequence directory: {seq_dir}")
    print("\nFiles created:")

    for file_path in sorted(seq_dir.glob("*")):
        size = file_path.stat().st_size
        print(f"  - {file_path.name} ({size} bytes)")

        # Show first few lines of text files
        if file_path.suffix == '.txt':
            print(f"    Preview:")
            with open(file_path) as f:
                for i, line in enumerate(f):
                    if i >= 3:
                        print(f"    ...")
                        break
                    print(f"    {line.rstrip()}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 5: Real AI CLI Tools (if available)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_ai_cli_tools():
    """
    Example using real AI CLI tools (if installed).

    Demonstrates the actual intended use case:
    - claude-code for generation
    - gemini for review
    - aider for fixes

    Note: Requires tools to be installed and in PATH
    """
    print("\n" + "="*60)
    print("Example 5: Real AI CLI Tools")
    print("="*60)

    # Check which tools are available
    import shutil
    available_tools = []
    for tool in ["claude-code", "gemini", "aider"]:
        if shutil.which(tool):
            available_tools.append(tool)

    if not available_tools:
        print("\n⚠️  No AI CLI tools found in PATH")
        print("   Install at least one of: claude-code, gemini, aider")
        print("   Skipping this example.\n")
        return

    print(f"\nAvailable tools: {', '.join(available_tools)}")

    # Create a simple workflow with available tools
    seq = CLISequence("ai-tools-workflow")

    if "claude-code" in available_tools:
        seq.add_step(
            "claude-code",
            "Write a Python function to calculate fibonacci numbers"
        )

    if "gemini" in available_tools and len(seq.steps) > 0:
        seq.add_step(
            "gemini",
            "Review this code for efficiency and correctness",
            use_previous_output=True
        )

    if len(seq.steps) == 0:
        print("Not enough tools available for workflow")
        return

    print(f"\nRunning {len(seq.steps)}-step workflow...")
    result = seq.run()

    seq.cleanup()

    print(f"\n✓ AI tools workflow completed!")
    print(f"  Steps: {result['successful_steps']}/{result['total_steps']}")
    print(f"  Sequence ID: {result['id']}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("EATS SIMPLE WORKFLOW EXAMPLES")
    print("="*60)
    print("\nDemonstrating core functionality:")
    print("  ✓ Run CLI tools in sequences")
    print("  ✓ Parse outputs")
    print("  ✓ Chain with follow-up inputs")
    print("  ✓ Save to text files + SQLite")
    print()

    # Run examples
    try:
        # Basic examples (always work)
        result1 = example_basic_python()
        result2 = example_chained_python()

        # Query what we just saved
        example_query_persistence()

        # Inspect files
        if result1:
            example_inspect_files(result1['id'])

        # Try AI tools if available
        example_ai_cli_tools()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*60)
    print("Examples complete!")
    print("="*60)

    print("\nWhat was saved:")
    print("  1. Text files: logs/sequences/YYYY-MM-DD/seq-*/")
    print("     - One .txt file per step (grep-able!)")
    print("     - metadata.json with sequence info")

    print("\n  2. SQLite database: logs/sequences/sequences.db")
    print("     - Query with: sqlite3 logs/sequences/sequences.db")
    print("     - Full-text search enabled")

    print("\nNext steps:")
    print("  - Install AI CLI tools: claude-code, gemini, aider")
    print("  - Create your own workflows in Python")
    print("  - Query and analyze saved sequences")
    print("  - Grep through text files for debugging")
    print()


if __name__ == "__main__":
    main()
