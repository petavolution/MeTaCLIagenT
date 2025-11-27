#!/usr/bin/env python3
# ghost_swarm.py
"""
GhostSwarm: Terminal-Based LLM Swarm Controller

A standalone script that launches a visual multi-agent LLM terminal swarm
using tmux sessions and GUI terminals (alacritty/kitty/xterm).

Features:
- Spawn multiple agents in visible terminal windows
- Arrange windows in Wahrscheinlichkeitsfächer (probability fan) layout
- Real-time output monitoring without OCR
- Interactive swarm control

Usage:
    python -m eats.ghost_swarm
    python -m eats.ghost_swarm --agents 5 --terminal kitty
"""

import argparse
import time
import sys
import signal
from typing import List, Optional, Any, TYPE_CHECKING

# Handle rich import with proper type hints
if TYPE_CHECKING:
    from rich.table import Table
    TableType = Table
else:
    TableType = Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    Console = None
    Table = None
    Live = None
    Panel = None
    RICH_AVAILABLE = False

from .tmux_transport import (
    TmuxTransport,
    TmuxAgentConfig,
    calculate_fan_layout,
    calculate_grid_layout,
)


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

DEFAULT_SESSION = "ghost_sovereign"
DEFAULT_TERMINAL = "alacritty"
DEFAULT_AGENT_CMD = ["python", "-i", "-q"]

# Agent archetypes for the swarm
AGENT_ARCHETYPES = [
    {
        "name": "Coder_Alpha",
        "task": "Write clean, efficient code with comprehensive comments",
        "role": "coder",
    },
    {
        "name": "Critic_Beta",
        "task": "Review code for security flaws, bugs, and improvements",
        "role": "critic",
    },
    {
        "name": "Dreamer_Gamma",
        "task": "Explore creative solutions and alternative approaches",
        "role": "dreamer",
    },
    {
        "name": "Tester_Delta",
        "task": "Design test cases and verify correctness",
        "role": "tester",
    },
    {
        "name": "Planner_Epsilon",
        "task": "Break down complex tasks into actionable steps",
        "role": "planner",
    },
]


