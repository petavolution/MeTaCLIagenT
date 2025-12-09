# core.py - Agent DNA and Evolution System
"""
Core EATS components: Agent DNA and Evolution engine.

Transport functionality is in transport.py (single source of truth).
This module focuses on evolutionary agent optimization.
"""

from __future__ import annotations
import time
import uuid
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Protocol

# Import Transport from canonical location (no duplication)
from .transport import Transport, PTYTransport, TmuxTransport, BufferOverflowError


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent DNA - The genetic blueprint for agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AgentDNA:
    """
    Agent blueprint - the "genome" that gets evolved.

    Phenotype: Observable traits (role, prompt)
    Genotype: Hidden parameters (temperature, timeout)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = "coder"
    system_prompt: str = "You are a helpful coding assistant."
    cmd: List[str] = field(default_factory=lambda: ["python", "-i"])

    # Evolvable parameters
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 30.0

    # Lineage tracking
    parent_id: Optional[str] = None
    generation: int = 0
    fitness_history: List[float] = field(default_factory=list)

    def mutate(self, rate: float = 0.2) -> AgentDNA:
        """Create mutated offspring."""
        # Mutate prompt
        new_prompt = self.system_prompt
        if random.random() < rate:
            mutations = [
                "\nThink step by step.",
                "\nBe concise and direct.",
                "\nDouble-check your work.",
                "\nConsider edge cases.",
                "\nPrioritize code quality.",
            ]
            new_prompt += random.choice(mutations)

        # Mutate temperature
        new_temp = self.temperature + random.uniform(-0.1, 0.1)
        new_temp = max(0.1, min(1.0, new_temp))

        return AgentDNA(
            role=self.role,
            system_prompt=new_prompt,
            cmd=self.cmd.copy(),
            temperature=round(new_temp, 2),
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            parent_id=self.id,
            generation=self.generation + 1,
        )

    def crossover(self, other: AgentDNA) -> AgentDNA:
        """Combine traits from two parents."""
        return AgentDNA(
            role=random.choice([self.role, other.role]),
            system_prompt=random.choice([self.system_prompt, other.system_prompt]),
            cmd=self.cmd.copy(),
            temperature=(self.temperature + other.temperature) / 2,
            max_tokens=random.choice([self.max_tokens, other.max_tokens]),
            parent_id=self.id,
            generation=max(self.generation, other.generation) + 1,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "system_prompt": self.system_prompt[:100] + "...",
            "temperature": self.temperature,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "avg_fitness": sum(self.fitness_history) / len(self.fitness_history) if self.fitness_history else 0,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent - Live running instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Turn:
    """A single prompt-response turn."""
    prompt: str
    response: str
    timestamp: float
    duration: float


class Agent:
    """
    A live agent instance with transport and conversation history.

    Usage:
        dna = AgentDNA(role="coder", cmd=["aider"])
        agent = Agent(dna)
        agent.start()
        response = agent.ask("Write hello world")
        agent.stop()
    """

    def __init__(
        self,
        dna: AgentDNA,
        transport_type: str = "pty",
        **transport_kwargs,
    ):
        self.dna = dna
        self.id = f"{dna.role}_{dna.id}"
        self.turns: List[Turn] = []
        self._transport: Optional[Transport] = None
        self._transport_type = transport_type
        self._transport_kwargs = transport_kwargs

    def start(self) -> None:
        """Start the agent's underlying process."""
        if self._transport_type == "tmux":
            self._transport = TmuxTransport(
                cmd=self.dna.cmd,
                window_name=self.id,
                **self._transport_kwargs,
            )
        else:
            self._transport = PTYTransport(
                cmd=self.dna.cmd,
                name=self.id,
            )
        self._transport.start()

        # Send system prompt if the tool supports it
        time.sleep(0.5)  # Wait for startup

    def ask(
        self,
        prompt: str,
        wait_seconds: Optional[float] = None,
        idle_threshold: float = 0.5,
    ) -> str:
        """Send prompt and get response."""
        if not self._transport:
            raise RuntimeError("Agent not started")

        wait = wait_seconds or self.dna.timeout
        start = time.time()

        response = self._transport.send_and_wait(
            prompt,
            wait_seconds=wait,
            idle_threshold=idle_threshold,
        )

        duration = time.time() - start
        self.turns.append(Turn(
            prompt=prompt,
            response=response,
            timestamp=start,
            duration=duration,
        ))

        return response

    def last_output(self, chars: int = 2000) -> str:
        """Get last output (for fitness evaluation)."""
        if self.turns:
            return self.turns[-1].response[-chars:]
        return ""

    def is_alive(self) -> bool:
        return self._transport is not None and self._transport.is_alive()

    def stop(self) -> None:
        """Stop the agent."""
        if self._transport:
            self._transport.terminate()
            self._transport = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Evolution Engine - Genetic algorithm for agent optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FitnessFn(Protocol):
    """Protocol for fitness functions."""
    def __call__(self, agent: Agent, task: str, response: str) -> float: ...


