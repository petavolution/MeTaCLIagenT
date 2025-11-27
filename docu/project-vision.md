# EATS Project Vision

## Evolutionary Agent Tree System - Design & Implementation Guide

**Version:** 2.2.0
**Status:** Active Development

---

## 1. Core Vision

EATS (Evolutionary Agent Tree System) is a **biologically-inspired multi-agent orchestration framework** for terminal-driven LLM coding agents. The system treats AI agents as organisms that can be spawned, evolved, and pruned based on performance, creating an adaptive swarm that improves over time.

### 1.1 Mission Statement

> Enable humans to orchestrate multiple LLM-based coding agents through a unified interface, leveraging evolutionary algorithms to discover optimal agent configurations while maintaining human supervision and control.

### 1.2 Core Principles

1. **Biological Metaphor**: Agents have DNA (configuration), fitness (performance), and senescence (decay). Evolution selects for the fittest.

2. **Human-in-the-Loop**: The system amplifies human capability, not replaces it. Humans supervise, direct, and make final decisions.

3. **Terminal-Native**: Agents operate through real terminal sessions (PTY/tmux), enabling use of any CLI tool (aider, interpreter, claude-code).

4. **Minimal Dependencies**: Core functionality works with zero external dependencies. Optional integrations enhance but don't require.

5. **Observable & Debuggable**: Real-time visualization, event streaming, and comprehensive logging for understanding system behavior.

---

## 2. Problem Statement

### 2.1 Current Challenges

| Challenge | EATS Solution |
|-----------|---------------|
| Single-agent limitations | Multi-agent swarm with specialized roles |
| Manual prompt optimization | Genetic algorithm evolves prompts automatically |
| Inconsistent agent quality | LLM-as-judge fitness evaluation |
| Hard to compare approaches | Parallel execution with result fusion |
| No institutional memory | Persistence layer stores winning DNA |
| Black-box agent behavior | Terminal visibility + event streaming |

### 2.2 Target Use Cases

1. **Complex Coding Tasks**: Decompose large features across Research/Creative/Execution branches
2. **Prompt Engineering**: Evolve system prompts to find optimal configurations
3. **Code Review Pipelines**: Multiple agents review from different perspectives
4. **Competitive Evaluation**: Tournament-style agent comparison
5. **Local Model Experimentation**: Test different models/configs on same tasks

---

## 3. Architecture Overview

### 3.1 System Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API/CLI Layer                                  │
│   FastAPI Server • CLI Supervisor • GhostSwarm Visual Controller         │
├─────────────────────────────────────────────────────────────────────────┤
│                        Orchestration Layer                               │
│   Workflows (DAG) • Swarm Controller • Evolution Engine                  │
├─────────────────────────────────────────────────────────────────────────┤
│                          Agent Layer                                     │
│   Agent DNA • Transport (PTY/tmux) • Turn History                        │
├─────────────────────────────────────────────────────────────────────────┤
│                        Evaluation Layer                                  │
│   LLM Judge • Fitness Functions • Result Pipeline                        │
├─────────────────────────────────────────────────────────────────────────┤
│                        Provider Layer                                    │
│   OpenAI • Anthropic • Ollama • Mock (testing)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                      Infrastructure Layer                                │
│   Events • Persistence • Metrics • Configuration                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Hierarchical Agent Tree

The default swarm structure organizes agents by function:

```
Meta-Orchestrator (Root)
├── Research Branch
│   ├── Planner      - Task decomposition
│   ├── Searcher     - Information gathering
│   └── Analyzer     - Data analysis
├── Creative Branch
│   ├── Generator    - Solution exploration
│   ├── Explorer     - Alternative approaches
│   └── Critic       - Quality evaluation
└── Execution Branch
    ├── Coder        - Implementation
    ├── Tester       - Test design
    └── Reviewer     - Code review
```

### 3.3 Data Flow

```
User Request
     │
     ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Orchestrator│───▶│ Agent Swarm  │───▶│ Result      │
│ (plan/route)│    │ (parallel)   │    │ Pipeline    │
└─────────────┘    └──────────────┘    └─────────────┘
                          │                   │
                          ▼                   ▼
                   ┌─────────────┐    ┌─────────────┐
                   │ LLM Judge   │    │ Fusion      │
                   │ (evaluate)  │    │ (synthesize)│
                   └─────────────┘    └─────────────┘
                          │                   │
                          ▼                   ▼
                   ┌─────────────────────────────────┐
                   │     Evolution Engine            │
                   │  (select, mutate, reproduce)    │
                   └─────────────────────────────────┘
```

---

## 4. Core Components

### 4.1 Agent DNA (`AgentDNA`)

