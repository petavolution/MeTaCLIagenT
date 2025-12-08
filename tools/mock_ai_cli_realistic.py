#!/usr/bin/env python3
"""
Realistic Mock AI CLI - Simulates AI coding assistant output

Outputs two-part format:
1. Base64-encoded 128-char random string (simulated text output)
2. 256-char hex sequence

Randomly injects keywords: 'identified', 'error', 'complete', 'refactor', 'optimize'
"""

import sys
import random
import base64
import argparse
from typing import List

# Keywords that can appear in output
KEYWORDS = ['identified', 'error', 'complete', 'refactor', 'optimize']

# Common AI assistant response patterns
RESPONSE_TEMPLATES = [
    "I've analyzed the code and {keyword} {count} issues that need attention.",
    "The audit is {keyword}. Found {count} potential improvements.",
    "I've {keyword} the following patterns in your codebase.",
    "Based on my analysis, I recommend to {keyword} these components.",
    "The current implementation has been {keyword} for quality.",
]


def generate_realistic_text(prompt: str = "", inject_keyword: bool = True) -> str:
    """
    Generate realistic-looking AI response text.

    Args:
        prompt: Input prompt (can influence response)
        inject_keyword: Whether to inject a keyword

    Returns:
        Realistic response text (will be base64 encoded)
    """
    # Randomly select response pattern
    template = random.choice(RESPONSE_TEMPLATES)

    # Inject keyword if requested
    if inject_keyword and random.random() > 0.3:  # 70% chance
        keyword = random.choice(KEYWORDS)
        count = random.randint(1, 15)
        text = template.format(keyword=keyword, count=count)
    else:
        # Generic response without keyword
        text = f"Analysis complete. Processing {random.randint(1, 20)} items from input."

    # Pad to approximately 128 chars
    while len(text) < 100:
        text += f" Additional context: {random.choice(['quality checks passed', 'optimization applied', 'validation complete', 'metrics collected'])}."

    # Truncate to reasonable length
    return text[:128]


def generate_hex_sequence(length: int = 256) -> str:
    """
    Generate random hex sequence.

    Args:
        length: Length of hex string (must be even)

    Returns:
        Hex string
    """
    num_bytes = length // 2
    random_bytes = random.randbytes(num_bytes)
    return random_bytes.hex()


def generate_output(prompt: str = "", force_keyword: str = None) -> str:
    """
    Generate two-part output format.

    Args:
        prompt: Input prompt
        force_keyword: Force specific keyword to appear

    Returns:
        Two-part output: base64 + hex
    """
    # Generate realistic text
    text = generate_realistic_text(prompt, inject_keyword=(force_keyword is None))

    # Inject forced keyword if specified
    if force_keyword and force_keyword in KEYWORDS:
        text = text.replace("complete", force_keyword, 1)

    # Encode to base64
    text_bytes = text.encode('utf-8')
    base64_output = base64.b64encode(text_bytes).decode('utf-8')

    # Generate hex sequence
    hex_output = generate_hex_sequence(256)

    # Format output
    output = f"[OUTPUT-PART-1-BASE64]\n{base64_output}\n\n[OUTPUT-PART-2-HEX]\n{hex_output}\n"

    return output


def interactive_mode():
    """Run in interactive mode - read prompts from stdin."""
    print("Mock AI CLI v1.0 (Interactive Mode)", file=sys.stderr)
    print("Ready to process commands...", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        while True:
            # Read prompt from stdin
            try:
                prompt = input()
            except EOFError:
                break

            if not prompt.strip():
                continue

            # Check for exit commands
            if prompt.lower() in ['exit', 'quit', 'q']:
                break

            # Generate and output response
            output = generate_output(prompt)
            print(output)
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nExiting...", file=sys.stderr)


def single_shot_mode(prompt: str, keyword: str = None):
    """Run in single-shot mode - process one prompt and exit."""
    output = generate_output(prompt, force_keyword=keyword)
    print(output)


def main():
    parser = argparse.ArgumentParser(
        description="Realistic Mock AI CLI - Simulates AI coding assistant"
    )
    parser.add_argument(
        'prompt',
        nargs='*',
        help='Prompt to process (if omitted, enters interactive mode)'
    )
    parser.add_argument(
        '-k', '--keyword',
        choices=KEYWORDS,
        help='Force specific keyword to appear in output'
    )
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Force interactive mode'
    )

    args = parser.parse_args()

    # Determine mode
    if args.interactive or not args.prompt:
        interactive_mode()
    else:
        prompt_text = ' '.join(args.prompt)
        single_shot_mode(prompt_text, args.keyword)


if __name__ == '__main__':
    main()
