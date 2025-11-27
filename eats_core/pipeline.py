# pipeline.py - Result Aggregation Pipeline
"""
Streamlined result processing and fusion system.

Features:
- DAG-based result tree
- Semantic deduplication (hash-based cache)
- Multiple fusion strategies (vote, synthesize, rollup)
- Context propagation from parents
"""

from __future__ import annotations
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .conflict import ConflictDetector, ConflictResolver


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Output Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FusionMethod(str, Enum):
    """Methods for combining multiple outputs."""
    VOTE = "vote"           # Select highest fitness
    SYNTHESIZE = "synthesize"  # Weighted combination
    ROLLUP = "rollup"       # Hierarchical consolidation
    CONCAT = "concat"       # Simple concatenation
    ARBITRATION = "arbitration"  # Conflict resolution via meta-agent


@dataclass
class FusedOutput:
    """Result of processing/fusing agent outputs."""
    agent_id: str
    content: str
    fitness: float
    timestamp: float = field(default_factory=time.time)

    # Provenance
    parent_id: Optional[str] = None
    source_ids: List[str] = field(default_factory=list)
    fusion_method: Optional[FusionMethod] = None

    # Metadata
    hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.md5(self.content[:500].encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "content": self.content[:500] + ("..." if len(self.content) > 500 else ""),
            "fitness": round(self.fitness, 2),
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "source_ids": self.source_ids,
            "fusion_method": self.fusion_method.value if self.fusion_method else None,
            "hash": self.hash,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DAG Node
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class DAGNode:
    """A node in the result DAG."""
    id: str
    output: FusedOutput
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    depth: int = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Result Pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ResultPipeline:
    """
    Pipeline for processing and aggregating agent outputs.

    Maintains a DAG of results with:
    - Semantic caching (dedupe similar outputs)
    - Parent context propagation
    - Multiple fusion strategies

    Usage:
        pipeline = ResultPipeline()

        # Add individual outputs
        output = pipeline.add("agent-1", "Hello world", fitness=7.5)

        # Add with parent context
        output = pipeline.add("agent-2", "Response", fitness=8.0, parent="agent-1")

        # Fuse multiple outputs
        fused = pipeline.fuse(["agent-1", "agent-2"], method=FusionMethod.VOTE)

        # Get final rollup
        final = pipeline.rollup()
    """

    def __init__(
        self,
        fitness_fn: Optional[Callable[[str], float]] = None,
        synthesize_fn: Optional[Callable[[str, Optional[str]], str]] = None,
        enable_conflict_resolution: bool = False,
    ):
        self._nodes: Dict[str, DAGNode] = {}
        self._cache: Dict[str, str] = {}  # hash -> node_id
        self._roots: List[str] = []
        self._counter = 0

        self._fitness_fn = fitness_fn or self._default_fitness
        self._synthesize_fn = synthesize_fn or self._default_synthesize

        # Conflict resolution (lazy init)
        self._enable_conflict_resolution = enable_conflict_resolution
        self._conflict_detector: Optional[ConflictDetector] = None
        self._conflict_resolver: Optional[ConflictResolver] = None

    # ─────────────────────────────────────────────────────
    # Add Outputs
    # ─────────────────────────────────────────────────────

    def add(
        self,
        agent_id: str,
        content: str,
        fitness: Optional[float] = None,
        parent: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> FusedOutput:
        """
        Add an agent output to the pipeline.

        Args:
            agent_id: Source agent identifier
            content: The output content
            fitness: Optional fitness score (computed if not provided)
            parent: Optional parent agent/node ID for context
            metadata: Optional metadata dict

        Returns:
            FusedOutput with computed hash and fitness
        """
        # Check cache for duplicates
        content_hash = hashlib.md5(content[:500].encode()).hexdigest()[:12]
        if content_hash in self._cache:
            existing_id = self._cache[content_hash]
            if existing_id in self._nodes:
                return self._nodes[existing_id].output

        # Get parent context
        parent_node = None
        parent_ctx = None
        if parent:
            # Look up by agent_id or node_id
            parent_node = self._find_node(parent)
            if parent_node:
                parent_ctx = parent_node.output.content

        # Synthesize with context
        synthesized = self._synthesize_fn(content, parent_ctx)

        # Compute fitness
        if fitness is None:
            fitness = self._fitness_fn(synthesized)

        # Create output
        output = FusedOutput(
            agent_id=agent_id,
            content=synthesized,
            fitness=fitness,
            parent_id=parent,
            hash=content_hash,
            metadata=metadata or {},
        )

        # Create DAG node
        self._counter += 1
        node_id = f"node_{self._counter}"

        depth = 0
        parent_node_id = None
        if parent_node:
            parent_node_id = parent_node.id
            depth = parent_node.depth + 1
            parent_node.children.append(node_id)

        node = DAGNode(
            id=node_id,
            output=output,
            parent_id=parent_node_id,
            depth=depth,
        )

        self._nodes[node_id] = node
        self._cache[content_hash] = node_id

        if parent_node_id is None:
            self._roots.append(node_id)

        return output

    def _find_node(self, identifier: str) -> Optional[DAGNode]:
        """Find node by ID or agent_id."""
        # Direct node ID
        if identifier in self._nodes:
            return self._nodes[identifier]

        # Search by agent_id (return most recent)
        for node in reversed(list(self._nodes.values())):
            if node.output.agent_id == identifier:
                return node

        return None

    # ─────────────────────────────────────────────────────
    # Fusion Methods
    # ─────────────────────────────────────────────────────

    def fuse(
        self,
        identifiers: List[str],
        method: FusionMethod = FusionMethod.VOTE,
    ) -> FusedOutput:
        """
        Fuse multiple outputs into one.

        Args:
            identifiers: List of node/agent IDs to fuse
            method: Fusion strategy to use

        Returns:
            Fused output
        """
        outputs = []
        for ident in identifiers:
            node = self._find_node(ident)
            if node:
                outputs.append(node.output)

        if not outputs:
            raise ValueError("No outputs found to fuse")

        if method == FusionMethod.VOTE:
            return self._vote(outputs)
        elif method == FusionMethod.SYNTHESIZE:
            return self._synthesize(outputs)
        elif method == FusionMethod.CONCAT:
            return self._concat(outputs)
        elif method == FusionMethod.ARBITRATION:
            return self.fuse_with_resolution(identifiers)
        else:
            return self._vote(outputs)

    def fuse_with_resolution(
        self,
        identifiers: List[str],
        auto_detect: bool = True,
    ) -> FusedOutput:
        """
        Fuse outputs with automatic conflict detection and resolution.

        Args:
            identifiers: List of node/agent IDs to fuse
            auto_detect: Whether to auto-detect conflicts (default: True)

        Returns:
            Fused output (resolution if conflict found, otherwise synthesis)
        """
        # Lazy init conflict resolution
        if not self._conflict_detector or not self._conflict_resolver:
            self._init_conflict_resolution()

        # Collect outputs
        outputs = []
        for ident in identifiers:
            node = self._find_node(ident)
            if node:
                outputs.append(node.output)

        if not outputs:
            raise ValueError("No outputs found to fuse")

        # Detect conflicts
        conflicts = []
        if auto_detect and self._conflict_detector:
            conflicts = self._conflict_detector.detect(outputs)

        # Resolve if conflicts found
        if conflicts and self._conflict_resolver:
            # Resolve most severe conflict
            conflict = max(conflicts, key=lambda c: c.severity)
            return self._conflict_resolver.resolve(conflict)

        # Fallback to synthesis
        return self._synthesize(outputs)

    def _init_conflict_resolution(self) -> None:
        """Lazy initialization of conflict resolution components."""
        if self._conflict_detector and self._conflict_resolver:
            return

        # Import here to avoid circular dependency
        from .conflict import ConflictDetector, ConflictResolver

        self._conflict_detector = ConflictDetector(use_llm=False)
        self._conflict_resolver = ConflictResolver()

    def _vote(self, outputs: List[FusedOutput]) -> FusedOutput:
        """Select output with highest fitness."""
        best = max(outputs, key=lambda o: o.fitness)
        return FusedOutput(
            agent_id="fused_vote",
            content=best.content,
            fitness=best.fitness,
            source_ids=[o.agent_id for o in outputs],
            fusion_method=FusionMethod.VOTE,
            metadata={"winner": best.agent_id, "count": len(outputs)},
        )

    def _synthesize(self, outputs: List[FusedOutput]) -> FusedOutput:
        """Weighted combination based on fitness."""
        # Sort by fitness
        sorted_outputs = sorted(outputs, key=lambda o: o.fitness, reverse=True)
        total_fitness = sum(o.fitness for o in outputs)

        # Build weighted content
        parts = []
        for o in sorted_outputs:
            weight = o.fitness / total_fitness if total_fitness > 0 else 1 / len(outputs)
            parts.append(f"[{o.agent_id}: weight={weight:.2f}]\n{o.content[:300]}")

        combined = "\n\n---\n\n".join(parts)
        avg_fitness = total_fitness / len(outputs)

        return FusedOutput(
            agent_id="fused_synthesize",
            content=combined,
            fitness=avg_fitness,
            source_ids=[o.agent_id for o in outputs],
            fusion_method=FusionMethod.SYNTHESIZE,
            metadata={"count": len(outputs)},
        )

    def _concat(self, outputs: List[FusedOutput]) -> FusedOutput:
        """Simple concatenation."""
        parts = [f"=== {o.agent_id} ===\n{o.content}" for o in outputs]
        combined = "\n\n".join(parts)
        avg_fitness = sum(o.fitness for o in outputs) / len(outputs)

        return FusedOutput(
            agent_id="fused_concat",
            content=combined,
            fitness=avg_fitness,
            source_ids=[o.agent_id for o in outputs],
            fusion_method=FusionMethod.CONCAT,
        )

    # ─────────────────────────────────────────────────────
    # Hierarchical Rollup
    # ─────────────────────────────────────────────────────

    def rollup(self) -> Optional[FusedOutput]:
        """
        Hierarchical rollup from leaves to root.

        Consolidates all leaf outputs upward.
        """
        leaves = self.get_leaves()
        if not leaves:
            return None

        if len(leaves) == 1:
            return leaves[0].output

        outputs = [node.output for node in leaves]
        return self._synthesize(outputs)

    def get_leaves(self) -> List[DAGNode]:
        """Get all leaf nodes (no children)."""
        return [n for n in self._nodes.values() if not n.children]

    def get_by_depth(self, depth: int) -> List[DAGNode]:
        """Get all nodes at a specific depth."""
        return [n for n in self._nodes.values() if n.depth == depth]

    def get_ancestors(self, node_id: str) -> List[DAGNode]:
        """Get all ancestors from node to root."""
        ancestors = []
        current = self._nodes.get(node_id)

        while current and current.parent_id:
            parent = self._nodes.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break

        return ancestors

    # ─────────────────────────────────────────────────────
    # Default Functions
    # ─────────────────────────────────────────────────────

    def _default_fitness(self, content: str) -> float:
        """Simple heuristic fitness."""
        score = 0.0

        # Length
        length = len(content)
        if length < 50:
            score += 1
        elif length < 500:
            score += 2
        elif length < 1500:
            score += 3
        else:
            score += 2

        # Code presence
        if "def " in content or "class " in content or "```" in content:
            score += 2

        # Structure
        if any(m in content for m in ["1.", "- ", "* "]):
            score += 1

        return min(10.0, score)

    def _default_synthesize(
        self,
        content: str,
        parent_ctx: Optional[str],
    ) -> str:
        """Default synthesis: prepend context summary."""
        if not parent_ctx:
            return content

        # Simple: add context marker
        ctx_preview = parent_ctx[:100].replace("\n", " ")
        return f"[Context: {ctx_preview}...]\n\n{content}"

    # ─────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────

    def get(self, identifier: str) -> Optional[FusedOutput]:
        """Get output by node/agent ID."""
        node = self._find_node(identifier)
        return node.output if node else None

    def get_by_agent(self, agent_id: str) -> List[FusedOutput]:
        """Get all outputs from a specific agent."""
        return [
            n.output for n in self._nodes.values()
            if n.output.agent_id == agent_id
        ]

    def get_all(self) -> List[FusedOutput]:
        """Get all outputs."""
        return [n.output for n in self._nodes.values()]

    def get_top(self, n: int = 5) -> List[FusedOutput]:
        """Get top N outputs by fitness."""
        outputs = sorted(
            [node.output for node in self._nodes.values()],
            key=lambda o: o.fitness,
            reverse=True,
        )
        return outputs[:n]

    # ─────────────────────────────────────────────────────
    # Stats & Export
    # ─────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        outputs = list(self._nodes.values())
        fitness_scores = [n.output.fitness for n in outputs]

        return {
            "total_outputs": len(outputs),
            "unique_agents": len(set(n.output.agent_id for n in outputs)),
            "cache_hits": len(self._cache),
            "max_depth": max((n.depth for n in outputs), default=0),
            "avg_fitness": sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0,
            "best_fitness": max(fitness_scores) if fitness_scores else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export pipeline state."""
        return {
            "nodes": {
                nid: {
                    "id": nid,
                    "output": n.output.to_dict(),
                    "parent_id": n.parent_id,
                    "children": n.children,
                    "depth": n.depth,
                }
                for nid, n in self._nodes.items()
            },
            "roots": self._roots,
            "stats": self.stats(),
        }

    def clear(self) -> None:
        """Clear all outputs."""
        self._nodes.clear()
        self._cache.clear()
        self._roots.clear()
        self._counter = 0
