#!/usr/bin/env python3
"""
EATS Quick Start - Minimal CLI Orchestration

This is the simplest entry point for running CLI tool sequences.
It demonstrates the correct execution flow with minimal dependencies.

Usage:
    python eats_quick.py                    # Run demo sequence
    python eats_quick.py --tool python      # Run with specific tool
    python eats_quick.py --prompt "hello"   # Custom prompt

Execution Flow:
    1. Transport Layer - PTY spawns CLI process
    2. CLI Sequence - Manages steps and output parsing
    3. Persistence - Saves results to logs/
    4. Cleanup - Terminates processes cleanly

Core Modules (minimal required):
    - eats_core/transport.py    : PTY/Tmux terminal control
    - eats_core/cli_orchestrator.py : Sequence management
    - eats_core/presets.py      : Tool configurations
    - eats_core/cli_persistence.py : Result storage
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Minimal imports for CLI orchestration
from eats_core.cli_orchestrator import CLISequence, OutputParser
from eats_core.transport import PTYTransport


def run_quick_demo():
    """Run a minimal demo of CLI orchestration."""
    print("=" * 60)
    print("EATS Quick Start - CLI Orchestration Demo")
    print("=" * 60)
    print()

    # Step 1: Create sequence (auto_save=False for demo)
    print("1. Creating CLI sequence...")
    seq = CLISequence(name="quick-demo", auto_save=False)

    # Step 2: Add a simple step
    print("2. Adding step: Python calculation")
    seq.add_step(
        tool_name="python",
        prompt="result = 2 + 2\nprint(f'2 + 2 = {result}')"
    )

    # Step 3: Run the sequence
    print("3. Running sequence...")
    print("-" * 40)
    result = seq.run()
    print("-" * 40)

    # Step 4: Display results
    print("\n4. Results:")
    print(f"   Status: {result['status']}")
    print(f"   Steps: {result['successful_steps']}/{result['total_steps']}")
    print(f"   Duration: {result.get('duration', 0):.2f}s")

    if result['steps']:
        step = result['steps'][0]
        output = step.get('raw_output', '')
        if '2 + 2 = 4' in output:
            print("   Output: 2 + 2 = 4 (correct!)")
        else:
            print(f"   Output: {output[:100]}")

    # Step 5: Cleanup
    print("\n5. Cleaning up...")
    seq.cleanup()

    print("\n" + "=" * 60)
    print("Demo complete! The execution flow was:")
    print("  PTYTransport -> CLISequence -> OutputParser -> Result")
    print("=" * 60)

    return 0 if result['status'] == 'completed' else 1


def run_custom(tool: str, prompt: str, save: bool = False):
    """Run a custom CLI sequence."""
    print(f"Running {tool} with prompt...")
    print("-" * 40)

    seq = CLISequence(name=f"custom-{tool}", auto_save=save)
    seq.add_step(tool_name=tool, prompt=prompt)

    result = seq.run()
    seq.cleanup()

    print("-" * 40)
    print(f"Status: {result['status']}")

    if result['steps']:
        output = result['steps'][0].get('raw_output', '')
        print(f"Output:\n{output[-500:]}")  # Last 500 chars

    return 0 if result['status'] == 'completed' else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='EATS Quick Start - Minimal CLI Orchestration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python eats_quick.py                         # Run demo
    python eats_quick.py --tool bash --prompt 'echo hello'
    python eats_quick.py --tool python --prompt 'print("hi")' --save

For full features, use:
    python eats_cli.py run <workflow>
    python run_core.py demo
        ''',
    )

    parser.add_argument(
        '--tool', '-t',
        default=None,
        help='CLI tool to run (python, bash, etc.)',
    )
    parser.add_argument(
        '--prompt', '-p',
        default=None,
        help='Prompt/command to send to tool',
    )
    parser.add_argument(
        '--save', '-s',
        action='store_true',
        help='Save results to database',
    )

    args = parser.parse_args()

    if args.tool and args.prompt:
        return run_custom(args.tool, args.prompt, args.save)
    else:
        return run_quick_demo()


if __name__ == '__main__':
    sys.exit(main())
