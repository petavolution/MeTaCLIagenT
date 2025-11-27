# easy.py - Simple High-Level API for EATS
"""
Easy-to-use high-level API for common EATS operations.

This module provides simplified functions for:
- Spawning CLI tool agents
- Running tasks on multiple agents
- Storing and retrieving results

Example:
    from eats_core.easy import spawn_agent, run_task, get_results

    # Spawn a Python agent
    agent = spawn_agent('python')

    # Run a task
    result = run_task(agent, 'print(2+2)')

    # Store result
    save_result('calc', result)
"""

from __future__ import annotations
import time
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

from .core import AgentDNA, Agent
from .presets import get_cli_tool, create_cli_agent, CLI_TOOLS
from .persistence import get_state_manager, FileStorage, StateManager
from .pipeline import ResultPipeline, FusionMethod
from .judge import LLMJudge
from .logging import get_logger

logger = get_logger("easy")


# ============================================================
# Simple Agent Management
# ============================================================

@dataclass
class AgentHandle:
    """Simple handle for managing an agent."""
    agent: Agent
    name: str
    tool: str
    started: bool = False

    def start(self) -> "AgentHandle":
        """Start the agent."""
        if not self.started:
            self.agent.start()
            self.started = True
            logger.info(f"Started agent: {self.name}")
        return self

    def stop(self) -> None:
        """Stop the agent."""
        if self.started:
            self.agent.stop()
            self.started = False
            logger.info(f"Stopped agent: {self.name}")

    def send(self, text: str) -> None:
        """Send text to the agent."""
        if self.agent._transport:
            self.agent._transport.send(text)

    def read(self, timeout: float = 1.0) -> str:
        """Read output from the agent."""
        if self.agent._transport:
            return self.agent._transport.recv(timeout=timeout)
        return ""

    def run(self, command: str, wait: float = 0.5) -> str:
        """Send command and read response."""
        self.send(command)
        time.sleep(wait)
        return self.read()


def spawn_agent(
    tool: str = "python",
    name: Optional[str] = None,
    start: bool = True,
) -> AgentHandle:
    """
    Spawn an agent with a CLI tool.

    Args:
        tool: CLI tool name ('python', 'bash', 'gemini', 'aider', etc.)
        name: Optional agent name (defaults to tool name)
        start: Whether to start the agent immediately

    Returns:
        AgentHandle for controlling the agent

    Example:
        agent = spawn_agent('python')
        result = agent.run('print(2+2)')
        agent.stop()
    """
    # Get tool config or use as command
    tool_config = get_cli_tool(tool)
    if tool_config:
        dna = create_cli_agent(tool, role=name or tool)
    else:
        # Treat as raw command
        dna = AgentDNA(
            role=name or tool,
            cmd=tool.split() if isinstance(tool, str) else tool,
        )

    agent = Agent(dna, transport_type="pty")
    handle = AgentHandle(
        agent=agent,
        name=name or dna.role,
        tool=tool,
    )

    if start:
        handle.start()

    return handle


def spawn_multiple(
    tools: List[str],
    start: bool = True,
) -> List[AgentHandle]:
    """
    Spawn multiple agents with different tools.

    Args:
        tools: List of CLI tool names
        start: Whether to start all agents immediately

    Returns:
        List of AgentHandles

    Example:
        agents = spawn_multiple(['python', 'python', 'python'])
        for a in agents:
            a.run('print("Hello")')
    """
    return [spawn_agent(tool, name=f"{tool}_{i}", start=start)
            for i, tool in enumerate(tools)]


def stop_all(agents: List[AgentHandle]) -> None:
    """Stop all agents in a list."""
    for agent in agents:
        agent.stop()


# ============================================================
# Task Execution
# ============================================================

@dataclass
class TaskResult:
    """Result from running a task."""
    agent_name: str
    tool: str
    command: str
    output: str
    duration_ms: float
    success: bool = True
    error: Optional[str] = None


