# api.py
"""
FastAPI Server: HTTP/WebSocket API for EATS.

Exposes endpoints for:
- Agent management (spawn, list, prompt)
- Task management (register, list)
- Evolution control (run, step, status)
- Graph visualization (Cytoscape format)
- Event streaming (SSE)
"""

import asyncio
import os
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel

from .orchestrator import MultiAgentOrchestrator
from .config_models import AgentBlueprint, TaskSpec, EvolutionConfig
from .evolution_engine import combined_fitness

# Path to static files
STATIC_DIR = Path(__file__).parent.parent / "static"


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

# Default command for agents - change this to your LLM CLI
# Examples:
#   ["aider"]
#   ["python", "-i", "-q"]
#   ["bash", "-c", "cat"]  # Echo for testing
DEFAULT_AGENT_CMD: List[str] = ["python", "-i", "-q"]

# Global orchestrator instance
orchestrator: Optional[MultiAgentOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global orchestrator
    orchestrator = MultiAgentOrchestrator(
        default_cmd=DEFAULT_AGENT_CMD,
        evo_config=EvolutionConfig(
            population_size=4,
            top_k_survivors=2,
            max_generations=3,
            max_turn_seconds=30.0,
            idle_gap_seconds=1.0,
        ),
    )
    print("[EATS] Orchestrator initialized")
    yield
    if orchestrator:
        orchestrator.shutdown()
        print("[EATS] Orchestrator shutdown")


app = FastAPI(
    title="EATS - Evolutionary Agent Tree System",
    description="Multi-agent orchestration with evolutionary optimization",
    version="0.1.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────

class AgentInfo(BaseModel):
    id: str
    blueprint_id: str
    role: str
    state: str
    turn_count: int
    last_output: str


class BlueprintCreate(BaseModel):
    role: str = "coder"
    system_prompt: str = "You are a helpful coding assistant."
    temperature: float = 0.7


class TaskCreate(BaseModel):
    description: str
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    timeout_seconds: float = 60.0


class PromptRequest(BaseModel):
    text: str
    include_system_prompt: bool = False


class EvolutionRequest(BaseModel):
    task_id: str
    base_role: str = "coder"
    base_prompt: str = "You are a helpful coding assistant."
    population_size: int = 4
    max_generations: int = 3


# ─────────────────────────────────────────────────────────
# Agent Endpoints
# ─────────────────────────────────────────────────────────

@app.post("/agents", response_model=AgentInfo, tags=["agents"])
def create_agent(body: BlueprintCreate):
    """Spawn a new agent from a blueprint."""
    blueprint = AgentBlueprint.create(
        role=body.role,
        system_prompt=body.system_prompt,
        cmd=DEFAULT_AGENT_CMD,
        temperature=body.temperature,
    )
    session = orchestrator.spawn_agent(blueprint=blueprint)
    return AgentInfo(
        id=session.id,
        blueprint_id=session.blueprint.id,
        role=session.blueprint.role,
        state=session.state,
        turn_count=len(session.log),
        last_output=session.last_output(500),
    )


@app.get("/agents", response_model=List[AgentInfo], tags=["agents"])
def list_agents():
    """List all active agents."""
    sessions = orchestrator.manager.list_sessions()
    return [
        AgentInfo(
            id=s.id,
            blueprint_id=s.blueprint.id,
            role=s.blueprint.role,
            state=s.state,
            turn_count=len(s.log),
            last_output=s.last_output(500),
        )
        for s in sessions
    ]


@app.get("/agents/{agent_id}", tags=["agents"])
def get_agent(agent_id: str):
    """Get detailed info about an agent."""
    try:
        session = orchestrator.manager.get_session(agent_id)
    except KeyError:
        raise HTTPException(404, "Agent not found")

    return {
        "id": session.id,
        "blueprint": session.blueprint.to_dict(),
        "state": session.state,
        "created_at": session.created_at,
        "turn_count": len(session.log),
        "turns": [t.to_dict() for t in session.log[-10:]],  # Last 10 turns
    }


@app.post("/agents/{agent_id}/prompt", response_model=AgentInfo, tags=["agents"])
def prompt_agent(agent_id: str, body: PromptRequest):
    """Send a prompt to an agent."""
    try:
        session = orchestrator.manager.get_session(agent_id)
    except KeyError:
        raise HTTPException(404, "Agent not found")

    try:
        orchestrator.send_prompt(agent_id, body.text)
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    return AgentInfo(
        id=session.id,
        blueprint_id=session.blueprint.id,
        role=session.blueprint.role,
        state=session.state,
        turn_count=len(session.log),
        last_output=session.last_output(500),
    )


@app.get("/agents/{agent_id}/log", tags=["agents"])
def get_agent_log(agent_id: str, last: int = 50):
    """Get conversation log for an agent."""
    try:
        session = orchestrator.manager.get_session(agent_id)
    except KeyError:
        raise HTTPException(404, "Agent not found")

    return {
        "id": session.id,
        "role": session.blueprint.role,
        "state": session.state,
        "turns": [t.to_dict() for t in session.log[-last:]],
    }


@app.delete("/agents/{agent_id}", tags=["agents"])
def terminate_agent(agent_id: str):
    """Terminate an agent."""
    try:
        orchestrator.manager.terminate_agent(agent_id)
        return {"status": "terminated", "agent_id": agent_id}
    except KeyError:
        raise HTTPException(404, "Agent not found")


# ─────────────────────────────────────────────────────────
# Task Endpoints
# ─────────────────────────────────────────────────────────

@app.post("/tasks", tags=["tasks"])
def create_task(body: TaskCreate):
    """Register a new task."""
    task = orchestrator.register_task(
        description=body.description,
        input_data=body.input_data,
        expected_output=body.expected_output,
        timeout_seconds=body.timeout_seconds,
    )
    return task.to_dict()


@app.get("/tasks", tags=["tasks"])
def list_tasks():
    """List all registered tasks."""
    return [t.to_dict() for t in orchestrator.list_tasks()]


@app.get("/tasks/{task_id}", tags=["tasks"])
def get_task(task_id: str):
    """Get a task by ID."""
    try:
        task = orchestrator.get_task(task_id)
        return task.to_dict()
    except KeyError:
        raise HTTPException(404, "Task not found")


# ─────────────────────────────────────────────────────────
# Evolution Endpoints
# ─────────────────────────────────────────────────────────

@app.post("/evolution/run", tags=["evolution"])
def run_evolution(body: EvolutionRequest):
    """
    Run a full evolution cycle.

    This is a blocking call that may take several minutes.
    """
    try:
        task = orchestrator.get_task(body.task_id)
    except KeyError:
        raise HTTPException(404, "Task not found")

    # Update config
    orchestrator.evo_config.population_size = body.population_size
    orchestrator.evo_config.max_generations = body.max_generations

    # Create base blueprint
    base = AgentBlueprint.create(
        role=body.base_role,
        system_prompt=body.base_prompt,
        cmd=DEFAULT_AGENT_CMD,
    )

    # Run evolution
    final_pop, results = orchestrator.run_evolution(
        base_blueprint=base,
        task=task,
        fitness_fn=combined_fitness,
    )

    return {
        "status": "complete",
        "generations": orchestrator._current_generation,
        "final_population_size": len(final_pop),
        "results": [r.to_dict() for r in results],
        "best_fitness": max(r.fitness_score for r in results) if results else 0,
        "fitness_summary": orchestrator.get_fitness_summary(),
    }


@app.get("/evolution/status", tags=["evolution"])
def get_evolution_status():
    """Get current evolution status."""
    return {
        "status": orchestrator.get_status(),
        "fitness_summary": orchestrator.get_fitness_summary(),
        "best_result": orchestrator.get_best_result().to_dict() if orchestrator.get_best_result() else None,
    }


# ─────────────────────────────────────────────────────────
# Graph Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/graph", tags=["graph"])
def get_graph():
    """Get the orchestration graph in Cytoscape.js format."""
    return orchestrator.get_graph_json()


@app.get("/graph/full", tags=["graph"])
def get_full_graph():
    """Get the full graph data structure."""
    return orchestrator.graph.to_dict()


# ─────────────────────────────────────────────────────────
# Event Streaming (SSE)
# ─────────────────────────────────────────────────────────

@app.get("/events", tags=["events"])
async def event_stream():
    """
    Server-Sent Events stream of system events.

    Connect with EventSource to receive live updates.
    """
    import json

    event_queue = orchestrator.event_bus.enable_async_queue(maxsize=100)

    async def generate():
        while True:
            try:
                # Check queue with timeout
                await asyncio.sleep(0.1)
                try:
                    event = event_queue.get_nowait()
                    data = json.dumps(event.to_dict())
                    yield f"data: {data}\n\n"
                except Exception:
                    # Send heartbeat every second
                    yield f": heartbeat\n\n"
            except asyncio.CancelledError:
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/events/history", tags=["events"])
def get_event_history(count: int = Query(50, le=200)):
    """Get recent event history."""
    events = orchestrator.event_bus.get_history(count)
    return [e.to_dict() for e in events]


# ─────────────────────────────────────────────────────────
# System Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/status", tags=["system"])
def get_status():
    """Get overall system status."""
    return orchestrator.get_status()


@app.post("/reset", tags=["system"])
def reset_system():
    """Reset the orchestrator (terminate all agents, clear state)."""
    orchestrator.reset()
    return {"status": "reset"}


@app.get("/", response_class=HTMLResponse, tags=["ui"])
def root():
    """Serve the main UI page."""
    # Try to serve from static directory first
    static_index = STATIC_DIR / "index.html"
    if static_index.exists():
        return FileResponse(static_index, media_type="text/html")

    # Fallback to embedded minimal UI
    return """
<!DOCTYPE html>
<html>
<head>
    <title>EATS - Evolutionary Agent Tree System</title>
    <meta charset="utf-8">
    <style>
        body { font-family: system-ui, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
        h1 { color: #58a6ff; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
        .section h2 { margin-top: 0; color: #8b949e; font-size: 14px; text-transform: uppercase; }
        pre { background: #0d1117; padding: 12px; border-radius: 4px; overflow-x: auto; }
        button { background: #238636; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-right: 8px; }
        button:hover { background: #2ea043; }
        button.secondary { background: #21262d; border: 1px solid #30363d; }
        button.secondary:hover { background: #30363d; }
        input, textarea { background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 8px; border-radius: 4px; width: 100%; box-sizing: border-box; }
        .agent { background: #21262d; padding: 12px; border-radius: 6px; margin-bottom: 8px; }
        .agent-header { display: flex; justify-content: space-between; align-items: center; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .status.idle { background: #238636; }
        .status.busy { background: #9e6a03; }
        .status.error { background: #da3633; }
        .log { max-height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; white-space: pre-wrap; }
        #graph { height: 400px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; }
    </style>
    <script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>EATS - Evolutionary Agent Tree System</h1>

        <div class="section">
            <h2>Quick Actions</h2>
            <button onclick="spawnAgent()">Spawn Agent</button>
            <button onclick="createTask()">Create Task</button>
            <button onclick="runEvolution()">Run Evolution</button>
            <button class="secondary" onclick="refreshAll()">Refresh</button>
            <button class="secondary" onclick="resetSystem()">Reset System</button>
        </div>

        <div class="section">
            <h2>Agents</h2>
            <div id="agents">Loading...</div>
        </div>

        <div class="section">
            <h2>Send Prompt</h2>
            <select id="agent-select" style="margin-bottom: 8px;"></select>
            <textarea id="prompt-input" rows="3" placeholder="Enter prompt..."></textarea>
            <button onclick="sendPrompt()" style="margin-top: 8px;">Send</button>
        </div>

        <div class="section">
            <h2>Agent Tree</h2>
            <div id="graph"></div>
        </div>

        <div class="section">
            <h2>System Status</h2>
            <pre id="status">Loading...</pre>
        </div>

        <div class="section">
            <h2>Event Log</h2>
            <div id="events" class="log">Connecting...</div>
        </div>
    </div>

    <script>
        let cy = null;

        async function refreshAgents() {
            const res = await fetch('/agents');
            const agents = await res.json();
            const select = document.getElementById('agent-select');
            select.innerHTML = agents.map(a =>
                `<option value="${a.id}">${a.role} (${a.id.slice(0,8)}) [${a.state}]</option>`
            ).join('');

            document.getElementById('agents').innerHTML = agents.map(a => `
                <div class="agent">
                    <div class="agent-header">
                        <strong>${a.role}</strong>
                        <span class="status ${a.state}">${a.state}</span>
                    </div>
                    <div style="font-size: 12px; color: #8b949e;">ID: ${a.id.slice(0,8)}... | Turns: ${a.turn_count}</div>
                    <div class="log" style="max-height: 100px; margin-top: 8px;">${escapeHtml(a.last_output || '(no output)')}</div>
                </div>
            `).join('') || '<em>No agents</em>';
        }

        async function refreshGraph() {
            const res = await fetch('/graph');
            const data = await res.json();

            if (!cy) {
                cy = cytoscape({
                    container: document.getElementById('graph'),
                    elements: data,
                    style: [
                        { selector: 'node[type="agent"]', style: {
                            'background-color': 'data(fitness_color)',
                            'label': 'data(label)',
                            'color': '#c9d1d9',
                            'text-valign': 'bottom',
                            'font-size': '10px'
                        }},
                        { selector: 'node[type="task"]', style: {
                            'background-color': '#58a6ff',
                            'shape': 'rectangle',
                            'label': 'data(label)',
                            'color': '#c9d1d9',
                            'text-valign': 'bottom',
                            'font-size': '10px'
                        }},
                        { selector: 'edge', style: {
                            'width': 2,
                            'line-color': '#30363d',
                            'target-arrow-shape': 'triangle',
                            'target-arrow-color': '#30363d',
                            'curve-style': 'bezier'
                        }}
                    ],
                    layout: { name: 'breadthfirst', directed: true }
                });
            } else {
                cy.elements().remove();
                cy.add(data.nodes);
                cy.add(data.edges);
                cy.layout({ name: 'breadthfirst', directed: true }).run();
            }
        }

        async function refreshStatus() {
            const res = await fetch('/status');
            const status = await res.json();
            document.getElementById('status').textContent = JSON.stringify(status, null, 2);
        }

        async function refreshAll() {
            await Promise.all([refreshAgents(), refreshGraph(), refreshStatus()]);
        }

        async function spawnAgent() {
            const role = prompt('Agent role:', 'coder');
            if (!role) return;
            await fetch('/agents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role, system_prompt: `You are a helpful ${role} assistant.` })
            });
            refreshAll();
        }

        async function createTask() {
            const desc = prompt('Task description:');
            if (!desc) return;
            await fetch('/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: desc })
            });
            alert('Task created!');
        }

        async function runEvolution() {
            const tasks = await (await fetch('/tasks')).json();
            if (tasks.length === 0) {
                alert('Create a task first!');
                return;
            }
            const taskId = tasks[0].id;
            alert('Starting evolution (this may take a while)...');
            const res = await fetch('/evolution/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    task_id: taskId,
                    base_role: 'coder',
                    base_prompt: 'You are a helpful coding assistant.',
                    population_size: 3,
                    max_generations: 2
                })
            });
            const result = await res.json();
            alert(`Evolution complete! Best fitness: ${result.best_fitness}`);
            refreshAll();
        }

        async function sendPrompt() {
            const agentId = document.getElementById('agent-select').value;
            const text = document.getElementById('prompt-input').value;
            if (!agentId || !text) return;

            await fetch(`/agents/${agentId}/prompt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            document.getElementById('prompt-input').value = '';
            refreshAgents();
        }

        async function resetSystem() {
            if (!confirm('Reset system? This will terminate all agents.')) return;
            await fetch('/reset', { method: 'POST' });
            refreshAll();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Event stream
        function connectEvents() {
            const eventsDiv = document.getElementById('events');
            const eventSource = new EventSource('/events');

            eventSource.onmessage = (e) => {
                try {
                    const event = JSON.parse(e.data);
                    const line = `[${new Date(event.timestamp * 1000).toLocaleTimeString()}] ${event.type}: ${JSON.stringify(event.payload)}\\n`;
                    eventsDiv.textContent = line + eventsDiv.textContent.slice(0, 5000);
                } catch {}
            };

            eventSource.onerror = () => {
                eventsDiv.textContent = 'Disconnected. Reconnecting...\\n' + eventsDiv.textContent;
                setTimeout(connectEvents, 3000);
            };
        }

        // Initial load
        refreshAll();
        connectEvents();
        setInterval(refreshAll, 5000);
    </script>
</body>
</html>
"""
