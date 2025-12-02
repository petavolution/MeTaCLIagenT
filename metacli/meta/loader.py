"""
WorkflowLoader - Load Workflows from YAML/JSON

Transform MetaCLI from imperative (Python code) to declarative (YAML/JSON files).

Features:
- Load workflows from YAML/JSON files
- Support context variables
- Validate workflow structure
- Convert to Workflow objects

Example:
    from metacli.meta import WorkflowLoader

    # Load from YAML
    workflow = WorkflowLoader.from_yaml("workflows/audit-refactor.yaml")
    result = workflow.run(context={"target": "src/"})

    # Load from JSON
    workflow = WorkflowLoader.from_json("workflows/tdd.json")
    result = workflow.run()
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from ..core import (
    Workflow,
    PromptTemplate,
    DecisionEngine,
    Condition,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Schema Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowValidationError(Exception):
    """Raised when workflow definition is invalid."""
    pass


def validate_workflow_schema(data: Dict[str, Any]) -> None:
    """
    Validate workflow structure.

    Required fields:
    - name: string
    - steps: list of step definitions

    Optional fields:
    - version: string
    - description: string
    - context: dict
    - decisions: dict

    Raises:
        WorkflowValidationError: If schema is invalid
    """
    # Check required fields
    if "name" not in data:
        raise WorkflowValidationError("Workflow must have 'name' field")

    if "steps" not in data or not isinstance(data["steps"], list):
        raise WorkflowValidationError("Workflow must have 'steps' list")

    if len(data["steps"]) == 0:
        raise WorkflowValidationError("Workflow must have at least one step")

    # Validate steps
    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            raise WorkflowValidationError(f"Step {i} must be a dictionary")

        if "name" not in step:
            raise WorkflowValidationError(f"Step {i} must have 'name' field")

        if "agent" not in step:
            raise WorkflowValidationError(f"Step {i} ({step['name']}) must have 'agent' field")

        if "prompt" not in step:
            raise WorkflowValidationError(f"Step {i} ({step['name']}) must have 'prompt' field")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Decision Function Resolver
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def resolve_decision(decision_spec: str | Dict[str, Any]) -> Optional[Any]:
    """
    Resolve decision function from string name or dict spec.

    Args:
        decision_spec: Decision name or specification

    Returns:
        Decision function or None

    Example:
        # String name
        decision = resolve_decision("has_errors")

        # Dict spec
        decision = resolve_decision({
            "type": "max_iterations",
            "max": 3
        })
    """
    if isinstance(decision_spec, str):
        # Built-in decision by name
        return DecisionEngine.get_decision(decision_spec)

    elif isinstance(decision_spec, dict):
        decision_type = decision_spec.get("type")

        if decision_type == "max_iterations":
            from ..core.decision import max_iterations_decision
            return max_iterations_decision(decision_spec.get("max", 3))

        elif decision_type == "custom":
            # TODO: Support custom decision functions
            return None

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WorkflowLoader
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowLoader:
    """
    Load workflows from YAML/JSON files.

    Transforms declarative workflow definitions into executable Workflow objects.

    Example:
        loader = WorkflowLoader()
        workflow = loader.from_yaml("workflows/audit-refactor.yaml")
        result = workflow.run(context={"target": "src/"})
    """

    @classmethod
    def from_yaml(cls, filepath: str, **kwargs) -> Workflow:
        """
        Load workflow from YAML file.

        Args:
            filepath: Path to YAML file
            **kwargs: Additional context to merge

        Returns:
            Executable Workflow object

        Raises:
            WorkflowValidationError: If workflow definition is invalid

        Example:
            workflow = WorkflowLoader.from_yaml("audit-refactor.yaml")
            result = workflow.run(context={"target": "src/api.py"})
        """
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required for YAML support. "
                "Install with: pip install pyyaml"
            )

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Workflow file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        return cls._build_workflow(data, **kwargs)

    @classmethod
    def from_json(cls, filepath: str, **kwargs) -> Workflow:
        """
        Load workflow from JSON file.

        Args:
            filepath: Path to JSON file
            **kwargs: Additional context to merge

        Returns:
            Executable Workflow object

        Example:
            workflow = WorkflowLoader.from_json("tdd-cycle.json")
            result = workflow.run()
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Workflow file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = json.load(f)

        return cls._build_workflow(data, **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], **kwargs) -> Workflow:
        """
        Load workflow from dictionary.

        Args:
            data: Workflow definition dict
            **kwargs: Additional context to merge

        Returns:
            Executable Workflow object

        Example:
            workflow_def = {
                "name": "simple",
                "steps": [
                    {"name": "test", "agent": "python", "prompt": "print('hi')"}
                ]
            }
            workflow = WorkflowLoader.from_dict(workflow_def)
        """
        return cls._build_workflow(data, **kwargs)

    @classmethod
    def _build_workflow(cls, data: Dict[str, Any], **kwargs) -> Workflow:
        """
        Build Workflow object from parsed data.

        Args:
            data: Workflow definition dictionary
            **kwargs: Additional context

        Returns:
            Workflow object
        """
        # Validate schema
        validate_workflow_schema(data)

        # Create workflow
        workflow = Workflow(
            name=data["name"],
            auto_save=data.get("auto_save", True)
        )

        # Set metadata
        if "version" in data:
            workflow.metadata = {"version": data["version"]}
        if "description" in data:
            workflow.metadata = workflow.metadata or {}
            workflow.metadata["description"] = data["description"]

        # Initialize context
        if "context" in data:
            workflow.context.update(data["context"])
        workflow.context.update(kwargs)  # Override with kwargs

        # Add steps
        for step_def in data["steps"]:
            cls._add_step_from_def(workflow, step_def)

        return workflow

    @classmethod
    def _add_step_from_def(cls, workflow: Workflow, step_def: Dict[str, Any]) -> None:
        """
        Add a step to workflow from step definition.

        Args:
            workflow: Workflow to add step to
            step_def: Step definition dict
        """
        name = step_def["name"]
        agent = step_def["agent"]
        prompt = step_def["prompt"]

        # Convert prompt to template if it contains {{variables}}
        if "{{" in prompt and "}}" in prompt:
            prompt = PromptTemplate(prompt)

        # Parse optional fields
        use_previous = step_def.get("use_previous", False)
        condition = step_def.get("condition")
        timeout = step_def.get("timeout", 60.0)

        # Parse decision
        decision = None
        if "decision" in step_def:
            decision = resolve_decision(step_def["decision"])

        # Parse loop config
        loop_to = step_def.get("loop", {}).get("to") if isinstance(step_def.get("loop"), dict) else None
        loop_back_to = step_def.get("loop", {}).get("back_to") if isinstance(step_def.get("loop"), dict) else None
        max_iterations = step_def.get("loop", {}).get("max_iterations") if isinstance(step_def.get("loop"), dict) else None

        # Add step to workflow
        workflow.add_step(
            name=name,
            tool_name=agent,
            prompt=prompt,
            use_previous=use_previous,
            condition=condition,
            decision=decision,
            loop_to=loop_to,
            loop_back_to=loop_back_to,
            max_iterations=max_iterations,
            timeout=timeout,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_workflow(filepath: str, **context) -> Workflow:
    """
    Load workflow from file (auto-detects YAML/JSON).

    Args:
        filepath: Path to workflow file
        **context: Context variables

    Returns:
        Workflow object

    Example:
        workflow = load_workflow("audit.yaml", target="src/")
        result = workflow.run()
    """
    filepath = Path(filepath)

    if filepath.suffix in ['.yaml', '.yml']:
        return WorkflowLoader.from_yaml(filepath, **context)
    elif filepath.suffix == '.json':
        return WorkflowLoader.from_json(filepath, **context)
    else:
        raise ValueError(f"Unsupported file format: {filepath.suffix}")