The genetic blueprint defining agent behavior:

| Gene | Type | Description | Evolvable |
|------|------|-------------|-----------|
| `role` | string | Agent specialization | No |
| `system_prompt` | string | Core instructions | Yes |
| `temperature` | float | Creativity vs determinism | Yes |
| `max_tokens` | int | Response length limit | Yes |
| `cmd` | list | CLI command to spawn | No |
| `parent_id` | string | Lineage tracking | N/A |
| `generation` | int | Evolution generation | N/A |

### 4.2 Evolution Engine

Implements genetic algorithm for agent optimization:

**Cycle:**
1. **Initialize**: Create population from base DNA via mutation
2. **Evaluate**: Run agents on task, score with fitness function
3. **Select**: Keep top-k performers (survivors)
4. **Reproduce**: Mutate survivors to fill population
5. **Repeat**: For n generations

**Mutation Types:**
- Prompt mutation: Append behavioral hints
- Temperature drift: Small random adjustments (±0.1)
- Crossover: Combine traits from two parents

### 4.3 Fitness Evaluation

Multi-method evaluation system:

| Method | Speed | Quality | Use Case |
|--------|-------|---------|----------|
| Heuristic | Fast | Low | Development/testing |
| LLM-as-Judge | Slow | High | Production evaluation |
| Hybrid | Medium | Medium | Balanced approach |
| Keyword | Fast | Medium | Specific requirements |

**Default Criteria:**
- Correctness (weight: 2.0)
- Completeness (weight: 1.5)
- Clarity (weight: 1.0)
- Efficiency (weight: 1.0)
- Creativity (weight: 0.5)

### 4.4 Swarm Controller

Dynamic agent management with:

- **Probability Spawning**: Weighted random role selection
- **Senescence Tracking**: Performance decay over time
- **Auto-Pruning**: Remove underperforming agents
- **Compute Allocation**: Dynamic resource distribution by branch
- **Visual Layout**: Fan/grid arrangement for GhostSwarm

### 4.5 Result Pipeline

DAG-based result aggregation:

**Fusion Methods:**
| Method | Description |
|--------|-------------|
| `VOTE` | Select highest fitness output |
| `SYNTHESIZE` | Weighted combination by fitness |
| `ROLLUP` | Hierarchical consolidation |
| `CONCAT` | Simple concatenation |

**Features:**
- Semantic deduplication (hash-based cache)
- Parent context propagation
- Lineage tracking

---

## 5. Design Decisions

### 5.1 Why Terminal-Based?

1. **CLI Tool Ecosystem**: Leverage existing tools (aider, interpreter, claude-code)
2. **Full Control**: Send any text, capture any output
3. **Visibility**: Human can see what agents are doing
4. **No API Lock-in**: Works with any CLI that accepts text input

### 5.2 Why Evolutionary?

1. **Automatic Optimization**: Discover good prompts without manual tuning
2. **Robustness**: Population diversity prevents local minima
3. **Interpretability**: Track lineage to understand what works
4. **Continuous Improvement**: Can resume evolution from saved DNA

### 5.3 Why Hierarchical Tree?

1. **Specialization**: Agents focus on what they do best
2. **Parallel Execution**: Branches work concurrently
3. **Result Aggregation**: Natural rollup from leaves to root
4. **Scalability**: Add/remove branches without redesign

---

## 6. Implementation Guidelines

### 6.1 Dependency Philosophy

| Category | Dependencies | Notes |
|----------|--------------|-------|
| Core | None | Pure Python stdlib |
| Server | FastAPI, uvicorn | Optional web interface |
| Terminal | libtmux | Optional visual mode |
| Display | rich | Optional pretty output |
| LLM API | httpx | Optional provider support |

### 6.2 Error Handling Strategy

1. **Graceful Degradation**: If LLM judge fails, fall back to heuristic
2. **Timeout Management**: All operations have configurable timeouts
3. **Agent Isolation**: One agent failure doesn't crash swarm
4. **Recovery**: Persist state for resumption

### 6.3 Performance Considerations

| Scenario | Recommendation |
|----------|----------------|
| Many agents | Use PTY transport (lighter than tmux) |
| Visual debugging | Use tmux + GhostSwarm |
| Large populations | Limit concurrent evaluations |
| Long prompts | Enable semantic caching |
| Production | Use async execution (`AsyncAgent`) |

---

## 7. Target Deployment

### 7.1 Hardware Profile (2026 Target)

| Component | Specification | Purpose |
|-----------|---------------|---------|
| GPU | RTX 5090 32GB GDDR7 | Local LLMs (Llama 70B Q4) |
| CPU | AMD Ryzen 9 9950X (16 core) | Agent orchestration |
| RAM | 128 GB DDR5-6000 | Large context windows |
| Storage | 4 TB NVMe | Model storage, persistence |

