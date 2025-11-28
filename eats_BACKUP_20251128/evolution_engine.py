# evolution_engine.py
"""
Evolution Engine: Genetic algorithm for agent optimization.

This module implements the evolutionary loop:
1. Create initial population of agent blueprints
2. Spawn agents and evaluate them on tasks
3. Select top performers
4. Mutate/crossover to create next generation
5. Repeat

The "genes" being evolved are:
- System prompts (with small mutations)
- Temperature settings
- Role specializations
"""

import random
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .config_models import AgentBlueprint, TaskSpec, EvolutionConfig
from .agents import AgentSession
from .manager import MetaManager
from .event_bus import EventBus, EventType, Event


@dataclass
class FitnessResult:
    """
    Result of evaluating an agent's fitness on a task.

    Attributes:
        blueprint_id: The blueprint that was evaluated
        session_id: The session that ran
        fitness_score: Overall fitness (0-10 scale)
        metrics: Breakdown of individual metrics
        response: The agent's raw response
    """
    blueprint_id: str
    session_id: str
    fitness_score: float
    metrics: Dict[str, float]
    response: str = ""

    def to_dict(self) -> Dict:
        return {
            "blueprint_id": self.blueprint_id,
            "session_id": self.session_id,
            "fitness_score": self.fitness_score,
            "metrics": self.metrics,
        }


# Type alias for fitness function
FitnessFn = Callable[[TaskSpec, AgentSession, str], FitnessResult]


# ─────────────────────────────────────────────────────────
# Mutation Snippets for Prompt Evolution
# ─────────────────────────────────────────────────────────

MUTATION_SNIPPETS = [
    "Focus on step-by-step reasoning.",
    "Prefer concise bullet points.",
    "Be more creative and exploratory.",
    "Be more critical and skeptical.",
    "Prioritize code correctness over brevity.",
    "Include edge case handling.",
    "Explain your reasoning clearly.",
    "Double-check your work before responding.",
    "Consider alternative approaches.",
    "Focus on maintainability and readability.",
]


