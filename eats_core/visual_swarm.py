# visual_swarm.py - Enhanced Visual Multi-Agent Swarm Controller
"""
VisualSwarm: Terminal-Based Multi-Agent Orchestration

Enhanced version of GhostSwarm with improved reliability and error handling.
Uses the consolidated eats_core.transport module for robust visual rendering.

Features:
- Spawn multiple agents in visible terminal windows
- Wahrscheinlichkeitsfächer (probability fan) and grid layouts
- Real-time output monitoring without OCR
- Interactive swarm control with rich UI
- Graceful dependency handling and fallbacks
- 95%+ reliability target

Usage:
    from eats_core import VisualSwarm

    swarm = VisualSwarm()
    swarm.initialize()
    swarm.spawn_swarm(agent_count=5, layout="fan")
    swarm.interactive_shell()
    swarm.shutdown()
"""

from __future__ import annotations
import math
import time
import sys
import signal
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple, TYPE_CHECKING

# Import from consolidated transport module
from .transport import TmuxTransport

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration and Archetypes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT_SESSION = "ghost_sovereign"
DEFAULT_TERMINAL = "alacritty"
DEFAULT_AGENT_CMD = ["python3", "-i", "-q"]

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


@dataclass
class AgentConfig:
    """Configuration for a visual agent."""
    name: str
    task: str
    role: str = "agent"
    command: Optional[List[str]] = None
    x_pos: int = 0
    y_pos: int = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layout Calculation Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calculate_fan_layout(
    num_agents: int,
    screen_width: int = 1920,
    screen_height: int = 1080,
    window_width: int = 600,
    window_height: int = 400,
) -> List[Tuple[int, int]]:
    """
    Calculate Wahrscheinlichkeitsfächer (probability fan) layout positions.

    Arranges windows in a fan/arc pattern across the screen.

    Args:
        num_agents: Number of agent windows to position
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        window_width: Agent window width
        window_height: Agent window height

    Returns:
        List of (x, y) position tuples
    """
    positions = []

    if num_agents == 1:
        # Single agent: center of screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        return [(x, y)]

    # Calculate arc parameters
    center_x = screen_width // 2
    center_y = screen_height // 2

    # Radius of the fan
    radius = min(screen_width, screen_height) * 0.35

    # Arc span (degrees)
    arc_span = 180  # Semicircle
    start_angle = 90 - (arc_span / 2)  # Start angle in degrees

    # Calculate positions along the arc
    for i in range(num_agents):
        angle_deg = start_angle + (arc_span * i / max(num_agents - 1, 1))
        angle_rad = math.radians(angle_deg)

        x = int(center_x + radius * math.cos(angle_rad) - window_width / 2)
        y = int(center_y + radius * math.sin(angle_rad) - window_height / 2)

        # Clamp to screen bounds
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))

        positions.append((x, y))

    return positions


