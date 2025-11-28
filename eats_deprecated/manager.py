# manager.py
"""
MetaManager: Central registry and controller for all agent sessions.

The MetaManager is the "brain stem" of the system:
- Spawns agents from blueprints
- Tracks all running sessions
- Provides high-level API for orchestration
- Integrates with event bus for notifications
"""

import uuid
from typing import Dict, List, Optional

from .transport_pty import PTYTransport
from .agents import AgentSession
from .config_models import AgentBlueprint, EvolutionConfig
from .event_bus import EventBus, emit_agent_spawned, EventType, Event


class MetaManager:
    """
    Central registry & controller for all agent sessions.

    Responsibilities:
    - Spawn agents from blueprints using PTYTransport
    - Track all running sessions
    - Route prompts to agents
    - Emit events for UI/logging

    Usage:
        manager = MetaManager(default_cmd=["python", "-i", "-q"])
        session = manager.spawn_agent(blueprint)
        response = manager.send_prompt(session.id, "Hello!")
        manager.shutdown()
    """

    def __init__(
        self,
        default_cmd: List[str],
        event_bus: Optional[EventBus] = None,
        evo_config: Optional[EvolutionConfig] = None,
    ):
        self.default_cmd = default_cmd
        self.event_bus = event_bus or EventBus()
        self.evo_config = evo_config or EvolutionConfig()
        self._sessions: Dict[str, AgentSession] = {}
        self._blueprints: Dict[str, AgentBlueprint] = {}

    # ─────────────────────────────────────────────────────
    # Agent Lifecycle
    # ─────────────────────────────────────────────────────

    def spawn_agent(
        self,
        blueprint: Optional[AgentBlueprint] = None,
        role: str = "coder",
        cmd: Optional[List[str]] = None,
    ) -> AgentSession:
        """
        Spawn a new agent from a blueprint or with defaults.

        Args:
            blueprint: Optional blueprint to use
            role: Role name if no blueprint provided
            cmd: Optional override for CLI command

        Returns:
            The newly created AgentSession
        """
        # Create default blueprint if none provided
        if blueprint is None:
            blueprint = AgentBlueprint.create(
                role=role,
                system_prompt=f"You are a helpful {role} assistant.",
                cmd=cmd or self.default_cmd,
            )

        # Store blueprint
        self._blueprints[blueprint.id] = blueprint

        # Create transport
        effective_cmd = cmd or blueprint.cmd or self.default_cmd
        session_id = str(uuid.uuid4())
        transport = PTYTransport(
            cmd=effective_cmd,
            name=f"{blueprint.role}-{session_id[:8]}",
        )
        transport.start()

        # Create session
        session = AgentSession(
            id=session_id,
            blueprint=blueprint,
            transport=transport,
        )
        self._sessions[session_id] = session

        # Emit event
        emit_agent_spawned(
            self.event_bus,
            agent_id=session_id,
            role=blueprint.role,
            blueprint_id=blueprint.id,
        )

        return session

    def spawn_from_blueprint_id(self, blueprint_id: str) -> AgentSession:
        """Spawn a new agent from an existing blueprint by ID."""
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            raise KeyError(f"Blueprint {blueprint_id} not found")
        return self.spawn_agent(blueprint=blueprint)

    def terminate_agent(self, agent_id: str) -> None:
        """Terminate an agent by ID."""
        session = self._sessions.get(agent_id)
        if session:
            session.terminate()
            self.event_bus.publish(Event(
                type=EventType.AGENT_TERMINATED,
                payload={"agent_id": agent_id, "role": session.blueprint.role},
                source="manager",
            ))

    # ─────────────────────────────────────────────────────
    # Session Access
    # ─────────────────────────────────────────────────────

    def get_session(self, agent_id: str) -> AgentSession:
        """Get a session by ID. Raises KeyError if not found."""
        return self._sessions[agent_id]

    def list_sessions(self) -> List[AgentSession]:
        """List all active sessions."""
        return list(self._sessions.values())

    def list_sessions_by_role(self, role: str) -> List[AgentSession]:
        """List sessions filtered by role."""
        return [s for s in self._sessions.values() if s.blueprint.role == role]

    def get_blueprint(self, blueprint_id: str) -> AgentBlueprint:
        """Get a blueprint by ID."""
        return self._blueprints[blueprint_id]

    def list_blueprints(self) -> List[AgentBlueprint]:
        """List all registered blueprints."""
        return list(self._blueprints.values())

    def register_blueprint(self, blueprint: AgentBlueprint) -> None:
        """Register a blueprint without spawning."""
        self._blueprints[blueprint.id] = blueprint

    # ─────────────────────────────────────────────────────
    # Prompt Handling
    # ─────────────────────────────────────────────────────

    def send_prompt(
        self,
        agent_id: str,
        prompt: str,
        include_system_prompt: bool = False,
    ) -> str:
        """
        Send a prompt to an agent and return the response.

        Args:
            agent_id: The session ID
            prompt: The prompt text
            include_system_prompt: Whether to prepend the blueprint's system prompt

        Returns:
            The agent's response text
        """
        session = self.get_session(agent_id)
        response = session.send_prompt(
            prompt,
            max_turn_seconds=self.evo_config.max_turn_seconds,
            idle_gap_seconds=self.evo_config.idle_gap_seconds,
            include_system_prompt=include_system_prompt,
        )

        # Emit turn event
        self.event_bus.publish(Event(
            type=EventType.AGENT_TURN_COMPLETE,
            payload={
                "agent_id": agent_id,
                "prompt_preview": prompt[:100],
                "response_length": len(response),
            },
            source="manager",
        ))

        return response

    # ─────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Terminate all running agents and clean up."""
        for session in list(self._sessions.values()):
            try:
                session.terminate()
            except Exception as e:
                print(f"[MetaManager] Error terminating {session.id}: {e}")
        self._sessions.clear()

    def get_status(self) -> Dict:
        """Get overall system status."""
        return {
            "total_sessions": len(self._sessions),
            "total_blueprints": len(self._blueprints),
            "sessions_by_state": self._count_by_state(),
            "sessions_by_role": self._count_by_role(),
        }

    def _count_by_state(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for session in self._sessions.values():
            counts[session.state] = counts.get(session.state, 0) + 1
        return counts

    def _count_by_role(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for session in self._sessions.values():
            role = session.blueprint.role
            counts[role] = counts.get(role, 0) + 1
        return counts
