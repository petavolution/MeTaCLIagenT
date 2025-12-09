#!/usr/bin/env python3
"""
Mock AI CLI Tool - Enhanced for Testing Meta-Orchestration

Simulates AI CLI tools with controllable keyword injection for testing
the orchestration framework's pattern detection and response system.

Usage:
    python mock_ai_cli.py                           # Interactive mode
    python mock_ai_cli.py --mode coder              # Specific mode
    python mock_ai_cli.py --inject error            # Force keyword
    python mock_ai_cli.py "prompt text"             # One-shot mode

Output Format (always 2 parts):
    1. Base64 encoded 128-char string (simulated text output)
    2. 256-char hex string (simulated binary/hash data)

Keywords for Detection (randomly injected):
    - 'identified' : Found something noteworthy
    - 'error'      : Problem detected
    - 'complete'   : Task finished
    - 'refactor'   : Suggest refactoring
    - 'optimize'   : Suggest optimization
    - 'continue'   : More work needed

The controller framework should detect these keywords and route
to appropriate response handlers.
"""

import sys
import time
import random
import argparse
import base64
import secrets
import hashlib
from typing import Optional, List, Dict

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Keywords for Controller Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KEYWORDS = [
    "identified",
    "error",
    "complete",
    "refactor",
    "optimize",
    "continue",
]

# Keyword probability based on mode
MODE_KEYWORD_WEIGHTS: Dict[str, Dict[str, float]] = {
    "coder": {
        "complete": 0.4,
        "continue": 0.3,
        "refactor": 0.15,
        "error": 0.1,
        "identified": 0.05,
    },
    "reviewer": {
        "identified": 0.35,
        "refactor": 0.25,
        "optimize": 0.2,
        "error": 0.15,
        "complete": 0.05,
    },
    "fixer": {
        "complete": 0.5,
        "error": 0.25,
        "continue": 0.15,
        "refactor": 0.1,
    },
    "auditor": {
        "identified": 0.4,
        "error": 0.25,
        "optimize": 0.2,
        "refactor": 0.15,
    },
    "default": {
        "complete": 0.25,
        "continue": 0.2,
        "identified": 0.2,
        "refactor": 0.15,
        "error": 0.1,
        "optimize": 0.1,
    },
}


def select_keywords(mode: str, count: int = 2, force_inject: Optional[str] = None) -> List[str]:
    """
    Select keywords to inject based on mode probabilities.

    Args:
        mode: Operating mode (coder, reviewer, fixer, etc.)
        count: Number of keywords to inject (1-3)
        force_inject: Force a specific keyword to be included

    Returns:
        List of keywords to inject into output
    """
    weights = MODE_KEYWORD_WEIGHTS.get(mode, MODE_KEYWORD_WEIGHTS["default"])
    keywords = list(weights.keys())
    probs = [weights.get(k, 0.1) for k in keywords]

    # Normalize probabilities
    total = sum(probs)
    probs = [p/total for p in probs]

    # Select keywords weighted by probability
    selected = []
    if force_inject and force_inject in KEYWORDS:
        selected.append(force_inject)
        count -= 1

    # Random selection with weights
    available = [(k, p) for k, p in zip(keywords, probs) if k not in selected]
    for _ in range(min(count, len(available))):
        if random.random() < 0.7:  # 70% chance to inject each keyword
            r = random.random()
            cumsum = 0
            for k, p in available:
                cumsum += p
                if r < cumsum:
                    if k not in selected:
                        selected.append(k)
                    break

    return selected


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_keyword_context(keyword: str) -> str:
    """Generate contextual sentence for a keyword."""
    contexts = {
        "identified": [
            "I have identified a potential issue in the implementation.",
            "Pattern identified: consider reviewing this section.",
            "Security concern identified in input validation.",
        ],
        "error": [
            "Error detected in the parsing logic.",
            "Syntax error found on line 42.",
            "Runtime error possible with null input.",
        ],
        "complete": [
            "Task complete. All tests passing.",
            "Implementation complete and ready for review.",
            "Refactoring complete. Code coverage improved.",
        ],
        "refactor": [
            "Suggest refactor: extract method for readability.",
            "This section needs refactor to reduce complexity.",
            "Refactor opportunity: consolidate duplicate logic.",
        ],
        "optimize": [
            "Performance can be improved: optimize database query.",
            "Memory usage can be reduced: optimize data structure.",
            "Consider lazy loading to optimize initial load time.",
        ],
        "continue": [
            "Please continue with the next step.",
            "More context needed to continue analysis.",
            "Ready to continue with implementation.",
        ],
    }
    return random.choice(contexts.get(keyword, [f"Status: {keyword}"]))


