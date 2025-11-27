# agents.py
"""
Agent Session: High-level wrapper around terminal-driven LLM processes.

An AgentSession represents one running LLM CLI with:
- A conversation log (list of Turns)
- State tracking (idle/busy/error/terminated)
- Methods to send prompts and receive responses
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional

from .transport_pty import PTYTransport
from .config_models import AgentBlueprint


@dataclass
class Turn:
    """
    One interaction turn with an agent.

    A turn captures:
    - prompt: what we sent to the agent
    - response: what the agent printed back
    - timestamp: when the turn completed
    - duration_seconds: how long it took
    """
    timestamp: float
    prompt: str
    response: str
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "prompt": self.prompt,
            "response": self.response,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class AgentSession:
    """
    High-level representation of one running LLM CLI agent.

    Wraps a PTYTransport and provides:
    - send_prompt(): blocking call that waits for response
    - Conversation log tracking
    - State management

    Attributes:
        id: Unique session identifier
        blueprint: The AgentBlueprint this session was spawned from
        transport: Low-level PTY transport
        state: Current state (idle|busy|error|terminated)
        log: List of Turn objects
    """
    id: str
    blueprint: AgentBlueprint
    transport: PTYTransport
    state: str = "idle"
    log: List[Turn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def send_prompt(
        self,
        prompt: str,
        max_turn_seconds: float = 30.0,
        idle_gap_seconds: float = 1.0,
        include_system_prompt: bool = False,
    ) -> str:
        """
        Send a prompt to the agent and collect its response.

        Strategy:
        1. Optionally prepend system prompt
        2. Send prompt as a line
        3. Read output until idle (no new data for idle_gap_seconds)
        4. Log the turn and return response

        Args:
            prompt: The user/task prompt to send
            max_turn_seconds: Maximum time to wait for response
            idle_gap_seconds: Time without output to consider turn complete
            include_system_prompt: Whether to prepend blueprint's system prompt

        Returns:
            The agent's response text

        Raises:
            RuntimeError: If agent process is not alive
        """
        if not self.transport.is_alive():
            self.state = "error"
            raise RuntimeError(f"Agent {self.id} is not alive")

        self.state = "busy"
        start_time = time.time()

        # Build full prompt
        if include_system_prompt and self.blueprint.system_prompt:
            full_prompt = f"{self.blueprint.system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Clear any pending output before sending
        self.transport.recv_now()

        # Send the prompt
        self.transport.send_line(full_prompt)

        # Collect response until idle
        buffer = ""
        last_data_time = time.time()

        while time.time() - start_time < max_turn_seconds:
            chunk = self.transport.recv_now()
            if chunk:
                buffer += chunk
                last_data_time = time.time()
            else:
                if time.time() - last_data_time >= idle_gap_seconds:
                    break
            time.sleep(0.05)

        # Update state
        self.state = "idle" if self.transport.is_alive() else "terminated"

        # Record turn
        duration = time.time() - start_time
        turn = Turn(
            timestamp=time.time(),
            prompt=prompt,
            response=buffer,
            duration_seconds=duration,
        )
        self.log.append(turn)

        return buffer

    def send_confirmation(self, response: str = "y") -> str:
        """
        Send a simple confirmation (y/n) and collect brief response.

        Useful for handling interactive prompts like "Apply changes? [y/N]"
        """
        if not self.transport.is_alive():
            self.state = "error"
            raise RuntimeError(f"Agent {self.id} is not alive")

        self.transport.send_line(response)
        time.sleep(0.5)
        return self.transport.recv_now()

    def last_output(self, max_chars: int = 2000) -> str:
        """
        Get a snippet of the most recent response.

        Useful for UI status displays.
        """
        if not self.log:
            return ""
        return self.log[-1].response[-max_chars:]

    def last_turn(self) -> Optional[Turn]:
        """Get the most recent turn, or None if no turns yet."""
        return self.log[-1] if self.log else None

    def get_full_transcript(self) -> str:
        """
        Get the full conversation transcript.

        Returns formatted string of all turns.
        """
        lines = []
        for i, turn in enumerate(self.log):
            lines.append(f"=== Turn {i+1} ===")
            lines.append(f"[PROMPT] {turn.prompt}")
            lines.append(f"[RESPONSE] {turn.response}")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize session to dictionary."""
        return {
            "id": self.id,
            "blueprint_id": self.blueprint.id,
            "role": self.blueprint.role,
            "state": self.state,
            "created_at": self.created_at,
            "turn_count": len(self.log),
            "last_output": self.last_output(500),
        }

    def terminate(self) -> None:
        """Terminate the agent's process."""
        self.state = "terminated"
        self.transport.terminate()