class EvolutionEngine:
    """
    Drives evolutionary cycles over AgentBlueprints.

    Usage:
        engine = EvolutionEngine(meta_manager, evo_config)
        results = engine.run_evolution(
            initial_blueprint,
            task,
            fitness_fn=simple_fitness,
        )
    """

    def __init__(
        self,
        meta_manager: MetaManager,
        evo_config: EvolutionConfig,
        event_bus: Optional[EventBus] = None,
    ):
        self.manager = meta_manager
        self.config = evo_config
        self.event_bus = event_bus or EventBus()

    # ─────────────────────────────────────────────────────
    # Population Lifecycle
    # ─────────────────────────────────────────────────────

    def create_initial_population(
        self,
        base_blueprint: AgentBlueprint,
    ) -> List[AgentBlueprint]:
        """
        Create initial population by cloning and mutating a base blueprint.

        Returns:
            List of AgentBlueprints for generation 0
        """
        population = []
        for i in range(self.config.population_size):
            if i == 0:
                # Keep one exact copy
                clone = AgentBlueprint(
                    id=str(uuid.uuid4()),
                    role=base_blueprint.role,
                    system_prompt=base_blueprint.system_prompt,
                    cmd=base_blueprint.cmd,
                    temperature=base_blueprint.temperature,
                    parent_id=base_blueprint.id,
                    generation=0,
                )
            else:
                # Mutate the rest
                clone = self.mutate_blueprint(base_blueprint, generation=0)
            population.append(clone)
        return population

    def spawn_sessions_for_population(
        self,
        population: List[AgentBlueprint],
    ) -> Dict[str, AgentSession]:
        """
        Spawn live AgentSessions for each blueprint.

        Returns:
            Mapping blueprint_id -> AgentSession
        """
        sessions = {}
        for bp in population:
            session = self.manager.spawn_agent(blueprint=bp)
            sessions[bp.id] = session
        return sessions

    # ─────────────────────────────────────────────────────
    # Fitness Evaluation
    # ─────────────────────────────────────────────────────

    def evaluate_population(
        self,
        task: TaskSpec,
        sessions_by_blueprint: Dict[str, AgentSession],
        fitness_fn: FitnessFn,
    ) -> List[FitnessResult]:
        """
        Evaluate all agents in the population on the given task.

        Args:
            task: The task to evaluate against
            sessions_by_blueprint: Blueprint ID -> Session mapping
            fitness_fn: Function that scores agent responses

        Returns:
            List of FitnessResults
        """
        results = []

        for bp_id, session in sessions_by_blueprint.items():
            # Build prompt from task
            prompt = task.description
            if task.input_data:
                prompt += f"\n\nInput: {task.input_data}"

            # Run the agent
            try:
                response = session.send_prompt(
                    prompt,
                    max_turn_seconds=self.config.max_turn_seconds,
                    idle_gap_seconds=self.config.idle_gap_seconds,
                    include_system_prompt=True,
                )
            except Exception as e:
                response = f"ERROR: {e}"

            # Evaluate fitness
            result = fitness_fn(task, session, response)
            results.append(result)

            # Emit event
            self.event_bus.publish(Event(
                type=EventType.FITNESS_EVALUATED,
                payload={
                    "blueprint_id": bp_id,
                    "session_id": session.id,
                    "fitness": result.fitness_score,
                },
                source="evolution",
            ))

        return results

    # ─────────────────────────────────────────────────────
    # Selection & Variation
    # ─────────────────────────────────────────────────────

    def select_survivors(
        self,
        population: List[AgentBlueprint],
        fitness_results: List[FitnessResult],
    ) -> List[AgentBlueprint]:
        """
        Select top-k blueprints as survivors based on fitness.

        Returns:
            List of surviving blueprints
        """
        # Create mapping of blueprint_id -> fitness
        fitness_by_bp = {r.blueprint_id: r.fitness_score for r in fitness_results}

        # Sort population by fitness (descending)
        sorted_pop = sorted(
            population,
            key=lambda bp: fitness_by_bp.get(bp.id, 0),
            reverse=True,
        )

        # Take top k
        survivors = sorted_pop[:self.config.top_k_survivors]

        self.event_bus.publish(Event(
            type=EventType.SELECTION_COMPLETE,
            payload={
                "survivors": [s.id for s in survivors],
                "survivor_count": len(survivors),
            },
            source="evolution",
        ))

        return survivors

    def mutate_blueprint(
        self,
        parent: AgentBlueprint,
        generation: int,
    ) -> AgentBlueprint:
        """
        Produce a mutated child blueprint.

        Mutations:
        - Append a random snippet to system prompt
        - Slightly adjust temperature
        """
        # Mutate prompt
        new_prompt = parent.system_prompt
        if random.random() < self.config.mutation_rate:
            snippet = random.choice(MUTATION_SNIPPETS)
            new_prompt = f"{parent.system_prompt}\n\nHINT: {snippet}"

        # Mutate temperature
        temp_delta = random.uniform(
            -self.config.temperature_mutation_range,
            self.config.temperature_mutation_range,
        )
        new_temp = max(0.1, min(1.0, parent.temperature + temp_delta))

        child = AgentBlueprint(
            id=str(uuid.uuid4()),
            role=parent.role,
            system_prompt=new_prompt,
            cmd=parent.cmd,
            temperature=round(new_temp, 2),
            extra_params=parent.extra_params.copy(),
            parent_id=parent.id,
            generation=generation,
        )

        self.event_bus.publish(Event(
            type=EventType.MUTATION_APPLIED,
            payload={
                "parent_id": parent.id,
                "child_id": child.id,
                "generation": generation,
            },
            source="evolution",
        ))

        return child

    def crossover_blueprints(
        self,
        parent_a: AgentBlueprint,
        parent_b: AgentBlueprint,
        generation: int,
    ) -> AgentBlueprint:
        """
        Combine traits from two parents.

        Simple strategy: take prompt from one, temperature from other.
        """
        # Randomly pick which parent contributes what
        if random.random() < 0.5:
            prompt = parent_a.system_prompt
            temp = parent_b.temperature
        else:
            prompt = parent_b.system_prompt
            temp = parent_a.temperature

        child = AgentBlueprint(
            id=str(uuid.uuid4()),
            role=parent_a.role,  # Keep role from parent A
            system_prompt=prompt,
            cmd=parent_a.cmd,
            temperature=temp,
            parent_id=parent_a.id,  # Primary parent for lineage
            generation=generation,
        )

        return child

    def produce_next_generation(
        self,
        survivors: List[AgentBlueprint],
        generation: int,
    ) -> List[AgentBlueprint]:
        """
        From survivors, create a new generation via mutation and crossover.

        Strategy:
        - Keep survivors as-is (with updated generation)
        - Fill remaining slots with mutated children
        """
        next_gen = []

        # Survivors continue (update their generation marker)
        for survivor in survivors:
            updated = AgentBlueprint(
                id=survivor.id,  # Keep same ID for continuity
                role=survivor.role,
                system_prompt=survivor.system_prompt,
                cmd=survivor.cmd,
                temperature=survivor.temperature,
                parent_id=survivor.parent_id,
                generation=generation,
            )
            next_gen.append(updated)

        # Fill remaining with children
        children_needed = self.config.population_size - len(survivors)
        for _ in range(children_needed):
            parent = random.choice(survivors)
            child = self.mutate_blueprint(parent, generation)
            next_gen.append(child)

        return next_gen

    # ─────────────────────────────────────────────────────
    # Main Evolution Loop
    # ─────────────────────────────────────────────────────

    def run_evolution(
        self,
        initial_blueprint: AgentBlueprint,
        task: TaskSpec,
        fitness_fn: FitnessFn,
        on_generation_done: Optional[
            Callable[[int, List[AgentBlueprint], List[FitnessResult]], None]
        ] = None,
    ) -> Tuple[List[AgentBlueprint], List[FitnessResult]]:
        """
        Run the full evolutionary cycle.

        Args:
            initial_blueprint: Base blueprint to evolve from
            task: Task to evaluate agents against
            fitness_fn: Function to compute fitness
            on_generation_done: Optional callback after each generation

        Returns:
            Tuple of (final_population, last_fitness_results)
        """
        # Initialize population
        population = self.create_initial_population(initial_blueprint)

        last_results: List[FitnessResult] = []

        for gen in range(self.config.max_generations):
            self.event_bus.publish(Event(
                type=EventType.GENERATION_STARTED,
                payload={"generation": gen, "population_size": len(population)},
                source="evolution",
            ))

            # Spawn sessions
            sessions = self.spawn_sessions_for_population(population)

            # Evaluate
            results = self.evaluate_population(task, sessions, fitness_fn)
            last_results = results

            # Calculate stats
            fitness_scores = [r.fitness_score for r in results]
            avg_fitness = sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0
            best_fitness = max(fitness_scores) if fitness_scores else 0

            self.event_bus.publish(Event(
                type=EventType.GENERATION_COMPLETE,
                payload={
                    "generation": gen,
                    "avg_fitness": round(avg_fitness, 2),
                    "best_fitness": round(best_fitness, 2),
                },
                source="evolution",
            ))

            # Callback
            if on_generation_done:
                on_generation_done(gen, population, results)

            # Terminate sessions (cleanup)
            for session in sessions.values():
                try:
                    session.terminate()
                except Exception:
                    pass

            # Select and produce next generation (unless last)
            if gen < self.config.max_generations - 1:
                survivors = self.select_survivors(population, results)
                population = self.produce_next_generation(survivors, gen + 1)

        return population, last_results


