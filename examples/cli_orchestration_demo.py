#!/usr/bin/env python3
"""
CLI Orchestration Examples - Practical Workflows

Demonstrates real-world usage of AI CLI tool sequencing:
1. Code generation → Review → Fix
2. Multi-LLM consensus
3. Test-driven development
4. Iterative refinement

Requirements:
- claude-code CLI (optional, uses mock if not available)
- gemini CLI (optional)
- aider (optional)
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eats_core.cli_orchestrator import (
    CLISequence,
    WorkflowPatterns,
    OutputParser,
    run_sequence,
    quick_chain,
)
from eats_core.logging import init_logging, get_logger

# Initialize logging
init_logging()
logger = get_logger("demo")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 1: Code → Review → Fix Workflow
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_code_review_fix():
    """
    Generate code with claude-code, review with gemini, fix with aider.
    """
    print("\n" + "="*60)
    print("Example 1: Code Generation → Review → Fix")
    print("="*60 + "\n")

    # Use pre-built pattern
    task = "Create a Python function to validate email addresses using regex"
    sequence = WorkflowPatterns.code_review_fix(task)

    print(f"Task: {task}\n")
    print(f"Workflow: {len(sequence.steps)} steps")
    for i, step in enumerate(sequence.steps, 1):
        print(f"  {i}. {step.tool_name}: {step.prompt[:60]}...")

    # Run (would execute if tools are available)
    print("\n[Simulating execution...]")
    print("Note: Actual execution requires CLI tools installed\n")

    # Show expected flow
    print("Expected flow:")
    print("1. claude-code generates email validation function")
    print("2. gemini reviews for bugs and edge cases")
    print("3. aider fixes any identified issues")
    print("4. Final output: Production-ready code")

    # Cleanup
    sequence.cleanup()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 2: Multi-LLM Consensus
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_multi_llm_consensus():
    """
    Get answers from multiple LLMs and compare.
    """
    print("\n" + "="*60)
    print("Example 2: Multi-LLM Consensus")
    print("="*60 + "\n")

    question = "What's the most efficient way to implement a LRU cache in Python?"

    # Create sequence querying multiple LLMs
    sequence = WorkflowPatterns.multi_llm_consensus(
        question,
        tools=["claude-code", "gemini", "ollama"]
    )

    print(f"Question: {question}\n")
    print(f"Querying {len(sequence.steps)} LLMs:")
    for step in sequence.steps:
        print(f"  - {step.tool_name}")

    print("\nExpected flow:")
    print("1. Each LLM provides independent answer")
    print("2. Outputs are parsed for code blocks")
    print("3. Compare approaches (OrderedDict vs custom implementation)")
    print("4. Identify consensus on best practices")

    sequence.cleanup()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 3: Custom Sequence with Output Parsing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_custom_sequence():
    """
    Build custom sequence with specific parsing logic.
    """
    print("\n" + "="*60)
    print("Example 3: Custom Sequence with Parsing")
    print("="*60 + "\n")

    sequence = CLISequence("custom-workflow")

    # Step 1: Generate API client
    sequence.add_step(
        "claude-code",
        "Create a Python REST API client for GitHub with authentication"
    )

    # Step 2: Generate tests (using previous output)
    sequence.add_step(
        "claude-code",
        "Write comprehensive pytest tests for this client",
        use_previous_output=True
    )

    # Step 3: Security review
    sequence.add_step(
        "gemini",
        "Review for security issues: auth handling, input validation, error exposure",
        use_previous_output=True
    )

    print("Custom 3-step workflow:")
    for i, step in enumerate(sequence.steps, 1):
        print(f"{i}. {step.tool_name}: {step.prompt[:70]}...")

    print("\nParsing features enabled:")
    print("  ✓ Extract code blocks (```python...```)")
    print("  ✓ Detect errors and warnings")
    print("  ✓ Find file paths mentioned")
    print("  ✓ Parse test results")

    sequence.cleanup()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 4: Iterative Refinement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_iterative_refinement():
    """
    Refine output through multiple iterations.
    """
    print("\n" + "="*60)
    print("Example 4: Iterative Refinement")
    print("="*60 + "\n")

    task = "Design a scalable microservices architecture for an e-commerce platform"

    sequence = WorkflowPatterns.iterative_refinement(task, iterations=4)

    print(f"Task: {task}\n")
    print(f"Iterations: {len(sequence.steps)}")
    print("\nRefinement process:")
    for i in range(len(sequence.steps)):
        if i == 0:
            print(f"  {i+1}. Initial design")
        else:
            print(f"  {i+1}. Refine and improve (iteration {i+1})")

    print("\nExpected improvements per iteration:")
    print("  1st: Basic architecture diagram")
    print("  2nd: Add service details and communication patterns")
    print("  3rd: Include scalability and fault tolerance")
    print("  4th: Finalize with deployment and monitoring")

    sequence.cleanup()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 5: Quick Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_quick_helpers():
    """
    Demonstrate quick helper functions for simple workflows.
    """
    print("\n" + "="*60)
    print("Example 5: Quick Helper Functions")
    print("="*60 + "\n")

    print("1. run_sequence() - Quick sequence from tuples:")
    print("""
    result = run_sequence([
        ("claude-code", "Write a binary search function"),
        ("gemini", "Review this code", True),
        ("aider", "Fix any issues", True),
    ])
    """)

    print("\n2. quick_chain() - Simple tool chaining:")
    print("""
    output = quick_chain(
        ["claude-code", "gemini", "aider"],
        "Write a web scraper for news articles"
    )
    """)

    print("\n3. OutputParser - Parse any CLI output:")
    parser = OutputParser()

    sample_output = """
