# events.py - Event System for Real-time Pub/Sub
"""
Async event system for EATS real-time updates.

Features:
- Type-safe event definitions
- Async pub/sub with multiple subscribers
- Event filtering and routing
- Event history/replay
- SSE streaming support
"""

from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Awaitable, Set
from enum import Enum, auto
from collections import deque
import json


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventType(str, Enum):
    """All event types in the system."""
    # Agent lifecycle
    AGENT_SPAWNED = "agent.spawned"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # Task execution
    TASK_SUBMITTED = "task.submitted"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Evolution
    GENERATION_STARTED = "evolution.generation_started"
    GENERATION_COMPLETED = "evolution.generation_completed"
    FITNESS_EVALUATED = "evolution.fitness_evaluated"
    MUTATION_APPLIED = "evolution.mutation_applied"
    SELECTION_COMPLETE = "evolution.selection_complete"
    EVOLUTION_COMPLETE = "evolution.complete"

    # Swarm
    SWARM_INITIALIZED = "swarm.initialized"
    NODE_CREATED = "swarm.node_created"
    NODE_PRUNED = "swarm.node_pruned"
    BRANCH_UPDATED = "swarm.branch_updated"

    # Pipeline
    OUTPUT_ADDED = "pipeline.output_added"
    OUTPUT_FUSED = "pipeline.output_fused"
    CACHE_HIT = "pipeline.cache_hit"

    # System
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    METRICS_UPDATE = "system.metrics"

    # Custom/wildcard
    CUSTOM = "custom"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Event:
    """
    An event in the system.

    Attributes:
        type: Event type from EventType enum
        data: Event payload (any JSON-serializable dict)
        source: Source component (e.g., "swarm", "evolution")
        id: Unique event ID
        timestamp: Unix timestamp
        correlation_id: Optional ID linking related events
    """
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """Format for Server-Sent Events."""
        return f"id: {self.id}\nevent: {self.type.value}\ndata: {json.dumps(self.data)}\n\n"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Event:
        return cls(
            type=EventType(d["type"]),
            data=d.get("data", {}),
            source=d.get("source", "system"),
            id=d.get("id", str(uuid.uuid4())[:8]),
            timestamp=d.get("timestamp", time.time()),
            correlation_id=d.get("correlation_id"),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Bus
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Handler type
EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Async pub/sub event bus.

    Supports:
    - Subscribe to specific event types
    - Subscribe to all events (wildcard)
    - Event history for replay
    - Async and sync handlers

    Usage:
        bus = EventBus()

        async def handler(event):
            print(f"Got event: {event.type}")

        bus.subscribe(EventType.AGENT_SPAWNED, handler)
        await bus.publish(Event(type=EventType.AGENT_SPAWNED, data={"id": "123"}))
    """

    def __init__(
        self,
        history_size: int = 1000,
        enable_history: bool = True,
    ):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._history: deque[Event] = deque(maxlen=history_size)
        self._enable_history = enable_history
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> Callable[[], None]:
        """
        Subscribe to a specific event type.

        Returns unsubscribe function.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

        def unsubscribe():
            if event_type in self._handlers:
                self._handlers[event_type].remove(handler)

        return unsubscribe

    def subscribe_all(self, handler: EventHandler) -> Callable[[], None]:
        """Subscribe to all events (wildcard)."""
        self._wildcard_handlers.append(handler)

        def unsubscribe():
            self._wildcard_handlers.remove(handler)

        return unsubscribe

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            if self._enable_history:
                self._history.append(event)

        # Get handlers
        handlers = list(self._wildcard_handlers)
        if event.type in self._handlers:
            handlers.extend(self._handlers[event.type])

        # Call all handlers concurrently
        if handlers:
            await asyncio.gather(
                *[self._safe_call(h, event) for h in handlers],
                return_exceptions=True,
            )

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Call handler with error protection."""
        try:
            await handler(event)
        except Exception as e:
            # Log but don't propagate
            print(f"Event handler error: {e}")

    def emit(self, event: Event) -> None:
        """Sync emit - schedules async publish."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event))
        except RuntimeError:
            # No running loop - store in history only
            if self._enable_history:
                self._history.append(event)

    def emit_simple(
        self,
        event_type: EventType,
        data: Optional[Dict] = None,
        source: str = "system",
    ) -> None:
        """Emit with simple interface."""
        self.emit(Event(type=event_type, data=data or {}, source=source))

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        since: Optional[float] = None,
    ) -> List[Event]:
        """Get event history with optional filtering."""
        events = list(self._history)

        if event_type:
            events = [e for e in events if e.type == event_type]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Stream (SSE Support)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventStream:
    """
    Async event stream for Server-Sent Events.

    Usage:
        stream = EventStream(bus)

        # In FastAPI:
        @app.get("/events")
        async def events():
            return StreamingResponse(
                stream.generate(),
                media_type="text/event-stream",
            )
    """

    def __init__(
        self,
        bus: EventBus,
        event_types: Optional[List[EventType]] = None,
    ):
        self.bus = bus
        self.event_types = set(event_types) if event_types else None
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._active = False
        self._unsubscribe: Optional[Callable] = None

    async def start(self) -> None:
        """Start listening to events."""
        if self._active:
            return

        async def handler(event: Event):
            if self.event_types is None or event.type in self.event_types:
                await self._queue.put(event)

        self._unsubscribe = self.bus.subscribe_all(handler)
        self._active = True

    async def stop(self) -> None:
        """Stop listening."""
        if self._unsubscribe:
            self._unsubscribe()
        self._active = False

    async def generate(self):
        """
        Async generator for SSE streaming.

        Yields SSE-formatted event strings.
        """
        await self.start()

        try:
            while self._active:
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=30.0,
                    )
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        finally:
            await self.stop()

    async def next_event(self, timeout: float = 30.0) -> Optional[Event]:
        """Get next event from stream."""
        if not self._active:
            await self.start()

        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event-Enabled Mixin
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventEmitter:
    """
    Mixin class for components that emit events.

    Usage:
        class MyComponent(EventEmitter):
            def do_something(self):
                self.emit(EventType.CUSTOM, {"action": "something"})
    """

    _bus: Optional[EventBus] = None

    def set_event_bus(self, bus: EventBus) -> None:
        """Set the event bus for this emitter."""
        self._bus = bus

    def emit(
        self,
        event_type: EventType,
        data: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Emit an event."""
        if self._bus:
            event = Event(
                type=event_type,
                data=data or {},
                source=self.__class__.__name__,
                correlation_id=correlation_id,
            )
            self._bus.emit(event)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Event Bus (Singleton)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def emit(
    event_type: EventType,
    data: Optional[Dict] = None,
    source: str = "system",
) -> None:
    """Emit event to global bus."""
    get_event_bus().emit_simple(event_type, data, source)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Event Decorators
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def on_event(event_type: EventType):
    """
    Decorator to register a function as event handler.

    Usage:
        @on_event(EventType.AGENT_SPAWNED)
        async def handle_spawn(event):
            print(f"Agent spawned: {event.data}")
    """
    def decorator(func: EventHandler):
        get_event_bus().subscribe(event_type, func)
        return func
    return decorator


def emits(event_type: EventType, extract_data: Optional[Callable] = None):
    """
    Decorator that emits event after function completes.

    Usage:
        @emits(EventType.TASK_COMPLETED)
        async def run_task(task_id):
            return {"result": "done"}
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            data = {}
            if extract_data:
                data = extract_data(result, *args, **kwargs)
            elif isinstance(result, dict):
                data = result

            emit(event_type, data, source=func.__name__)
            return result

        return wrapper
    return decorator
