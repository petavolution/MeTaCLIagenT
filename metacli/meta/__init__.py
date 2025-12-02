"""
MetaCLI Meta Layer - Declarative Workflows

Transform from imperative (Python code) to declarative (YAML/JSON files).

Components:
- WorkflowLoader: Load workflows from YAML/JSON
- WorkflowRegistry: Manage reusable workflows
- load_workflow: Convenience function

Examples:
    # Load from YAML
    from metacli.meta import WorkflowLoader

    workflow = WorkflowLoader.from_yaml("audit-refactor.yaml")
    result = workflow.run(context={"target": "src/"})

    # Use registry
    from metacli.meta import get_registry

    registry = get_registry()
    registry.register("audit", "./workflows/audit.yaml")

    workflow = registry.get("audit")
    result = workflow.run(context={"target": "src/"})
"""

# Loader
from .loader import (
    WorkflowLoader,
    WorkflowValidationError,
    load_workflow,
)

# Registry
from .registry import (
    WorkflowRegistry,
    get_registry,
)

__all__ = [
    # Loader
    "WorkflowLoader",
    "WorkflowValidationError",
    "load_workflow",

    # Registry
    "WorkflowRegistry",
    "get_registry",
]

__version__ = "2.0.0-alpha"