Here's a Python implementation:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

This works but has O(2^n) complexity.
"""

    print("\nSample output:")
    print(sample_output)

    code_blocks = parser.extract_code_blocks(sample_output)
    print(f"\nExtracted {len(code_blocks)} code block(s):")
    for block in code_blocks:
        print(f"  Language: {block['language']}")
        print(f"  Code: {block['code'][:60]}...")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 6: Real Execution (if tools available)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_real_execution():
    """
    Actually run a sequence if tools are available.

    This would execute real CLI tools if installed.
    """
    print("\n" + "="*60)
    print("Example 6: Real Execution (Simulated)")
    print("="*60 + "\n")

    print("To execute real workflows, ensure CLI tools are installed:")
    print("  • claude-code: npm install -g @anthropic-ai/claude-cli")
    print("  • gemini: pip install google-generativeai")
    print("  • aider: pip install aider-chat")
    print("  • ollama: https://ollama.ai/download\n")

    print("Example real execution code:")
    print("""
    sequence = CLISequence("real-workflow")
    sequence.add_step("claude-code", "Write a FastAPI hello world app")
    sequence.add_step("python", "python -m pytest", timeout=30)

    result = sequence.run()

    print(f"Success: {result['successful_steps']}/{result['total_steps']}")
    print(f"Duration: {result['duration']:.1f}s")

    if result['final_output']:
        print(f"Final output: {result['final_output'][:200]}...")

    sequence.cleanup()
    """)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Demo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("CLI ORCHESTRATION EXAMPLES")
    print("="*60)

    examples = [
        ("Code Review Fix", example_code_review_fix),
        ("Multi-LLM Consensus", example_multi_llm_consensus),
        ("Custom Sequence", example_custom_sequence),
        ("Iterative Refinement", example_iterative_refinement),
        ("Quick Helpers", example_quick_helpers),
        ("Real Execution", example_real_execution),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n[ERROR in {name}]: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60 + "\n")

    print("Key Takeaways:")
    print("1. CLISequence: Chain multiple AI CLI tools")
    print("2. OutputParser: Extract structured data from outputs")
    print("3. WorkflowPatterns: Pre-built common workflows")
    print("4. Quick helpers: run_sequence(), quick_chain()")
    print("5. Real execution: Works with installed CLI tools")


if __name__ == "__main__":
    main()