@dataclass
class EvolutionConfig:
    """Evolution hyperparameters."""
    population_size: int = 4
    survivors: int = 2
    mutation_rate: float = 0.3
    generations: int = 3
    task_prompt: str = "Write a Python function that reverses a string."


@dataclass
class GenerationResult:
    """Results from one generation."""
    generation: int
    population: List[AgentDNA]
    fitness_scores: Dict[str, float]
    best_dna: AgentDNA
    best_fitness: float
    avg_fitness: float


class Evolution:
    """
    Evolutionary optimization engine for agent DNA.

    Usage:
        evo = Evolution(config)
        best_dna = evo.run(base_dna, fitness_fn)
    """

    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.history: List[GenerationResult] = []

    def run(
        self,
        base_dna: AgentDNA,
        fitness_fn: FitnessFn,
        on_generation: Optional[Callable[[GenerationResult], None]] = None,
    ) -> AgentDNA:
        """
        Run evolutionary optimization.

        Args:
            base_dna: Starting DNA to evolve from
            fitness_fn: Function(agent, task, response) -> float
            on_generation: Optional callback after each generation

        Returns:
            Best performing DNA
        """
        # Initialize population
        population = self._init_population(base_dna)

        for gen in range(self.config.generations):
            # Evaluate fitness
            fitness_scores = self._evaluate(population, fitness_fn)

            # Record results
            sorted_pop = sorted(
                population,
                key=lambda d: fitness_scores.get(d.id, 0),
                reverse=True,
            )
            best = sorted_pop[0]
            best_fit = fitness_scores.get(best.id, 0)
            avg_fit = sum(fitness_scores.values()) / len(fitness_scores)

            result = GenerationResult(
                generation=gen,
                population=population.copy(),
                fitness_scores=fitness_scores,
                best_dna=best,
                best_fitness=best_fit,
                avg_fitness=avg_fit,
            )
            self.history.append(result)

            if on_generation:
                on_generation(result)

            # Final generation - return best
            if gen == self.config.generations - 1:
                return best

            # Select survivors and reproduce
            survivors = sorted_pop[:self.config.survivors]
            population = self._reproduce(survivors, gen + 1)

        return population[0]  # Should not reach here

    def _init_population(self, base: AgentDNA) -> List[AgentDNA]:
        """Create initial population via mutation."""
        pop = [base]  # Keep original
        for _ in range(self.config.population_size - 1):
            pop.append(base.mutate(self.config.mutation_rate))
        return pop

    def _evaluate(
        self,
        population: List[AgentDNA],
        fitness_fn: FitnessFn,
    ) -> Dict[str, float]:
        """Evaluate all agents in population."""
        scores = {}

        for dna in population:
            agent = Agent(dna)
            try:
                agent.start()
                response = agent.ask(self.config.task_prompt)
                score = fitness_fn(agent, self.config.task_prompt, response)
                scores[dna.id] = score
                dna.fitness_history.append(score)
            except Exception as e:
                scores[dna.id] = 0.0
                print(f"Error evaluating {dna.id}: {e}")
            finally:
                agent.stop()

        return scores

    def _reproduce(
        self,
        survivors: List[AgentDNA],
        generation: int,
    ) -> List[AgentDNA]:
        """Create next generation from survivors."""
        next_gen = list(survivors)  # Keep survivors

        # Fill remaining with offspring
        while len(next_gen) < self.config.population_size:
            parent = random.choice(survivors)
            child = parent.mutate(self.config.mutation_rate)
            next_gen.append(child)

        return next_gen


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Built-in Fitness Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def heuristic_fitness(agent: Agent, task: str, response: str) -> float:
    """
    Heuristic fitness based on response quality indicators.

    Scores 0-10 based on:
    - Length (not too short/long)
    - Code presence
    - Explanation quality
    - Response time
    """
    score = 0.0

    # Length score (optimal: 200-1500 chars)
    length = len(response)
    if length < 50:
        score += 1
    elif length < 200:
        score += 2
    elif length < 1500:
        score += 3
    else:
        score += 2

    # Code presence
    if "def " in response or "class " in response or "```" in response:
        score += 3

    # Structure (lists, steps)
    if any(m in response for m in ["1.", "- ", "* ", "Step"]):
        score += 2

    # Response time (faster is better, within reason)
    if agent.turns:
        duration = agent.turns[-1].duration
        if 1 < duration < 10:
            score += 2
        elif duration < 30:
            score += 1

    return min(10.0, score)


def keyword_fitness(
    keywords: Dict[str, float],
) -> FitnessFn:
    """Create fitness function that scores based on keyword presence."""
    def fn(agent: Agent, task: str, response: str) -> float:
        score = 0.0
        response_lower = response.lower()
        for kw, weight in keywords.items():
            if kw.lower() in response_lower:
                score += weight
        return min(10.0, score)
    return fn
