# workflows.py - DAG-Based Workflow Orchestration
"""
DAG workflow system for multi-step agent pipelines.

Based on best practices from LlamaIndex QueryPipeline and LangGraph:
- Define workflows as directed acyclic graphs
- Automatic dependency resolution and parallelization
- Prompt chaining with context propagation
- Error handling and retries
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Awaitable, Set, Union
from enum import Enum
import time
import uuid

from .async_core import AsyncAgent, TaskResult
from .events import EventBus, Event, EventType


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Node Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NodeType(str, Enum):
    """Types of workflow nodes."""
    AGENT = "agent"           # Execute agent prompt
    TRANSFORM = "transform"   # Transform data
    BRANCH = "branch"         # Conditional routing
    PARALLEL = "parallel"     # Fan-out
    JOIN = "join"            # Fan-in
    INPUT = "input"          # Workflow input
    OUTPUT = "output"        # Workflow output


class NodeStatus(str, Enum):
    """Execution status of a node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Node
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class WorkflowNode:
    """
    A node in the workflow DAG.

    Attributes:
        id: Unique node identifier
        node_type: Type of node
        config: Node-specific configuration
        dependencies: IDs of nodes this depends on
        outputs_to: IDs of nodes that depend on this
    """
    id: str
    node_type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    outputs_to: List[str] = field(default_factory=list)

    # Runtime state
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "outputs_to": self.outputs_to,
            "duration": self.duration,
            "error": self.error,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Definition
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Workflow:
    """
    DAG-based workflow definition and execution.

    Usage:
        wf = Workflow("code_review")

        # Add nodes
        wf.add_input("code")
        wf.add_agent("analyzer", agent, prompt="Analyze: {code}")
        wf.add_agent("reviewer", agent, prompt="Review: {code}")
        wf.add_join("combine", template="Analysis: {analyzer}\nReview: {reviewer}")
        wf.add_output("result")

        # Define edges
        wf.connect("code", "analyzer")
        wf.connect("code", "reviewer")
        wf.connect("analyzer", "combine")
        wf.connect("reviewer", "combine")
        wf.connect("combine", "result")

        # Execute
        result = await wf.run(code="def foo(): pass")
    """

    def __init__(
        self,
        name: str,
        event_bus: Optional[EventBus] = None,
    ):
        self.name = name
        self.event_bus = event_bus
        self._nodes: Dict[str, WorkflowNode] = {}
        self._agents: Dict[str, AsyncAgent] = {}
        self._transforms: Dict[str, Callable] = {}
        self._input_node: Optional[str] = None
        self._output_node: Optional[str] = None

    # ─────────────────────────────────────────────────────
    # Node Addition
    # ─────────────────────────────────────────────────────

    def add_input(self, node_id: str = "input") -> str:
        """Add input node (entry point)."""
        node = WorkflowNode(id=node_id, node_type=NodeType.INPUT)
        self._nodes[node_id] = node
        self._input_node = node_id
        return node_id

    def add_output(self, node_id: str = "output") -> str:
        """Add output node (exit point)."""
        node = WorkflowNode(id=node_id, node_type=NodeType.OUTPUT)
        self._nodes[node_id] = node
        self._output_node = node_id
        return node_id

    def add_agent(
        self,
        node_id: str,
        agent: AsyncAgent,
        prompt_template: str,
        timeout: float = 30.0,
    ) -> str:
        """
        Add agent node.

        Args:
            node_id: Unique identifier
            agent: AsyncAgent to execute
            prompt_template: Template with {var} placeholders
            timeout: Execution timeout
        """
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.AGENT,
            config={
                "prompt_template": prompt_template,
                "timeout": timeout,
            },
        )
        self._nodes[node_id] = node
        self._agents[node_id] = agent
        return node_id

    def add_transform(
        self,
        node_id: str,
        transform_fn: Callable[[Dict[str, Any]], Any],
    ) -> str:
        """
        Add transform node.

        Args:
            node_id: Unique identifier
            transform_fn: Function that transforms input dict to output
        """
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.TRANSFORM,
        )
        self._nodes[node_id] = node
        self._transforms[node_id] = transform_fn
        return node_id

    def add_branch(
        self,
        node_id: str,
        condition_fn: Callable[[Dict[str, Any]], str],
        branches: Dict[str, str],
    ) -> str:
        """
        Add conditional branch node.

        Args:
            node_id: Unique identifier
            condition_fn: Function returning branch key
            branches: Mapping of branch key -> target node
        """
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.BRANCH,
            config={"branches": branches},
        )
        self._nodes[node_id] = node
        self._transforms[node_id] = condition_fn
        return node_id

    def add_join(
        self,
        node_id: str,
        template: Optional[str] = None,
        join_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> str:
        """
        Add join node (combines multiple inputs).

        Args:
            node_id: Unique identifier
            template: Template to format joined inputs
            join_fn: Custom join function (overrides template)
        """
        node = WorkflowNode(
            id=node_id,
            node_type=NodeType.JOIN,
            config={"template": template},
        )
        self._nodes[node_id] = node
        if join_fn:
            self._transforms[node_id] = join_fn
        return node_id

    # ─────────────────────────────────────────────────────
    # Edge Definition
    # ─────────────────────────────────────────────────────

    def connect(self, from_node: str, to_node: str) -> None:
        """Connect two nodes (create edge)."""
        if from_node not in self._nodes:
            raise ValueError(f"Node not found: {from_node}")
        if to_node not in self._nodes:
            raise ValueError(f"Node not found: {to_node}")

        self._nodes[from_node].outputs_to.append(to_node)
        self._nodes[to_node].dependencies.append(from_node)

    def chain(self, *node_ids: str) -> None:
        """Connect nodes in sequence."""
        for i in range(len(node_ids) - 1):
            self.connect(node_ids[i], node_ids[i + 1])

    # ─────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────

    async def run(self, **inputs) -> Any:
        """
        Execute the workflow.

        Args:
            **inputs: Input values passed to input node

        Returns:
            Output from the output node
        """
        # Reset state
        for node in self._nodes.values():
            node.status = NodeStatus.PENDING
            node.result = None
            node.error = None
            node.start_time = None
            node.end_time = None

        # Set input
        if self._input_node:
            self._nodes[self._input_node].result = inputs
            self._nodes[self._input_node].status = NodeStatus.COMPLETED

        # Execute DAG
        results = {}
        results.update(inputs)

        # Topological execution
        executed = set()
        while len(executed) < len(self._nodes):
            # Find ready nodes (all deps satisfied)
            ready = []
            for node in self._nodes.values():
                if node.id in executed:
                    continue
                if node.status == NodeStatus.COMPLETED:
                    executed.add(node.id)
                    continue
                if all(d in executed for d in node.dependencies):
                    ready.append(node)

            if not ready:
                # Check for cycles or stuck state
                pending = [n.id for n in self._nodes.values() if n.id not in executed]
                raise RuntimeError(f"Workflow stuck. Pending nodes: {pending}")

            # Execute ready nodes in parallel
            await asyncio.gather(*[
                self._execute_node(node, results)
                for node in ready
            ])

            # Collect results
            for node in ready:
                executed.add(node.id)
                if node.result is not None:
                    results[node.id] = node.result

        # Return output
        if self._output_node and self._output_node in results:
            return results[self._output_node]

        return results

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any],
    ) -> None:
        """Execute a single node."""
        node.status = NodeStatus.RUNNING
        node.start_time = time.time()

        try:
            if node.node_type == NodeType.INPUT:
                # Input already set
                node.status = NodeStatus.COMPLETED

            elif node.node_type == NodeType.OUTPUT:
                # Collect from dependencies
                if node.dependencies:
                    dep_id = node.dependencies[0]
                    node.result = context.get(dep_id)
                node.status = NodeStatus.COMPLETED

            elif node.node_type == NodeType.AGENT:
                node.result = await self._execute_agent_node(node, context)
                node.status = NodeStatus.COMPLETED

            elif node.node_type == NodeType.TRANSFORM:
                node.result = await self._execute_transform_node(node, context)
                node.status = NodeStatus.COMPLETED

            elif node.node_type == NodeType.JOIN:
                node.result = self._execute_join_node(node, context)
                node.status = NodeStatus.COMPLETED

            elif node.node_type == NodeType.BRANCH:
                node.result = self._execute_branch_node(node, context)
                node.status = NodeStatus.COMPLETED

        except Exception as e:
            node.status = NodeStatus.FAILED
            node.error = str(e)
            raise

        finally:
            node.end_time = time.time()
            self._emit_event(EventType.TASK_COMPLETED, {
                "node_id": node.id,
                "status": node.status.value,
                "duration": node.duration,
            })

    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any],
    ) -> str:
        """Execute an agent node."""
        agent = self._agents.get(node.id)
        if not agent:
            raise ValueError(f"Agent not found for node: {node.id}")

        # Format prompt template
        template = node.config.get("prompt_template", "{input}")
        prompt = template.format(**context)

        # Execute agent
        timeout = node.config.get("timeout", 30.0)
        response = await agent.ask(prompt, timeout=timeout)

        return response

    async def _execute_transform_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a transform node."""
        transform_fn = self._transforms.get(node.id)
        if not transform_fn:
            raise ValueError(f"Transform not found for node: {node.id}")

        # Run transform (may be sync or async)
        result = transform_fn(context)
        if asyncio.iscoroutine(result):
            result = await result

        return result

    def _execute_join_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any],
    ) -> Any:
        """Execute a join node."""
        # Custom join function
        if node.id in self._transforms:
            return self._transforms[node.id](context)

        # Template-based join
        template = node.config.get("template")
        if template:
            return template.format(**context)

        # Default: collect dependency results
        return {dep: context.get(dep) for dep in node.dependencies}

    def _execute_branch_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any],
    ) -> str:
        """Execute a branch node (returns selected branch key)."""
        condition_fn = self._transforms.get(node.id)
        if not condition_fn:
            raise ValueError(f"Condition not found for node: {node.id}")

        return condition_fn(context)

    def _emit_event(self, event_type: EventType, data: Dict) -> None:
        """Emit event if bus available."""
        if self.event_bus:
            self.event_bus.emit(Event(
                type=event_type,
                data={"workflow": self.name, **data},
                source="workflow",
            ))

    # ─────────────────────────────────────────────────────
    # Utilities
    # ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Export workflow definition."""
        return {
            "name": self.name,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "input": self._input_node,
            "output": self._output_node,
        }

    def visualize(self) -> str:
        """Create ASCII visualization of workflow."""
        lines = [f"Workflow: {self.name}", ""]

        for node in self._nodes.values():
            deps = ", ".join(node.dependencies) if node.dependencies else "none"
            outs = ", ".join(node.outputs_to) if node.outputs_to else "none"
            status = f"[{node.status.value}]" if node.status != NodeStatus.PENDING else ""
            lines.append(f"  {node.id} ({node.node_type.value}) {status}")
            lines.append(f"    deps: {deps}")
            lines.append(f"    outs: {outs}")

        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Builder (Fluent API)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowBuilder:
    """
    Fluent builder for workflows.

    Usage:
        wf = (WorkflowBuilder("pipeline")
            .input("query")
            .agent("search", searcher, "Search for: {query}")
            .agent("analyze", analyzer, "Analyze: {search}")
            .transform("format", lambda ctx: ctx["analyze"].upper())
            .output("result")
            .build())
    """

    def __init__(self, name: str):
        self._workflow = Workflow(name)
        self._last_node: Optional[str] = None

    def input(self, node_id: str = "input") -> WorkflowBuilder:
        """Add input node."""
        self._workflow.add_input(node_id)
        self._last_node = node_id
        return self

    def output(self, node_id: str = "output") -> WorkflowBuilder:
        """Add output node, connecting from last node."""
        self._workflow.add_output(node_id)
        if self._last_node:
            self._workflow.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def agent(
        self,
        node_id: str,
        agent: AsyncAgent,
        prompt: str,
        timeout: float = 30.0,
    ) -> WorkflowBuilder:
        """Add agent node, auto-connecting from last node."""
        self._workflow.add_agent(node_id, agent, prompt, timeout)
        if self._last_node:
            self._workflow.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def transform(
        self,
        node_id: str,
        fn: Callable[[Dict], Any],
    ) -> WorkflowBuilder:
        """Add transform node, auto-connecting from last node."""
        self._workflow.add_transform(node_id, fn)
        if self._last_node:
            self._workflow.connect(self._last_node, node_id)
        self._last_node = node_id
        return self

    def join(
        self,
        node_id: str,
        *from_nodes: str,
        template: Optional[str] = None,
    ) -> WorkflowBuilder:
        """Add join node connecting from specified nodes."""
        self._workflow.add_join(node_id, template=template)
        for from_node in from_nodes:
            self._workflow.connect(from_node, node_id)
        self._last_node = node_id
        return self

    def connect(self, from_node: str, to_node: str) -> WorkflowBuilder:
        """Explicitly connect two nodes."""
        self._workflow.connect(from_node, to_node)
        return self

    def build(self) -> Workflow:
        """Build and return the workflow."""
        return self._workflow


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-built Workflow Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_chain_workflow(
    name: str,
    agents: List[AsyncAgent],
    prompts: List[str],
) -> Workflow:
    """Create a simple sequential chain workflow."""
    builder = WorkflowBuilder(name).input("input")

    for i, (agent, prompt) in enumerate(zip(agents, prompts)):
        builder.agent(f"step_{i}", agent, prompt)

    return builder.output("output").build()


def create_parallel_workflow(
    name: str,
    agents: List[AsyncAgent],
    prompts: List[str],
    join_template: str = "{results}",
) -> Workflow:
    """Create a parallel fan-out/fan-in workflow."""
    wf = Workflow(name)

    wf.add_input("input")

    # Parallel agents
    agent_ids = []
    for i, (agent, prompt) in enumerate(zip(agents, prompts)):
        aid = f"agent_{i}"
        wf.add_agent(aid, agent, prompt)
        wf.connect("input", aid)
        agent_ids.append(aid)

    # Join
    wf.add_join("join", template=join_template)
    for aid in agent_ids:
        wf.connect(aid, "join")

    wf.add_output("output")
    wf.connect("join", "output")

    return wf
