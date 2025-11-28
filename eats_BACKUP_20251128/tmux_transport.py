# tmux_transport.py
"""
Tmux Transport: GhostSwarm-style multi-terminal agent control.

This module provides advanced terminal control using tmux sessions,
with optional GUI terminal manifestation via alacritty/kitty/xterm
and window positioning via wmctrl.

Features:
- Spawn agents in dedicated tmux windows
- Optional GUI terminal windows for visual monitoring
- wmctrl-based window positioning for "Wahrscheinlichkeitsfächer" layouts
- Direct pane capture without OCR
- Multi-agent swarm coordination
"""

import os
import shlex
import time
import threading
import subprocess
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass, field

# Handle libtmux import with proper type hints
if TYPE_CHECKING:
    import libtmux
    ServerType = libtmux.Server
    SessionType = libtmux.Session
    PaneType = libtmux.Pane
else:
    ServerType = Any
    SessionType = Any
    PaneType = Any

try:
    import libtmux
    LIBTMUX_AVAILABLE = True
except ImportError:
    libtmux = None
    LIBTMUX_AVAILABLE = False


@dataclass
class TmuxAgentConfig:
    """Configuration for a tmux-based agent."""
    name: str
    task_prompt: str
    command: List[str]
    x_pos: int = 0
    y_pos: int = 0
    width: int = 800
    height: int = 600
    spawn_gui: bool = False
    terminal_cmd: str = "alacritty"  # or gnome-terminal, kitty, xterm