def run_task(
    agent: AgentHandle,
    command: str,
    wait: float = 1.0,
) -> TaskResult:
    """
    Run a task on an agent and get the result.

    Args:
        agent: AgentHandle to run the task on
        command: Command/prompt to send
        wait: Time to wait for response

    Returns:
        TaskResult with output

    Example:
        agent = spawn_agent('python')
        result = run_task(agent, 'print(sum(range(10)))')
        print(result.output)  # "45"
    """
    start = time.perf_counter()
    try:
        output = agent.run(command, wait=wait)
        duration = (time.perf_counter() - start) * 1000
        return TaskResult(
            agent_name=agent.name,
            tool=agent.tool,
            command=command,
            output=output.strip(),
            duration_ms=duration,
            success=True,
        )
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.error(f"Task error: {e}")
        return TaskResult(
            agent_name=agent.name,
            tool=agent.tool,
            command=command,
            output="",
            duration_ms=duration,
            success=False,
            error=str(e),
        )


def run_parallel(
    agents: List[AgentHandle],
    command: str,
    wait: float = 1.0,
) -> List[TaskResult]:
    """
    Run same task on multiple agents in parallel.

    Args:
        agents: List of agents to run on
        command: Command to send to all
        wait: Time to wait for responses

    Returns:
        List of TaskResults
    """
    # Send to all
    for agent in agents:
        agent.send(command)

    # Wait
    time.sleep(wait)

    # Collect results
    results = []
    for agent in agents:
        output = agent.read()
        results.append(TaskResult(
            agent_name=agent.name,
            tool=agent.tool,
            command=command,
            output=output.strip(),
            duration_ms=wait * 1000,
        ))

    return results


# ============================================================
# Result Storage
# ============================================================

_storage: Optional[StateManager] = None


def _get_storage() -> StateManager:
    """Get or create storage manager."""
    global _storage
    if _storage is None:
        _storage = StateManager(storage=FileStorage(".eats_data"))
    return _storage


def save_result(key: str, result: Union[TaskResult, Dict, Any]) -> None:
    """
    Save a result to persistent storage.

    Args:
        key: Storage key
        result: TaskResult or dict to save
    """
    storage = _get_storage()
    if isinstance(result, TaskResult):
        data = {
            "agent": result.agent_name,
            "tool": result.tool,
            "command": result.command,
            "output": result.output,
            "duration_ms": result.duration_ms,
            "success": result.success,
            "timestamp": time.time(),
        }
    else:
        data = result
    storage.storage.save(f"results/{key}", data)
    logger.info(f"Saved result: {key}")


def load_result(key: str) -> Optional[Dict]:
    """Load a result from storage."""
    return _get_storage().storage.load(f"results/{key}")


def list_results() -> List[str]:
    """List all saved result keys."""
    keys = _get_storage().storage.list_keys("results/")
    return [k.replace("results/", "") for k in keys]


# ============================================================
# Convenience Functions
# ============================================================

def quick_run(tool: str, command: str, wait: float = 1.0) -> str:
    """
    Quick one-shot: spawn agent, run command, return output.

    Args:
        tool: CLI tool to use
        command: Command to run
        wait: Time to wait for response

    Returns:
        Output string

    Example:
        output = quick_run('python', 'print(2**10)')
        # Returns: "1024"
    """
    agent = spawn_agent(tool)
    try:
        result = run_task(agent, command, wait=wait)
        return result.output
    finally:
        agent.stop()


def compare_tools(
    tools: List[str],
    command: str,
    wait: float = 2.0,
) -> Dict[str, str]:
    """
    Run same command on different tools and compare outputs.

    Args:
        tools: List of tool names
        command: Command to run on all
        wait: Time to wait

    Returns:
        Dict mapping tool name to output
    """
    agents = spawn_multiple(tools)
    try:
        results = run_parallel(agents, command, wait=wait)
        return {r.tool: r.output for r in results}
    finally:
        stop_all(agents)
