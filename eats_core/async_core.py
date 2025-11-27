# async_core.py - Async Multi-Agent Concurrency
"""
Async patterns for concurrent multi-agent execution.

Based on best practices:
- asyncio.TaskGroup for safe concurrent execution
- asyncio.gather for parallel agent runs
- Proper cancellation and error handling
- Rate limiting and backpressure
"""

from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Awaitable, TypeVar
from enum import Enum
import random

from .core import Agent, AgentDNA, Transport
from .judge import LLMJudge, Fitness

T = TypeVar('T')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Async Agent Wrapper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AsyncAgent:
    """
    Async wrapper for Agent with non-blocking I/O.

    Runs blocking PTY operations in executor to avoid blocking event loop.
    """

    def __init__(self, agent: Agent):
        self.agent = agent
        self._lock = asyncio.Lock()

    @classmethod
    def from_dna(cls, dna: AgentDNA) -> AsyncAgent:
        return cls(Agent(dna))

    async def start(self) -> None:
        """Start agent in executor (non-blocking)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.agent.start)

    async def ask(
        self,
        prompt: str,
        timeout: Optional[float] = None,
    ) -> str:
        """Send prompt and get response (non-blocking)."""
        async with self._lock:
            loop = asyncio.get_event_loop()
            wait_time = timeout or self.agent.dna.timeout

            def _ask():
                return self.agent.ask(prompt, wait_seconds=wait_time)

            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, _ask),
                    timeout=wait_time + 5,  # Extra buffer
                )
            except asyncio.TimeoutError:
                return "[TIMEOUT]"

    async def stop(self) -> None:
        """Stop agent (non-blocking)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.agent.stop)

    @property
    def id(self) -> str:
        return self.agent.id

    @property
    def dna(self) -> AgentDNA:
        return self.agent.dna


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Concurrent Execution Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TaskResult:
    """Result from a concurrent task."""
    agent_id: str
    prompt: str
    response: str
    duration: float
    success: bool
    error: Optional[str] = None
    fitness: Optional[float] = None


async def run_parallel(
    agents: List[AsyncAgent],
    prompt: str,
    timeout: float = 30.0,
) -> List[TaskResult]:
    """
    Run same prompt on multiple agents in parallel using gather.

    All agents execute concurrently; results returned when all complete.
    """
    async def run_one(agent: AsyncAgent) -> TaskResult:
        start = time.time()
        try:
            response = await agent.ask(prompt, timeout=timeout)
            return TaskResult(
                agent_id=agent.id,
                prompt=prompt,
                response=response,
                duration=time.time() - start,
                success=True,
            )
        except Exception as e:
            return TaskResult(
                agent_id=agent.id,
                prompt=prompt,
                response="",
                duration=time.time() - start,
                success=False,
                error=str(e),
            )

    results = await asyncio.gather(*[run_one(a) for a in agents])
    return list(results)


async def run_with_taskgroup(
    agents: List[AsyncAgent],
    prompt: str,
    timeout: float = 30.0,
    on_complete: Optional[Callable[[TaskResult], Awaitable[None]]] = None,
) -> List[TaskResult]:
    """
    Run using TaskGroup with automatic cancellation on failure.

    Safer than gather - cancels remaining tasks if one fails.
    """
    results: List[TaskResult] = []
    results_lock = asyncio.Lock()

    async def run_one(agent: AsyncAgent) -> None:
        start = time.time()
        try:
            response = await agent.ask(prompt, timeout=timeout)
            result = TaskResult(
                agent_id=agent.id,
                prompt=prompt,
                response=response,
                duration=time.time() - start,
                success=True,
            )
        except Exception as e:
            result = TaskResult(
                agent_id=agent.id,
                prompt=prompt,
                response="",
                duration=time.time() - start,
                success=False,
                error=str(e),
            )

        async with results_lock:
            results.append(result)

        if on_complete:
            await on_complete(result)

    async with asyncio.TaskGroup() as tg:
        for agent in agents:
            tg.create_task(run_one(agent))

    return results