class GhostSwarm:
    """
    Multi-agent terminal swarm controller.

    Spawns and manages multiple LLM CLI agents in visible terminal windows,
    providing real-time monitoring and interaction capabilities.
    """

    def __init__(
        self,
        session_name: str = DEFAULT_SESSION,
        terminal_cmd: str = DEFAULT_TERMINAL,
        agent_cmd: Optional[List[str]] = None,
        spawn_gui: bool = True,
    ):
        self.session_name = session_name
        self.terminal_cmd = terminal_cmd
        self.agent_cmd = agent_cmd or DEFAULT_AGENT_CMD
        self.spawn_gui = spawn_gui

        self.transport = TmuxTransport(session_name=session_name)
        self.agents: List[str] = []
        self._running = False

        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

    def print(self, message: str, style: str = "") -> None:
        """Print with optional rich styling."""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def initialize(self) -> None:
        """Initialize the tmux session."""
        self.print(f"[bold green]Initializing Ghost Shell '{self.session_name}'...[/bold green]")
        self.transport.start()
        self._running = True

    def spawn_agent(
        self,
        name: str,
        task_prompt: str,
        x_pos: int = 0,
        y_pos: int = 0,
    ) -> None:
        """Spawn a single agent in the swarm."""
        self.print(f"[cyan]Spawning Agent: {name}[/cyan]")

        config = TmuxAgentConfig(
            name=name,
            task_prompt=task_prompt,
            command=self.agent_cmd,
            x_pos=x_pos,
            y_pos=y_pos,
            width=600,
            height=400,
            spawn_gui=self.spawn_gui,
            terminal_cmd=self.terminal_cmd,
        )

        self.transport.spawn_agent(config)
        self.agents.append(name)

        # Give the agent a moment to start
        time.sleep(0.3)

    def spawn_swarm(
        self,
        archetypes: Optional[List[dict]] = None,
        layout: str = "fan",
        screen_width: int = 1920,
        screen_height: int = 1080,
    ) -> None:
        """
        Spawn a full swarm of agents with automatic layout.

        Args:
            archetypes: List of agent definitions (name, task, role)
            layout: "fan" or "grid"
            screen_width: Screen width for layout calculation
            screen_height: Screen height for layout calculation
        """
        archetypes = archetypes or AGENT_ARCHETYPES
        num_agents = len(archetypes)

        # Calculate positions
        if layout == "fan":
            positions = calculate_fan_layout(
                num_agents,
                screen_width=screen_width,
                screen_height=screen_height,
            )
        else:
            positions = calculate_grid_layout(
                num_agents,
                screen_width=screen_width,
                screen_height=screen_height,
            )

        # Spawn each agent
        for i, archetype in enumerate(archetypes):
            x, y = positions[i] if i < len(positions) else (0, 0)
            self.spawn_agent(
                name=archetype["name"],
                task_prompt=archetype["task"],
                x_pos=x,
                y_pos=y,
            )

        self.print(f"[bold green]Swarm of {num_agents} agents spawned![/bold green]")

    def send_to_agent(self, agent_name: str, text: str) -> None:
        """Send a prompt to a specific agent."""
        self.transport.send_line(agent_name, text)

    def send_to_all(self, text: str) -> None:
        """Broadcast a message to all agents."""
        for agent in self.agents:
            self.transport.send_line(agent, text)

    def read_agent(self, agent_name: str, lines: int = 20) -> str:
        """Read recent output from an agent."""
        return self.transport.capture_output(agent_name, lines=lines)

    def get_status_table(self) -> Optional[TableType]:
        """Create a rich table showing agent status."""
        if not RICH_AVAILABLE:
            return None

        table = Table(title="Ghost Swarm Status")
        table.add_column("Agent", style="cyan")
        table.add_column("Alive", style="green")
        table.add_column("Last Output (preview)")

        for agent in self.agents:
            alive = "Yes" if self.transport.is_alive(agent) else "[red]No[/red]"
            output = self.transport.capture_output(agent, lines=1)
            preview = output.strip()[:50] + "..." if len(output) > 50 else output.strip()
            table.add_row(agent, alive, preview)

        return table

    def monitor_loop(self, interval: float = 2.0) -> None:
        """Run a monitoring loop with live status display."""
        if not RICH_AVAILABLE:
            self.print("Rich not available. Running simple monitor...")
            self._simple_monitor(interval)
            return

        self.print("[bold]Starting swarm monitor (Ctrl+C to stop)...[/bold]")

        try:
            with Live(self.get_status_table(), refresh_per_second=1) as live:
                while self._running:
                    live.update(self.get_status_table())
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.print("\n[yellow]Monitor stopped.[/yellow]")

    def _simple_monitor(self, interval: float) -> None:
        """Simple monitoring without rich."""
        try:
            while self._running:
                print("\n" + "=" * 50)
                print(f"Ghost Swarm Status - {time.strftime('%H:%M:%S')}")
                print("=" * 50)
                for agent in self.agents:
                    alive = "ALIVE" if self.transport.is_alive(agent) else "DEAD"
                    print(f"  {agent}: {alive}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")

    def interactive_shell(self) -> None:
        """Run an interactive shell for swarm control."""
        self.print("[bold]GhostSwarm Interactive Shell[/bold]")
        self.print("Commands: list, send <agent> <msg>, broadcast <msg>, read <agent>, status, quit")

        while self._running:
            try:
                cmd = input("ghost> ").strip()
                if not cmd:
                    continue

                parts = cmd.split(maxsplit=2)
                action = parts[0].lower()

                if action == "quit" or action == "exit":
                    break

                elif action == "list":
                    for agent in self.agents:
                        alive = "OK" if self.transport.is_alive(agent) else "DEAD"
                        print(f"  {agent} [{alive}]")

                elif action == "send" and len(parts) >= 3:
                    agent_name = parts[1]
                    message = parts[2]
                    if agent_name in self.agents:
                        self.send_to_agent(agent_name, message)
                        print(f"Sent to {agent_name}")
                    else:
                        print(f"Agent '{agent_name}' not found")

                elif action == "broadcast" and len(parts) >= 2:
                    message = parts[1]
                    self.send_to_all(message)
                    print(f"Broadcast to {len(self.agents)} agents")

                elif action == "read" and len(parts) >= 2:
                    agent_name = parts[1]
                    if agent_name in self.agents:
                        output = self.read_agent(agent_name)
                        print(f"--- {agent_name} ---")
                        print(output)
                        print("---")
                    else:
                        print(f"Agent '{agent_name}' not found")

                elif action == "status":
                    table = self.get_status_table()
                    if table and self.console:
                        self.console.print(table)
                    else:
                        for agent in self.agents:
                            print(f"  {agent}: {'OK' if self.transport.is_alive(agent) else 'DEAD'}")

                else:
                    print("Unknown command. Try: list, send, broadcast, read, status, quit")

            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

    def shutdown(self) -> None:
        """Shutdown the swarm."""
        self._running = False
        self.print("[bold red]Shutting down Ghost Swarm...[/bold red]")
        self.transport.terminate()
        self.agents.clear()


def main():
    """Main entry point for GhostSwarm."""
    parser = argparse.ArgumentParser(
        description="GhostSwarm: Terminal-Based LLM Swarm Controller"
    )
    parser.add_argument(
        "--session", "-s",
        default=DEFAULT_SESSION,
        help="Tmux session name",
    )
    parser.add_argument(
        "--terminal", "-t",
        default=DEFAULT_TERMINAL,
        choices=["alacritty", "kitty", "gnome-terminal", "xterm"],
        help="Terminal emulator to use",
    )
    parser.add_argument(
        "--agents", "-a",
        type=int,
        default=3,
        help="Number of agents to spawn",
    )
    parser.add_argument(
        "--layout", "-l",
        default="fan",
        choices=["fan", "grid"],
        help="Window layout style",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Don't spawn GUI windows (tmux-only)",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Start in monitor mode instead of interactive",
    )
    parser.add_argument(
        "--cmd",
        nargs="+",
        default=DEFAULT_AGENT_CMD,
        help="Command to run for each agent",
    )

    args = parser.parse_args()

    # Create swarm
    swarm = GhostSwarm(
        session_name=args.session,
        terminal_cmd=args.terminal,
        agent_cmd=args.cmd,
        spawn_gui=not args.no_gui,
    )

    # Handle signals
    def signal_handler(sig, frame):
        swarm.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize
        swarm.initialize()

        # Spawn agents (use subset of archetypes)
        archetypes = AGENT_ARCHETYPES[:args.agents]
        swarm.spawn_swarm(
            archetypes=archetypes,
            layout=args.layout,
        )

        # Run in selected mode
        if args.monitor:
            swarm.monitor_loop()
        else:
            swarm.interactive_shell()

    finally:
        swarm.shutdown()


if __name__ == "__main__":
    main()
