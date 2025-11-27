# universal_orchestrator.py - Unified Execution Engine
"""
Universal Orchestrator - The Heart of the Meta-Framework

This is the single, unified execution engine that replaces multiple
fragmented execution paths (SwarmController, CLISequence, ParallelExecutor).

Philosophy:
- ONE execution engine, multiple strategies
- Automatic strategy selection based on requirements
- Uniform interface regardless of execution mode
- Self-similar patterns at all levels

The orchestrator can execute:
- Sequential workflows (one tool after another)
- Parallel workflows (multiple tools concurrently)
- Adaptive workflows (dynamic routing based on results)
- Evolutionary workflows (genetic algorithm selection)

Usage:
    # Create orchestrator
    orchestrator = UniversalOrchestrator()

    # Sequential execution
    result = await orchestrator.execute_sequential([tool1, tool2, tool3])

    # Parallel execution
    results = await orchestrator.execute_parallel([tool1, tool2, tool3])

    # Adaptive execution (based on results)
    result = await orchestrator.execute_adaptive(tools, strategy_fn)

    # From playbook (declarative)
    result = await orchestrator.execute_playbook(playbook)
"""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Union
from enum import Enum
import time

from .universal_tool import (
    UniversalTool,
    ToolResult,
    ExecutionStatus,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Strategies
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExecutionStrategy(Enum):
    """Execution strategy for orchestration."""
    SEQUENTIAL = "sequential"      # One after another
    PARALLEL = "parallel"           # All at once
    ADAPTIVE = "adaptive"           # Dynamic routing based on results
    EVOLUTIONARY = "evolutionary"   # Genetic algorithm selection
    AUTO = "auto"                   # Automatic selection


@dataclass
class ExecutionConfig:
    """Configuration for orchestration execution."""
    strategy: ExecutionStrategy = ExecutionStrategy.AUTO
    max_parallel: int = 10          # Max parallel executions
    timeout: Optional[float] = None # Overall timeout
    retry_on_failure: bool = False
    max_retries: int = 3
    continue_on_error: bool = True  # Continue if one tool fails


@dataclass
class OrchestrationResult:
    """
    Result of orchestration execution.

    Contains results from all tools executed.
    """
    # Execution metadata
    strategy: ExecutionStrategy
    status: ExecutionStatus
    total_duration: float

    # Results
    tool_results: List[ToolResult] = field(default_factory=list)
    aggregated_output: str = ""

    # Statistics
    total_tools: int = 0
    successful_tools: int = 0
    failed_tools: int = 0

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        """Check if orchestration was successful."""
        return self.status == ExecutionStatus.COMPLETED and self.failed_tools == 0

    def get_output(self) -> str:
        """Get aggregated output from all tools."""
        if self.aggregated_output:
            return self.aggregated_output
        return "\n\n".join(r.combined_output for r in self.tool_results if r.combined_output)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Strategy Implementations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BaseStrategy(ABC):
    """Base class for execution strategies."""

    @abstractmethod
    async def execute(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        context: Dict[str, Any],
        config: ExecutionConfig,
    ) -> List[ToolResult]:
        """Execute tools according to strategy."""
        pass


class SequentialStrategy(BaseStrategy):
    """
    Sequential execution strategy.

    Executes tools one after another, passing output from one tool
    as input to the next (pipeline pattern).
    """

    async def execute(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        context: Dict[str, Any],
        config: ExecutionConfig,
    ) -> List[ToolResult]:
        """Execute tools sequentially."""
        results = []
        current_input = inputs[0] if inputs else ""

        for i, tool in enumerate(tools):
            # Use provided input or output from previous tool
            if i < len(inputs):
                current_input = inputs[i]

            # Execute tool
            result = await tool.execute(
                input_text=current_input,
                context=context,
                timeout=config.timeout,
            )

            results.append(result)

            # Stop on failure if configured
            if result.is_failure() and not config.continue_on_error:
                break

            # Pass output to next tool
            current_input = result.combined_output

        return results


class ParallelStrategy(BaseStrategy):
    """
    Parallel execution strategy.

    Executes all tools concurrently for maximum speed.
    """

    async def execute(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        context: Dict[str, Any],
        config: ExecutionConfig,
    ) -> List[ToolResult]:
        """Execute tools in parallel."""
        # Create tasks for all tools
        tasks = []
        for i, tool in enumerate(tools):
            input_text = inputs[i] if i < len(inputs) else inputs[0] if inputs else ""
            task = tool.execute(
                input_text=input_text,
                context=context,
                timeout=config.timeout,
            )
            tasks.append(task)

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ToolResult(
                    tool_name=tools[i].name,
                    status=ExecutionStatus.FAILED,
                    error=result,
                    error_message=str(result),
                ))
            else:
                final_results.append(result)

        return final_results


