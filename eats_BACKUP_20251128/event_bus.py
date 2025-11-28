# event_bus.py
"""
Event Bus: Simple pub/sub system for internal event streaming.

Events flow from:
- EvolutionEngine (generation complete, fitness evaluated)
- MetaManager (agent spawned, terminated)
- Orchestrator (task started, completed)

To:
- Web UI (via WebSocket/SSE)
- Logging systems
- Human review interfaces
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import threading
import queue


class EventType(str, Enum):
    """Standard event types in the system."""
    # Agent lifecycle
    AGENT_SPAWNED = "agent_spawned"
    AGENT_TERMINATED = "agent_terminated"
    AGENT_STATE_CHANGED = "agent_state_changed"
    AGENT_TURN_COMPLETE = "agent_turn_complete"

    # Evolution events
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETE = "generation_complete"
    FITNESS_EVALUATED = "fitness_evaluated"
    MUTATION_APPLIED = "mutation_applied"
    SELECTION_COMPLETE = "selection_complete"

    # Task events
    TASK_REGISTERED = "task_registered"
    TASK_STARTED = "task_started"
    TASK_COMPLETE = "task_complete"

    # System events
    SYSTEM_ERROR = "system_error"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


@dataclass
class Event:
    """
    A single event in the system.

    Attributes:
        type: The event type (from EventType enum or custom string)
        payload: Event-specific data
        timestamp: When the event occurred
        source: Optional identifier of what generated the event
    """
    type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
        }


Subscriber = Callable[[Event], None]


class EventBus:
    """
    Simple in-process pub/sub event bus.

    Thread-safe implementation that allows:
    - Publishing events from any thread
    - Subscribing callbacks (called synchronously)
    - Optional async queue for web clients

    Usage:
        bus = EventBus()
        bus.subscribe(lambda e: print(e))
        bus.publish(Event(type="test", payload={"msg": "hello"}))
    """

    def __init__(self, max_history: int = 100):
        self._subscribers: List[Subscriber] = []
        self._type_subscribers: Dict[str, List[Subscriber]] = {}
        self._lock = threading.Lock()
        self._history: List[Event] = []
        self._max_history = max_history
        self._async_queue: Optional[queue.Queue] = None

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Thread-safe. Subscribers are called synchronously.
        """
        with self._lock:
            # Store in history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Copy subscriber lists to avoid issues during iteration
            all_subs = list(self._subscribers)
            type_subs = list(self._type_subscribers.get(event.type, []))

            # Add to async queue if enabled
            if self._async_queue is not None:
                try:
                    self._async_queue.put_nowait(event)
                except queue.Full:
                    pass  # Drop event if queue is full

        # Call subscribers outside lock
        for sub in all_subs:
            try:
                sub(event)
            except Exception as e:
                print(f"[EventBus] Subscriber error: {e}")

        for sub in type_subs:
            try:
                sub(event)
            except Exception as e:
                print(f"[EventBus] Type subscriber error: {e}")

    def subscribe(self, callback: Subscriber) -> None:
        """Subscribe to all events."""
        with self._lock:
            self._subscribers.append(callback)

    def subscribe_type(self, event_type: str, callback: Subscriber) -> None:
        """Subscribe to events of a specific type."""
        with self._lock:
            if event_type not in self._type_subscribers:
                self._type_subscribers[event_type] = []
            self._type_subscribers[event_type].append(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        """Unsubscribe from all events."""
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s is not callback]
            for type_subs in self._type_subscribers.values():
                type_subs[:] = [s for s in type_subs if s is not callback]

    def get_history(self, count: int = 50, event_type: Optional[str] = None) -> List[Event]:
        """
        Get recent event history.

        Args:
            count: Maximum number of events to return
            event_type: Optional filter by event type

        Returns:
            List of recent events (newest last)
        """
        with self._lock:
            if event_type:
                filtered = [e for e in self._history if e.type == event_type]
                return filtered[-count:]
            return self._history[-count:]

    def enable_async_queue(self, maxsize: int = 100) -> queue.Queue:
        """
        Enable async queue for web clients.

        Returns a Queue that receives all events.
        Useful for SSE/WebSocket streaming.
        """
        with self._lock:
            self._async_queue = queue.Queue(maxsize=maxsize)
        return self._async_queue

    def clear_history(self) -> None:
        """Clear event history."""
        with self._lock:
            self._history.clear()


# ─────────────────────────────────────────────────────────
# Convenience functions for common events
# ─────────────────────────────────────────────────────────

def emit_agent_spawned(bus: EventBus, agent_id: str, role: str, blueprint_id: str) -> None:
    """Emit an agent spawned event."""
    bus.publish(Event(
        type=EventType.AGENT_SPAWNED,
        payload={
            "agent_id": agent_id,
            "role": role,
            "blueprint_id": blueprint_id,
        },
        source="manager",
    ))


def emit_agent_turn(bus: EventBus, agent_id: str, prompt: str, response_preview: str) -> None:
    """Emit an agent turn complete event."""
    bus.publish(Event(
        type=EventType.AGENT_TURN_COMPLETE,
        payload={
            "agent_id": agent_id,
            "prompt_preview": prompt[:100],
            "response_preview": response_preview[:200],
        },
        source="agent",
    ))


def emit_generation_complete(
    bus: EventBus,
    generation: int,
    population_size: int,
    best_fitness: float,
    avg_fitness: float,
) -> None:
    """Emit a generation complete event."""
    bus.publish(Event(
        type=EventType.GENERATION_COMPLETE,
        payload={
            "generation": generation,
            "population_size": population_size,
            "best_fitness": best_fitness,
            "avg_fitness": avg_fitness,
        },
        source="evolution",
    ))
