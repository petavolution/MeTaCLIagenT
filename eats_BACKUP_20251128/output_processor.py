# output_processor.py
"""
Agent Output Processing Pipeline.

Implements the stream aggregation architecture from EATS spec:
- Directed Acyclic Graph (DAG) for result trees
- Semantic caching via embeddings
- Synthesis with parent context
- Fusion methods (voting, weighted synthesis, hierarchical roll-up)
"""

import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class FusionMethod(str, Enum):
    """Methods for fusing multiple agent outputs."""
    ENSEMBLE_VOTING = "ensemble_voting"
    WEIGHTED_SYNTHESIS = "weighted_synthesis"
    HIERARCHICAL_ROLLUP = "hierarchical_rollup"
    CONFLICT_RESOLUTION = "conflict_resolution"


@dataclass
class ProcessedOutput:
    """Result of processing an agent's output."""
    agent_id: str
    raw_output: str
    synthesized: str
    embedding_hash: str
    fitness: float
    timestamp: float
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "raw_output": self.raw_output[:500],
            "synthesized": self.synthesized[:500],
            "embedding_hash": self.embedding_hash,
            "fitness": self.fitness,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
        }


@dataclass
class DAGNode:
    """A node in the result DAG."""
    id: str
    agent_id: str
    output: ProcessedOutput
    children: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    level: int = 0


class ResultDAG:
    """
    Directed Acyclic Graph for organizing agent outputs.

    Supports:
    - Hierarchical result trees
    - Parent context retrieval
    - Leaf-to-root consolidation
    """

    def __init__(self):
        self._nodes: Dict[str, DAGNode] = {}
        self._roots: List[str] = []

    def add_node(
        self,
        node_id: str,
        agent_id: str,
        output: ProcessedOutput,
        parent_id: Optional[str] = None,
    ) -> DAGNode:
        """Add a node to the DAG."""
        level = 0
        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            parent.children.append(node_id)
            level = parent.level + 1

        node = DAGNode(
            id=node_id,
            agent_id=agent_id,
            output=output,
            parent_id=parent_id,
            level=level,
        )
        self._nodes[node_id] = node

        if parent_id is None:
            self._roots.append(node_id)

        return node

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        return self._nodes.get(node_id)

    def get_parent(self, node_id: str) -> Optional[DAGNode]:
        node = self._nodes.get(node_id)
        if node and node.parent_id:
            return self._nodes.get(node.parent_id)
        return None

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

    def get_leaves(self) -> List[DAGNode]:
        """Get all leaf nodes (no children)."""
        return [n for n in self._nodes.values() if not n.children]

    def get_by_level(self, level: int) -> List[DAGNode]:
        """Get all nodes at a specific level."""
        return [n for n in self._nodes.values() if n.level == level]

    def to_dict(self) -> Dict:
        return {
            "nodes": {k: {
                "id": v.id,
                "agent_id": v.agent_id,
                "parent_id": v.parent_id,
                "children": v.children,
                "level": v.level,
                "fitness": v.output.fitness,
            } for k, v in self._nodes.items()},
            "roots": self._roots,
            "total_nodes": len(self._nodes),
            "max_level": max((n.level for n in self._nodes.values()), default=0),
        }


class SemanticCache:
    """
    Simple semantic cache using content hashing.

    In a full implementation, this would use embeddings and vector similarity.
    For hackathon, we use content hashing with fuzzy matching.
    """

    def __init__(self, similarity_threshold: float = 0.95):
        self._cache: Dict[str, ProcessedOutput] = {}
        self._threshold = similarity_threshold

    def _hash_content(self, content: str) -> str:
        """Create a hash of content for cache lookup."""
        # Normalize: lowercase, strip whitespace, remove punctuation
        normalized = content.lower().strip()
        normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
        return hashlib.md5(normalized.encode()).hexdigest()

    def check(self, content: str) -> Optional[ProcessedOutput]:
        """Check if similar content exists in cache."""
        content_hash = self._hash_content(content)

        # Exact match
        if content_hash in self._cache:
            return self._cache[content_hash]

        # For hackathon, we only do exact matching
        # Full implementation would compute embedding similarity
        return None

    def store(self, content: str, output: ProcessedOutput) -> None:
        """Store processed output in cache."""
        content_hash = self._hash_content(content)
        self._cache[content_hash] = output

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


