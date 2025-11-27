# config_models.py
"""
Configuration models for the Evolutionary Agent Tree System.

These dataclasses define the "DNA" of agents (AgentBlueprint),
task specifications (TaskSpec), and evolution parameters (EvolutionConfig).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid


@dataclass
class AgentBlueprint:
    """
    Immutable description of an agent type for evolution.

    This is what evolves:
    - system_prompt: The personality/instruction prompt
    - role: Semantic role (coder, tester, planner, etc.)
    - cmd: The CLI command to spawn this agent
    - temperature: LLM temperature parameter
    - extra_params: Additional model-specific parameters

    The blueprint is like DNA - it gets mutated and passed to offspring.
    """
    id: str
    role: str
    system_prompt: str
    cmd: List[str]
    temperature: float = 0.7
    extra_params: Dict[str, str] = field(default_factory=dict)
    parent_id: Optional[str] = None  # For lineage tracking
    generation: int = 0

    @classmethod
    def create(
        cls,
        role: str,
        system_prompt: str,
        cmd: List[str],
        temperature: float = 0.7,
        parent_id: Optional[str] = None,
        generation: int = 0,
    ) -> "AgentBlueprint":
        """Factory method with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            role=role,
            system_prompt=system_prompt,
            cmd=cmd,
            temperature=temperature,
            parent_id=parent_id,
            generation=generation,
        )

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "cmd": self.cmd,
            "temperature": self.temperature,
            "extra_params": self.extra_params,
            "parent_id": self.parent_id,
            "generation": self.generation,
        }


@dataclass
class TaskSpec:
    """
    Abstract description of a task for the multi-agent system.

    A task is the "environment" that agents are evaluated against.
    """
    id: str
    description: str
    input_data: Optional[str] = None
    expected_output: Optional[str] = None  # For fitness evaluation
    constraints: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 60.0

    @classmethod
    def create(
        cls,
        description: str,
        input_data: Optional[str] = None,
        expected_output: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ) -> "TaskSpec":
        """Factory method with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            description=description,
            input_data=input_data,
            expected_output=expected_output,
            timeout_seconds=timeout_seconds,
        )

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "constraints": self.constraints,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class EvolutionConfig:
    """
    Parameters controlling evolutionary cycles.

    These knobs control the genetic algorithm behavior.
    """
    population_size: int = 4          # Number of agents per generation
    top_k_survivors: int = 2          # How many survive to reproduce
    mutation_rate: float = 0.2        # Probability of mutation per gene
    prompt_mutation_strength: float = 0.1  # How much to perturb prompts
    temperature_mutation_range: float = 0.1  # Max temp change per mutation
    max_generations: int = 5          # Evolution iterations
    max_turn_seconds: float = 30.0    # Max time to wait for agent response
    idle_gap_seconds: float = 1.0     # Idle time to detect turn completion

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "population_size": self.population_size,
            "top_k_survivors": self.top_k_survivors,
            "mutation_rate": self.mutation_rate,
            "prompt_mutation_strength": self.prompt_mutation_strength,
            "temperature_mutation_range": self.temperature_mutation_range,
            "max_generations": self.max_generations,
            "max_turn_seconds": self.max_turn_seconds,
            "idle_gap_seconds": self.idle_gap_seconds,
        }


# ─────────────────────────────────────────────────────────
# Preset Blueprints for Common Roles
# ─────────────────────────────────────────────────────────

CODER_PROMPT = """You are a precise coding assistant running in a terminal.
When given a task, respond with clean, working code.
Include brief comments explaining key logic.
Always prioritize correctness and clarity."""

TESTER_PROMPT = """You are a meticulous testing assistant.
When given code, identify potential bugs, edge cases, and improvements.
Suggest specific test cases that would verify correctness.
Be thorough but concise."""

PLANNER_PROMPT = """You are a strategic planning assistant.
When given a complex task, break it down into clear, actionable steps.
Identify dependencies and potential blockers.
Output a numbered plan that can be executed sequentially."""

CRITIC_PROMPT = """You are a skeptical code reviewer.
Challenge assumptions and identify weaknesses in proposed solutions.
Look for security issues, performance problems, and maintainability concerns.
Be constructively critical."""


def create_default_blueprints(base_cmd: List[str]) -> Dict[str, AgentBlueprint]:
    """
    Create a set of default blueprints for common agent roles.

    Args:
        base_cmd: The CLI command to use (e.g., ["python", "-i", "-q"])

    Returns:
        Dictionary mapping role names to blueprints.
    """
    return {
        "coder": AgentBlueprint.create(
            role="coder",
            system_prompt=CODER_PROMPT,
            cmd=base_cmd,
            temperature=0.7,
        ),
        "tester": AgentBlueprint.create(
            role="tester",
            system_prompt=TESTER_PROMPT,
            cmd=base_cmd,
            temperature=0.5,
        ),
        "planner": AgentBlueprint.create(
            role="planner",
            system_prompt=PLANNER_PROMPT,
            cmd=base_cmd,
            temperature=0.6,
        ),
        "critic": AgentBlueprint.create(
            role="critic",
            system_prompt=CRITIC_PROMPT,
            cmd=base_cmd,
            temperature=0.4,
        ),
    }
