# core.py - Unified Transport, Agent, and Evolution System
"""
Core EATS components: Transport abstraction, Agent DNA, Evolution engine.

Optimized for minimal dependencies and maximum flexibility.
"""

from __future__ import annotations
import os
import pty
import select
import shlex
import subprocess
import threading
import time
import uuid
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Protocol
from enum import Enum

# Late import to avoid circular dependency
def _get_audit_logger():
    """Lazy import audit logger to avoid circular deps."""
    try:
        from .audit import get_audit_logger
        return get_audit_logger()
    except ImportError:
        return None

# Optional libtmux support
try:
    import libtmux
    TMUX_AVAILABLE = True
except ImportError:
    libtmux = None
    TMUX_AVAILABLE = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Transport Layer - Unified interface for terminal control
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Transport(ABC):
    """Abstract transport for terminal-based agent control."""

    @abstractmethod
    def start(self) -> None:
        """Initialize the transport."""
        pass

    @abstractmethod
    def send(self, text: str, newline: bool = True) -> None:
        """Send text to the terminal."""
        pass

    @abstractmethod
    def recv(self, timeout: float = 0.1) -> str:
        """Receive available output (non-blocking)."""
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """Check if underlying process is running."""
        pass

    @abstractmethod
    def terminate(self) -> None:
        """Clean shutdown."""
        pass

    def send_and_wait(
        self,
        text: str,
        wait_seconds: float = 2.0,
        idle_threshold: float = 0.5,
    ) -> str:
        """Send text and wait for response with idle detection."""
        self.send(text)

        output = ""
        last_recv_time = time.time()
        start = time.time()

        while time.time() - start < wait_seconds:
            chunk = self.recv(timeout=0.1)
            if chunk:
                output += chunk
                last_recv_time = time.time()
            elif time.time() - last_recv_time > idle_threshold:
                # Agent has been idle - response complete
                break
            time.sleep(0.05)

        return output


class BufferOverflowError(Exception):
    """Raised when buffer exceeds maximum size."""
    pass