class AdaptiveStrategy(BaseStrategy):
    """
    Adaptive execution strategy.

    Routes execution dynamically based on results and context.
    Implements conditional logic and decision trees.
    """

    def __init__(self, router_fn: Optional[Callable] = None):
        """
        Initialize adaptive strategy.

        Args:
            router_fn: Function that decides which tool to execute next
                      Signature: (results, context) -> next_tool_index
        """
        self.router_fn = router_fn or self._default_router

    def _default_router(
        self,
        results: List[ToolResult],
        tools: List[UniversalTool],
        context: Dict[str, Any],
    ) -> Optional[int]:
        """Default routing logic: execute next tool if previous succeeded."""
        if not results:
            return 0  # Start with first tool

        last_result = results[-1]
        if last_result.is_success() and len(results) < len(tools):
            return len(results)  # Execute next tool

        return None  # Stop execution

    async def execute(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        context: Dict[str, Any],
        config: ExecutionConfig,
    ) -> List[ToolResult]:
        """Execute tools with adaptive routing."""
        results = []
        current_input = inputs[0] if inputs else ""

        while True:
            # Decide which tool to execute next
            next_index = self.router_fn(results, tools, context)

            if next_index is None or next_index >= len(tools):
                break

            # Get input for this tool
            if next_index < len(inputs):
                current_input = inputs[next_index]
            elif results:
                current_input = results[-1].combined_output

            # Execute tool
            result = await tools[next_index].execute(
                input_text=current_input,
                context=context,
                timeout=config.timeout,
            )

            results.append(result)

            # Update context with result
            context[f"result_{next_index}"] = result.to_dict()

        return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Universal Orchestrator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UniversalOrchestrator:
    """
    Universal Orchestration Engine.

    The single, unified execution engine for the meta-framework.
    Replaces fragmented execution paths with one adaptable orchestrator.

    Key Features:
    - Automatic strategy selection
    - Multiple execution modes (sequential, parallel, adaptive, evolutionary)
    - Uniform interface regardless of tools or strategy
    - Session management and state tracking
    - Result aggregation and synthesis
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        """
        Initialize universal orchestrator.

        Args:
            config: Execution configuration (or use defaults)
        """
        self.config = config or ExecutionConfig()

        # Execution strategies
        self.strategies = {
            ExecutionStrategy.SEQUENTIAL: SequentialStrategy(),
            ExecutionStrategy.PARALLEL: ParallelStrategy(),
            ExecutionStrategy.ADAPTIVE: AdaptiveStrategy(),
        }

        # State tracking
        self.execution_history: List[OrchestrationResult] = []

    # ─────────────────────────────────────────────────────
    # High-Level Execution Methods
    # ─────────────────────────────────────────────────────

    async def execute(
        self,
        tools: Union[UniversalTool, List[UniversalTool]],
        inputs: Union[str, List[str]],
        strategy: Optional[ExecutionStrategy] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """
        Execute tools with automatic strategy selection.

        This is the main entry point for orchestration.

        Args:
            tools: Single tool or list of tools to execute
            inputs: Single input or list of inputs
            strategy: Execution strategy (or auto-select)
            context: Execution context

        Returns:
            OrchestrationResult with all outputs
        """
        # Normalize inputs
        if isinstance(tools, UniversalTool):
            tools = [tools]
        if isinstance(inputs, str):
            inputs = [inputs]

        context = context or {}
        strategy = strategy or self._select_strategy(tools, context)

        # Execute with selected strategy
        return await self._execute_with_strategy(tools, inputs, strategy, context)

    async def execute_sequential(
        self,
        tools: List[UniversalTool],
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """Execute tools sequentially (pipeline)."""
        return await self.execute(
            tools=tools,
            inputs=[input_text],
            strategy=ExecutionStrategy.SEQUENTIAL,
            context=context,
        )

    async def execute_parallel(
        self,
        tools: List[UniversalTool],
        inputs: Union[str, List[str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """Execute tools in parallel."""
        return await self.execute(
            tools=tools,
            inputs=inputs if isinstance(inputs, list) else [inputs] * len(tools),
            strategy=ExecutionStrategy.PARALLEL,
            context=context,
        )

    async def execute_adaptive(
        self,
        tools: List[UniversalTool],
        input_text: str,
        router_fn: Callable,
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """Execute tools with adaptive routing."""
        # Create adaptive strategy with custom router
        adaptive_strategy = AdaptiveStrategy(router_fn)
        self.strategies[ExecutionStrategy.ADAPTIVE] = adaptive_strategy

        return await self.execute(
            tools=tools,
            inputs=[input_text],
            strategy=ExecutionStrategy.ADAPTIVE,
            context=context,
        )

    # ─────────────────────────────────────────────────────
    # Strategy Selection and Execution
    # ─────────────────────────────────────────────────────

    def _select_strategy(
        self,
        tools: List[UniversalTool],
        context: Dict[str, Any],
    ) -> ExecutionStrategy:
        """
        Automatically select optimal execution strategy.

        Args:
            tools: Tools to execute
            context: Execution context

        Returns:
            ExecutionStrategy to use
        """
        # If context specifies strategy, use it
        if "strategy" in context:
            return ExecutionStrategy(context["strategy"])

        # If only one tool, use sequential
        if len(tools) == 1:
            return ExecutionStrategy.SEQUENTIAL

        # If all tools are independent (stateless, fast), use parallel
        all_independent = all(
            not tool.capabilities.stateful and not tool.capabilities.long_running
            for tool in tools
        )
        if all_independent:
            return ExecutionStrategy.PARALLEL

        # Default to sequential for safety
        return ExecutionStrategy.SEQUENTIAL

    async def _execute_with_strategy(
        self,
        tools: List[UniversalTool],
        inputs: List[str],
        strategy: ExecutionStrategy,
        context: Dict[str, Any],
    ) -> OrchestrationResult:
        """
        Execute tools with specified strategy.

        Args:
            tools: Tools to execute
            inputs: Inputs for tools
            strategy: Execution strategy
            context: Execution context

        Returns:
            OrchestrationResult
        """
        start_time = time.time()

        # Handle AUTO strategy - select best strategy
        if strategy == ExecutionStrategy.AUTO:
            strategy = self._select_strategy(tools, context)

        # Get strategy implementation
        strategy_impl = self.strategies.get(strategy)
        if not strategy_impl:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Execute
        try:
            tool_results = await strategy_impl.execute(
                tools=tools,
                inputs=inputs,
                context=context,
                config=self.config,
            )

            # Build orchestration result
            result = OrchestrationResult(
                strategy=strategy,
                status=ExecutionStatus.COMPLETED,
                total_duration=time.time() - start_time,
                tool_results=tool_results,
                total_tools=len(tools),
                successful_tools=sum(1 for r in tool_results if r.is_success()),
                failed_tools=sum(1 for r in tool_results if r.is_failure()),
                context=context,
            )

        except Exception as e:
            # Execution failed
            result = OrchestrationResult(
                strategy=strategy,
                status=ExecutionStatus.FAILED,
                total_duration=time.time() - start_time,
                total_tools=len(tools),
                context=context,
            )
            result.artifacts["error"] = str(e)

        # Store in history
        self.execution_history.append(result)

        return result

    # ─────────────────────────────────────────────────────
    # Convenience Methods
    # ─────────────────────────────────────────────────────

    async def chain(
        self,
        *tools: UniversalTool,
        input_text: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """
        Chain tools in a pipeline (tool1 | tool2 | tool3).

        Args:
            *tools: Tools to chain
            input_text: Initial input
            context: Execution context

        Returns:
            OrchestrationResult
        """
        return await self.execute_sequential(
            tools=list(tools),
            input_text=input_text,
            context=context,
        )

    async def fanout(
        self,
        *tools: UniversalTool,
        input_text: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """
        Fan out to multiple tools in parallel (same input to all).

        Args:
            *tools: Tools to execute
            input_text: Input for all tools
            context: Execution context

        Returns:
            OrchestrationResult
        """
        return await self.execute_parallel(
            tools=list(tools),
            inputs=input_text,
            context=context,
        )

    def get_history(self) -> List[OrchestrationResult]:
        """Get execution history."""
        return self.execution_history

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
