#!/usr/bin/env python3
"""
EATS - Evolutionary Agent Tree System

Unified entry point for all EATS functionality.

Usage:
    python run_core.py demo         # Run quick demo
    python run_core.py test         # Run test suite
    python run_core.py server       # Start API server at http://localhost:8000
    python run_core.py cli          # Interactive CLI
    python run_core.py ghost [N]    # GhostSwarm with N agents (visual mode)
    python run_core.py help         # Show this help

Modules:
    eats_core/  - Core v2.0 (primary, recommended)
    eats/       - Legacy v1.0 (deprecated, for backward compatibility)
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def lazy_import_server():
    """Lazy import to avoid loading all modules upfront."""
    from eats_core.server import run_server, run_cli
    return run_server, run_cli


def run_demo():
    """Run a quick demonstration of EATS Core capabilities."""
    print("=" * 60)
    print("EATS Core - Quick Demo")
    print("=" * 60)

    from eats_core.core import AgentDNA, Evolution, EvolutionConfig, heuristic_fitness
    from eats_core.swarm import SwarmController, AgentRole
    from eats_core.judge import LLMJudge
    from eats_core.pipeline import ResultPipeline, FusionMethod

    # 1. Create swarm
    print("\n1. Creating hierarchical swarm...")
    swarm = SwarmController()
    root_id = swarm.initialize_tree()
    print(f"   Created tree with root: {root_id}")
    print(f"   Total nodes: {len(swarm._nodes)}")

    # 2. Show tree structure
    print("\n2. Tree structure:")
    for node in swarm._nodes.values():
        indent = "  " * node.depth
        print(f"   {indent}{node.role.value} ({node.id[:20]}...)")

    # 3. Test evolution (dry run - no actual agents)
    print("\n3. Evolution system:")
    config = EvolutionConfig(
        population_size=3,
        generations=2,
        task_prompt="Write a hello world function",
    )
    print(f"   Config: pop={config.population_size}, gens={config.generations}")

    base_dna = AgentDNA(role="coder", system_prompt="You are a Python coder.")
    print(f"   Base DNA: {base_dna.role}, temp={base_dna.temperature}")

    # Create mutations
    mutations = [base_dna.mutate() for _ in range(3)]
    print(f"   Created {len(mutations)} mutations")
    for m in mutations:
        print(f"     - {m.id}: temp={m.temperature}, gen={m.generation}")

    # 4. Test judge
    print("\n4. LLM Judge (heuristic mode):")
    judge = LLMJudge()

    test_responses = [
        "def hello():\n    print('Hello World')",
        "Hello world is easy just use print",
        "```python\ndef hello():\n    '''Print hello world'''\n    print('Hello, World!')\n```",
    ]

    for i, resp in enumerate(test_responses):
        fitness = judge.evaluate("Write hello world", resp)
        print(f"   Response {i+1}: fitness={fitness.score:.2f} ({fitness.method})")

    # 5. Test pipeline
    print("\n5. Result Pipeline:")
    pipeline = ResultPipeline()

    outputs = [
        ("agent-1", "First response with code def foo(): pass", 7.5),
        ("agent-2", "Second more detailed response", 6.0),
        ("agent-3", "Third comprehensive answer with examples", 8.2),
    ]

    for agent_id, content, fitness in outputs:
        pipeline.add(agent_id, content, fitness=fitness)
    print(f"   Added {len(outputs)} outputs to pipeline")

    # Fuse
    fused = pipeline.fuse(["agent-1", "agent-2", "agent-3"], method=FusionMethod.VOTE)
    print(f"   Fused result (vote): {fused.agent_id}, fitness={fused.fitness:.2f}")

    top = pipeline.get_top(2)
    print(f"   Top 2: {[o.agent_id for o in top]}")

    # 6. Stats
    print("\n6. Pipeline stats:")
    stats = pipeline.stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Cleanup
    swarm.shutdown()

    print("\n" + "=" * 60)
    print("Demo complete! Run 'python run_core.py server' for web UI")
    print("=" * 60)


def run_ghost():
    """Run GhostSwarm visual multi-terminal mode."""
    try:
        from eats.ghost_swarm import GhostSwarm
        agents = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        print(f"Starting GhostSwarm with {agents} agents...")
        swarm = GhostSwarm()
        swarm.run(agent_count=agents)
    except ImportError as e:
        print(f"GhostSwarm requires libtmux: pip install libtmux")
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"GhostSwarm error: {e}")
        sys.exit(1)


def run_tests():
    """Run the test suite."""
    from tests.test_core import main as test_main
    # Pass remaining args to test runner
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    test_main()


def show_help():
    """Show help and available commands."""
    print(__doc__)
    print("\nQuick start:")
    print("  1. Run demo:    python run_core.py demo")
    print("  2. Run tests:   python run_core.py test")
    print("  3. Start API:   python run_core.py server")
    print("  4. Open:        http://localhost:8000")
    print("\nFor programmatic use:")
    print("  from eats_core import SwarmController, AgentDNA, Evolution")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    mode = sys.argv[1].lower()

    if mode == "server":
        run_server, _ = lazy_import_server()
        run_server()
    elif mode == "cli":
        _, run_cli = lazy_import_server()
        run_cli()
    elif mode == "demo":
        run_demo()
    elif mode == "test":
        run_tests()
    elif mode == "ghost":
        run_ghost()
    elif mode in ("help", "-h", "--help"):
        show_help()
    else:
        print(f"Unknown mode: {mode}")
        show_help()
        sys.exit(1)
