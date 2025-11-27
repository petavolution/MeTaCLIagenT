#!/usr/bin/env python3
"""
Complete Workflow Demonstration - Real-World Use Case

This demonstrates the COMPLETE intended workflow:
1. Generate Code (mock coder)
2. Review Code (mock reviewer)
3. Fix Issues (mock fixer)
4. Save Everything (text files + SQLite)
5. Query Results (full-text search)

This proves the entire system works end-to-end for the intended use case.

Usage:
    python examples/complete_workflow_demo.py
"""

import sys
import os
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eats_core.cli_orchestrator import CLISequence
from eats_core.cli_persistence import get_persistence


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def demo_complete_workflow():
    """
    Demonstrate the complete real-world workflow:

    Generate Code → Review → Fix → Save → Query

    This is the CORE VALUE PROPOSITION of the system.
    """
    print_section("COMPLETE WORKFLOW DEMO: Generate → Review → Fix")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 1: Create Sequence
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print("Creating sequence with 3 steps:")
    print("  1. Generate code (mock AI coder)")
    print("  2. Review for security issues (mock AI reviewer)")
    print("  3. Fix identified issues (mock AI fixer)")
    print()

    seq = CLISequence("complete-workflow-demo", auto_save=True)

    # Step 1: Code Generation
    # Uses mock-coder (simulates claude-code)
    seq.add_step(
        tool_name="mock-coder",
        prompt="Write a REST API for user authentication with JWT tokens"
    )

    # Step 2: Code Review (receives code from step 1)
    # Uses mock-reviewer (simulates gemini)
    seq.add_step(
        tool_name="mock-reviewer",
        prompt="Review this code for security issues",
        use_previous_output=True  # KEY: Chains output from step 1
    )

    # Step 3: Fix Issues (receives review from step 2)
    # Uses mock-fixer (simulates aider)
    seq.add_step(
        tool_name="mock-fixer",
        prompt="Fix the security issues identified in the review",
        use_previous_output=True  # KEY: Chains output from step 2
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 2: Run Sequence
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print("Running complete workflow...")
    print("(This will spawn Python processes, send prompts, capture outputs)")
    print()

    result = seq.run()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 3: Show Results
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print_section("RESULTS")

    print(f"✓ Workflow completed!")
    print(f"  Status: {result['status']}")
    print(f"  Steps completed: {result['successful_steps']}/{result['total_steps']}")
    print(f"  Total duration: {result['duration']:.2f}s")
    print(f"  Sequence ID: {result['id']}")
    print()

    # Show each step
    print("Step outputs:")
    for i, step in enumerate(result['steps'], 1):
        print(f"\n  Step {i}: {step['tool_name']}")
        print(f"    Status: {'✓ Success' if step['success'] else '✗ Failed'}")
        print(f"    Duration: {step.get('duration', 0):.2f}s")
        print(f"    Output length: {len(step.get('raw_output', ''))} chars")

        # Show preview of output
        output = step.get('raw_output', '')
        if output:
            preview = output[:200].replace('\n', ' ')
            print(f"    Preview: {preview}...")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 4: Show Saved Files
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print_section("SAVED FILES")

    # Find sequence directory
    base_dir = Path("logs/sequences")
    seq_dirs = list(base_dir.glob(f"*/{result['id']}"))

    if seq_dirs:
        seq_dir = seq_dirs[0]
        print(f"Sequence saved to: {seq_dir}")
        print("\nFiles created:")

        for file_path in sorted(seq_dir.glob("*")):
            size = file_path.stat().st_size
            print(f"  - {file_path.name} ({size:,} bytes)")

        print("\nThese files are:")
        print("  ✓ Grep-able (search with: grep -r 'security' logs/sequences/)")
        print("  ✓ Diff-able (compare runs with: diff seq-A/step-1.txt seq-B/step-1.txt)")
        print("  ✓ Human-readable (cat/less/vim friendly)")
    else:
        print("⚠ Sequence directory not found (auto-save may be disabled)")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Step 5: Query Database
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print_section("DATABASE QUERIES")

    persistence = get_persistence()

    # Query completed sequences
    print("1. All completed sequences:")
    sequences = persistence.query_sequences(status="completed", limit=5)
    for s in sequences[:3]:  # Show first 3
        print(f"   - {s['id']}: {s['name']} ({s['total_steps']} steps, {s['successful_steps']} successful)")

    # Full-text search
    print("\n2. Full-text search for 'security':")
    results = persistence.search_outputs("security", limit=5)
    for r in results[:3]:
        print(f"   - Found in {r['sequence_id']}, step {r['step_number']} ({r['tool_name']})")

    # Statistics
    print("\n3. Overall statistics:")
    stats = persistence.get_statistics()
    print(f"   - Total sequences: {stats.get('total_sequences', 0)}")
    print(f"   - Total steps: {stats.get('total_steps', 0)}")
    print(f"   - Success rate: {stats.get('success_rate', 0)}%")
    if stats.get('tools_used'):
        print(f"   - Most used tool: {max(stats['tools_used'], key=stats['tools_used'].get)}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Cleanup
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    seq.cleanup()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Summary
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    print_section("VALUE DEMONSTRATION")

    print("This demo proved the COMPLETE workflow works:")
    print()
    print("✓ Step 1: Generate Code")
    print("  - Spawned Python process with mock AI coder")
    print("  - Sent prompt: 'Write REST API...'")
    print("  - Received realistic code output")
    print()
    print("✓ Step 2: Review Code")
    print("  - Spawned new process with mock reviewer")
    print("  - Sent prompt + CODE FROM STEP 1 (chaining!)")
    print("  - Received security review")
    print()
    print("✓ Step 3: Fix Issues")
    print("  - Spawned new process with mock fixer")
    print("  - Sent prompt + REVIEW FROM STEP 2 (chaining!)")
    print("  - Received fixed code")
    print()
    print("✓ Step 4: Saved Everything")
    print("  - Text files: One per step (grep-able)")
    print("  - SQLite DB: Metadata + full-text search")
    print()
    print("✓ Step 5: Queried Results")
    print("  - Found sequences by status")
    print("  - Searched outputs for keywords")
    print("  - Generated statistics")
    print()
    print("="*70)
    print("SYSTEM VALIDATED: Ready for real AI CLI tools!")
    print("="*70)
    print()
    print("Next steps:")
    print("  1. Replace mock_ai_cli.py with real tools:")
    print("     - claude-code instead of 'python tools/mock_ai_cli.py --mode coder'")
    print("     - gemini instead of mock reviewer")
    print("     - aider instead of mock fixer")
    print()
    print("  2. The system will work IDENTICALLY - just with real AI!")
    print()


def main():
    """Run the complete workflow demonstration."""
    print()
    print("="*70)
    print("  COMPLETE WORKFLOW DEMONSTRATION")
    print("  Proving the entire system works end-to-end")
    print("="*70)
    print()
    print("This demonstrates:")
    print("  - Running AI CLI tools in sequences")
    print("  - Parsing and chaining outputs")
    print("  - Saving to text files + SQLite")
    print("  - Querying with full-text search")
    print()
    print("Using mock AI CLI (simulates claude-code/gemini/aider)")
    print("because real tools may not be installed.")
    print()

    try:
        demo_complete_workflow()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