def calculate_grid_layout(
    num_agents: int,
    screen_width: int = 1920,
    screen_height: int = 1080,
    window_width: int = 600,
    window_height: int = 400,
    padding: int = 20,
) -> List[Tuple[int, int]]:
    """
    Calculate grid layout positions.

    Arranges windows in an evenly-spaced grid.

    Args:
        num_agents: Number of agent windows to position
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        window_width: Agent window width
        window_height: Agent window height
        padding: Padding between windows

    Returns:
        List of (x, y) position tuples
    """
    positions = []

    # Calculate grid dimensions
    cols = math.ceil(math.sqrt(num_agents * screen_width / screen_height))
    rows = math.ceil(num_agents / cols)

    # Calculate spacing
    x_spacing = (screen_width - padding) // cols
    y_spacing = (screen_height - padding) // rows

    for i in range(num_agents):
        row = i // cols
        col = i % cols

        x = padding + col * x_spacing
        y = padding + row * y_spacing

        # Clamp to screen bounds
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))

        positions.append((x, y))

    return positions


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VisualSwarm Class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class VisualSwarm:
    """
    Enhanced multi-agent visual swarm controller.

    Spawns and manages multiple CLI agents in visible terminal windows,
    with improved reliability, error handling, and graceful fallbacks.

    Improvements over legacy GhostSwarm:
    - Uses consolidated eats_core.transport module
    - Better error handling and recovery
    - Graceful dependency checking
    - More robust tmux session management
    - Clear error messages
    """

    def __init__(
        self,
        session_name: str = DEFAULT_SESSION,
        terminal: str = DEFAULT_TERMINAL,
        agent_cmd: Optional[List[str]] = None,
        spawn_gui: bool = True,
    ):
        """
        Initialize VisualSwarm.

        Args:
            session_name: Tmux session name
            terminal: Terminal emulator (alacritty, kitty, gnome-terminal, xterm)
            agent_cmd: Command to run for each agent
            spawn_gui: Whether to spawn visible GUI terminals
        """
        self.session_name = session_name
        self.terminal = terminal
        self.agent_cmd = agent_cmd or DEFAULT_AGENT_CMD
        self.spawn_gui = spawn_gui

        # Agent tracking
        self.agents: Dict[str, Dict[str, Any]] = {}  # name -> {transport, config, pane_id}
        self._running = False

        # Rich console (if available)
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

        # Dependency checks
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check for required dependencies and warn if missing."""
        issues = []

        # Check tmux
        try:
            subprocess.run(
                ["tmux", "-V"],
                capture_output=True,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            issues.append("tmux not found. Install with: sudo apt-get install tmux")

        # Check terminal emulator (if spawning GUI)
        if self.spawn_gui:
            try:
                # Try to find the terminal
                subprocess.run(
                    ["which", self.terminal],
                    capture_output=True,
                    check=True,
                )
            except subprocess.CalledProcessError:
                issues.append(
                    f"Terminal '{self.terminal}' not found. "
                    f"Install {self.terminal} or use --terminal to specify a different one."
                )

        if issues:
            self.print("[bold yellow]Warning: Missing dependencies:[/bold yellow]")
            for issue in issues:
                self.print(f"  - {issue}", style="yellow")
            self.print(
                "[yellow]VisualSwarm may not work correctly. "
                "Install missing dependencies or run without --spawn-gui[/yellow]"
            )

    def print(self, message: str, style: str = "") -> None:
        """Print with optional rich styling."""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def initialize(self) -> None:
        """
        Initialize the swarm.

        Creates tmux session and prepares for agent spawning.
        """
        self.print(f"[bold green]Initializing VisualSwarm '{self.session_name}'...[/bold green]")

        try:
            # Check if session already exists
            result = subprocess.run(
                ["tmux", "has-session", "-t", self.session_name],
                capture_output=True,
            )

            if result.returncode == 0:
                # Session exists - kill it
                self.print(f"[yellow]Killing existing session '{self.session_name}'...[/yellow]")
                subprocess.run(
                    ["tmux", "kill-session", "-t", self.session_name],
                    check=True,
                )
                time.sleep(0.5)

            # Create new session
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", self.session_name],
                check=True,
            )

            self._running = True
            self.print("[bold green]✓ VisualSwarm initialized[/bold green]")

        except subprocess.CalledProcessError as e:
            self.print(f"[bold red]Failed to initialize tmux session: {e}[/bold red]")
            raise RuntimeError(f"Tmux initialization failed: {e}")

    def spawn_agent(
        self,
        name: str,
        task: str,
        x_pos: int = 0,
        y_pos: int = 0,
    ) -> None:
        """
        Spawn a single agent in the swarm.

        Args:
            name: Agent name/identifier
            task: Task prompt for the agent
            x_pos: X position for GUI window (if spawning GUI)
            y_pos: Y position for GUI window (if spawning GUI)
        """
        self.print(f"[cyan]Spawning agent: {name}[/cyan]")

        try:
            # Create transport for this agent
            transport = TmuxTransport(
                cmd=self.agent_cmd,
                session_name=self.session_name,
                window_name=name,
                spawn_gui=self.spawn_gui,
                terminal=self.terminal,
            )

            # Start the transport
            transport.start()

            # Store agent info
            self.agents[name] = {
                "transport": transport,
                "task": task,
                "x_pos": x_pos,
                "y_pos": y_pos,
            }

            # Send initial task prompt
            time.sleep(0.2)  # Give agent time to start
            transport.send_line(f"# Agent: {name}")
            transport.send_line(f"# Task: {task}")

            self.print(f"[green]✓ {name} spawned[/green]")

        except Exception as e:
            self.print(f"[red]✗ Failed to spawn {name}: {e}[/red]")
            # Continue with other agents

    def spawn_swarm(
        self,
        agent_count: int = 3,
        layout: str = "fan",
        screen_width: int = 1920,
        screen_height: int = 1080,
        archetypes: Optional[List[Dict]] = None,
    ) -> None:
        """
        Spawn a full swarm of agents with automatic layout.

        Args:
            agent_count: Number of agents to spawn
            layout: Layout style ("fan" or "grid")
            screen_width: Screen width for layout calculation
            screen_height: Screen height for layout calculation
            archetypes: Optional list of agent archetypes
        """
        archetypes = archetypes or AGENT_ARCHETYPES
        agents_to_spawn = archetypes[:agent_count]

        self.print(f"[bold]Spawning swarm of {len(agents_to_spawn)} agents with {layout} layout...[/bold]")

        # Calculate positions
        if layout == "fan":
            positions = calculate_fan_layout(
                len(agents_to_spawn),
                screen_width=screen_width,
                screen_height=screen_height,
            )
        else:  # grid
            positions = calculate_grid_layout(
                len(agents_to_spawn),
                screen_width=screen_width,
                screen_height=screen_height,
            )

        # Spawn each agent
        for i, archetype in enumerate(agents_to_spawn):
            x, y = positions[i] if i < len(positions) else (0, 0)
            self.spawn_agent(
                name=archetype["name"],
                task=archetype["task"],
                x_pos=x,
                y_pos=y,
            )
            time.sleep(0.3)  # Stagger spawning

        self.print(f"[bold green]✓ Swarm of {len(self.agents)} agents ready![/bold green]")

    def send_to_agent(self, agent_name: str, text: str) -> None:
        """Send a command to a specific agent."""
        if agent_name not in self.agents:
            self.print(f"[red]Agent '{agent_name}' not found[/red]")
            return

        transport = self.agents[agent_name]["transport"]
        transport.send_line(text)

    def send_to_all(self, text: str) -> None:
        """Broadcast a command to all agents."""
        for agent_name in self.agents:
            self.send_to_agent(agent_name, text)

    def read_agent(self, agent_name: str) -> str:
        """Read output from a specific agent."""
        if agent_name not in self.agents:
            return f"Agent '{agent_name}' not found"

        transport = self.agents[agent_name]["transport"]
        return transport.recv_now()

    def is_agent_alive(self, agent_name: str) -> bool:
        """Check if an agent is still running."""
        if agent_name not in self.agents:
            return False

        transport = self.agents[agent_name]["transport"]
        return transport.is_alive()

    def get_status_table(self) -> Optional[TableType]:
        """Create a rich table showing agent status."""
        if not RICH_AVAILABLE or not Table:
            return None

        table = Table(title="VisualSwarm Status")
        table.add_column("Agent", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Task", style="yellow")

        for name, info in self.agents.items():
            status = "[green]●[/green]" if self.is_agent_alive(name) else "[red]●[/red]"
            task = info["task"][:40] + "..." if len(info["task"]) > 40 else info["task"]
            table.add_row(name, status, task)

        return table

    def interactive_shell(self) -> None:
        """
        Run an interactive shell for swarm control.

        Commands:
        - list: Show all agents
        - send <agent> <message>: Send message to specific agent
        - broadcast <message>: Send message to all agents
        - read <agent>: Read output from agent
        - status: Show status table
        - quit/exit: Shutdown and exit
        """
        self.print("[bold]VisualSwarm Interactive Shell[/bold]")
        self.print("Commands: list, send <agent> <msg>, broadcast <msg>, read <agent>, status, quit")
        self.print("")

        while self._running:
            try:
                cmd = input("swarm> ").strip()
                if not cmd:
                    continue

                parts = cmd.split(maxsplit=2)
                action = parts[0].lower()

                if action in ("quit", "exit"):
                    break

                elif action == "list":
                    for name in self.agents:
                        alive = "OK" if self.is_agent_alive(name) else "DEAD"
                        print(f"  {name} [{alive}]")

                elif action == "send" and len(parts) >= 3:
                    agent_name = parts[1]
                    message = parts[2]
                    self.send_to_agent(agent_name, message)
                    print(f"→ Sent to {agent_name}")

                elif action == "broadcast" and len(parts) >= 2:
                    message = parts[1]
                    self.send_to_all(message)
                    print(f"→ Broadcast to {len(self.agents)} agents")

                elif action == "read" and len(parts) >= 2:
                    agent_name = parts[1]
                    output = self.read_agent(agent_name)
                    print(f"\n--- {agent_name} ---")
                    print(output)
                    print("---\n")

                elif action == "status":
                    table = self.get_status_table()
                    if table and self.console:
                        self.console.print(table)
                    else:
                        for name in self.agents:
                            status = "OK" if self.is_agent_alive(name) else "DEAD"
                            print(f"  {name}: {status}")

                else:
                    print("Unknown command. Available: list, send, broadcast, read, status, quit")

            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

    def monitor_loop(self, interval: float = 2.0) -> None:
        """
        Run a monitoring loop with live status display.

        Args:
            interval: Update interval in seconds
        """
        if not RICH_AVAILABLE or not Live:
            self.print("[yellow]Rich not available. Use interactive shell instead.[/yellow]")
            return

        self.print("[bold]Starting swarm monitor (Ctrl+C to stop)...[/bold]")

        try:
            with Live(self.get_status_table(), refresh_per_second=1) as live:
                while self._running:
                    live.update(self.get_status_table())
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.print("\n[yellow]Monitor stopped.[/yellow]")

    def shutdown(self) -> None:
        """Shutdown the swarm and clean up resources."""
        self._running = False
        self.print("[bold red]Shutting down VisualSwarm...[/bold red]")

        # Terminate all agents
        for name, info in self.agents.items():
            try:
                transport = info["transport"]
                transport.terminate()
                self.print(f"[dim]✓ Terminated {name}[/dim]")
            except Exception as e:
                self.print(f"[dim red]✗ Error terminating {name}: {e}[/dim red]")

        # Kill tmux session
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", self.session_name],
                capture_output=True,
            )
        except Exception:
            pass

        self.agents.clear()
        self.print("[bold green]✓ VisualSwarm shutdown complete[/bold green]")

    def run(
        self,
        agent_count: int = 3,
        layout: str = "fan",
        monitor: bool = False,
    ) -> None:
        """
        Convenience method to initialize, spawn, and run the swarm.

        Args:
            agent_count: Number of agents to spawn
            layout: Layout style ("fan" or "grid")
            monitor: Use monitor mode instead of interactive shell
        """
        # Signal handlers
        def signal_handler(sig, frame):
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.initialize()
            self.spawn_swarm(agent_count=agent_count, layout=layout)

            if monitor:
                self.monitor_loop()
            else:
                self.interactive_shell()

        finally:
            self.shutdown()
