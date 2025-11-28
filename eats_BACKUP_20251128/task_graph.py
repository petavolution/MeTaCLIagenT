# task_graph.py
"""
Task Graph: Data structures for the orchestration graph.

This module provides the graph representation that tracks:
- Tasks being worked on
- Agent nodes (from blueprints)
- Evolutionary lineage (parent/child relationships)
- Task-agent relationships (which agents attempt which tasks)

The graph is what gets visualized in the web UI.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

from .config_models import AgentBlueprint, TaskSpec


@dataclass
class AgentNode:
    """
    A node representing an agent in the orchestration graph.

    Attributes:
        id: Unique node identifier
        blueprint_id: Reference to the AgentBlueprint
        role: Agent role (coder, tester, etc.)
        generation: Which evolutionary generation
        fitness: Last evaluated fitness score
        state: Current state (idle, busy, etc.)
        parent_id: Parent agent node (for evolution lineage)
        created_at: Timestamp
    """
    id: str
    blueprint_id: str
    role: str
    generation: int = 0
    fitness: Optional[float] = None
    state: str = "idle"
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": "agent",
            "blueprint_id": self.blueprint_id,
            "role": self.role,
            "generation": self.generation,
            "fitness": self.fitness,
            "state": self.state,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
        }


@dataclass
class TaskNode:
    """
    A node representing a task in the orchestration graph.

    Attributes:
        id: Unique node identifier
        description: Task description
        status: pending | in_progress | completed | failed
        result: Final result if completed
    """
    id: str
    description: str
    status: str = "pending"
    result: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": "task",
            "description": self.description,
            "status": self.status,
            "result": self.result[:200] if self.result else None,
            "created_at": self.created_at,
        }


@dataclass
class Edge:
    """
    An edge in the orchestration graph.

    Edge types:
    - "evolved_from": Agent evolved from parent agent
    - "attempts": Agent attempts a task
    - "completed": Agent completed a task
    - "spawned": Task spawned an agent
    """
    id: str
    source: str
    target: str
    edge_type: str
    weight: float = 1.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "metadata": self.metadata,
        }


class OrchestrationGraph:
    """
    The full orchestration graph.

    Provides methods to:
    - Add/remove nodes and edges
    - Query the graph
    - Export for visualization (Cytoscape.js format)

    Usage:
        graph = OrchestrationGraph()
        task_node = graph.add_task(task_spec)
        agent_node = graph.add_agent(blueprint, generation=0)
        graph.add_edge(agent_node.id, task_node.id, "attempts")
    """

    def __init__(self):
        self.agent_nodes: Dict[str, AgentNode] = {}
        self.task_nodes: Dict[str, TaskNode] = {}
        self.edges: Dict[str, Edge] = {}
        self._edge_counter = 0

    # ─────────────────────────────────────────────────────
    # Node Management
    # ─────────────────────────────────────────────────────

    def add_task(self, task: TaskSpec) -> TaskNode:
        """Add a task to the graph."""
        node = TaskNode(
            id=task.id,
            description=task.description,
            status="pending",
        )
        self.task_nodes[node.id] = node
        return node

    def add_agent(
        self,
        blueprint: AgentBlueprint,
        session_id: str,
        generation: int = 0,
        parent_agent_id: Optional[str] = None,
    ) -> AgentNode:
        """
        Add an agent to the graph.

        Args:
            blueprint: The agent's blueprint
            session_id: The running session ID
            generation: Evolutionary generation
            parent_agent_id: Optional parent for lineage tracking
        """
        node = AgentNode(
            id=session_id,
            blueprint_id=blueprint.id,
            role=blueprint.role,
            generation=generation,
            parent_id=parent_agent_id,
        )
        self.agent_nodes[node.id] = node

        # Add evolution edge if parent exists
        if parent_agent_id:
            self.add_edge(parent_agent_id, session_id, "evolved_from")

        return node

    def update_agent_fitness(self, agent_id: str, fitness: float) -> None:
        """Update an agent's fitness score."""
        if agent_id in self.agent_nodes:
            self.agent_nodes[agent_id].fitness = fitness

    def update_agent_state(self, agent_id: str, state: str) -> None:
        """Update an agent's state."""
        if agent_id in self.agent_nodes:
            self.agent_nodes[agent_id].state = state

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> None:
        """Update a task's status and optional result."""
        if task_id in self.task_nodes:
            self.task_nodes[task_id].status = status
            if result:
                self.task_nodes[task_id].result = result

    # ─────────────────────────────────────────────────────
    # Edge Management
    # ─────────────────────────────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> Edge:
        """Add an edge between two nodes."""
        self._edge_counter += 1
        edge_id = f"e{self._edge_counter}"
        edge = Edge(
            id=edge_id,
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            metadata=metadata or {},
        )
        self.edges[edge_id] = edge
        return edge

    def get_edges_from(self, node_id: str) -> List[Edge]:
        """Get all edges originating from a node."""
        return [e for e in self.edges.values() if e.source == node_id]

    def get_edges_to(self, node_id: str) -> List[Edge]:
        """Get all edges pointing to a node."""
        return [e for e in self.edges.values() if e.target == node_id]

    # ─────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────

    def get_agents_by_generation(self, generation: int) -> List[AgentNode]:
        """Get all agents in a specific generation."""
        return [a for a in self.agent_nodes.values() if a.generation == generation]

    def get_children(self, agent_id: str) -> List[AgentNode]:
        """Get child agents (evolved from this agent)."""
        return [a for a in self.agent_nodes.values() if a.parent_id == agent_id]

    def get_lineage(self, agent_id: str) -> List[AgentNode]:
        """Get the full lineage (ancestors) of an agent."""
        lineage = []
        current = self.agent_nodes.get(agent_id)
        while current and current.parent_id:
            parent = self.agent_nodes.get(current.parent_id)
            if parent:
                lineage.append(parent)
                current = parent
            else:
                break
        return lineage

    def get_best_agent(self) -> Optional[AgentNode]:
        """Get the agent with highest fitness."""
        agents_with_fitness = [a for a in self.agent_nodes.values() if a.fitness is not None]
        if not agents_with_fitness:
            return None
        return max(agents_with_fitness, key=lambda a: a.fitness or 0)

    # ─────────────────────────────────────────────────────
    # Export for Visualization
    # ─────────────────────────────────────────────────────

    def to_cytoscape_json(self) -> Dict:
        """
        Export graph in Cytoscape.js format.

        Returns:
            {
                "nodes": [{"data": {...}}, ...],
                "edges": [{"data": {...}}, ...]
            }
        """
        nodes = []

        # Agent nodes
        for agent in self.agent_nodes.values():
            nodes.append({
                "data": {
                    **agent.to_dict(),
                    "label": f"{agent.role} (g{agent.generation})",
                    "fitness_color": self._fitness_to_color(agent.fitness),
                }
            })

        # Task nodes
        for task in self.task_nodes.values():
            nodes.append({
                "data": {
                    **task.to_dict(),
                    "label": task.description[:30],
                }
            })

        # Edges
        edges = [{"data": e.to_dict()} for e in self.edges.values()]

        return {"nodes": nodes, "edges": edges}

    def to_dict(self) -> Dict:
        """Export full graph as dictionary."""
        return {
            "agent_nodes": {k: v.to_dict() for k, v in self.agent_nodes.items()},
            "task_nodes": {k: v.to_dict() for k, v in self.task_nodes.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
            "stats": {
                "total_agents": len(self.agent_nodes),
                "total_tasks": len(self.task_nodes),
                "total_edges": len(self.edges),
                "max_generation": max((a.generation for a in self.agent_nodes.values()), default=0),
            },
        }

    def _fitness_to_color(self, fitness: Optional[float]) -> str:
        """Convert fitness score to a color for visualization."""
        if fitness is None:
            return "#888888"  # Gray for unevaluated
        if fitness >= 8:
            return "#2ecc71"  # Green for high fitness
        if fitness >= 5:
            return "#f1c40f"  # Yellow for medium
        return "#e74c3c"  # Red for low

    def clear(self) -> None:
        """Clear the entire graph."""
        self.agent_nodes.clear()
        self.task_nodes.clear()
        self.edges.clear()
        self._edge_counter = 0
