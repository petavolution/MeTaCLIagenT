#!/usr/bin/env python3
# cli_supervisor.py
"""
CLI Supervisor: Human-supervised command-line interface for EATS.

This is the primary way to manually control the multi-agent system:
- Spawn agents interactively
- Send prompts and view responses
- Run evolution with manual oversight
- Inspect state and logs

Run with: python -m eats.cli_supervisor
"""

import sys
import cmd
import textwrap
from typing import List, Optional

from .orchestrator import MultiAgentOrchestrator
from .config_models import AgentBlueprint, TaskSpec, EvolutionConfig
from .evolution_engine import combined_fitness, simple_length_fitness


# Default command - change to your LLM CLI
DEFAULT_CMD: List[str] = ["python", "-i", "-q"]


class EATSSupervisor(cmd.Cmd):
    """
    Interactive CLI for EATS supervision.

    Commands are human-driven; the system does nothing automatically.
    """

    intro = textwrap.dedent("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║  EATS - Evolutionary Agent Tree System - CLI Supervisor       ║
    ║                                                               ║
    ║  Type 'help' for commands, 'quit' to exit.                    ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    prompt = "eats> "

    def __init__(self, cmd: Optional[List[str]] = None):
        super().__init__()
        self.orch = MultiAgentOrchestrator(
            default_cmd=cmd or DEFAULT_CMD,
            evo_config=EvolutionConfig(
                population_size=4,
                top_k_survivors=2,
                max_generations=3,
                max_turn_seconds=30.0,
                idle_gap_seconds=1.0,
            ),
        )
        self._selected_agent: Optional[str] = None
        self._selected_task: Optional[str] = None

    # ─────────────────────────────────────────────────────
    # Agent Commands
    # ─────────────────────────────────────────────────────

    def do_spawn(self, arg: str):
        """
        Spawn a new agent.

        Usage: spawn [role]
        Example: spawn coder
        """
        role = arg.strip() or "coder"
        bp = AgentBlueprint.create(
            role=role,
            system_prompt=f"You are a helpful {role} assistant.",
            cmd=DEFAULT_CMD,
        )
        session = self.orch.spawn_agent(blueprint=bp)
        print(f"✓ Spawned agent: {session.id[:8]}... (role={role})")
        self._selected_agent = session.id

    def do_agents(self, arg: str):
        """
        List all agents.

        Usage: agents
        """
        sessions = self.orch.manager.list_sessions()
        if not sessions:
            print("No agents running.")
            return

        print(f"\n{'ID':<12} {'Role':<12} {'State':<10} {'Turns':<6}")
        print("-" * 44)
        for s in sessions:
            marker = "→ " if s.id == self._selected_agent else "  "
            print(f"{marker}{s.id[:10]:<10} {s.blueprint.role:<12} {s.state:<10} {len(s.log):<6}")
        print()

    def do_select(self, arg: str):
        """
        Select an agent by ID (partial match).

        Usage: select <agent_id>
        """
        if not arg:
            print("Usage: select <agent_id>")
            return

        for s in self.orch.manager.list_sessions():
            if s.id.startswith(arg):
                self._selected_agent = s.id
                print(f"✓ Selected agent: {s.id[:8]}...")
                return
        print(f"✗ No agent found matching '{arg}'")

    def do_prompt(self, arg: str):
        """
        Send a prompt to the selected agent.

        Usage: prompt <text>
        """
        if not self._selected_agent:
            print("✗ No agent selected. Use 'select <id>' first.")
            return
        if not arg:
            print("Usage: prompt <text>")
            return

        try:
            print(f"Sending to {self._selected_agent[:8]}...")
            response = self.orch.send_prompt(self._selected_agent, arg)
            print("\n--- RESPONSE ---")
            print(response[:2000])
            if len(response) > 2000:
                print(f"\n... ({len(response)} chars total)")
            print("--- END ---\n")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_tail(self, arg: str):
        """
        Show the last output from selected agent.

        Usage: tail [chars]
        """
        if not self._selected_agent:
            print("✗ No agent selected.")
            return

        try:
            session = self.orch.manager.get_session(self._selected_agent)
            chars = int(arg) if arg else 1000
            print(session.last_output(chars))
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_log(self, arg: str):
        """
        Show conversation log for selected agent.

        Usage: log [count]
        """
        if not self._selected_agent:
            print("✗ No agent selected.")
            return

        try:
            session = self.orch.manager.get_session(self._selected_agent)
            count = int(arg) if arg else 5
            for i, turn in enumerate(session.log[-count:]):
                print(f"\n=== Turn {i+1} ===")
                print(f"[PROMPT] {turn.prompt[:200]}...")
                print(f"[RESPONSE] {turn.response[:500]}...")
        except Exception as e:
            print(f"✗ Error: {e}")

    def do_kill(self, arg: str):
        """
        Terminate an agent.

        Usage: kill [agent_id]  (defaults to selected)
        """
        agent_id = arg.strip() if arg else self._selected_agent
        if not agent_id:
            print("✗ No agent specified.")
            return

        # Find full ID
        for s in self.orch.manager.list_sessions():
            if s.id.startswith(agent_id):
                self.orch.manager.terminate_agent(s.id)
                print(f"✓ Terminated: {s.id[:8]}...")
                if self._selected_agent == s.id:
                    self._selected_agent = None
                return
        print(f"✗ No agent found matching '{agent_id}'")

    # ─────────────────────────────────────────────────────
    # Task Commands
    # ─────────────────────────────────────────────────────

    def do_task(self, arg: str):
        """
        Create a new task.

        Usage: task <description>
        """
        if not arg:
            print("Usage: task <description>")
            return

        task = self.orch.register_task(description=arg)
        print(f"✓ Created task: {task.id[:8]}...")
        self._selected_task = task.id

    def do_tasks(self, arg: str):
        """
        List all tasks.

        Usage: tasks
        """
        tasks = self.orch.list_tasks()
        if not tasks:
            print("No tasks.")
            return

        for t in tasks:
            marker = "→ " if t.id == self._selected_task else "  "
            print(f"{marker}{t.id[:8]}... : {t.description[:60]}")

    # ─────────────────────────────────────────────────────
    # Evolution Commands
    # ─────────────────────────────────────────────────────

    def do_evolve(self, arg: str):
        """
        Run evolution on selected task.

        Usage: evolve [generations]
        """
        if not self._selected_task:
            print("✗ No task selected. Create one with 'task <description>'.")
            return

        gens = int(arg) if arg else 3
        self.orch.evo_config.max_generations = gens

        task = self.orch.get_task(self._selected_task)
        base = AgentBlueprint.create(
            role="coder",
            system_prompt="You are a helpful coding assistant.",
            cmd=DEFAULT_CMD,
        )

        print(f"Starting evolution: {gens} generations, population {self.orch.evo_config.population_size}")
        print("This may take a while...\n")

        def on_gen(gen, pop, results):
            scores = [r.fitness_score for r in results]
            print(f"  Gen {gen}: best={max(scores):.2f}, avg={sum(scores)/len(scores):.2f}")

        final_pop, results = self.orch.evo_engine.run_evolution(
            initial_blueprint=base,
            task=task,
            fitness_fn=combined_fitness,
            on_generation_done=on_gen,
        )

        print(f"\n✓ Evolution complete!")
        print(f"  Best fitness: {max(r.fitness_score for r in results):.2f}")

    def do_fitness(self, arg: str):
        """
        Show fitness summary across generations.

        Usage: fitness
        """
        summary = self.orch.get_fitness_summary()
        if not summary:
            print("No fitness data yet. Run 'evolve' first.")
            return

        print(f"\n{'Gen':<6} {'Best':<8} {'Avg':<8} {'Worst':<8}")
        print("-" * 32)
        for s in summary:
            print(f"{s['generation']:<6} {s['best']:<8.2f} {s['avg']:<8.2f} {s['worst']:<8.2f}")
        print()

    # ─────────────────────────────────────────────────────
    # System Commands
    # ─────────────────────────────────────────────────────

    def do_status(self, arg: str):
        """
        Show system status.

        Usage: status
        """
        status = self.orch.get_status()
        print("\n=== System Status ===")
        for k, v in status.items():
            print(f"  {k}: {v}")
        print()

    def do_graph(self, arg: str):
        """
        Show text representation of agent graph.

        Usage: graph
        """
        data = self.orch.graph.to_dict()
        print(f"\nAgents: {data['stats']['total_agents']}")
        print(f"Tasks: {data['stats']['total_tasks']}")
        print(f"Edges: {data['stats']['total_edges']}")
        print(f"Max generation: {data['stats']['max_generation']}")

        if data['agent_nodes']:
            print("\nAgent Nodes:")
            for aid, node in data['agent_nodes'].items():
                print(f"  {aid[:8]}... gen={node['generation']} fitness={node.get('fitness', 'N/A')}")

    def do_reset(self, arg: str):
        """
        Reset the system (terminate all agents, clear state).

        Usage: reset
        """
        confirm = input("Are you sure? (y/N): ")
        if confirm.lower() == 'y':
            self.orch.reset()
            self._selected_agent = None
            self._selected_task = None
            print("✓ System reset.")
        else:
            print("Cancelled.")

    def do_quit(self, arg: str):
        """Exit the supervisor."""
        print("Shutting down...")
        self.orch.shutdown()
        return True

    def do_exit(self, arg: str):
        """Exit the supervisor."""
        return self.do_quit(arg)

    def do_EOF(self, arg: str):
        """Handle Ctrl+D."""
        print()
        return self.do_quit(arg)

    def default(self, line: str):
        """Handle unknown commands."""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")

    def emptyline(self):
        """Do nothing on empty line."""
        pass


def main():
    """Entry point for CLI supervisor."""
    import argparse
    parser = argparse.ArgumentParser(description="EATS CLI Supervisor")
    parser.add_argument("--cmd", nargs="+", default=DEFAULT_CMD,
                        help="Command to run for agents")
    args = parser.parse_args()

    supervisor = EATSSupervisor(cmd=args.cmd)
    try:
        supervisor.cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        supervisor.orch.shutdown()


if __name__ == "__main__":
    main()