async def run_first_wins(
    agents: List[AsyncAgent],
    prompt: str,
    timeout: float = 30.0,
) -> TaskResult:
    """
    Run on multiple agents, return first successful response.

    Cancels remaining agents once one completes successfully.
    """
    async def run_one(agent: AsyncAgent) -> TaskResult:
        start = time.time()
        response = await agent.ask(prompt, timeout=timeout)
        return TaskResult(
            agent_id=agent.id,
            prompt=prompt,
            response=response,
            duration=time.time() - start,
            success=bool(response and response != "[TIMEOUT]"),
        )

    tasks = [asyncio.create_task(run_one(a)) for a in agents]

    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining
        for task in pending:
            task.cancel()

        # Return first completed
        for task in done:
            result = task.result()
            if result.success:
                return result

        # All failed - return first anyway
        return next(iter(done)).result()

    except Exception as e:
        return TaskResult(
            agent_id="unknown",
            prompt=prompt,
            response="",
            duration=0,
            success=False,
            error=str(e),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Rate-Limited Worker Pool
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkerPool:
    """
    Async worker pool with rate limiting and backpressure.

    Manages a pool of agents, distributing tasks with concurrency control.
    """

    def __init__(
        self,
        agents: List[AsyncAgent],
        max_concurrent: int = 4,
        rate_limit: float = 0.0,  # Min seconds between task starts
    ):
        self.agents = agents
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._last_task_time = 0.0
        self._rate_lock = asyncio.Lock()

        # Round-robin agent selection
        self._agent_idx = 0
        self._agent_lock = asyncio.Lock()

    async def _get_next_agent(self) -> AsyncAgent:
        """Get next agent in round-robin fashion."""
        async with self._agent_lock:
            agent = self.agents[self._agent_idx]
            self._agent_idx = (self._agent_idx + 1) % len(self.agents)
            return agent

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting between tasks."""
        if self.rate_limit <= 0:
            return

        async with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_task_time
            if elapsed < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed)
            self._last_task_time = time.time()

    async def submit(self, prompt: str, timeout: float = 30.0) -> TaskResult:
        """Submit a single task to the pool."""
        async with self._semaphore:
            await self._apply_rate_limit()
            agent = await self._get_next_agent()

            start = time.time()
            try:
                response = await agent.ask(prompt, timeout=timeout)
                return TaskResult(
                    agent_id=agent.id,
                    prompt=prompt,
                    response=response,
                    duration=time.time() - start,
                    success=True,
                )
            except Exception as e:
                return TaskResult(
                    agent_id=agent.id,
                    prompt=prompt,
                    response="",
                    duration=time.time() - start,
                    success=False,
                    error=str(e),
                )

    async def map(
        self,
        prompts: List[str],
        timeout: float = 30.0,
    ) -> List[TaskResult]:
        """Map multiple prompts across pool concurrently."""
        tasks = [self.submit(p, timeout) for p in prompts]
        return await asyncio.gather(*tasks)

    async def shutdown(self) -> None:
        """Stop all agents in pool."""
        await asyncio.gather(*[a.stop() for a in self.agents])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Async Evolution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AsyncEvolutionConfig:
    """Config for async evolution."""
    population_size: int = 4
    survivors: int = 2
    generations: int = 3
    mutation_rate: float = 0.3
    task_prompt: str = ""
    timeout: float = 30.0
    parallel_eval: bool = True  # Evaluate population in parallel


@dataclass
class GenerationStats:
    """Statistics for one generation."""
    generation: int
    best_fitness: float
    avg_fitness: float
    best_agent_id: str
    results: List[TaskResult]


class AsyncEvolution:
    """
    Async evolutionary optimization with parallel evaluation.

    Evaluates entire population concurrently for faster evolution.
    """

    def __init__(
        self,
        config: AsyncEvolutionConfig,
        judge: Optional[LLMJudge] = None,
    ):
        self.config = config
        self.judge = judge or LLMJudge()
        self.history: List[GenerationStats] = []

    async def run(
        self,
        base_dna: AgentDNA,
        on_generation: Optional[Callable[[GenerationStats], Awaitable[None]]] = None,
    ) -> AgentDNA:
        """
        Run async evolution with parallel fitness evaluation.

        Returns best performing DNA.
        """
        # Initialize population
        population = self._init_population(base_dna)

        for gen in range(self.config.generations):
            # Create async agents
            agents = [AsyncAgent.from_dna(dna) for dna in population]

            # Start all agents
            await asyncio.gather(*[a.start() for a in agents])

            try:
                # Evaluate in parallel or sequential
                if self.config.parallel_eval:
                    results = await run_parallel(
                        agents,
                        self.config.task_prompt,
                        timeout=self.config.timeout,
                    )
                else:
                    results = []
                    for agent in agents:
                        r = await self._eval_one(agent)
                        results.append(r)

                # Score with judge
                for result in results:
                    if result.success:
                        fitness = self.judge.evaluate(
                            self.config.task_prompt,
                            result.response,
                        )
                        result.fitness = fitness.score

                # Calculate stats
                scored = [r for r in results if r.fitness is not None]
                if scored:
                    best = max(scored, key=lambda r: r.fitness or 0)
                    avg = sum(r.fitness or 0 for r in scored) / len(scored)
                else:
                    best = results[0] if results else None
                    avg = 0.0

                stats = GenerationStats(
                    generation=gen,
                    best_fitness=best.fitness if best else 0,
                    avg_fitness=avg,
                    best_agent_id=best.agent_id if best else "",
                    results=results,
                )
                self.history.append(stats)

                if on_generation:
                    await on_generation(stats)

                # Select and reproduce
                if gen < self.config.generations - 1:
                    population = self._select_and_reproduce(
                        population, results, gen + 1
                    )

            finally:
                # Stop all agents
                await asyncio.gather(*[a.stop() for a in agents])

        # Return best DNA
        best_idx = 0
        best_fit = 0.0
        for i, dna in enumerate(population):
            avg = sum(dna.fitness_history) / len(dna.fitness_history) if dna.fitness_history else 0
            if avg > best_fit:
                best_fit = avg
                best_idx = i

        return population[best_idx]

    async def _eval_one(self, agent: AsyncAgent) -> TaskResult:
        """Evaluate single agent."""
        start = time.time()
        try:
            response = await agent.ask(
                self.config.task_prompt,
                timeout=self.config.timeout,
            )
            return TaskResult(
                agent_id=agent.id,
                prompt=self.config.task_prompt,
                response=response,
                duration=time.time() - start,
                success=True,
            )
        except Exception as e:
            return TaskResult(
                agent_id=agent.id,
                prompt=self.config.task_prompt,
                response="",
                duration=time.time() - start,
                success=False,
                error=str(e),
            )

    def _init_population(self, base: AgentDNA) -> List[AgentDNA]:
        """Create initial population."""
        pop = [base]
        for _ in range(self.config.population_size - 1):
            pop.append(base.mutate(self.config.mutation_rate))
        return pop

    def _select_and_reproduce(
        self,
        population: List[AgentDNA],
        results: List[TaskResult],
        generation: int,
    ) -> List[AgentDNA]:
        """Select survivors and create next generation."""
        # Map agent_id to fitness
        fitness_map = {r.agent_id: r.fitness or 0 for r in results}

        # Sort by fitness
        sorted_pop = sorted(
            population,
            key=lambda d: fitness_map.get(f"{d.role}_{d.id}", 0),
            reverse=True,
        )

        # Keep survivors
        survivors = sorted_pop[:self.config.survivors]

        # Create offspring
        next_gen = list(survivors)
        while len(next_gen) < self.config.population_size:
            parent = random.choice(survivors)
            child = parent.mutate(self.config.mutation_rate)
            next_gen.append(child)

        return next_gen


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Orchestrator-Worker Pattern
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OrchestratorWorker:
    """
    Orchestrator-worker pattern: one agent decomposes, workers execute.

    The orchestrator breaks down complex tasks, delegates to workers,
    and synthesizes results.
    """

    def __init__(
        self,
        orchestrator: AsyncAgent,
        workers: List[AsyncAgent],
    ):
        self.orchestrator = orchestrator
        self.workers = workers

    async def execute(
        self,
        task: str,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Execute task using orchestrator-worker pattern.

        1. Orchestrator decomposes task into subtasks
        2. Workers execute subtasks in parallel
        3. Orchestrator synthesizes results
        """
        # Step 1: Decompose
        decompose_prompt = f"""Break this task into {len(self.workers)} subtasks.
Return ONLY a numbered list, one subtask per line.

TASK: {task}"""

        subtasks_response = await self.orchestrator.ask(decompose_prompt, timeout=timeout)
        subtasks = self._parse_subtasks(subtasks_response)

        # Step 2: Execute in parallel
        worker_results = []
        if subtasks:
            # Assign subtasks to workers
            for i, (worker, subtask) in enumerate(zip(self.workers, subtasks)):
                worker_results.append((worker, subtask))

            results = await asyncio.gather(*[
                worker.ask(subtask, timeout=timeout)
                for worker, subtask in worker_results
            ])
        else:
            # Fallback: all workers on original task
            results = await run_parallel(self.workers, task, timeout)
            results = [r.response for r in results]

        # Step 3: Synthesize
        synthesis_prompt = f"""Original task: {task}

Worker results:
{self._format_results(results)}

Synthesize these into a final cohesive response."""

        final = await self.orchestrator.ask(synthesis_prompt, timeout=timeout)

        return {
            "task": task,
            "subtasks": subtasks,
            "worker_results": results,
            "final": final,
        }

    def _parse_subtasks(self, response: str) -> List[str]:
        """Parse numbered list of subtasks."""
        lines = response.strip().split('\n')
        subtasks = []
        for line in lines:
            line = line.strip()
            # Remove numbering
            if line and line[0].isdigit():
                line = line.lstrip('0123456789.-) ').strip()
            if line:
                subtasks.append(line)
        return subtasks[:len(self.workers)]

    def _format_results(self, results: List[str]) -> str:
        """Format worker results for synthesis."""
        parts = []
        for i, result in enumerate(results):
            parts.append(f"Worker {i+1}:\n{result[:500]}")
        return "\n\n".join(parts)

    async def shutdown(self) -> None:
        """Stop all agents."""
        await self.orchestrator.stop()
        await asyncio.gather(*[w.stop() for w in self.workers])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_agent_pool(
    count: int,
    base_dna: Optional[AgentDNA] = None,
    start: bool = True,
) -> List[AsyncAgent]:
    """Create and optionally start a pool of agents."""
    dna = base_dna or AgentDNA(role="worker")
    agents = [AsyncAgent.from_dna(dna.mutate(0.1)) for _ in range(count)]

    if start:
        await asyncio.gather(*[a.start() for a in agents])

    return agents


async def shutdown_agents(agents: List[AsyncAgent]) -> None:
    """Shutdown multiple agents concurrently."""
    await asyncio.gather(*[a.stop() for a in agents], return_exceptions=True)
