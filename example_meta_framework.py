#!/usr/bin/env python3
"""
Meta-Framework Example - Unified Orchestration

This demonstrates the new universal abstractions that unify all execution paths.

Shows:
1. Universal Tool abstraction (AI + POSIX + Custom tools)
2. Universal Orchestrator (single execution engine)
3. Multiple strategies (sequential, parallel, adaptive)
4. Clean, uniform interface

Run:
    python example_meta_framework.py
"""

import asyncio
from eats_core import (
    # Universal Meta-Framework
    UniversalTool,
    POSIXTool,
    AIAssistantTool,
    UniversalOrchestrator,
    ExecutionStrategy,
    ToolCapabilities,
)


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def example_1_posix_tools():
    """Example 1: POSIX tool pipeline (grep | wc)."""
    print_section("Example 1: POSIX Tool Pipeline")

    # Create POSIX tools
    echo_tool = POSIXTool(
        name="echo",
        command=["echo"],
        capabilities=ToolCapabilities(
            interactive=False,
            needs_pty=False,
            stateful=False,
        ),
        description="Echo text",
    )

    # Create orchestrator
    orchestrator = UniversalOrchestrator()

    # Execute single tool
    print("\n1. Single tool execution:")
    print("   Command: echo 'Hello from Meta-Framework!'")

    result = await orchestrator.execute(
        tools=echo_tool,
        inputs="Hello from Meta-Framework!",
    )

    print(f"   Status: {result.status.value}")
    print(f"   Output: {result.get_output().strip()}")
    print(f"   Duration: {result.total_duration:.3f}s")


async def example_2_sequential_execution():
    """Example 2: Sequential execution (pipeline)."""
    print_section("Example 2: Sequential Pipeline")

    # Create multiple echo tools to simulate a pipeline
    tool1 = POSIXTool(
        name="step1",
        command=["echo"],
        description="First step",
    )

    tool2 = POSIXTool(
        name="step2",
        command=["echo"],
        description="Second step",
    )

    tool3 = POSIXTool(
        name="step3",
        command=["echo"],
        description="Third step",
    )

    # Create orchestrator
    orchestrator = UniversalOrchestrator()

    # Execute sequentially
    print("\n2. Sequential execution (pipeline):")
    print("   step1 → step2 → step3")

    result = await orchestrator.execute_sequential(
        tools=[tool1, tool2, tool3],
        input_text="Starting pipeline...",
    )

    print(f"\n   Status: {result.status.value}")
    print(f"   Strategy: {result.strategy.value}")
    print(f"   Total tools: {result.total_tools}")
    print(f"   Successful: {result.successful_tools}")
    print(f"   Duration: {result.total_duration:.3f}s")

    print("\n   Individual results:")
    for i, tool_result in enumerate(result.tool_results, 1):
        print(f"     {i}. {tool_result.tool_name}: {tool_result.status.value}")


async def example_3_parallel_execution():
    """Example 3: Parallel execution."""
    print_section("Example 3: Parallel Execution")

    # Create multiple tools to execute in parallel
    tools = [
        POSIXTool(
            name=f"parallel_task_{i}",
            command=["echo"],
            description=f"Parallel task {i}",
        )
        for i in range(5)
    ]

    # Create orchestrator
    orchestrator = UniversalOrchestrator()

    # Execute in parallel
    print("\n3. Parallel execution (5 tools simultaneously):")

    result = await orchestrator.execute_parallel(
        tools=tools,
        inputs=[f"Task {i} output" for i in range(5)],
    )

    print(f"\n   Status: {result.status.value}")
    print(f"   Strategy: {result.strategy.value}")
    print(f"   Total tools: {result.total_tools}")
    print(f"   Successful: {result.successful_tools}")
    print(f"   Duration: {result.total_duration:.3f}s")

    print("\n   Parallel results:")
    for tool_result in result.tool_results:
        print(f"     • {tool_result.tool_name}: {tool_result.combined_output.strip()}")


async def example_4_automatic_strategy():
    """Example 4: Automatic strategy selection."""
    print_section("Example 4: Automatic Strategy Selection")

    # Create mix of tools
    fast_tools = [
        POSIXTool(
            name=f"fast_{i}",
            command=["echo"],
            capabilities=ToolCapabilities(
                stateful=False,
                long_running=False,
            ),
        )
        for i in range(3)
    ]

    # Orchestrator will automatically select parallel strategy
    orchestrator = UniversalOrchestrator()

    print("\n4. Automatic strategy (all tools are fast and stateless):")

    result = await orchestrator.execute(
        tools=fast_tools,
        inputs=["Fast task 1", "Fast task 2", "Fast task 3"],
        strategy=ExecutionStrategy.AUTO,  # Let orchestrator decide
    )

    print(f"\n   Auto-selected strategy: {result.strategy.value}")
    print(f"   Status: {result.status.value}")
    print(f"   Duration: {result.total_duration:.3f}s")
    print(f"   ✓ Orchestrator chose optimal strategy automatically!")


async def example_5_tool_from_config():
    """Example 5: Create tools from configuration."""
    print_section("Example 5: Tools from Configuration")

    # Define tool configurations
    tool_configs = [
        {
            "name": "grep",
            "command": ["grep", "--version"],
            "type": "posix_utility",
            "description": "Search tool",
            "capabilities": {
                "interactive": False,
                "needs_pty": False,
                "stateful": False,
            }
        },
    ]

    print("\n5. Creating tools from configuration:")

    for config in tool_configs:
        tool = UniversalTool.from_config(config)
        print(f"\n   Tool: {tool.name}")
        print(f"   Type: {tool.tool_type.value}")
        print(f"   Command: {' '.join(tool.command)}")
        print(f"   Interactive: {tool.capabilities.interactive}")


async def main():
    """Run all examples."""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  🌟 META-FRAMEWORK UNIFIED ORCHESTRATION DEMO 🌟".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("║" + "  Demonstrates the new universal abstractions that unify".center(68) + "║")
    print("║" + "  all execution paths into ONE powerful framework".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    # Run examples
    await example_1_posix_tools()
    await example_2_sequential_execution()
    await example_3_parallel_execution()
    await example_4_automatic_strategy()
    await example_5_tool_from_config()

    # Summary
    print_section("Summary")
    print("""
✅ Universal Tool Abstraction
   - Uniform interface for ANY CLI tool
   - AI assistants, POSIX utilities, custom apps

✅ Universal Orchestrator
   - ONE execution engine
   - Multiple strategies: sequential, parallel, adaptive
   - Automatic strategy selection

✅ Clean Architecture
   - Replaces fragmented execution paths
   - Self-similar patterns at all levels
   - Foundation for playbook system

NEXT STEPS:
   1. Create playbook YAML parser
   2. Integrate with existing CLISequence/SwarmController
   3. Add session management
   4. Implement template engine

The meta-framework foundation is solid! 🚀
    """)


if __name__ == "__main__":
    asyncio.run(main())
