# orchestrator.py
"""
Multi-Agent Orchestrator: High-level coordination of the EATS system.

The Orchestrator ties together:
- MetaManager (agent lifecycle)
- EvolutionEngine (genetic optimization)
- OrchestrationGraph (state visualization)
- EventBus (notifications)

It provides human-supervised entry points for:
- Starting evolution runs
- Stepping through generations manually
- Routing outputs between agents
- Inspecting system state
"""

from typing import Callable, Dict, List, Optional, Tuple

from .config_models import AgentBlueprint, TaskSpec, EvolutionConfig
from .manager import MetaManager
from .evolution_engine import EvolutionEngine, FitnessResult, FitnessFn, combined_fitness
from .task_graph import OrchestrationGraph
from .event_bus import EventBus, Event, EventType
from .agents import AgentSession


class MultiAgentOrchestrator:
    """
    High-level orchestration layer for EATS.

    Provides human-in-the-loop entry points:
    - register_task(): Add a task to work on
    - run_evolution(): Run full evolutionary optimization
    - step_generation(): Step through one generation at a time
    - inspect_state(): View current system state

    Usage:
        orch = MultiAgentOrchestrator(default_cmd=["python", "-i"])
        task = orch.register_task("Write a sorting function")
        results = orch.run_evolution(base_blueprint, task)
    """

    def __init__(
        self,
        default_cmd: List[str],
        evo_config: Optional[EvolutionConfig] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.evo_config = evo_config or EvolutionConfig()
        self.event_bus = event_bus or EventBus()
        self.graph = OrchestrationGraph()

        # Initialize manager
        self.manager = MetaManager(
            default_cmd=default_cmd,
            event_bus=self.event_bus,
            evo_config=self.evo_config,
        )

        # Initialize evolution engine
        self.evo_engine = EvolutionEngine(
            meta_manager=self.manager,
            evo_config=self.evo_config,
            event_bus=self.event_bus,
        )

        # Track tasks and evolution state
        self._tasks: Dict[str, TaskSpec] = {}
        self._current_population: List[AgentBlueprint] = []
        self._current_generation: int = 0
        self._fitness_history: List[List[FitnessResult]] = []

    # ─────────────────────────────────────────────────────
    # Task Management
    # ─────────────────────────────────────────────────────

    def register_task(
        self,
        description: str,
        input_data: Optional[str] = None,
        expected_output: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ) -> TaskSpec:
        """
        Register a new task for agents to work on.

        Returns:
            The created TaskSpec
        """
        task = TaskSpec.create(
            description=description,
            input_data=input_data,
            expected_output=expected_output,
            timeout_seconds=timeout_seconds,
        )
        self._tasks[task.id] = task

        # Add to graph
        self.graph.add_task(task)

        self.event_bus.publish(Event(
            type=EventType.TASK_REGISTERED,
            payload={"task_id": task.id, "description": description[:100]},
            source="orchestrator",
        ))

        return task

    def get_task(self, task_id: str) -> TaskSpec:
        """Get a task by ID."""
        return self._tasks[task_id]

    def list_tasks(self) -> List[TaskSpec]:
        """List all registered tasks."""
        return list(self._tasks.values())

    # ─────────────────────────────────────────────────────
    # Evolution Control (Human-Supervised)
    # ─────────────────────────────────────────────────────

    def run_evolution(
        self,
        base_blueprint: AgentBlueprint,
        task: TaskSpec,
        fitness_fn: Optional[FitnessFn] = None,
    ) -> Tuple[List[AgentBlueprint], List[FitnessResult]]:
        """
        Run a full evolution cycle for a task.

        This is a blocking call that runs through all generations.
        For step-by-step control, use initialize_evolution() + step_generation().

        Args:
            base_blueprint: Starting blueprint to evolve from
            task: Task to optimize for
            fitness_fn: Optional custom fitness function (default: combined_fitness)

        Returns:
            Tuple of (final_population, final_fitness_results)
        """
        if fitness_fn is None:
            fitness_fn = combined_fitness

        # Register blueprint
        self.manager.register_blueprint(base_blueprint)

        # Track in graph
        self.graph.add_task(task)

        def on_generation_done(gen: int, pop: List[AgentBlueprint], results: List[FitnessResult]):
            # Update graph with generation data
            for bp in pop:
                for session in self.manager.list_sessions():
                    if session.blueprint.id == bp.id:
                        node = self.graph.add_agent(
                            bp, session.id, generation=gen,
                            parent_agent_id=bp.parent_id,
                        )
                        # Update fitness
                        for r in results:
                            if r.blueprint_id == bp.id:
                                self.graph.update_agent_fitness(session.id, r.fitness_score)

            self._fitness_history.append(results)

        # Run evolution
        self.event_bus.publish(Event(
            type=EventType.TASK_STARTED,
            payload={"task_id": task.id},
            source="orchestrator",
        ))

        final_pop, final_results = self.evo_engine.run_evolution(
            initial_blueprint=base_blueprint,
            task=task,
            fitness_fn=fitness_fn,
            on_generation_done=on_generation_done,
        )

        self.event_bus.publish(Event(
            type=EventType.TASK_COMPLETE,
            payload={
                "task_id": task.id,
                "best_fitness": max(r.fitness_score for r in final_results) if final_results else 0,
            },
            source="orchestrator",
        ))

        return final_pop, final_results

    def initialize_evolution(
        self,
        base_blueprint: AgentBlueprint,
    ) -> List[AgentBlueprint]:
        """
        Initialize evolution with a base blueprint.

        Use this for step-by-step evolution control.

        Returns:
            Initial population of blueprints
        """
        self.manager.register_blueprint(base_blueprint)
        self._current_population = self.evo_engine.create_initial_population(base_blueprint)
        self._current_generation = 0
        self._fitness_history = []
        return self._current_population

    def step_generation(
        self,
        task: TaskSpec,
        fitness_fn: Optional[FitnessFn] = None,
    ) -> Tuple[List[AgentBlueprint], List[FitnessResult]]:
        """
        Execute one generation of evolution.

        Call initialize_evolution() first, then call this repeatedly.

        Returns:
            Tuple of (new_population, fitness_results)
        """
        if not self._current_population:
            raise RuntimeError("Call initialize_evolution() first")

        if fitness_fn is None:
            fitness_fn = combined_fitness

        # Spawn sessions
        sessions = self.evo_engine.spawn_sessions_for_population(self._current_population)

        # Evaluate
        results = self.evo_engine.evaluate_population(task, sessions, fitness_fn)
        self._fitness_history.append(results)

        # Update graph
        for bp in self._current_population:
            session = sessions.get(bp.id)
            if session:
                self.graph.add_agent(
                    bp, session.id,
                    generation=self._current_generation,
                    parent_agent_id=bp.parent_id,
                )
                for r in results:
                    if r.blueprint_id == bp.id:
                        self.graph.update_agent_fitness(session.id, r.fitness_score)

        # Cleanup sessions
        for session in sessions.values():
            try:
                session.terminate()
            except Exception:
                pass

        # Produce next generation
        survivors = self.evo_engine.select_survivors(self._current_population, results)
        self._current_generation += 1
        self._current_population = self.evo_engine.produce_next_generation(
            survivors, self._current_generation
        )

        return self._current_population, results

    # ─────────────────────────────────────────────────────
    # Agent Interaction (Manual Control)
    # ─────────────────────────────────────────────────────

    def spawn_agent(
        self,
        blueprint: Optional[AgentBlueprint] = None,
        role: str = "coder",
    ) -> AgentSession:
        """
        Manually spawn an agent (outside of evolution).

        Useful for testing or one-off interactions.
        """
        session = self.manager.spawn_agent(blueprint=blueprint, role=role)
        if blueprint:
            self.graph.add_agent(blueprint, session.id, generation=0)
        return session

    def send_prompt(self, agent_id: str, prompt: str) -> str:
        """Send a prompt to a specific agent."""
        return self.manager.send_prompt(agent_id, prompt)

    def route_output(
        self,
        from_agent_id: str,
        to_agent_id: str,
        context: str = "",
    ) -> str:
        """
        Route output from one agent to another.

        Takes the last output from from_agent and sends it
        (with optional context) to to_agent.
        """
        from_session = self.manager.get_session(from_agent_id)
        last_output = from_session.last_output()

        prompt = f"{context}\n\nPrevious agent output:\n{last_output}" if context else last_output

        return self.manager.send_prompt(to_agent_id, prompt)

    # ─────────────────────────────────────────────────────
    # State Inspection
    # ─────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        """Get overall orchestrator status."""
        return {
            "manager_status": self.manager.get_status(),
            "current_generation": self._current_generation,
            "population_size": len(self._current_population),
            "task_count": len(self._tasks),
            "fitness_history_generations": len(self._fitness_history),
            "graph_stats": self.graph.to_dict().get("stats", {}),
        }

    def get_fitness_summary(self) -> List[Dict]:
        """Get summary of fitness across generations."""
        summary = []
        for gen, results in enumerate(self._fitness_history):
            scores = [r.fitness_score for r in results]
            summary.append({
                "generation": gen,
                "best": max(scores) if scores else 0,
                "avg": sum(scores) / len(scores) if scores else 0,
                "worst": min(scores) if scores else 0,
                "count": len(scores),
            })
        return summary

    def get_best_result(self) -> Optional[FitnessResult]:
        """Get the best fitness result across all generations."""
        all_results = [r for gen_results in self._fitness_history for r in gen_results]
        if not all_results:
            return None
        return max(all_results, key=lambda r: r.fitness_score)

    def get_graph_json(self) -> Dict:
        """Get the orchestration graph in Cytoscape.js format."""
        return self.graph.to_cytoscape_json()

    # ─────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Shutdown all agents and clean up."""
        self.manager.shutdown()

    def reset(self) -> None:
        """Reset the orchestrator state (keeps config)."""
        self.manager.shutdown()
        self.graph.clear()
        self._tasks.clear()
        self._current_population.clear()
        self._current_generation = 0
        self._fitness_history.clear()