class PTYTransport(Transport):
    """
    PTY-based transport for LLM CLI processes.

    Uses pseudo-terminal for full interactive control with
    background thread for non-blocking reads.

    Security Features:
    - Bounded buffers to prevent memory exhaustion
    - Raises BufferOverflowError if limits exceeded
    """

    # Security limits
    MAX_BUFFER_SIZE = 10 * 1024 * 1024   # 10MB max buffer

    def __init__(self, cmd: List[str], name: str = "agent",
                 max_buffer_size: Optional[int] = None):
        self.cmd = cmd
        self.name = name
        self._master_fd: Optional[int] = None
        self._proc: Optional[subprocess.Popen] = None
        self._buffer = ""
        self._lock = threading.Lock()
        self._running = False
        self._reader: Optional[threading.Thread] = None
        self._overflow_error: Optional[Exception] = None

        # Configurable limit
        self.max_buffer_size = max_buffer_size or self.MAX_BUFFER_SIZE

    def start(self) -> None:
        if self._proc is not None:
            raise RuntimeError("Already started")

        master_fd, slave_fd = pty.openpty()
        self._master_fd = master_fd

        # Set reasonable terminal size
        try:
            import fcntl, struct, termios
            winsize = struct.pack('HHHH', 50, 120, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

        self._proc = subprocess.Popen(
            self.cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            bufsize=0,
            close_fds=True,
            text=False,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        os.close(slave_fd)

        self._running = True
        self._reader = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name=f"PTY-{self.name}",
        )
        self._reader.start()

    def _read_loop(self) -> None:
        """Background read loop with buffer overflow protection."""
        while self._running and self._master_fd:
            try:
                r, _, _ = select.select([self._master_fd], [], [], 0.1)
                if self._master_fd in r:
                    data = os.read(self._master_fd, 4096)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")

                    with self._lock:
                        # Check buffer limit before append
                        if len(self._buffer) + len(text) > self.max_buffer_size:
                            buffer_size = len(self._buffer) + len(text)
                            self._overflow_error = BufferOverflowError(
                                f"Buffer exceeded {self.max_buffer_size} bytes. "
                                f"Process '{self.name}' generating too much output."
                            )

                            # AUDIT: Log buffer overflow
                            audit = _get_audit_logger()
                            if audit:
                                audit.log_buffer_overflow(
                                    agent_name=self.name,
                                    buffer_size=buffer_size,
                                    max_size=self.max_buffer_size
                                )

                            self._running = False
                            break

                        self._buffer += text
            except (OSError, ValueError):
                break

    def send(self, text: str, newline: bool = True) -> None:
        if not self._master_fd:
            raise RuntimeError("Not started")
        data = (text + ("\n" if newline else "")).encode("utf-8")
        os.write(self._master_fd, data)

    def recv(self, timeout: float = 0.1) -> str:
        """
        Receive buffered data.

        Raises:
            BufferOverflowError: If buffer exceeded limits during read
        """
        time.sleep(min(timeout, 0.05))  # Small delay for buffer fill
        with self._lock:
            # Check for overflow error from reader thread
            if self._overflow_error:
                error = self._overflow_error
                self._overflow_error = None
                raise error

            data = self._buffer
            self._buffer = ""
        return data

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def terminate(self) -> None:
        self._running = False
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        if self._master_fd:
            try:
                os.close(self._master_fd)
            except OSError:
                pass


class TmuxTransport(Transport):
    """
    Tmux-based transport for visible multi-agent orchestration.

    Uses libtmux to manage sessions/panes with optional GUI windows.
    Falls back to subprocess if libtmux unavailable.
    """

    def __init__(
        self,
        session_name: str = "eats",
        window_name: str = "agent",
        cmd: Optional[List[str]] = None,
        spawn_gui: bool = False,
        terminal: str = "alacritty",
    ):
        self.session_name = session_name
        self.window_name = window_name
        self.cmd = cmd or ["bash"]
        self.spawn_gui = spawn_gui
        self.terminal = terminal

        self._server: Any = None
        self._session: Any = None
        self._pane: Any = None

    def start(self) -> None:
        if not TMUX_AVAILABLE:
            raise RuntimeError("libtmux not installed: pip install libtmux")

        self._server = libtmux.Server()

        # Get or create session
        existing = self._server.sessions.filter(session_name=self.session_name)
        if existing:
            self._session = existing[0]
        else:
            self._session = self._server.new_session(
                session_name=self.session_name,
                detach=True,
            )

        # Create window and pane
        self._pane = self._session.active_window.active_pane

        # Start command in pane - SECURITY: properly escape command args
        cmd_str = " ".join(shlex.quote(arg) for arg in self.cmd)
        self._pane.send_keys(cmd_str, enter=True)

        # Optionally spawn GUI terminal
        if self.spawn_gui:
            self._spawn_gui_window()

    def _spawn_gui_window(self) -> None:
        """Spawn a visible terminal attached to the tmux session."""
        # SECURITY: Use array form to prevent command injection via session_name
        if self.terminal == "alacritty":
            subprocess.Popen(["alacritty", "-e", "tmux", "attach", "-t", self.session_name])
        elif self.terminal == "kitty":
            subprocess.Popen(["kitty", "-e", "tmux", "attach", "-t", self.session_name])
        elif self.terminal == "gnome-terminal":
            subprocess.Popen(["gnome-terminal", "--", "tmux", "attach", "-t", self.session_name])
        else:  # xterm fallback
            subprocess.Popen(["xterm", "-e", "tmux", "attach", "-t", self.session_name])

    def send(self, text: str, newline: bool = True) -> None:
        """
        Send text to tmux pane.

        WARNING: Text is sent as-is to the shell. Caller must sanitize
        if text comes from untrusted sources to prevent command injection.
        """
        if not self._pane:
            raise RuntimeError("Not started")
        self._pane.send_keys(text, enter=newline)

    def recv(self, timeout: float = 0.1) -> str:
        if not self._pane:
            return ""
        time.sleep(timeout)
        try:
            lines = self._pane.capture_pane()
            return "\n".join(lines) if lines else ""
        except Exception:
            return ""

    def is_alive(self) -> bool:
        return self._pane is not None

    def terminate(self) -> None:
        if self._session:
            try:
                self._session.kill()
            except Exception:
                pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent DNA - The genetic blueprint for agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AgentDNA:
    """
    Agent blueprint - the "genome" that gets evolved.

    Phenotype: Observable traits (role, prompt)
    Genotype: Hidden parameters (temperature, timeout)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = "coder"
    system_prompt: str = "You are a helpful coding assistant."
    cmd: List[str] = field(default_factory=lambda: ["python", "-i"])

    # Evolvable parameters
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 30.0

    # Lineage tracking
    parent_id: Optional[str] = None
    generation: int = 0
    fitness_history: List[float] = field(default_factory=list)

    def mutate(self, rate: float = 0.2) -> AgentDNA:
        """Create mutated offspring."""
        # Mutate prompt
        new_prompt = self.system_prompt
        if random.random() < rate:
            mutations = [
                "\nThink step by step.",
                "\nBe concise and direct.",
                "\nDouble-check your work.",
                "\nConsider edge cases.",
                "\nPrioritize code quality.",
            ]
            new_prompt += random.choice(mutations)

        # Mutate temperature
        new_temp = self.temperature + random.uniform(-0.1, 0.1)
        new_temp = max(0.1, min(1.0, new_temp))

        return AgentDNA(
            role=self.role,
            system_prompt=new_prompt,
            cmd=self.cmd.copy(),
            temperature=round(new_temp, 2),
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            parent_id=self.id,
            generation=self.generation + 1,
        )

    def crossover(self, other: AgentDNA) -> AgentDNA:
        """Combine traits from two parents."""
        return AgentDNA(
            role=random.choice([self.role, other.role]),
            system_prompt=random.choice([self.system_prompt, other.system_prompt]),
            cmd=self.cmd.copy(),
            temperature=(self.temperature + other.temperature) / 2,
            max_tokens=random.choice([self.max_tokens, other.max_tokens]),
            parent_id=self.id,
            generation=max(self.generation, other.generation) + 1,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "system_prompt": self.system_prompt[:100] + "...",
            "temperature": self.temperature,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "avg_fitness": sum(self.fitness_history) / len(self.fitness_history) if self.fitness_history else 0,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent - Live running instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Turn:
    """A single prompt-response turn."""
    prompt: str
    response: str
    timestamp: float
    duration: float


class Agent:
    """
    A live agent instance with transport and conversation history.

    Usage:
        dna = AgentDNA(role="coder", cmd=["aider"])
        agent = Agent(dna)
        agent.start()
        response = agent.ask("Write hello world")
        agent.stop()
    """

    def __init__(
        self,
        dna: AgentDNA,
        transport_type: str = "pty",
        **transport_kwargs,
    ):
        self.dna = dna
        self.id = f"{dna.role}_{dna.id}"
        self.turns: List[Turn] = []
        self._transport: Optional[Transport] = None
        self._transport_type = transport_type
        self._transport_kwargs = transport_kwargs

    def start(self) -> None:
        """Start the agent's underlying process."""
        if self._transport_type == "tmux":
            self._transport = TmuxTransport(
                cmd=self.dna.cmd,
                window_name=self.id,
                **self._transport_kwargs,
            )
        else:
            self._transport = PTYTransport(
                cmd=self.dna.cmd,
                name=self.id,
            )
        self._transport.start()

        # Send system prompt if the tool supports it
        time.sleep(0.5)  # Wait for startup

    def ask(
        self,
        prompt: str,
        wait_seconds: Optional[float] = None,
        idle_threshold: float = 0.5,
    ) -> str:
        """Send prompt and get response."""
        if not self._transport:
            raise RuntimeError("Agent not started")

        wait = wait_seconds or self.dna.timeout
        start = time.time()

        response = self._transport.send_and_wait(
            prompt,
            wait_seconds=wait,
            idle_threshold=idle_threshold,
        )

        duration = time.time() - start
        self.turns.append(Turn(
            prompt=prompt,
            response=response,
            timestamp=start,
            duration=duration,
        ))

        return response

    def last_output(self, chars: int = 2000) -> str:
        """Get last output (for fitness evaluation)."""
        if self.turns:
            return self.turns[-1].response[-chars:]
        return ""

    def is_alive(self) -> bool:
        return self._transport is not None and self._transport.is_alive()

    def stop(self) -> None:
        """Stop the agent."""
        if self._transport:
            self._transport.terminate()
            self._transport = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Evolution Engine - Genetic algorithm for agent optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FitnessFn(Protocol):
    """Protocol for fitness functions."""
    def __call__(self, agent: Agent, task: str, response: str) -> float: ...


@dataclass
class EvolutionConfig:
    """Evolution hyperparameters."""
    population_size: int = 4
    survivors: int = 2
    mutation_rate: float = 0.3
    generations: int = 3
    task_prompt: str = "Write a Python function that reverses a string."


@dataclass
class GenerationResult:
    """Results from one generation."""
    generation: int
    population: List[AgentDNA]
    fitness_scores: Dict[str, float]
    best_dna: AgentDNA
    best_fitness: float
    avg_fitness: float


class Evolution:
    """
    Evolutionary optimization engine for agent DNA.

    Usage:
        evo = Evolution(config)
        best_dna = evo.run(base_dna, fitness_fn)
    """

    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.history: List[GenerationResult] = []

    def run(
        self,
        base_dna: AgentDNA,
        fitness_fn: FitnessFn,
        on_generation: Optional[Callable[[GenerationResult], None]] = None,
    ) -> AgentDNA:
        """
        Run evolutionary optimization.

        Args:
            base_dna: Starting DNA to evolve from
            fitness_fn: Function(agent, task, response) -> float
            on_generation: Optional callback after each generation

        Returns:
            Best performing DNA
        """
        # Initialize population
        population = self._init_population(base_dna)

        for gen in range(self.config.generations):
            # Evaluate fitness
            fitness_scores = self._evaluate(population, fitness_fn)

            # Record results
            sorted_pop = sorted(
                population,
                key=lambda d: fitness_scores.get(d.id, 0),
                reverse=True,
            )
            best = sorted_pop[0]
            best_fit = fitness_scores.get(best.id, 0)
            avg_fit = sum(fitness_scores.values()) / len(fitness_scores)

            result = GenerationResult(
                generation=gen,
                population=population.copy(),
                fitness_scores=fitness_scores,
                best_dna=best,
                best_fitness=best_fit,
                avg_fitness=avg_fit,
            )
            self.history.append(result)

            if on_generation:
                on_generation(result)

            # Final generation - return best
            if gen == self.config.generations - 1:
                return best

            # Select survivors and reproduce
            survivors = sorted_pop[:self.config.survivors]
            population = self._reproduce(survivors, gen + 1)

        return population[0]  # Should not reach here

    def _init_population(self, base: AgentDNA) -> List[AgentDNA]:
        """Create initial population via mutation."""
        pop = [base]  # Keep original
        for _ in range(self.config.population_size - 1):
            pop.append(base.mutate(self.config.mutation_rate))
        return pop

    def _evaluate(
        self,
        population: List[AgentDNA],
        fitness_fn: FitnessFn,
    ) -> Dict[str, float]:
        """Evaluate all agents in population."""
        scores = {}

        for dna in population:
            agent = Agent(dna)
            try:
                agent.start()
                response = agent.ask(self.config.task_prompt)
                score = fitness_fn(agent, self.config.task_prompt, response)
                scores[dna.id] = score
                dna.fitness_history.append(score)
            except Exception as e:
                scores[dna.id] = 0.0
                print(f"Error evaluating {dna.id}: {e}")
            finally:
                agent.stop()

        return scores

    def _reproduce(
        self,
        survivors: List[AgentDNA],
        generation: int,
    ) -> List[AgentDNA]:
        """Create next generation from survivors."""
        next_gen = list(survivors)  # Keep survivors

        # Fill remaining with offspring
        while len(next_gen) < self.config.population_size:
            parent = random.choice(survivors)
            child = parent.mutate(self.config.mutation_rate)
            next_gen.append(child)

        return next_gen


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Built-in Fitness Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def heuristic_fitness(agent: Agent, task: str, response: str) -> float:
    """
    Heuristic fitness based on response quality indicators.

    Scores 0-10 based on:
    - Length (not too short/long)
    - Code presence
    - Explanation quality
    - Response time
    """
    score = 0.0

    # Length score (optimal: 200-1500 chars)
    length = len(response)
    if length < 50:
        score += 1
    elif length < 200:
        score += 2
    elif length < 1500:
        score += 3
    else:
        score += 2

    # Code presence
    if "def " in response or "class " in response or "```" in response:
        score += 3

    # Structure (lists, steps)
    if any(m in response for m in ["1.", "- ", "* ", "Step"]):
        score += 2

    # Response time (faster is better, within reason)
    if agent.turns:
        duration = agent.turns[-1].duration
        if 1 < duration < 10:
            score += 2
        elif duration < 30:
            score += 1

    return min(10.0, score)


def keyword_fitness(
    keywords: Dict[str, float],
) -> FitnessFn:
    """Create fitness function that scores based on keyword presence."""
    def fn(agent: Agent, task: str, response: str) -> float:
        score = 0.0
        response_lower = response.lower()
        for kw, weight in keywords.items():
            if kw.lower() in response_lower:
                score += weight
        return min(10.0, score)
    return fn
