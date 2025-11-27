# swarm.py - Hierarchical Swarm Controller
"""
Unified swarm management combining:
- Hierarchical agent tree (Research/Creative/Execution branches)
- GhostSwarm visual terminal control
- Wahrscheinlichkeitsfacher (probability fan) spawning
- Senescence tracking and pruning
"""

from __future__ import annotations
import time
import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum

from .transport import Transport, TmuxTransport, PTYTransport
from .core import Agent, AgentDNA

# Optional rich console
try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    Console = None
    Table = None
    RICH_AVAILABLE = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Branch Types and Roles
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BranchType(str, Enum):
    """Specialized branches in the agent tree."""
    RESEARCH = "research"      # Information gathering
    CREATIVE = "creative"      # Solution exploration
    EXECUTION = "execution"    # Code implementation
    COORDINATION = "meta"      # Meta-orchestration


class AgentRole(str, Enum):
    """Specialized agent roles within branches."""
    # Meta
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"

    # Research
    SEARCHER = "searcher"
    ANALYZER = "analyzer"
    SYNTHESIZER = "synthesizer"

    # Creative
    GENERATOR = "generator"
    EXPLORER = "explorer"
    CRITIC = "critic"

    # Execution
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"


# Role -> Branch mapping
ROLE_BRANCH: Dict[AgentRole, BranchType] = {
    AgentRole.ORCHESTRATOR: BranchType.COORDINATION,
    AgentRole.PLANNER: BranchType.COORDINATION,
    AgentRole.SEARCHER: BranchType.RESEARCH,
    AgentRole.ANALYZER: BranchType.RESEARCH,
    AgentRole.SYNTHESIZER: BranchType.RESEARCH,
    AgentRole.GENERATOR: BranchType.CREATIVE,
    AgentRole.EXPLORER: BranchType.CREATIVE,
    AgentRole.CRITIC: BranchType.CREATIVE,
    AgentRole.CODER: BranchType.EXECUTION,
    AgentRole.TESTER: BranchType.EXECUTION,
    AgentRole.REVIEWER: BranchType.EXECUTION,
}