### 7.2 Deployment Modes

1. **Development**: Single-machine, mock provider, heuristic fitness
2. **Local Production**: Local LLMs via Ollama/vLLM, tmux visual
3. **Hybrid**: Local orchestration, cloud LLM providers
4. **Distributed**: (Future) SSH transport to remote agents

---

## 8. Extension Roadmap

### 8.1 Planned Features

| Feature | Priority | Status |
|---------|----------|--------|
| SSH remote transport | High | Planned |
| Vector embeddings (semantic similarity) | Medium | Planned |
| Redis distributed messaging | Medium | Planned |
| vLLM integration | High | Planned |
| VR visualization (Godot/Unity) | Low | Concept |
| Image generation agents | Medium | Planned |

### 8.2 Integration Points

- **MCP Servers**: Connect to external tool servers
- **ComfyUI**: Multimodal workflows with image generation
- **LangChain/LlamaIndex**: Alternative workflow engines
- **Prometheus/Grafana**: Production observability

---

## 9. CLI Tool Integration

### 9.1 Supported CLI Tools

| Tool | Command | Description |
|------|---------|-------------|
| `claude-code` | `claude` | Anthropic Claude Code CLI |
| `gemini` | `gemini chat` | Google Gemini CLI |
| `aider` | `aider` | AI pair programming |
| `interpreter` | `interpreter` | Open Interpreter |
| `ollama` | `ollama run codellama` | Local LLM |
| `python` | `python3 -i` | Python REPL |
| `bash` | `bash` | Shell |

### 9.2 Easy API

```python
from eats_core import spawn_agent, run_task, quick_run, save_result

# One-liner execution
output = quick_run('python', 'print(2**10)')  # "1024"

# Full workflow
agent = spawn_agent('gemini')  # or 'aider', 'claude-code', etc.
result = run_task(agent, 'Write a sorting function')
save_result('sort_task', result)
agent.stop()

# Multiple agents in parallel
from eats_core import spawn_multiple, run_parallel, stop_all

agents = spawn_multiple(['python', 'python', 'python'])
results = run_parallel(agents, 'print("hello")')
stop_all(agents)
```

---

## 10. Usage Patterns

### 10.1 Evolution

```python
from eats_core import AgentDNA, Evolution, EvolutionConfig, heuristic_fitness

config = EvolutionConfig(population_size=4, generations=3)
base_dna = AgentDNA(role="coder", system_prompt="You write Python.")

evo = Evolution(config)
best_dna = evo.run(base_dna, heuristic_fitness)
```

### 10.2 Hierarchical Swarm

```python
from eats_core import SwarmController, AgentRole

swarm = SwarmController()
swarm.initialize_tree()  # Creates Research/Creative/Execution branches
response = swarm.ask("meta_orchestrator_1", "Implement a sorting algorithm")
swarm.shutdown()
```

### 10.3 Workflow Pipeline

```python
from eats_core import WorkflowBuilder, AsyncAgent

wf = (WorkflowBuilder("code_review")
    .input("code")
    .agent("analyze", analyzer, "Analyze: {code}")
    .agent("review", reviewer, "Review: {analyze}")
    .output("result")
    .build())

result = await wf.run(code="def foo(): pass")
```

---

## 11. Success Criteria

### 11.1 Technical Metrics

| Metric | Target |
|--------|--------|
| Agent spawn time | < 500ms |
| Evaluation latency (heuristic) | < 10ms |
| Evolution cycle (4 agents, 3 gen) | < 5 min |
| Memory per agent | < 50MB |
| API response time | < 100ms |

### 11.2 Quality Metrics

| Metric | Target |
|--------|--------|
| Evolved prompt improvement | 20%+ fitness gain |
| Result fusion quality | Better than single best |
| Agent specialization benefit | Measurable per-branch improvement |

---

## 12. Conclusion

EATS provides a framework for orchestrating multiple AI coding agents with biologically-inspired optimization. The system balances automation (evolution) with human control (supervision), visual debugging (GhostSwarm), and practical deployment (terminal-native design).

Key differentiators:
1. **Evolutionary optimization** of agent configurations
2. **Hierarchical organization** with specialized branches
3. **Terminal-native** compatibility with existing tools
4. **Minimal dependencies** with progressive enhancement
5. **Human-in-the-loop** supervision at all levels

The framework is designed for practical use on prosumer hardware, enabling individual developers and small teams to leverage multi-agent AI workflows without cloud dependencies.

---

*Document generated from codebase audit. Last updated: 2024*