class TmuxTransport:
    """
    Tmux-based transport for terminal-driven LLM agents.

    Creates agents in tmux windows/panes with optional GUI manifestation.
    Supports the GhostSwarm pattern for visual multi-agent orchestration.

    Usage:
        transport = TmuxTransport(session_name="eats_swarm")
        transport.start()
        pane = transport.spawn_agent(TmuxAgentConfig(
            name="coder",
            task_prompt="Write a sorting function",
            command=["python", "-i"],
            spawn_gui=True,
        ))
        transport.send_line(pane, "print('hello')")
        output = transport.capture_output(pane)
    """

    def __init__(
        self,
        session_name: str = "eats_sovereign",
        kill_existing: bool = True,
    ):
        if not LIBTMUX_AVAILABLE:
            raise ImportError("libtmux not installed. Run: pip install libtmux")

        self.session_name = session_name
        self.kill_existing = kill_existing
        self.server: Optional[ServerType] = None
        self.session: Optional[SessionType] = None
        self._panes: Dict[str, PaneType] = {}
        self._running = False
        self._reader_threads: Dict[str, threading.Thread] = {}
        self._buffers: Dict[str, str] = {}
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialize the tmux session."""
        self.server = libtmux.Server()

        # Clean slate if requested
        if self.kill_existing and self.server.has_session(self.session_name):
            self.server.kill_session(self.session_name)

        self.session = self.server.new_session(
            self.session_name,
            window_name="master_control",
        )
        self._running = True
        print(f"[TmuxTransport] Session '{self.session_name}' initialized")

    def terminate(self) -> None:
        """Terminate the tmux session and all agents."""
        self._running = False

        # Stop reader threads
        for thread in self._reader_threads.values():
            thread.join(timeout=1.0)

        # Kill tmux session
        if self.server and self.server.has_session(self.session_name):
            try:
                self.server.kill_session(self.session_name)
            except Exception as e:
                print(f"[TmuxTransport] Error killing session: {e}")

        self._panes.clear()
        self._buffers.clear()
        print(f"[TmuxTransport] Session '{self.session_name}' terminated")

    # ─────────────────────────────────────────────────────
    # Agent Spawning
    # ─────────────────────────────────────────────────────

    def spawn_agent(self, config: TmuxAgentConfig) -> PaneType:
        """
        Spawn an agent in a new tmux window.

        If spawn_gui=True, also creates a visible GUI terminal window
        attached to that tmux window and positions it on screen.
        """
        if self.session is None:
            raise RuntimeError("Session not started. Call start() first.")

        # Create tmux window
        window = self.session.new_window(window_name=config.name)
        pane = window.attached_pane

        # Store pane reference
        self._panes[config.name] = pane
        self._buffers[config.name] = ""

        # Spawn GUI terminal if requested
        if config.spawn_gui:
            self._spawn_gui_terminal(config)

        # Start the agent command - SECURITY: properly escape command args
        if config.command:
            cmd_str = " ".join(shlex.quote(arg) for arg in config.command)
            pane.send_keys(cmd_str, enter=True)
            time.sleep(0.5)  # Allow command to start

        # Inject task prompt as initial context
        # NOTE: task_prompt is sent to shell, but prefixed with # so it's a comment
        if config.task_prompt:
            pane.send_keys(f"# TASK: {config.task_prompt}", enter=True)

        # Start background reader
        self._start_reader(config.name, pane)

        return pane

    def _spawn_gui_terminal(self, config: TmuxAgentConfig) -> None:
        """Spawn a GUI terminal window attached to the tmux pane."""
        window_title = f"EATS-{config.name}"

        # Build terminal command based on terminal type
        if config.terminal_cmd == "alacritty":
            cmd = [
                "alacritty",
                "--title", window_title,
                "-e", "tmux", "attach", "-t",
                f"{self.session_name}:{config.name}",
            ]
        elif config.terminal_cmd == "kitty":
            cmd = [
                "kitty",
                "--title", window_title,
                "tmux", "attach", "-t",
                f"{self.session_name}:{config.name}",
            ]
        elif config.terminal_cmd in ("gnome-terminal", "gnome-terminal.real"):
            cmd = [
                config.terminal_cmd,
                "--title", window_title,
                "--", "tmux", "attach", "-t",
                f"{self.session_name}:{config.name}",
            ]
        else:
            # Generic xterm-style
            cmd = [
                config.terminal_cmd,
                "-T", window_title,
                "-e", f"tmux attach -t {self.session_name}:{config.name}",
            ]

        try:
            subprocess.Popen(cmd, start_new_session=True)
            time.sleep(0.5)  # Allow window manager to register

            # Position window using wmctrl
            self._position_window(window_title, config)
        except Exception as e:
            print(f"[TmuxTransport] Failed to spawn GUI terminal: {e}")

    def _position_window(self, window_title: str, config: TmuxAgentConfig) -> None:
        """Position a GUI window using wmctrl."""
        try:
            geometry = f"0,{config.x_pos},{config.y_pos},{config.width},{config.height}"
            subprocess.run(
                ["wmctrl", "-r", window_title, "-e", geometry],
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            print("[TmuxTransport] wmctrl not found, skipping window positioning")
        except Exception as e:
            print(f"[TmuxTransport] Failed to position window: {e}")

    # ─────────────────────────────────────────────────────
    # I/O Interface
    # ─────────────────────────────────────────────────────

    def send_line(self, agent_name: str, text: str) -> None:
        """Send a line to an agent's pane."""
        pane = self._panes.get(agent_name)
        if pane is None:
            raise KeyError(f"Agent '{agent_name}' not found")
        pane.send_keys(text, enter=True)

    def send_keys(self, agent_name: str, keys: str, enter: bool = False) -> None:
        """Send raw keys to an agent's pane."""
        pane = self._panes.get(agent_name)
        if pane is None:
            raise KeyError(f"Agent '{agent_name}' not found")
        pane.send_keys(keys, enter=enter)

    def capture_output(self, agent_name: str, lines: int = 50) -> str:
        """
        Capture recent output from an agent's pane.

        Uses tmux's capture-pane to get actual terminal content.
        """
        pane = self._panes.get(agent_name)
        if pane is None:
            raise KeyError(f"Agent '{agent_name}' not found")

        try:
            captured = pane.capture_pane(start=-lines)
            return "\n".join(captured) if captured else ""
        except Exception as e:
            print(f"[TmuxTransport] Capture error: {e}")
            return ""

    def recv_now(self, agent_name: str) -> str:
        """Get buffered output and clear buffer."""
        with self._lock:
            data = self._buffers.get(agent_name, "")
            self._buffers[agent_name] = ""
        return data

    def get_full_output(self, agent_name: str) -> str:
        """Get full pane history."""
        return self.capture_output(agent_name, lines=1000)

    # ─────────────────────────────────────────────────────
    # Background Reading
    # ─────────────────────────────────────────────────────

    def _start_reader(self, agent_name: str, pane: PaneType) -> None:
        """Start background thread to monitor pane output."""
        def reader_loop():
            last_content = ""
            while self._running:
                try:
                    current = "\n".join(pane.capture_pane(start=-50) or [])
                    if current != last_content:
                        # Compute new content
                        new_content = current[len(last_content):] if current.startswith(last_content) else current
                        with self._lock:
                            self._buffers[agent_name] += new_content
                        last_content = current
                except Exception:
                    pass
                time.sleep(0.1)

        thread = threading.Thread(
            target=reader_loop,
            daemon=True,
            name=f"TmuxReader-{agent_name}",
        )
        thread.start()
        self._reader_threads[agent_name] = thread

    # ─────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────

    def list_agents(self) -> List[str]:
        """List all spawned agent names."""
        return list(self._panes.keys())

    def get_pane(self, agent_name: str) -> Optional[PaneType]:
        """Get the raw libtmux Pane object for an agent."""
        return self._panes.get(agent_name)

    def is_alive(self, agent_name: str) -> bool:
        """Check if an agent's pane is still active."""
        pane = self._panes.get(agent_name)
        if pane is None:
            return False
        try:
            # Try to capture - will fail if pane is dead
            pane.capture_pane(start=-1)
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────────────────
# Layout Helpers - Wahrscheinlichkeitsfächer (Probability Fan)
# ─────────────────────────────────────────────────────────