# Default prompts per role
ROLE_PROMPTS: Dict[AgentRole, str] = {
    AgentRole.ORCHESTRATOR: "You coordinate multiple AI agents to solve complex tasks.",
    AgentRole.PLANNER: "You break down complex tasks into actionable steps.",
    AgentRole.SEARCHER: "You search for relevant information and documentation.",
    AgentRole.ANALYZER: "You analyze code and documents for key insights.",
    AgentRole.SYNTHESIZER: "You synthesize information from multiple sources.",
    AgentRole.GENERATOR: "You generate creative solutions and approaches.",
    AgentRole.EXPLORER: "You explore alternative approaches and edge cases.",
    AgentRole.CRITIC: "You critically evaluate solutions for flaws.",
    AgentRole.CODER: "You write clean, efficient, well-documented code.",
    AgentRole.TESTER: "You design comprehensive test cases.",
    AgentRole.REVIEWER: "You review code for quality and best practices.",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tree Node - Individual agent in the hierarchy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TreeNode:
    """A node in the hierarchical agent tree."""
    id: str
    role: AgentRole
    branch: BranchType
    dna: AgentDNA

    # Hierarchy
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    depth: int = 0

    # State
    agent: Optional[Agent] = None
    is_active: bool = True
    task_queue: List[str] = field(default_factory=list)

    # Metrics
    fitness: float = 0.0
    senescence: float = 0.0  # Performance decay
    total_tasks: int = 0
    total_tokens: int = 0
    last_active: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "branch": self.branch.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "depth": self.depth,
            "is_active": self.is_active,
            "fitness": self.fitness,
            "senescence": self.senescence,
            "total_tasks": self.total_tasks,
            "queue_size": len(self.task_queue),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layout Calculators
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fan_layout(
    n: int,
    width: int = 1920,
    height: int = 1080,
    spread: float = 120,
) -> List[Tuple[int, int]]:
    """
    Wahrscheinlichkeitsfacher (probability fan) layout.

    Arranges windows in a fan pattern emanating from bottom center.
    """
    if n == 0:
        return []
    if n == 1:
        return [(width // 2 - 300, height // 2 - 200)]

    positions = []
    center_x = width // 2
    base_y = height - 100

    start_angle = 180 - spread / 2
    angle_step = spread / (n - 1) if n > 1 else 0

    for i in range(n):
        angle = math.radians(start_angle + i * angle_step)
        radius = height * 0.6
        x = int(center_x + radius * math.cos(angle) - 300)
        y = int(base_y - radius * math.sin(angle) - 200)
        positions.append((max(0, x), max(0, y)))

    return positions


def grid_layout(
    n: int,
    width: int = 1920,
    height: int = 1080,
    window_w: int = 600,
    window_h: int = 400,
) -> List[Tuple[int, int]]:
    """Simple grid layout."""
    if n == 0:
        return []

    cols = max(1, width // window_w)
    positions = []

    for i in range(n):
        row = i // cols
        col = i % cols
        x = col * window_w
        y = row * window_h
        positions.append((x, y))

    return positions


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Swarm Controller - Main orchestration class
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SwarmController:
    """
    Hierarchical multi-agent swarm controller.

    Combines:
    - Tree-based agent organization
    - Dynamic spawning based on task load
    - Senescence-based pruning
    - Visual terminal layout (optional)

    Usage:
        swarm = SwarmController()
        swarm.initialize_tree()
        swarm.spawn_agent(role=AgentRole.CODER)
        response = swarm.ask("root", "Write hello world")
        swarm.shutdown()
    """

    def __init__(
        self,
        spawn_threshold: int = 5,
        prune_threshold: float = 0.5,
        max_children: int = 4,
        use_tmux: bool = False,
        visual: bool = False,
    ):
        self.spawn_threshold = spawn_threshold
        self.prune_threshold = prune_threshold
        self.max_children = max_children
        self.use_tmux = use_tmux
        self.visual = visual

        self._nodes: Dict[str, TreeNode] = {}
        self._root_id: Optional[str] = None
        self._counter = 0

        # Branch compute allocation (0-1)
        self._compute: Dict[BranchType, float] = {
            BranchType.RESEARCH: 0.25,
            BranchType.CREATIVE: 0.25,
            BranchType.EXECUTION: 0.4,
            BranchType.COORDINATION: 0.1,
        }

        self.console = Console() if RICH_AVAILABLE else None

    # ─────────────────────────────────────────────────────
    # Tree Construction
    # ─────────────────────────────────────────────────────

    def initialize_tree(self) -> str:
        """
        Create default hierarchical tree structure:

        Orchestrator (root)
        ├── Planner
        │   ├── Searcher
        │   └── Analyzer
        ├── Generator
        │   ├── Explorer
        │   └── Critic
        └── Coder
            ├── Tester
            └── Reviewer
        """
        # Root orchestrator
        root = self._create_node(AgentRole.ORCHESTRATOR)
        self._root_id = root.id

        # Research branch
        planner = self._create_node(AgentRole.PLANNER, parent=root.id)
        self._create_node(AgentRole.SEARCHER, parent=planner.id)
        self._create_node(AgentRole.ANALYZER, parent=planner.id)

        # Creative branch
        generator = self._create_node(AgentRole.GENERATOR, parent=root.id)
        self._create_node(AgentRole.EXPLORER, parent=generator.id)
        self._create_node(AgentRole.CRITIC, parent=generator.id)

        # Execution branch
        coder = self._create_node(AgentRole.CODER, parent=root.id)
        self._create_node(AgentRole.TESTER, parent=coder.id)
        self._create_node(AgentRole.REVIEWER, parent=coder.id)

        return root.id

    def _create_node(
        self,
        role: AgentRole,
        parent: Optional[str] = None,
        cmd: Optional[List[str]] = None,
    ) -> TreeNode:
        """Create a new node in the tree."""
        self._counter += 1
        branch = ROLE_BRANCH[role]
        node_id = f"{branch.value}_{role.value}_{self._counter}"

        dna = AgentDNA(
            role=role.value,
            system_prompt=ROLE_PROMPTS.get(role, "You are a helpful assistant."),
            cmd=cmd or ["python", "-i", "-q"],
        )

        depth = 0
        if parent and parent in self._nodes:
            depth = self._nodes[parent].depth + 1
            self._nodes[parent].children.append(node_id)

        node = TreeNode(
            id=node_id,
            role=role,
            branch=branch,
            dna=dna,
            parent_id=parent,
            depth=depth,
        )

        self._nodes[node_id] = node
        return node

    # ─────────────────────────────────────────────────────
    # Agent Lifecycle
    # ─────────────────────────────────────────────────────

    def spawn_agent(
        self,
        node_id: Optional[str] = None,
        role: Optional[AgentRole] = None,
        parent_id: Optional[str] = None,
    ) -> Optional[TreeNode]:
        """
        Spawn an agent (start its process).

        Either provide node_id to start existing node, or role to create new.
        """
        if node_id:
            node = self._nodes.get(node_id)
            if not node:
                return None
        elif role:
            node = self._create_node(role, parent=parent_id or self._root_id)
        else:
            return None

        # Check max children
        if node.parent_id:
            parent = self._nodes.get(node.parent_id)
            if parent and len(parent.children) > self.max_children:
                return None

        # Start agent
        transport_type = "tmux" if self.use_tmux else "pty"
        agent = Agent(
            node.dna,
            transport_type=transport_type,
            spawn_gui=self.visual,
        )
        try:
            agent.start()
            node.agent = agent
            node.is_active = True
            return node
        except Exception as e:
            print(f"Failed to spawn {node.id}: {e}")
            return None

    def stop_agent(self, node_id: str) -> bool:
        """Stop a specific agent."""
        node = self._nodes.get(node_id)
        if node and node.agent:
            node.agent.stop()
            node.agent = None
            node.is_active = False
            return True
        return False

    # ─────────────────────────────────────────────────────
    # Task Execution
    # ─────────────────────────────────────────────────────

    def ask(
        self,
        node_id: str,
        prompt: str,
        wait_seconds: float = 30.0,
    ) -> Optional[str]:
        """Send a prompt to a specific agent."""
        node = self._nodes.get(node_id)
        if not node:
            return None

        # Auto-spawn if needed
        if not node.agent or not node.is_active:
            self.spawn_agent(node_id=node_id)

        if node.agent:
            response = node.agent.ask(prompt, wait_seconds=wait_seconds)
            node.total_tasks += 1
            node.last_active = time.time()
            return response

        return None

    def broadcast(
        self,
        prompt: str,
        branch: Optional[BranchType] = None,
    ) -> Dict[str, str]:
        """Send prompt to all agents (optionally filtered by branch)."""
        results = {}
        for node in self._nodes.values():
            if not node.is_active:
                continue
            if branch and node.branch != branch:
                continue
            response = self.ask(node.id, prompt)
            if response:
                results[node.id] = response
        return results

    # ─────────────────────────────────────────────────────
    # Dynamic Spawning (Probability Fan)
    # ─────────────────────────────────────────────────────

    def probability_spawn(
        self,
        parent_id: str,
        role_weights: Dict[AgentRole, float],
    ) -> Optional[TreeNode]:
        """
        Wahrscheinlichkeitsfacher spawning - weighted role selection.

        Args:
            parent_id: Parent node to spawn from
            role_weights: Dict mapping roles to spawn probability weights
        """
        # Normalize weights
        total = sum(role_weights.values())
        if total == 0:
            return None

        # Weighted random selection
        rand = random.random() * total
        cumulative = 0.0
        selected_role = None

        for role, weight in role_weights.items():
            cumulative += weight
            if rand <= cumulative:
                selected_role = role
                break

        if selected_role:
            return self.spawn_agent(role=selected_role, parent_id=parent_id)
        return None

    def check_auto_spawn(self) -> List[str]:
        """Check which nodes should auto-spawn children based on load."""
        should_spawn = []
        for node in self._nodes.values():
            if not node.is_active:
                continue
            if len(node.task_queue) > self.spawn_threshold:
                if len(node.children) < self.max_children:
                    should_spawn.append(node.id)
        return should_spawn

    # ─────────────────────────────────────────────────────
    # Senescence & Pruning
    # ─────────────────────────────────────────────────────

    def update_fitness(self, node_id: str, fitness: float) -> None:
        """Update node fitness and recalculate senescence."""
        node = self._nodes.get(node_id)
        if not node:
            return

        old_fitness = node.fitness
        node.fitness = fitness
        node.dna.fitness_history.append(fitness)
        node.last_active = time.time()

        # Update senescence based on fitness trend
        if fitness < old_fitness:
            # Declining performance increases senescence
            node.senescence += (old_fitness - fitness) * 0.1
        else:
            # Improving performance decreases senescence
            node.senescence = max(0, node.senescence - 0.05)

    def get_prune_candidates(self) -> List[str]:
        """Get nodes that should be pruned (high senescence + low fitness)."""
        candidates = []
        for node in self._nodes.values():
            if not node.is_active:
                continue
            if node.id == self._root_id:
                continue
            if node.senescence > self.prune_threshold and node.fitness < 3.0:
                candidates.append(node.id)
        return candidates

    def prune(self, node_id: str) -> bool:
        """Prune (deactivate) a node."""
        node = self._nodes.get(node_id)
        if not node or node.id == self._root_id:
            return False

        self.stop_agent(node_id)

        # Remove from parent's children
        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            if node_id in parent.children:
                parent.children.remove(node_id)

        return True

    # ─────────────────────────────────────────────────────
    # Compute Allocation
    # ─────────────────────────────────────────────────────

    def update_compute_allocation(self) -> Dict[BranchType, float]:
        """Update compute allocation based on branch performance."""
        branch_fitness: Dict[BranchType, float] = {}

        for branch in BranchType:
            total = sum(
                n.fitness for n in self._nodes.values()
                if n.branch == branch and n.is_active
            )
            branch_fitness[branch] = total

        total_fitness = sum(branch_fitness.values())
        if total_fitness > 0:
            self._compute = {
                b: f / total_fitness
                for b, f in branch_fitness.items()
            }
        return self._compute

    # ─────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        return self._nodes.get(node_id)

    def get_by_role(self, role: AgentRole) -> List[TreeNode]:
        return [n for n in self._nodes.values() if n.role == role and n.is_active]

    def get_by_branch(self, branch: BranchType) -> List[TreeNode]:
        return [n for n in self._nodes.values() if n.branch == branch and n.is_active]

    def get_children(self, node_id: str) -> List[TreeNode]:
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[cid] for cid in node.children if cid in self._nodes]

    def active_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.is_active)

    # ─────────────────────────────────────────────────────
    # Visual Layout
    # ─────────────────────────────────────────────────────

    def arrange_windows(self, layout: str = "fan") -> None:
        """Arrange visible windows using wmctrl (if available)."""
        if not self.visual:
            return

        active_nodes = [n for n in self._nodes.values() if n.is_active and n.agent]
        n = len(active_nodes)

        if layout == "fan":
            positions = fan_layout(n)
        else:
            positions = grid_layout(n)

        # Use wmctrl to position windows (Linux)
        import subprocess
        for i, node in enumerate(active_nodes):
            if i < len(positions):
                x, y = positions[i]
                try:
                    subprocess.run(
                        ["wmctrl", "-r", node.id, "-e", f"0,{x},{y},600,400"],
                        capture_output=True,
                        timeout=1,
                    )
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_id": self._root_id,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "compute_allocation": {b.value: v for b, v in self._compute.items()},
            "stats": {
                "total_nodes": len(self._nodes),
                "active_nodes": self.active_count(),
            },
        }

    def to_cytoscape(self) -> Dict[str, Any]:
        """Export for Cytoscape.js visualization."""
        nodes = []
        edges = []

        for node in self._nodes.values():
            nodes.append({
                "data": {
                    "id": node.id,
                    "label": f"{node.role.value}",
                    "branch": node.branch.value,
                    "fitness": node.fitness,
                    "active": node.is_active,
                }
            })
            if node.parent_id:
                edges.append({
                    "data": {
                        "source": node.parent_id,
                        "target": node.id,
                    }
                })

        return {"nodes": nodes, "edges": edges}

    # ─────────────────────────────────────────────────────
    # Status Display
    # ─────────────────────────────────────────────────────

    def print_status(self) -> None:
        """Print swarm status (uses rich if available)."""
        if RICH_AVAILABLE and self.console:
            table = Table(title="Swarm Status")
            table.add_column("ID")
            table.add_column("Role")
            table.add_column("Branch")
            table.add_column("Fitness")
            table.add_column("Active")

            for node in self._nodes.values():
                table.add_row(
                    node.id[:20],
                    node.role.value,
                    node.branch.value,
                    f"{node.fitness:.2f}",
                    "[green]Yes" if node.is_active else "[red]No",
                )
            self.console.print(table)
        else:
            print(f"Swarm: {self.active_count()} active agents")
            for node in self._nodes.values():
                status = "ACTIVE" if node.is_active else "inactive"
                print(f"  {node.id}: {node.role.value} [{status}] fit={node.fitness:.2f}")

    # ─────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Stop all agents and cleanup."""
        for node in self._nodes.values():
            if node.agent:
                try:
                    node.agent.stop()
                except Exception:
                    pass
                node.agent = None
                node.is_active = False
