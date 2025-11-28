#!/usr/bin/env python3
"""
Headless Execution Demo for MeTaCLIagenT

Demonstrates non-interactive execution patterns inspired by Codex CLI.

Features demonstrated:
- One-shot execution with JSONL streaming
- Prompt reading from stdin/file
- Python wrapper for programmatic control
- Event logging and monitoring

Usage:
    # Run demo
    python examples/headless_execution_demo.py

    # Use as Python wrapper
    from examples.headless_execution_demo import EATSWrapper
    wrapper = EATSWrapper()
    wrapper.exec_one_shot("Analyze this codebase")
"""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eats_core.universal_orchestrator import UniversalOrchestrator, ExecutionConfig
from eats_core.universal_tool import POSIXTool, ToolCapabilities
from eats_core.headless_executor import HeadlessExecutor, PromptSource
from eats_core.event_logger import JSONLEventLogger


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 1: Basic One-Shot Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def example_one_shot():
    """
    Example: One-shot headless execution.

    Simulates: eats exec "List Python files in current directory"
    """
    print("=" * 70)
    print("Example 1: One-Shot Execution")
    print("=" * 70)

    # Create tools
    list_files = POSIXTool(
        name="list-python-files",
        command=["find", ".", "-name", "*.py", "-type", "f"],
        capabilities=ToolCapabilities(
            interactive=False,
            needs_pty=False,
            stateful=False,
        ),
    )

    # Create orchestrator
    orchestrator = UniversalOrchestrator()

    # Create event logger (to stdout)
    event_logger = JSONLEventLogger(auto_flush=True)

    # Create headless executor
    executor = HeadlessExecutor(
        orchestrator=orchestrator,
        session_manager=None,  # No persistence for this demo
        event_logger=event_logger,
    )

    # Execute
    prompt = ""  # Empty for find command
    result = await executor.execute_one_shot(
        prompt=prompt,
        tools=[list_files],
    )

    # Print results
    print(f"\n{'='*70}")
    print("Execution Result:")
    print(f"{'='*70}")
    print(f"Session ID: {result.session_id}")
    print(f"Success: {result.is_success()}")
    print(f"Duration: {result.total_duration:.2f}s")
    print(f"\nFinal Output (first 500 chars):")
    print(result.final_output[:500])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 2: JSONL Event Streaming to File
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def example_jsonl_streaming():
    """
    Example: JSONL event streaming to file.

    Simulates: eats exec --json "prompt" > events.jsonl
    """
    print("\n" + "=" * 70)
    print("Example 2: JSONL Event Streaming to File")
    print("=" * 70)

    # Create output directory
    output_dir = Path("logs/headless_demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    events_file = output_dir / "events.jsonl"
    output_file = output_dir / "final_output.txt"

    # Create tool
    echo_tool = POSIXTool(
        name="echo",
        command=["echo"],
        capabilities=ToolCapabilities(),
    )

    # Create orchestrator
    orchestrator = UniversalOrchestrator()

    # Create event logger to file
    with JSONLEventLogger.to_file(str(events_file)) as event_logger:
        # Create executor
        executor = HeadlessExecutor(
            orchestrator=orchestrator,
            event_logger=event_logger,
        )

        # Execute
        result = await executor.execute_one_shot(
            prompt="Hello from EATS Headless Mode!",
            tools=[echo_tool],
        )

    # Write final output
    executor.write_final_output(result, str(output_file))

    # Print results
    print(f"\nEvents logged to: {events_file}")
    print(f"Final output written to: {output_file}")
    print(f"\nEvent log contents:")
    print(events_file.read_text())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Example 3: Prompt Parsing (stdin, file, arg)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_prompt_parsing():
    """
    Example: Parse prompts from different sources.

    Demonstrates:
    - Direct argument
    - File reading
    - Stdin reading (simulated)
    """
    print("\n" + "=" * 70)
    print("Example 3: Prompt Parsing")
    print("=" * 70)

    # Parse from argument
    prompt1 = HeadlessExecutor.parse_prompt(prompt_arg="This is a direct prompt")
    print(f"\n1. From argument:")
    print(f"   Type: {prompt1.type}")
    print(f"   Content: {prompt1.content}")

    # Parse from file
    test_file = Path("logs/headless_demo/test_prompt.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("This is a prompt from a file")

    prompt2 = HeadlessExecutor.parse_prompt(filepath=str(test_file))
    print(f"\n2. From file:")
    print(f"   Type: {prompt2.type}")
    print(f"   Filepath: {prompt2.filepath}")
    print(f"   Content: {prompt2.content}")

    # Note: stdin parsing would require actual stdin input
    print(f"\n3. From stdin:")
    print(f"   (Use '-' as prompt argument to read from stdin)")
    print(f"   Example: echo 'my prompt' | eats exec -")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Python Wrapper Example
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EATSWrapper:
    """
    Python wrapper for programmatic EATS headless execution.

    Example usage:
        wrapper = EATSWrapper()
        result = wrapper.exec_one_shot("Analyze codebase")
        print(result.final_output)
    """

    def __init__(self):
        self.orchestrator = UniversalOrchestrator()

    def exec_one_shot(
        self,
        prompt: str,
        tools: list = None,
        log_events: bool = True,
    ) -> dict:
        """
        Execute one-shot prompt.

        Args:
            prompt: Prompt text
            tools: Optional list of tools (uses defaults if None)
            log_events: Enable JSONL event logging

        Returns:
            Result dictionary
        """
        # Default tools
        if tools is None:
            tools = [
                POSIXTool(
                    name="echo",
                    command=["echo"],
                    capabilities=ToolCapabilities(),
                )
            ]

        # Create event logger
        event_logger = JSONLEventLogger() if log_events else None

        # Create executor
        executor = HeadlessExecutor(
            orchestrator=self.orchestrator,
            event_logger=event_logger,
        )

        # Execute
        result = asyncio.run(executor.execute_one_shot(
            prompt=prompt,
            tools=tools,
        ))

        return result.to_dict()


async def example_python_wrapper():
    """Example: Using Python wrapper for programmatic control."""
    print("\n" + "=" * 70)
    print("Example 4: Python Wrapper")
    print("=" * 70)

    wrapper = EATSWrapper()

    # Execute simple prompt
    result = wrapper.exec_one_shot(
        prompt="Hello from Python wrapper!",
        log_events=False,  # Disable events for cleaner output
    )

    print(f"\nResult:")
    print(f"  Session ID: {result['session_id']}")
    print(f"  Success: {result['success']}")
    print(f"  Duration: {result['total_duration']:.2f}s")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Demo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("EATS Headless Execution Demo")
    print("Inspired by Codex CLI's exec command")
    print("=" * 70)

    # Run examples
    await example_one_shot()
    await example_jsonl_streaming()
    example_prompt_parsing()
    await example_python_wrapper()

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Implement 'eats exec' CLI command")
    print("2. Add playbook execution (Phase 6)")
    print("3. Add session resume (Phase 7)")
    print("4. Test with real AI tools (aider, claude-code)")


if __name__ == "__main__":
    asyncio.run(main())
