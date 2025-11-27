#!/usr/bin/env python3
# server.py - Minimal FastAPI Server + CLI
"""
Unified server providing:
- REST API for swarm control
- SSE for real-time updates
- Web UI with graph visualization
- CLI for interactive control
"""

from __future__ import annotations
import asyncio
import json
import time
import argparse
import sys
from typing import Dict, List, Optional, Any, AsyncGenerator
from contextlib import asynccontextmanager

# FastAPI imports (with fallback)
try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Local imports
from .core import AgentDNA, Agent, Evolution, EvolutionConfig, heuristic_fitness
from .swarm import SwarmController, AgentRole, BranchType
from .judge import LLMJudge, Fitness, create_fitness_fn
from .pipeline import ResultPipeline, FusionMethod

# Rich CLI (optional)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    Console = None
    RICH_AVAILABLE = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pydantic Models for API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if FASTAPI_AVAILABLE:
    class TaskRequest(BaseModel):
        prompt: str
        target: Optional[str] = None  # Node ID or "all"
        branch: Optional[str] = None

    class SpawnRequest(BaseModel):
        role: str
        parent_id: Optional[str] = None

    class EvolutionRequest(BaseModel):
        task: str
        population_size: int = 4
        generations: int = 3
        base_role: str = "coder"

    class FuseRequest(BaseModel):
        agent_ids: List[str]
        method: str = "vote"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AppState:
    """Global application state."""
    swarm: Optional[SwarmController] = None
    pipeline: Optional[ResultPipeline] = None
    judge: Optional[LLMJudge] = None
    events: List[Dict] = []

