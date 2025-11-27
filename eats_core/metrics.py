# metrics.py - Observability and Metrics System
"""
Metrics collection and monitoring for EATS.

Tracks:
- Agent performance (response time, fitness, tokens)
- Evolution progress (fitness trends, mutations)
- System health (active agents, queue depths)
- Cost estimation (token usage, API calls)
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
from enum import Enum
import statistics


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metric Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"      # Monotonically increasing
    GAUGE = "gauge"          # Current value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Duration measurements


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metric Collectors
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Counter:
    """Monotonically increasing counter."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._values: Dict[str, float] = defaultdict(float)

    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter."""
        key = self._labels_key(labels)
        self._values[key] += value

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current value."""
        key = self._labels_key(labels)
        return self._values[key]

    def _labels_key(self, labels: Optional[Dict]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Gauge:
    """Current value gauge."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._values: Dict[str, float] = defaultdict(float)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        key = self._labels_key(labels)
        self._values[key] = value

    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        key = self._labels_key(labels)
        self._values[key] += value

    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        key = self._labels_key(labels)
        self._values[key] -= value

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current value."""
        key = self._labels_key(labels)
        return self._values[key]

    def _labels_key(self, labels: Optional[Dict]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Histogram:
    """Distribution of values."""

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
    ):
        self.name = name
        self.description = description
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        self._values: Dict[str, List[float]] = defaultdict(list)

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation."""
        key = self._labels_key(labels)
        self._values[key].append(value)

    def get_stats(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get distribution statistics."""
        key = self._labels_key(labels)
        values = self._values[key]

        if not values:
            return {"count": 0, "sum": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_vals = sorted(values)
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p50": self._percentile(sorted_vals, 50),
            "p95": self._percentile(sorted_vals, 95),
            "p99": self._percentile(sorted_vals, 99),
        }

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not sorted_values:
            return 0.0
        idx = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def _labels_key(self, labels: Optional[Dict]) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Timer:
    """Timer for measuring durations."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._histogram = Histogram(f"{name}_seconds", description)

    def time(self, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing."""
        return TimerContext(self, labels)

    def record(self, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a duration."""
        self._histogram.observe(duration, labels)

    def get_stats(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get timing statistics."""
        return self._histogram.get_stats(labels)


class TimerContext:
    """Context manager for timing code blocks."""

    def __init__(self, timer: Timer, labels: Optional[Dict[str, str]] = None):
        self.timer = timer
        self.labels = labels
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start_time
        self.timer.record(duration, self.labels)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metrics Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MetricsRegistry:
    """
    Central registry for all metrics.

    Usage:
        metrics = MetricsRegistry()

        # Create metrics
        requests = metrics.counter("agent_requests", "Total agent requests")
        active = metrics.gauge("active_agents", "Currently active agents")
        latency = metrics.histogram("response_latency", "Response latency")
        duration = metrics.timer("task_duration", "Task execution time")

        # Record values
        requests.inc(labels={"agent": "coder"})
        active.set(5)
        latency.observe(1.5, labels={"agent": "coder"})

        with duration.time(labels={"task": "code"}):
            do_work()
    """

    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._timers: Dict[str, Timer] = {}

    def counter(self, name: str, description: str = "") -> Counter:
        """Get or create counter."""
        if name not in self._counters:
            self._counters[name] = Counter(name, description)
        return self._counters[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        """Get or create gauge."""
        if name not in self._gauges:
            self._gauges[name] = Gauge(name, description)
        return self._gauges[name]

    def histogram(self, name: str, description: str = "", buckets: Optional[List[float]] = None) -> Histogram:
        """Get or create histogram."""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name, description, buckets)
        return self._histograms[name]

    def timer(self, name: str, description: str = "") -> Timer:
        """Get or create timer."""
        if name not in self._timers:
            self._timers[name] = Timer(name, description)
        return self._timers[name]

    def get_all(self) -> Dict[str, Any]:
        """Get all metrics as dict."""
        return {
            "counters": {name: c._values for name, c in self._counters.items()},
            "gauges": {name: g._values for name, g in self._gauges.items()},
            "histograms": {name: h.get_stats() for name, h in self._histograms.items()},
            "timers": {name: t.get_stats() for name, t in self._timers.items()},
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EATS-Specific Metrics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EATSMetrics:
    """
    Pre-configured metrics for EATS system.

    Provides semantic methods for common operations.
    """

    def __init__(self, registry: Optional[MetricsRegistry] = None):
        self.registry = registry or MetricsRegistry()

        # Agent metrics
        self.agent_spawned = self.registry.counter("agent_spawned_total", "Total agents spawned")
        self.agent_stopped = self.registry.counter("agent_stopped_total", "Total agents stopped")
        self.active_agents = self.registry.gauge("active_agents", "Currently active agents")
        self.agent_response_time = self.registry.histogram(
            "agent_response_seconds",
            "Agent response time distribution",
            buckets=[0.5, 1, 2, 5, 10, 30, 60],
        )

        # Evolution metrics
        self.generations_run = self.registry.counter("generations_total", "Total generations run")
        self.fitness_scores = self.registry.histogram(
            "fitness_score",
            "Fitness score distribution",
            buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        )
        self.best_fitness = self.registry.gauge("best_fitness", "Best fitness score")
        self.avg_fitness = self.registry.gauge("avg_fitness", "Average fitness score")

        # Task metrics
        self.tasks_submitted = self.registry.counter("tasks_submitted_total", "Total tasks submitted")
        self.tasks_completed = self.registry.counter("tasks_completed_total", "Total tasks completed")
        self.tasks_failed = self.registry.counter("tasks_failed_total", "Total tasks failed")
        self.task_duration = self.registry.timer("task_duration", "Task execution duration")

        # Token/cost metrics
        self.tokens_input = self.registry.counter("tokens_input_total", "Total input tokens")
        self.tokens_output = self.registry.counter("tokens_output_total", "Total output tokens")
        self.estimated_cost = self.registry.gauge("estimated_cost_usd", "Estimated cost in USD")

        # Pipeline metrics
        self.outputs_processed = self.registry.counter("outputs_processed_total", "Outputs processed")
        self.cache_hits = self.registry.counter("cache_hits_total", "Cache hits")
        self.fusions_performed = self.registry.counter("fusions_total", "Fusions performed")

    # ─────────────────────────────────────────────────────
    # Agent Methods
    # ─────────────────────────────────────────────────────

    def record_agent_spawn(self, role: str) -> None:
        """Record agent spawn."""
        self.agent_spawned.inc(labels={"role": role})
        self.active_agents.inc(labels={"role": role})

    def record_agent_stop(self, role: str) -> None:
        """Record agent stop."""
        self.agent_stopped.inc(labels={"role": role})
        self.active_agents.dec(labels={"role": role})

    def record_response(self, agent_id: str, duration: float, role: str = "unknown") -> None:
        """Record agent response time."""
        self.agent_response_time.observe(duration, labels={"role": role})

    # ─────────────────────────────────────────────────────
    # Evolution Methods
    # ─────────────────────────────────────────────────────

    def record_generation(
        self,
        generation: int,
        best_fitness: float,
        avg_fitness: float,
        population_size: int,
    ) -> None:
        """Record generation completion."""
        self.generations_run.inc()
        self.best_fitness.set(best_fitness, labels={"generation": str(generation)})
        self.avg_fitness.set(avg_fitness, labels={"generation": str(generation)})

    def record_fitness(self, score: float, agent_id: str) -> None:
        """Record individual fitness score."""
        self.fitness_scores.observe(score, labels={"agent": agent_id})

    # ─────────────────────────────────────────────────────
    # Task Methods
    # ─────────────────────────────────────────────────────

    def record_task_start(self, task_type: str = "default") -> None:
        """Record task start."""
        self.tasks_submitted.inc(labels={"type": task_type})

    def record_task_complete(self, task_type: str = "default", duration: float = 0) -> None:
        """Record task completion."""
        self.tasks_completed.inc(labels={"type": task_type})
        if duration > 0:
            self.task_duration.record(duration, labels={"type": task_type})

    def record_task_failed(self, task_type: str = "default", error: str = "") -> None:
        """Record task failure."""
        self.tasks_failed.inc(labels={"type": task_type})

    # ─────────────────────────────────────────────────────
    # Token/Cost Methods
    # ─────────────────────────────────────────────────────

    def record_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "unknown",
    ) -> None:
        """Record token usage."""
        self.tokens_input.inc(input_tokens, labels={"model": model})
        self.tokens_output.inc(output_tokens, labels={"model": model})

        # Estimate cost (rough approximation)
        # Assumes ~$0.01 per 1K input, $0.03 per 1K output
        cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)
        self.estimated_cost.inc(cost)

    # ─────────────────────────────────────────────────────
    # Pipeline Methods
    # ─────────────────────────────────────────────────────

    def record_output(self, agent_id: str, fitness: float) -> None:
        """Record processed output."""
        self.outputs_processed.inc(labels={"agent": agent_id})
        self.fitness_scores.observe(fitness)

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits.inc()

    def record_fusion(self, method: str, input_count: int) -> None:
        """Record fusion operation."""
        self.fusions_performed.inc(labels={"method": method})

    # ─────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "agents": {
                "spawned": self.agent_spawned.get(),
                "stopped": self.agent_stopped.get(),
                "active": self.active_agents.get(),
                "response_time": self.agent_response_time.get_stats(),
            },
            "evolution": {
                "generations": self.generations_run.get(),
                "best_fitness": self.best_fitness.get(),
                "avg_fitness": self.avg_fitness.get(),
                "fitness_distribution": self.fitness_scores.get_stats(),
            },
            "tasks": {
                "submitted": self.tasks_submitted.get(),
                "completed": self.tasks_completed.get(),
                "failed": self.tasks_failed.get(),
                "duration": self.task_duration.get_stats(),
            },
            "tokens": {
                "input": self.tokens_input.get(),
                "output": self.tokens_output.get(),
                "estimated_cost_usd": self.estimated_cost.get(),
            },
            "pipeline": {
                "outputs": self.outputs_processed.get(),
                "cache_hits": self.cache_hits.get(),
                "fusions": self.fusions_performed.get(),
            },
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Metrics Instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_metrics: Optional[EATSMetrics] = None


def get_metrics() -> EATSMetrics:
    """Get global metrics instance."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = EATSMetrics()
    return _global_metrics
