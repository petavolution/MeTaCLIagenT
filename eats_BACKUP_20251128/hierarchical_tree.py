# hierarchical_tree.py
"""
Hierarchical Agent Tree Structure.

Implements the multi-branch spawning tree from EATS spec:

Meta-Orchestrator (Root)
├── Research Branch
│   ├── Web Search Agents
│   ├── Document Analysis Agents
│   └── Synthesis Agent
├── Creative Branch
│   ├── Text Generators
│   ├── Image Coordinators
│   └── Multimodal Fusion Agent
└── Execution Branch
    ├── Code Executors
    ├── File System Agents
    └── QA Agent

Features:
- Dynamic spawning based on task queue depth
- Gradient-based compute allocation
- Branch specialization detection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import time
import random


class BranchType(str, Enum):
    """Types of specialized branches in the agent tree."""
    RESEARCH = "research"
    CREATIVE = "creative"
    EXECUTION = "execution"
    ANALYSIS = "analysis"
    COORDINATION = "coordination"


class AgentRole(str, Enum):
    """Specialized agent roles within branches."""
    # Research Branch
    WEB_SEARCH = "web_search"
    DOCUMENT_ANALYSIS = "document_analysis"
    SYNTHESIS = "synthesis"

    # Creative Branch
    TEXT_GENERATOR = "text_generator"
    IMAGE_COORDINATOR = "image_coordinator"
    MULTIMODAL_FUSION = "multimodal_fusion"

    # Execution Branch
    CODE_EXECUTOR = "code_executor"
    FILE_SYSTEM = "file_system"
    QA_AGENT = "qa_agent"

    # Meta roles
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    CRITIC = "critic"


@dataclass
class TreeNode:
    """A node in the hierarchical agent tree."""
    id: str
    role: AgentRole
    branch: BranchType
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)

    # Operational state
    task_queue_depth: int = 0
    current_fitness: float = 0.0
    total_tokens_processed: int = 0
    spawn_count: int = 0
    last_active: float = field(default_factory=time.time)

    # Lifecycle state
    is_active: bool = True
    senescence_score: float = 0.0  # Performance decay marker

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "role": self.role.value,
            "branch": self.branch.value,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "task_queue_depth": self.task_queue_depth,
            "current_fitness": self.current_fitness,
            "total_tokens_processed": self.total_tokens_processed,
            "spawn_count": self.spawn_count,
            "is_active": self.is_active,
            "senescence_score": self.senescence_score,
        }


@dataclass
class Branch:
    """A branch in the agent tree (e.g., Research, Creative, Execution)."""
    type: BranchType
    root_node_id: str
    node_ids: List[str] = field(default_factory=list)
    total_fitness: float = 0.0
    compute_allocation: float = 0.33  # Fraction of total compute

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "root_node_id": self.root_node_id,
            "node_count": len(self.node_ids),
            "total_fitness": self.total_fitness,
            "compute_allocation": self.compute_allocation,
        }


class HierarchicalAgentTree:
    """
    Hierarchical spawning tree for multi-agent orchestration.

    Implements:
    - Branch-based organization (Research/Creative/Execution)
    - Dynamic spawning based on task queue depth
    - Gradient-based compute allocation
    - Senescence detection and pruning
    """

    def __init__(
        self,
        spawn_threshold: int = 5,
        prune_threshold: float = 0.3,
        max_children_per_node: int = 4,
    ):
        self.spawn_threshold = spawn_threshold
        self.prune_threshold = prune_threshold
        self.max_children_per_node = max_children_per_node

        self._nodes: Dict[str, TreeNode] = {}
        self._branches: Dict[BranchType, Branch] = {}
        self._root_id: Optional[str] = None
        self._node_counter = 0

    # ─────────────────────────────────────────────────────
    # Tree Construction
    # ─────────────────────────────────────────────────────

    def initialize_default_tree(self) -> str:
        """
        Initialize the default hierarchical structure.

        Returns the root node ID.
        """
        # Create root orchestrator
        root = self._create_node(
            role=AgentRole.ORCHESTRATOR,
            branch=BranchType.COORDINATION,
        )
        self._root_id = root.id

        # Create branch roots
        research_root = self._create_node(
            role=AgentRole.PLANNER,
            branch=BranchType.RESEARCH,
            parent_id=root.id,
        )
        creative_root = self._create_node(
            role=AgentRole.TEXT_GENERATOR,
            branch=BranchType.CREATIVE,
            parent_id=root.id,
        )
        execution_root = self._create_node(
            role=AgentRole.CODE_EXECUTOR,
            branch=BranchType.EXECUTION,
            parent_id=root.id,
        )

        # Register branches
        self._branches[BranchType.RESEARCH] = Branch(
            type=BranchType.RESEARCH,
            root_node_id=research_root.id,
            node_ids=[research_root.id],
        )
        self._branches[BranchType.CREATIVE] = Branch(
            type=BranchType.CREATIVE,
            root_node_id=creative_root.id,
            node_ids=[creative_root.id],
        )
        self._branches[BranchType.EXECUTION] = Branch(
            type=BranchType.EXECUTION,
            root_node_id=execution_root.id,
            node_ids=[execution_root.id],
        )

        # Add initial specialized agents to each branch
        self._populate_research_branch(research_root.id)
        self._populate_creative_branch(creative_root.id)
        self._populate_execution_branch(execution_root.id)

        return root.id

    def _populate_research_branch(self, root_id: str) -> None:
        """Add specialized agents to research branch."""
        branch = self._branches[BranchType.RESEARCH]

        for role in [AgentRole.WEB_SEARCH, AgentRole.DOCUMENT_ANALYSIS, AgentRole.SYNTHESIS]:
            node = self._create_node(
                role=role,
                branch=BranchType.RESEARCH,
                parent_id=root_id,
            )
            branch.node_ids.append(node.id)

    def _populate_creative_branch(self, root_id: str) -> None:
        """Add specialized agents to creative branch."""
        branch = self._branches[BranchType.CREATIVE]

        for role in [AgentRole.TEXT_GENERATOR, AgentRole.IMAGE_COORDINATOR, AgentRole.MULTIMODAL_FUSION]:
            node = self._create_node(
                role=role,
                branch=BranchType.CREATIVE,
                parent_id=root_id,
            )
            branch.node_ids.append(node.id)

    def _populate_execution_branch(self, root_id: str) -> None:
        """Add specialized agents to execution branch."""
        branch = self._branches[BranchType.EXECUTION]

        for role in [AgentRole.CODE_EXECUTOR, AgentRole.FILE_SYSTEM, AgentRole.QA_AGENT]:
            node = self._create_node(
                role=role,
                branch=BranchType.EXECUTION,
                parent_id=root_id,
            )
            branch.node_ids.append(node.id)

    def _create_node(
        self,
        role: AgentRole,
        branch: BranchType,
        parent_id: Optional[str] = None,
    ) -> TreeNode:
        """Create a new node in the tree."""
        self._node_counter += 1
        node_id = f"{branch.value}_{role.value}_{self._node_counter}"

        node = TreeNode(
            id=node_id,
            role=role,
            branch=branch,
            parent_id=parent_id,
        )

        self._nodes[node_id] = node

        # Update parent's children list
        if parent_id and parent_id in self._nodes:
            self._nodes[parent_id].children_ids.append(node_id)
            self._nodes[parent_id].spawn_count += 1

        return node

    # ─────────────────────────────────────────────────────
    # Dynamic Spawning
    # ─────────────────────────────────────────────────────

    def check_spawn_conditions(self) -> List[str]:
        """
        Check which nodes should spawn children based on queue depth.

        Returns list of node IDs that should spawn.
        """
        should_spawn = []

        for node in self._nodes.values():
            if not node.is_active:
                continue

            # Check if queue depth exceeds threshold
            if node.task_queue_depth > self.spawn_threshold:
                # Check if can spawn more children
                if len(node.children_ids) < self.max_children_per_node:
                    should_spawn.append(node.id)

        return should_spawn

    def spawn_child(
        self,
        parent_id: str,
        role: Optional[AgentRole] = None,
    ) -> Optional[TreeNode]:
        """
        Spawn a child node from a parent.

        If role not specified, inherits parent's role (cloning).
        """
        parent = self._nodes.get(parent_id)
        if not parent:
            return None

        if len(parent.children_ids) >= self.max_children_per_node:
            return None

        child_role = role or parent.role
        child = self._create_node(
            role=child_role,
            branch=parent.branch,
            parent_id=parent_id,
        )

        # Add to branch
        if parent.branch in self._branches:
            self._branches[parent.branch].node_ids.append(child.id)

        return child

    def probability_fan_spawn(
        self,
        parent_id: str,
        role_probabilities: Dict[AgentRole, float],
    ) -> Optional[TreeNode]:
        """
        Wahrscheinlichkeitsfächer (Probability Fan) spawning.

        Spawn a child with role selected via weighted probabilities.
        """
        # Normalize probabilities
        total = sum(role_probabilities.values())
        if total == 0:
            return None

        normalized = {r: p / total for r, p in role_probabilities.items()}

        # Weighted random selection
        rand = random.random()
        cumulative = 0.0
        selected_role = None

        for role, prob in normalized.items():
            cumulative += prob
            if rand <= cumulative:
                selected_role = role
                break

        if selected_role:
            return self.spawn_child(parent_id, selected_role)

        return None

    # ─────────────────────────────────────────────────────
    # Compute Allocation
    # ─────────────────────────────────────────────────────

    def update_compute_allocation(self) -> None:
        """
        Gradient-based compute allocation.

        Allocates more compute to high-fitness branches.
        """
        total_fitness = sum(b.total_fitness for b in self._branches.values())

        if total_fitness == 0:
            # Equal allocation
            for branch in self._branches.values():
                branch.compute_allocation = 1.0 / len(self._branches)
        else:
            # Fitness-weighted allocation
            for branch in self._branches.values():
                branch.compute_allocation = branch.total_fitness / total_fitness

    def get_compute_allocation(self) -> Dict[BranchType, float]:
        """Get current compute allocation per branch."""
        return {b.type: b.compute_allocation for b in self._branches.values()}

    # ─────────────────────────────────────────────────────
    # Senescence & Pruning
    # ─────────────────────────────────────────────────────

    def update_senescence(self, node_id: str, performance_delta: float) -> None:
        """
        Update senescence score based on performance trend.

        Negative performance delta increases senescence.
        """
        node = self._nodes.get(node_id)
        if not node:
            return

        if performance_delta < 0:
            # Performance decay increases senescence
            node.senescence_score += abs(performance_delta) * 0.1
        else:
            # Good performance reduces senescence
            node.senescence_score = max(0, node.senescence_score - performance_delta * 0.05)

    def get_prune_candidates(self) -> List[str]:
        """
        Get nodes that should be pruned (high senescence, low fitness).

        Bottom 10% by fitness that also have high senescence.
        """
        active_nodes = [n for n in self._nodes.values() if n.is_active and n.id != self._root_id]

        if len(active_nodes) < 5:
            return []

        # Sort by fitness (ascending)
        sorted_nodes = sorted(active_nodes, key=lambda n: n.current_fitness)

        # Bottom 10%
        prune_count = max(1, len(sorted_nodes) // 10)
        candidates = []

        for node in sorted_nodes[:prune_count]:
            if node.senescence_score > self.prune_threshold:
                candidates.append(node.id)

        return candidates

    def prune_node(self, node_id: str) -> bool:
        """
        Prune (deactivate) a node.

        Returns True if pruned, False if protected (e.g., root or branch root).
        """
        node = self._nodes.get(node_id)
        if not node:
            return False

        # Don't prune root or branch roots
        if node_id == self._root_id:
            return False

        for branch in self._branches.values():
            if node_id == branch.root_node_id:
                return False

        node.is_active = False

        # Remove from branch
        if node.branch in self._branches:
            branch = self._branches[node.branch]
            if node_id in branch.node_ids:
                branch.node_ids.remove(node_id)

        return True

    # ─────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        return self._nodes.get(node_id)

    def get_branch(self, branch_type: BranchType) -> Optional[Branch]:
        return self._branches.get(branch_type)

    def get_nodes_by_role(self, role: AgentRole) -> List[TreeNode]:
        return [n for n in self._nodes.values() if n.role == role and n.is_active]

    def get_nodes_by_branch(self, branch_type: BranchType) -> List[TreeNode]:
        return [n for n in self._nodes.values() if n.branch == branch_type and n.is_active]

    def get_children(self, node_id: str) -> List[TreeNode]:
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[cid] for cid in node.children_ids if cid in self._nodes]

    def get_active_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.is_active)

    # ─────────────────────────────────────────────────────
    # Update Operations
    # ─────────────────────────────────────────────────────

    def update_node_fitness(self, node_id: str, fitness: float) -> None:
        """Update a node's fitness and recalculate branch totals."""
        node = self._nodes.get(node_id)
        if not node:
            return

        old_fitness = node.current_fitness
        node.current_fitness = fitness
        node.last_active = time.time()

        # Update senescence based on change
        self.update_senescence(node_id, fitness - old_fitness)

        # Recalculate branch fitness
        if node.branch in self._branches:
            branch = self._branches[node.branch]
            branch.total_fitness = sum(
                self._nodes[nid].current_fitness
                for nid in branch.node_ids
                if nid in self._nodes and self._nodes[nid].is_active
            )

    def update_queue_depth(self, node_id: str, depth: int) -> None:
        """Update a node's task queue depth."""
        node = self._nodes.get(node_id)
        if node:
            node.task_queue_depth = depth

    def add_tokens_processed(self, node_id: str, tokens: int) -> None:
        """Add to a node's token count."""
        node = self._nodes.get(node_id)
        if node:
            node.total_tokens_processed += tokens

    # ─────────────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        """Serialize tree to dictionary."""
        return {
            "root_id": self._root_id,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "branches": {bt.value: b.to_dict() for bt, b in self._branches.items()},
            "stats": {
                "total_nodes": len(self._nodes),
                "active_nodes": self.get_active_count(),
                "total_spawns": sum(n.spawn_count for n in self._nodes.values()),
            },
        }

    def to_cytoscape_elements(self) -> Dict:
        """Export tree as Cytoscape.js elements."""
        nodes = []
        edges = []

        for node in self._nodes.values():
            nodes.append({
                "data": {
                    "id": node.id,
                    "label": f"{node.role.value}\n({node.branch.value})",
                    "role": node.role.value,
                    "branch": node.branch.value,
                    "fitness": node.current_fitness,
                    "queue_depth": node.task_queue_depth,
                    "is_active": node.is_active,
                    "senescence": node.senescence_score,
                    # Visual encoding
                    "fitness_color": self._fitness_to_color(node.current_fitness),
                    "size": max(20, min(100, node.total_tokens_processed / 100)),
                    "opacity": 1.0 if node.is_active else 0.3,
                }
            })

            # Add edge to parent
            if node.parent_id:
                edges.append({
                    "data": {
                        "id": f"e_{node.parent_id}_{node.id}",
                        "source": node.parent_id,
                        "target": node.id,
                        "weight": node.current_fitness,
                    }
                })

        return {"nodes": nodes, "edges": edges}

    def _fitness_to_color(self, fitness: float) -> str:
        """Convert fitness to color for visualization."""
        if fitness >= 8:
            return "#2ecc71"  # Green
        if fitness >= 5:
            return "#f1c40f"  # Yellow
        if fitness >= 2:
            return "#e67e22"  # Orange
        return "#e74c3c"  # Red