# ─────────────────────────────────────────────────────────
# Built-in Fitness Functions
# ─────────────────────────────────────────────────────────

def simple_length_fitness(task: TaskSpec, session: AgentSession, response: str) -> FitnessResult:
    """
    Very simple fitness: score based on response length.

    Useful for testing the evolution loop.
    """
    # Longer responses get higher scores (up to a point)
    length = len(response)
    score = min(10.0, length / 100)

    return FitnessResult(
        blueprint_id=session.blueprint.id,
        session_id=session.id,
        fitness_score=score,
        metrics={"length": length},
        response=response,
    )


def keyword_fitness(
    task: TaskSpec,
    session: AgentSession,
    response: str,
    keywords: Optional[Dict[str, float]] = None,
) -> FitnessResult:
    """
    Score based on presence of expected keywords.

    Args:
        keywords: Dict mapping keyword -> weight (e.g., {"def": 2.0, "return": 1.5})
    """
    if keywords is None:
        keywords = {"def": 2.0, "return": 1.5, "class": 1.0}

    score = 0.0
    metrics = {}
    response_lower = response.lower()

    for kw, weight in keywords.items():
        count = response_lower.count(kw.lower())
        contribution = min(count * weight, weight * 3)  # Cap per keyword
        metrics[f"kw_{kw}"] = count
        score += contribution

    # Normalize to 0-10
    score = min(10.0, score)

    return FitnessResult(
        blueprint_id=session.blueprint.id,
        session_id=session.id,
        fitness_score=score,
        metrics=metrics,
        response=response,
    )


def combined_fitness(task: TaskSpec, session: AgentSession, response: str) -> FitnessResult:
    """
    Combined fitness using multiple heuristics.

    Factors:
    - Response length (not too short, not too long)
    - Contains code blocks
    - Contains explanations
    - Response time
    """
    metrics = {}

    # Length score (optimal around 500-1500 chars)
    length = len(response)
    if length < 100:
        length_score = length / 100
    elif length < 500:
        length_score = 1.0 + (length - 100) / 400
    elif length < 1500:
        length_score = 2.0
    else:
        length_score = max(0.5, 2.0 - (length - 1500) / 2000)
    metrics["length"] = length
    metrics["length_score"] = length_score

    # Code presence
    has_code = "```" in response or "def " in response or "class " in response
    code_score = 2.0 if has_code else 0.0
    metrics["has_code"] = 1.0 if has_code else 0.0

    # Explanation presence
    explanation_markers = ["because", "therefore", "this means", "note that", "importantly"]
    explanation_count = sum(1 for m in explanation_markers if m in response.lower())
    explanation_score = min(2.0, explanation_count * 0.5)
    metrics["explanation_score"] = explanation_score

    # Response time (faster is better, but too fast might be error)
    last_turn = session.last_turn()
    if last_turn and last_turn.duration_seconds > 0:
        duration = last_turn.duration_seconds
        if duration < 0.5:
            time_score = 0.5  # Suspiciously fast
        elif duration < 5:
            time_score = 2.0  # Good speed
        elif duration < 15:
            time_score = 1.5
        else:
            time_score = 1.0  # Slow
        metrics["duration"] = duration
    else:
        time_score = 1.0
    metrics["time_score"] = time_score

    # Total score
    total = length_score + code_score + explanation_score + time_score
    normalized = min(10.0, total * 1.25)  # Scale to 0-10

    return FitnessResult(
        blueprint_id=session.blueprint.id,
        session_id=session.id,
        fitness_score=round(normalized, 2),
        metrics=metrics,
        response=response,
    )