def calculate_fan_layout(
    num_agents: int,
    screen_width: int = 1920,
    screen_height: int = 1080,
    window_width: int = 600,
    window_height: int = 400,
) -> List[Tuple[int, int]]:
    """
    Calculate positions for a "probability fan" layout.

    Arranges windows in a fan pattern emanating from center-bottom,
    representing the branching of agent possibilities.
    """
    positions = []
    if num_agents == 1:
        return [(screen_width // 2 - window_width // 2, screen_height // 2 - window_height // 2)]

    # Fan out from bottom center
    center_x = screen_width // 2
    base_y = screen_height - window_height - 50

    for i in range(num_agents):
        # Spread across width
        spread = (i - (num_agents - 1) / 2) * (window_width + 20)
        x = int(center_x + spread - window_width // 2)

        # Slight vertical variation for depth effect
        y_offset = abs(i - (num_agents - 1) / 2) * 30
        y = int(base_y - y_offset)

        positions.append((max(0, x), max(0, y)))

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
    Calculate positions for a grid layout.
    """
    cols = max(1, screen_width // (window_width + padding))
    positions = []

    for i in range(num_agents):
        row = i // cols
        col = i % cols
        x = col * (window_width + padding)
        y = row * (window_height + padding)
        positions.append((x, y))

    return positions


def calculate_hierarchy_layout(
    hierarchy: Dict[str, List[str]],  # parent -> children
    screen_width: int = 1920,
    screen_height: int = 1080,
    window_width: int = 500,
    window_height: int = 350,
) -> Dict[str, Tuple[int, int]]:
    """
    Calculate positions for a hierarchical tree layout.

    Input: {"root": ["child1", "child2"], "child1": ["grandchild1"]}
    """
    positions = {}

    # Find root (node that is not a child of anyone)
    all_children = set()
    for children in hierarchy.values():
        all_children.update(children)
    roots = [k for k in hierarchy.keys() if k not in all_children]

    if not roots:
        return positions

    # BFS to assign levels
    levels: Dict[str, int] = {}
    queue = [(root, 0) for root in roots]
    while queue:
        node, level = queue.pop(0)
        levels[node] = level
        for child in hierarchy.get(node, []):
            queue.append((child, level + 1))

    # Group by level
    level_nodes: Dict[int, List[str]] = {}
    for node, level in levels.items():
        if level not in level_nodes:
            level_nodes[level] = []
        level_nodes[level].append(node)

    # Position each level
    max_level = max(level_nodes.keys()) if level_nodes else 0
    level_height = screen_height // (max_level + 1)

    for level, nodes in level_nodes.items():
        y = level * level_height + 50
        node_width = screen_width // (len(nodes) + 1)

        for i, node in enumerate(nodes):
            x = (i + 1) * node_width - window_width // 2
            positions[node] = (max(0, x), y)

    return positions
