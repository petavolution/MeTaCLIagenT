#!/usr/bin/env python3
"""
Mock AI CLI Tool - Simple random output generator

This tool outputs random data to test the orchestration system.
Much simpler than realistic AI responses - just proves data flows correctly.

Usage:
    python mock_ai_cli.py [--mode MODE]

Output format (always 2 parts):
    1. Base64 encoded random 128-char string (looks like text output)
    2. 256-char random hex string (looks like binary/hash data)

This enables testing the full orchestration workflow without requiring
actual AI CLI tools to be installed.
"""

import sys
import time
import random
import argparse
import base64
import secrets


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Random Output Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_random_output(mode: str = "default") -> str:
    """
    Generate random output with 2 parts:
    1. Base64 encoded random 128-char string
    2. 256-char hex string

    Args:
        mode: Mode identifier (coder, reviewer, fixer, etc.) - included in output

    Returns:
        Formatted random output
    """
    # Part 1: Random 128-char string, base64 encoded
    random_bytes = secrets.token_bytes(96)  # 96 bytes -> 128 chars base64
    part1 = base64.b64encode(random_bytes).decode('ascii')

    # Part 2: 256-char hex string
    part2 = secrets.token_hex(128)  # 128 bytes -> 256 hex chars

    # Format output
    output = f"""
Mock AI CLI ({mode} mode) - Response

Part 1 (base64 random text):
{part1}

Part 2 (hex random data):
{part2}

---
Generated at: {time.time()}
Mode: {mode}
"""
    return output


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Interactive Mode
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def interactive_mode(mode: str):
    """
    Run in interactive mode - accepts prompts and responds with random data.

    This simulates how real AI CLI tools work (stay open, respond to input).
    """
    print(f"Mock AI CLI ({mode} mode) - Ready!")
    print("Type your prompts (Ctrl+D to exit):")
    print()

    try:
        while True:
            # Read input (could be from orchestrator)
            try:
                line = input()
            except EOFError:
                break

            if not line.strip():
                continue

            # Simulate thinking time (0.1-0.3 seconds)
            time.sleep(random.uniform(0.1, 0.3))

            # Generate random response
            response = generate_random_output(mode)
            print(response)
            print()  # Blank line between responses

            # Flush output (important for PTY communication)
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nExiting...")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(description="Mock AI CLI Tool")
    parser.add_argument(
        "--mode",
        choices=["coder", "reviewer", "fixer", "interactive"],
        default="interactive",
        help="Tool mode (default: interactive)"
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
        response = generate_random_output(args.mode)
        print(response)
    else:
        # Interactive mode
        interactive_mode(args.mode)


if __name__ == "__main__":
    main()