def generate_output(
    mode: str = "default",
    force_inject: Optional[str] = None,
    prompt: str = "",
) -> str:
    """
    Generate mock AI output with keyword injection.

    Args:
        mode: Operating mode (coder, reviewer, fixer, auditor, default)
        force_inject: Force a specific keyword into output
        prompt: Input prompt (used for deterministic hash)

    Returns:
        Formatted output with:
        - Keywords injected in readable text
        - Base64 encoded random 128-char string
        - 256-char hex string
    """
    # Select keywords to inject
    keywords = select_keywords(mode, count=2, force_inject=force_inject)

    # Generate keyword context sentences
    keyword_lines = [generate_keyword_context(kw) for kw in keywords]

    # Part 1: Random 128-char string, base64 encoded
    random_bytes = secrets.token_bytes(96)  # 96 bytes -> 128 chars base64
    part1_base64 = base64.b64encode(random_bytes).decode('ascii')

    # Part 2: 256-char hex string
    part2_hex = secrets.token_hex(128)  # 128 bytes -> 256 hex chars

    # Generate deterministic hash from prompt (for lookup table testing)
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16] if prompt else "0" * 16

    # Format output
    output = f"""
[Mock AI CLI - {mode} mode]
Prompt hash: {prompt_hash}

Analysis:
{chr(10).join(f'  - {line}' for line in keyword_lines)}

Keywords detected: [{', '.join(keywords)}]

=== Output Part 1 (Base64 Text Simulation) ===
{part1_base64}

=== Output Part 2 (Hex Data) ===
{part2_hex}

---
timestamp: {time.time():.6f}
mode: {mode}
keywords: {','.join(keywords)}
"""
    return output


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Interactive Mode
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def interactive_mode(mode: str, force_inject: Optional[str] = None):
    """
    Run in interactive mode - accepts prompts and responds.

    This simulates how real AI CLI tools work (stay open, respond to input).
    The orchestrator can send prompts and receive keyword-injected responses.
    """
    print(f"Mock AI CLI ({mode} mode) - Ready!")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    if force_inject:
        print(f"Force inject: {force_inject}")
    print("Type prompts (Ctrl+D to exit):")
    print()
    sys.stdout.flush()

    try:
        while True:
            try:
                line = input()
            except EOFError:
                break

            if not line.strip():
                continue

            # Simulate thinking time (0.1-0.5 seconds)
            time.sleep(random.uniform(0.1, 0.5))

            # Generate response with keywords
            response = generate_output(
                mode=mode,
                force_inject=force_inject,
                prompt=line.strip(),
            )
            print(response)
            print()  # Blank line between responses
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nExiting...")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="Mock AI CLI Tool with Keyword Injection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Keywords for detection:
  identified  - Found something noteworthy
  error       - Problem detected
  complete    - Task finished
  refactor    - Suggest refactoring
  optimize    - Suggest optimization
  continue    - More work needed

Examples:
  python mock_ai_cli.py                    # Interactive default mode
  python mock_ai_cli.py --mode reviewer    # Reviewer mode (more 'identified')
  python mock_ai_cli.py --inject error     # Force 'error' keyword
  python mock_ai_cli.py "Write hello"      # One-shot mode
        """,
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["coder", "reviewer", "fixer", "auditor", "default"],
        default="default",
        help="Tool mode affects keyword probability distribution"
    )
    parser.add_argument(
        "--inject", "-i",
        choices=KEYWORDS,
        default=None,
        help="Force inject a specific keyword"
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt to process (if not interactive)"
    )

    args = parser.parse_args()

    if args.prompt:
        # One-shot mode
        prompt = " ".join(args.prompt)
        response = generate_output(
            mode=args.mode,
            force_inject=args.inject,
            prompt=prompt,
        )
        print(response)
    else:
        # Interactive mode
        interactive_mode(args.mode, args.inject)


if __name__ == "__main__":
    main()