class AgentOutputProcessor:
    """
    Main output processing pipeline.

    Processes agent outputs through:
    1. Semantic cache check (avoid redundant processing)
    2. Context synthesis with parent outputs
    3. Fitness evaluation
    4. DAG update

    Usage:
        processor = AgentOutputProcessor()
        result = await processor.process_agent_stream(
            agent_id="coder-001",
            output_stream="def hello(): print('hi')",
            parent_agent_id="planner-001",
        )
    """

    def __init__(
        self,
        fitness_fn: Optional[Callable[[str, Optional[str]], float]] = None,
        synthesize_fn: Optional[Callable[[str, str], str]] = None,
    ):
        self.result_tree = ResultDAG()
        self.semantic_cache = SemanticCache()
        self._fitness_fn = fitness_fn or self._default_fitness
        self._synthesize_fn = synthesize_fn or self._default_synthesize
        self._node_counter = 0

    async def process_agent_stream(
        self,
        agent_id: str,
        output_stream: str,
        parent_agent_id: Optional[str] = None,
    ) -> ProcessedOutput:
        """
        Process an agent's output stream.

        1. Check semantic cache
        2. Get parent context
        3. Synthesize with context
        4. Evaluate fitness
        5. Update result tree
        """
        # Check cache
        cached = self.semantic_cache.check(output_stream)
        if cached:
            return cached

        # Get parent context
        parent_ctx = None
        parent_node_id = None
        if parent_agent_id:
            # Find most recent node from parent agent
            for node in reversed(list(self.result_tree._nodes.values())):
                if node.agent_id == parent_agent_id:
                    parent_ctx = node.output.synthesized
                    parent_node_id = node.id
                    break

        # Synthesize with context
        synthesized = self._synthesize_fn(output_stream, parent_ctx)

        # Evaluate fitness
        fitness = self._fitness_fn(synthesized, parent_ctx)

        # Create processed output
        self._node_counter += 1
        embedding_hash = hashlib.md5(output_stream.encode()).hexdigest()[:12]

        output = ProcessedOutput(
            agent_id=agent_id,
            raw_output=output_stream,
            synthesized=synthesized,
            embedding_hash=embedding_hash,
            fitness=fitness,
            timestamp=time.time(),
            parent_id=parent_agent_id,
        )

        # Update DAG
        node_id = f"node_{self._node_counter}"
        self.result_tree.add_node(
            node_id=node_id,
            agent_id=agent_id,
            output=output,
            parent_id=parent_node_id,
        )

        # Store in cache
        self.semantic_cache.store(output_stream, output)

        return output

    def _default_fitness(self, content: str, parent_ctx: Optional[str]) -> float:
        """Default fitness function based on content quality heuristics."""
        score = 0.0

        # Length score (optimal: 200-1000 chars)
        length = len(content)
        if length < 50:
            score += 1.0
        elif length < 200:
            score += 2.0
        elif length < 1000:
            score += 3.0
        else:
            score += 2.5

        # Code presence
        if "def " in content or "class " in content or "```" in content:
            score += 2.0

        # Structure (bullet points, numbered lists)
        if any(marker in content for marker in ["- ", "1.", "* ", "•"]):
            score += 1.0

        # Context relevance (if parent context exists)
        if parent_ctx:
            # Simple word overlap
            parent_words = set(parent_ctx.lower().split())
            content_words = set(content.lower().split())
            overlap = len(parent_words & content_words)
            score += min(2.0, overlap * 0.1)

        return min(10.0, score)

    def _default_synthesize(self, content: str, parent_ctx: Optional[str]) -> str:
        """Default synthesis: prepend summary of parent context."""
        if not parent_ctx:
            return content

        # Simple synthesis: add context marker
        return f"[Context: {parent_ctx[:100]}...]\n\n{content}"

    # ─────────────────────────────────────────────────────
    # Fusion Methods
    # ─────────────────────────────────────────────────────

    def ensemble_vote(self, outputs: List[ProcessedOutput]) -> ProcessedOutput:
        """
        Ensemble voting: select output with highest fitness.

        For factual consensus - pick the most agreed-upon answer.
        """
        if not outputs:
            raise ValueError("No outputs to vote on")

        best = max(outputs, key=lambda o: o.fitness)
        return ProcessedOutput(
            agent_id="ensemble",
            raw_output=best.raw_output,
            synthesized=f"[VOTED] {best.synthesized}",
            embedding_hash=best.embedding_hash,
            fitness=best.fitness,
            timestamp=time.time(),
            metadata={"method": "ensemble_voting", "winner": best.agent_id},
        )

    def weighted_synthesis(self, outputs: List[ProcessedOutput]) -> ProcessedOutput:
        """
        Weighted synthesis: combine outputs weighted by fitness.

        Creates a merged output prioritizing high-fitness contributions.
        """
        if not outputs:
            raise ValueError("No outputs to synthesize")

        # Sort by fitness (descending)
        sorted_outputs = sorted(outputs, key=lambda o: o.fitness, reverse=True)

        # Build weighted combination
        parts = []
        total_fitness = sum(o.fitness for o in outputs)

        for o in sorted_outputs:
            weight = o.fitness / total_fitness if total_fitness > 0 else 1.0 / len(outputs)
            parts.append(f"[{o.agent_id} w={weight:.2f}]\n{o.synthesized[:300]}")

        combined = "\n\n---\n\n".join(parts)
        avg_fitness = total_fitness / len(outputs)

        return ProcessedOutput(
            agent_id="synthesizer",
            raw_output=combined,
            synthesized=combined,
            embedding_hash=hashlib.md5(combined.encode()).hexdigest()[:12],
            fitness=avg_fitness,
            timestamp=time.time(),
            metadata={"method": "weighted_synthesis", "input_count": len(outputs)},
        )

    def hierarchical_rollup(self) -> Optional[ProcessedOutput]:
        """
        Hierarchical roll-up: consolidate from leaves to root.

        Combines all leaf outputs, then their parents, etc.
        """
        leaves = self.result_tree.get_leaves()
        if not leaves:
            return None

        # Simple rollup: combine all leaf outputs
        leaf_outputs = [node.output for node in leaves]
        return self.weighted_synthesis(leaf_outputs)

    def conflict_resolution(
        self,
        outputs: List[ProcessedOutput],
        resolver_fn: Optional[Callable[[List[str]], str]] = None,
    ) -> ProcessedOutput:
        """
        Conflict resolution: use meta-agent arbitration.

        When outputs conflict, a resolver decides the final output.
        """
        if not outputs:
            raise ValueError("No outputs to resolve")

        if len(outputs) == 1:
            return outputs[0]

        # Default resolver: pick highest fitness
        if resolver_fn is None:
            return self.ensemble_vote(outputs)

        # Use custom resolver
        texts = [o.synthesized for o in outputs]
        resolved = resolver_fn(texts)

        return ProcessedOutput(
            agent_id="arbitrator",
            raw_output=resolved,
            synthesized=resolved,
            embedding_hash=hashlib.md5(resolved.encode()).hexdigest()[:12],
            fitness=max(o.fitness for o in outputs),
            timestamp=time.time(),
            metadata={"method": "conflict_resolution"},
        )

    def get_statistics(self) -> Dict:
        """Get processing statistics."""
        return {
            "dag_stats": self.result_tree.to_dict(),
            "cache_size": self.semantic_cache.size(),
            "total_processed": self._node_counter,
        }