state = AppState()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI App
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_app() -> Any:
    """Create and configure FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI not installed: pip install fastapi uvicorn")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        state.swarm = SwarmController()
        state.swarm.initialize_tree()
        state.pipeline = ResultPipeline()
        state.judge = LLMJudge()
        yield
        # Shutdown
        if state.swarm:
            state.swarm.shutdown()

    app = FastAPI(
        title="EATS Core",
        description="Evolutionary Agent Tree System - Optimized",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─────────────────────────────────────────────────────
    # Health & Status
    # ─────────────────────────────────────────────────────

    @app.get("/")
    async def root():
        return HTMLResponse(get_dashboard_html())

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "2.0.0"}

    @app.get("/status")
    async def status():
        return {
            "swarm": state.swarm.to_dict() if state.swarm else None,
            "pipeline": state.pipeline.stats() if state.pipeline else None,
        }

    # ─────────────────────────────────────────────────────
    # Swarm Endpoints
    # ─────────────────────────────────────────────────────

    @app.get("/swarm")
    async def get_swarm():
        if not state.swarm:
            raise HTTPException(500, "Swarm not initialized")
        return state.swarm.to_dict()

    @app.get("/swarm/graph")
    async def get_graph():
        if not state.swarm:
            raise HTTPException(500, "Swarm not initialized")
        return state.swarm.to_cytoscape()

    @app.post("/swarm/spawn")
    async def spawn_agent(req: SpawnRequest):
        if not state.swarm:
            raise HTTPException(500, "Swarm not initialized")

        try:
            role = AgentRole(req.role)
        except ValueError:
            raise HTTPException(400, f"Invalid role: {req.role}")

        node = state.swarm.spawn_agent(role=role, parent_id=req.parent_id)
        if node:
            _emit_event("agent_spawned", {"node_id": node.id, "role": req.role})
            return {"success": True, "node": node.to_dict()}
        return {"success": False, "error": "Failed to spawn"}

    @app.post("/swarm/ask")
    async def ask_agent(req: TaskRequest):
        if not state.swarm:
            raise HTTPException(500, "Swarm not initialized")

        if req.target == "all" or req.target is None:
            # Broadcast
            results = state.swarm.broadcast(
                req.prompt,
                branch=BranchType(req.branch) if req.branch else None,
            )
            # Add to pipeline
            for agent_id, response in results.items():
                fitness = state.judge.evaluate("", response).score if state.judge else 5.0
                state.pipeline.add(agent_id, response, fitness=fitness)

            return {"responses": results, "count": len(results)}
        else:
            # Single agent
            response = state.swarm.ask(req.target, req.prompt)
            if response and state.pipeline:
                fitness = state.judge.evaluate(req.prompt, response).score if state.judge else 5.0
                state.pipeline.add(req.target, response, fitness=fitness)

            return {"node_id": req.target, "response": response}

    @app.delete("/swarm/{node_id}")
    async def stop_agent(node_id: str):
        if not state.swarm:
            raise HTTPException(500, "Swarm not initialized")
        success = state.swarm.stop_agent(node_id)
        return {"success": success}

    # ─────────────────────────────────────────────────────
    # Evolution Endpoints
    # ─────────────────────────────────────────────────────

    @app.post("/evolution/run")
    async def run_evolution(req: EvolutionRequest, background: BackgroundTasks):
        config = EvolutionConfig(
            population_size=req.population_size,
            generations=req.generations,
            task_prompt=req.task,
        )

        base_dna = AgentDNA(
            role=req.base_role,
            system_prompt=f"You are a {req.base_role}. Complete tasks efficiently.",
            cmd=["python", "-i", "-q"],
        )

        def run_evo():
            evo = Evolution(config)
            fitness_fn = create_fitness_fn(state.judge, req.task)

            def on_gen(result):
                _emit_event("generation_complete", {
                    "generation": result.generation,
                    "best_fitness": result.best_fitness,
                    "avg_fitness": result.avg_fitness,
                })

            best = evo.run(base_dna, fitness_fn, on_generation=on_gen)
            _emit_event("evolution_complete", {
                "best_dna": best.to_dict(),
                "generations": len(evo.history),
            })

        background.add_task(run_evo)
        return {"status": "started", "config": config.__dict__}

    # ─────────────────────────────────────────────────────
    # Pipeline Endpoints
    # ─────────────────────────────────────────────────────

    @app.get("/pipeline")
    async def get_pipeline():
        if not state.pipeline:
            raise HTTPException(500, "Pipeline not initialized")
        return state.pipeline.to_dict()

    @app.get("/pipeline/top")
    async def get_top_outputs(n: int = 5):
        if not state.pipeline:
            raise HTTPException(500, "Pipeline not initialized")
        outputs = state.pipeline.get_top(n)
        return {"outputs": [o.to_dict() for o in outputs]}

    @app.post("/pipeline/fuse")
    async def fuse_outputs(req: FuseRequest):
        if not state.pipeline:
            raise HTTPException(500, "Pipeline not initialized")

        try:
            method = FusionMethod(req.method)
        except ValueError:
            method = FusionMethod.VOTE

        fused = state.pipeline.fuse(req.agent_ids, method=method)
        return {"fused": fused.to_dict()}

    @app.get("/pipeline/rollup")
    async def rollup():
        if not state.pipeline:
            raise HTTPException(500, "Pipeline not initialized")
        result = state.pipeline.rollup()
        return {"result": result.to_dict() if result else None}

    # ─────────────────────────────────────────────────────
    # Judge Endpoints
    # ─────────────────────────────────────────────────────

    @app.post("/judge/evaluate")
    async def evaluate(task: str, response: str):
        if not state.judge:
            raise HTTPException(500, "Judge not initialized")
        fitness = state.judge.evaluate(task, response)
        return fitness.to_dict()

    @app.post("/judge/compare")
    async def compare(task: str, response_a: str, response_b: str):
        if not state.judge:
            raise HTTPException(500, "Judge not initialized")
        result = state.judge.compare(task, response_a, response_b)
        return result

    # ─────────────────────────────────────────────────────
    # Conflict Resolution Endpoints
    # ─────────────────────────────────────────────────────

    @app.post("/conflicts/detect")
    async def detect_conflicts(agent_ids: List[str]):
        """Detect conflicts between outputs from specified agents."""
        if not state.pipeline:
            raise HTTPException(500, "Pipeline not initialized")

        from .conflict import ConflictDetector
        detector = ConflictDetector()

        # Get outputs
        outputs = []
        for agent_id in agent_ids:
            agent_outputs = state.pipeline.get_by_agent(agent_id)
            outputs.extend(agent_outputs)

        if not outputs:
            return {"conflicts": [], "count": 0}

        # Detect conflicts
        conflicts = detector.detect(outputs)
        return {
            "conflicts": [c.to_dict() for c in conflicts],
            "count": len(conflicts),
        }

    @app.post("/conflicts/resolve")
    async def resolve_conflict_endpoint(agent_ids: List[str]):
        """Resolve conflicts between outputs using arbitration."""
        if not state.pipeline:
            raise HTTPException(500, "Pipeline not initialized")

        # Use pipeline's built-in resolution
        try:
            result = state.pipeline.fuse(
                agent_ids,
                method=FusionMethod.ARBITRATION,
            )
            return {"resolution": result.to_dict(), "success": True}
        except Exception as e:
            raise HTTPException(400, str(e))

    # ─────────────────────────────────────────────────────
    # Server-Sent Events
    # ─────────────────────────────────────────────────────

    @app.get("/events")
    async def events():
        async def event_generator() -> AsyncGenerator[str, None]:
            last_idx = 0
            while True:
                if last_idx < len(state.events):
                    for event in state.events[last_idx:]:
                        yield f"data: {json.dumps(event)}\n\n"
                    last_idx = len(state.events)
                await asyncio.sleep(0.5)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    return app


def _emit_event(event_type: str, data: Dict) -> None:
    """Emit an SSE event."""
    state.events.append({
        "type": event_type,
        "data": data,
        "timestamp": time.time(),
    })
    # Keep only last 100 events
    if len(state.events) > 100:
        state.events = state.events[-100:]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dashboard HTML
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>EATS Core Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
    <script src="https://unpkg.com/dagre@0.8.5/dist/dagre.min.js"></script>
    <script src="https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }
        .container { display: grid; grid-template-columns: 280px 1fr 300px; height: 100vh; }
        .sidebar { background: #1e293b; padding: 16px; overflow-y: auto; }
        .graph { background: #0f172a; }
        .detail { background: #1e293b; padding: 16px; overflow-y: auto; }
        h1 { font-size: 1.25rem; margin-bottom: 16px; color: #38bdf8; }
        h2 { font-size: 1rem; margin: 16px 0 8px; color: #94a3b8; }
        .btn { background: #3b82f6; color: white; border: none; padding: 8px 16px;
               border-radius: 6px; cursor: pointer; margin: 4px; font-size: 0.875rem; }
        .btn:hover { background: #2563eb; }
        .btn-red { background: #ef4444; }
        .btn-green { background: #22c55e; }
        input, select { background: #334155; border: 1px solid #475569; color: white;
                       padding: 8px; border-radius: 4px; width: 100%; margin: 4px 0; }
        #cy { width: 100%; height: 100%; }
        .card { background: #334155; border-radius: 8px; padding: 12px; margin: 8px 0; }
        .stat { display: flex; justify-content: space-between; padding: 4px 0; }
        .log { font-family: monospace; font-size: 0.75rem; max-height: 200px;
               overflow-y: auto; background: #0f172a; padding: 8px; border-radius: 4px; }
        .event { padding: 4px 0; border-bottom: 1px solid #475569; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>EATS Core</h1>
            <div class="card">
                <h2>Actions</h2>
                <button class="btn" onclick="refreshGraph()">Refresh Graph</button>
                <button class="btn btn-green" onclick="spawnAgent()">Spawn Agent</button>
            </div>
            <div class="card">
                <h2>Ask Agent</h2>
                <input id="prompt" placeholder="Enter prompt...">
                <input id="target" placeholder="Target (node ID or 'all')">
                <button class="btn" onclick="askAgent()">Send</button>
            </div>
            <div class="card">
                <h2>Evolution</h2>
                <input id="evo-task" placeholder="Task prompt...">
                <input id="evo-gens" type="number" value="3" placeholder="Generations">
                <button class="btn" onclick="runEvolution()">Run Evolution</button>
            </div>
            <div class="card">
                <h2>Stats</h2>
                <div id="stats" class="stat"></div>
            </div>
        </div>
        <div class="graph">
            <div id="cy"></div>
        </div>
        <div class="detail">
            <h2>Selected Node</h2>
            <div id="node-detail" class="card">Select a node</div>
            <h2>Events</h2>
            <div id="events" class="log"></div>
        </div>
    </div>
    <script>
        const cy = cytoscape({
            container: document.getElementById('cy'),
            style: [
                { selector: 'node', style: {
                    'label': 'data(label)', 'background-color': '#3b82f6',
                    'color': '#fff', 'text-valign': 'center', 'font-size': '10px',
                    'width': 60, 'height': 60
                }},
                { selector: 'edge', style: {
                    'width': 2, 'line-color': '#475569', 'target-arrow-color': '#475569',
                    'target-arrow-shape': 'triangle', 'curve-style': 'bezier'
                }},
                { selector: ':selected', style: { 'background-color': '#22c55e' }}
            ],
            layout: { name: 'dagre', rankDir: 'TB', nodeSep: 50 }
        });

        cy.on('tap', 'node', (e) => {
            document.getElementById('node-detail').innerHTML =
                '<pre>' + JSON.stringify(e.target.data(), null, 2) + '</pre>';
        });

        async function refreshGraph() {
            const res = await fetch('/swarm/graph');
            const data = await res.json();
            cy.elements().remove();
            cy.add(data.nodes);
            cy.add(data.edges);
            cy.layout({ name: 'dagre', rankDir: 'TB' }).run();
            updateStats();
        }

        async function updateStats() {
            const res = await fetch('/status');
            const data = await res.json();
            document.getElementById('stats').innerHTML =
                `<div>Nodes: ${data.swarm?.stats?.total_nodes || 0}</div>
                 <div>Active: ${data.swarm?.stats?.active_nodes || 0}</div>`;
        }

        async function spawnAgent() {
            const role = prompt('Role (coder/tester/critic/etc):') || 'coder';
            await fetch('/swarm/spawn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role })
            });
            refreshGraph();
        }

        async function askAgent() {
            const prompt = document.getElementById('prompt').value;
            const target = document.getElementById('target').value || 'all';
            const res = await fetch('/swarm/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, target })
            });
            const data = await res.json();
            addEvent('response', data);
        }

        async function runEvolution() {
            const task = document.getElementById('evo-task').value;
            const generations = parseInt(document.getElementById('evo-gens').value) || 3;
            await fetch('/evolution/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task, generations, population_size: 4 })
            });
            addEvent('evolution_started', { task });
        }

        function addEvent(type, data) {
            const div = document.getElementById('events');
            div.innerHTML = `<div class="event"><b>${type}</b>: ${JSON.stringify(data).slice(0,100)}</div>` + div.innerHTML;
        }

        // SSE
        const es = new EventSource('/events');
        es.onmessage = (e) => {
            const event = JSON.parse(e.data);
            addEvent(event.type, event.data);
            if (event.type.includes('spawn') || event.type.includes('complete')) refreshGraph();
        };

        refreshGraph();
    </script>
</body>
</html>'''


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_cli():
    """Run interactive CLI."""
    console = Console() if RICH_AVAILABLE else None

    def p(msg, style=""):
        if console:
            console.print(msg, style=style)
        else:
            print(msg)

    p("[bold cyan]EATS Core CLI[/bold cyan]")
    p("Commands: spawn <role>, ask <id> <prompt>, status, evolve <task>, quit")

    # Initialize
    swarm = SwarmController()
    swarm.initialize_tree()
    pipeline = ResultPipeline()
    judge = LLMJudge()

    while True:
        try:
            cmd = input("eats> ").strip()
            if not cmd:
                continue

            parts = cmd.split(maxsplit=2)
            action = parts[0].lower()

            if action in ("quit", "exit", "q"):
                break

            elif action == "spawn" and len(parts) >= 2:
                try:
                    role = AgentRole(parts[1])
                    node = swarm.spawn_agent(role=role)
                    if node:
                        p(f"[green]Spawned: {node.id}[/green]")
                    else:
                        p("[red]Spawn failed[/red]")
                except ValueError:
                    p(f"[red]Invalid role: {parts[1]}[/red]")

            elif action == "ask" and len(parts) >= 3:
                node_id = parts[1]
                prompt = parts[2]
                response = swarm.ask(node_id, prompt)
                if response:
                    fitness = judge.evaluate(prompt, response)
                    pipeline.add(node_id, response, fitness=fitness.score)
                    p(f"[cyan]Response (fitness={fitness.score:.1f}):[/cyan]")
                    p(response[:500])
                else:
                    p("[red]No response[/red]")

            elif action == "broadcast" and len(parts) >= 2:
                prompt = parts[1]
                results = swarm.broadcast(prompt)
                p(f"[cyan]Got {len(results)} responses[/cyan]")
                for aid, resp in results.items():
                    p(f"  {aid}: {resp[:100]}...")

            elif action == "status":
                swarm.print_status()
                stats = pipeline.stats()
                p(f"Pipeline: {stats['total_outputs']} outputs, avg fitness {stats['avg_fitness']:.2f}")

            elif action == "evolve" and len(parts) >= 2:
                task = parts[1]
                p(f"[yellow]Running evolution for: {task}[/yellow]")
                config = EvolutionConfig(task_prompt=task, generations=2, population_size=3)
                evo = Evolution(config)
                base = AgentDNA(role="coder")

                def on_gen(r):
                    p(f"  Gen {r.generation}: best={r.best_fitness:.2f}, avg={r.avg_fitness:.2f}")

                best = evo.run(base, heuristic_fitness, on_generation=on_gen)
                p(f"[green]Best DNA: {best.id}, fitness avg: {sum(best.fitness_history)/len(best.fitness_history):.2f}[/green]")

            elif action == "top":
                outputs = pipeline.get_top(5)
                p("[cyan]Top outputs:[/cyan]")
                for o in outputs:
                    p(f"  {o.agent_id}: {o.fitness:.2f} - {o.content[:60]}...")

            elif action == "help":
                p("Commands:")
                p("  spawn <role>           - Spawn agent (coder/tester/critic/etc)")
                p("  ask <id> <prompt>      - Ask specific agent")
                p("  broadcast <prompt>     - Ask all agents")
                p("  status                 - Show swarm status")
                p("  evolve <task>          - Run evolution")
                p("  top                    - Show top outputs")
                p("  quit                   - Exit")

            else:
                p(f"[yellow]Unknown: {action}. Type 'help'[/yellow]")

        except KeyboardInterrupt:
            p("\nInterrupted")
            break
        except EOFError:
            break
        except Exception as e:
            p(f"[red]Error: {e}[/red]")

    swarm.shutdown()
    p("[cyan]Goodbye![/cyan]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main Entry Points
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server."""
    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        sys.exit(1)

    app = create_app()
    uvicorn.run(app, host=host, port=port)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="EATS Core - Evolutionary Agent Tree System")
    parser.add_argument("mode", choices=["server", "cli"], default="cli", nargs="?",
                       help="Run mode: 'server' for API, 'cli' for interactive")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")

    args = parser.parse_args()

    if args.mode == "server":
        run_server(args.host, args.port)
    else:
        run_cli()


if __name__ == "__main__":
    main()
