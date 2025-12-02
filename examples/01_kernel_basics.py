#!/usr/bin/env python3
"""
Kernel Layer Example - Process Spawning Basics

Demonstrates the metacli kernel layer with simple process execution.

This shows Layer 0 (Kernel) usage - raw process primitives without
any orchestration logic.
"""

import sys
import time

# Add parent to path for local testing
sys.path.insert(0, '/home/user/MeTaCLIagenT')

from metacli.kernel import Process, Security, SecurityError


def example_subprocess():
    """Example 1: Simple subprocess execution."""
    print("=" * 70)
    print("Example 1: Simple Subprocess (grep alternative)")
    print("=" * 70)

    # Spawn simple subprocess
    proc = Process.spawn(["echo", "Hello from MetaCLI Kernel!"], interactive=False)

    proc.start()
    print(f"✅ Process started (PID available via proc.proc.pid)")

    output = proc.read(timeout=1.0)
    print(f"📤 Output: {output.strip()}")

    proc.terminate()
    print(f"✅ Process terminated\n")


def example_security_validation():
    """Example 2: Security validation."""
    print("=" * 70)
    print("Example 2: Security Validation")
    print("=" * 70)

    security = Security()

    # Safe command
    safe_cmd = ["python3", "-c", "print('safe')"]
    print(f"Validating safe command: {safe_cmd}")
    try:
        security.validate_command(safe_cmd)
        print("✅ Command is SAFE\n")
    except SecurityError as e:
        print(f"❌ Command rejected: {e}\n")

    # Dangerous command
    dangerous_cmd = ["rm", "-rf", "/"]
    print(f"Validating dangerous command: {dangerous_cmd}")
    try:
        security.validate_command(dangerous_cmd)
        print("✅ Command is SAFE\n")
    except SecurityError as e:
        print(f"❌ Command rejected: {e}\n")


def example_python_execution():
    """Example 3: Execute Python code."""
    print("=" * 70)
    print("Example 3: Python Code Execution")
    print("=" * 70)

    # Validate first
    security = Security()
    cmd = ["python3", "-c", "for i in range(5): print(f'Count: {i}')"]

    print(f"Validating: python3 -c ...")
    security.validate_command(cmd)
    print("✅ Validation passed")

    # Execute
    proc = Process.spawn(cmd, interactive=False)
    proc.start()
    print("✅ Process started")

    output = proc.read(timeout=2.0)
    print(f"\n📤 Output:\n{output}")

    proc.terminate()
    print("✅ Process terminated\n")


def example_shell_escaping():
    """Example 4: Shell escaping."""
    print("=" * 70)
    print("Example 4: Shell Escaping")
    print("=" * 70)

    # Dangerous user input
    user_input = "'; rm -rf /; echo 'hacked"

    print(f"User input: {user_input}")
    print(f"Escaped: {Security.escape_shell(user_input)}")
    print("✅ Safely escaped for shell usage\n")


def example_custom_allowlist():
    """Example 5: Custom security allowlist."""
    print("=" * 70)
    print("Example 5: Custom Allowlist")
    print("=" * 70)

    # Create security with custom allowlist
    security = Security(allowlist={"echo", "python3", "custom-tool"})

    # Try allowed command
    print("Testing allowed command: echo")
    try:
        security.validate_command(["echo", "hello"])
        print("✅ echo is allowed")
    except SecurityError as e:
        print(f"❌ Rejected: {e}")

    # Try non-allowed command
    print("\nTesting non-allowed command: git")
    try:
        security.validate_command(["git", "status"])
        print("✅ git is allowed")
    except SecurityError as e:
        print(f"❌ Rejected: {e}")

    # Add to allowlist dynamically
    print("\nAdding 'git' to allowlist...")
    security.add_to_allowlist("git")

    print("Testing git again...")
    try:
        security.validate_command(["git", "status"])
        print("✅ git is now allowed\n")
    except SecurityError as e:
        print(f"❌ Rejected: {e}\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MetaCLI Kernel Layer Examples")
    print("Layer 0: Execution Primitives")
    print("=" * 70 + "\n")

    try:
        example_subprocess()
        example_security_validation()
        example_python_execution()
        example_shell_escaping()
        example_custom_allowlist()

        print("=" * 70)
        print("✅ All kernel examples completed successfully!")
        print("=" * 70)
        print("\nNext Steps:")
        print("- Layer 1 (Core): CLISequence for tool orchestration")
        print("- Layer 2 (Meta): Playbook-based workflows")
        print("- Layer 3 (Autonomous): Evolution and optimization")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
