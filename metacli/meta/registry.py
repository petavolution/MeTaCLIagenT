"""
WorkflowRegistry - Manage Reusable Workflows

Store, version, and retrieve workflows by name.

Features:
- Register workflows from files or objects
- Load workflows by name
- Version management
- Local workflow library
- Search and discovery

Example:
    from metacli.meta import WorkflowRegistry

    # Create registry
    registry = WorkflowRegistry()

    # Register workflow
    registry.register("audit-refactor", "workflows/audit-refactor.yaml")

    # Use by name
    workflow = registry.get("audit-refactor")
    result = workflow.run(context={"target": "src/"})

    # List available
    workflows = registry.list()
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from .loader import WorkflowLoader, load_workflow
from ..core import Workflow


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WorkflowRegistry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowRegistry:
    """
    Registry for managing reusable workflows.

    Stores workflows by name and provides discovery/retrieval.

    Example:
        registry = WorkflowRegistry()
        registry.register("audit", "./workflows/audit.yaml")

        workflow = registry.get("audit")
        workflow.run(context={"target": "src/"})
    """

    def __init__(self, registry_dir: str = ".metacli/workflows"):
        """
        Initialize registry.

        Args:
            registry_dir: Directory to store registry data
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.registry_dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load workflow index from disk."""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self) -> None:
        """Save workflow index to disk."""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)

    def register(
        self,
        name: str,
        source: str | Dict[str, Any],
        version: str = "1.0.0",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Register a workflow.

        Args:
            name: Unique workflow name
            source: Path to workflow file or workflow dict
            version: Semantic version
            description: Workflow description
            tags: Tags for discovery

        Example:
            registry.register(
                "audit-refactor",
                "./workflows/audit-refactor.yaml",
                version="2.0.0",
                description="Iterative code audit and refactoring",
                tags=["audit", "refactor", "python"]
            )
        """
        # Parse source
        if isinstance(source, str):
            source_path = Path(source)
            if not source_path.exists():
                raise FileNotFoundError(f"Workflow file not found: {source}")

            # Copy to registry
            target_path = self.registry_dir / f"{name}.yaml"
            import shutil
            shutil.copy(source_path, target_path)

            source_type = "file"
            source_location = str(target_path)

        elif isinstance(source, dict):
            # Save dict as JSON
            target_path = self.registry_dir / f"{name}.json"
            with open(target_path, 'w') as f:
                json.dump(source, f, indent=2)

            source_type = "dict"
            source_location = str(target_path)

        else:
            raise ValueError(f"Invalid source type: {type(source)}")

        # Add to index
        self.index[name] = {
            "name": name,
            "version": version,
            "description": description,
            "tags": tags or [],
            "source_type": source_type,
            "source_location": source_location,
        }

        self._save_index()

    def get(self, name: str, **context) -> Workflow:
        """
        Get workflow by name.

        Args:
            name: Workflow name
            **context: Context variables to pass to workflow

        Returns:
            Loaded Workflow object

        Raises:
            KeyError: If workflow not found

        Example:
            workflow = registry.get("audit-refactor", target="src/api.py")
            result = workflow.run()
        """
        if name not in self.index:
            raise KeyError(f"Workflow not found: {name}")

        entry = self.index[name]
        source_location = entry["source_location"]

        # Load workflow
        workflow = load_workflow(source_location, **context)

        return workflow

    def list(self, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List registered workflows.

        Args:
            tags: Optional tags to filter by

        Returns:
            List of workflow metadata dicts

        Example:
            # All workflows
            all_workflows = registry.list()

            # Filtered by tags
            audit_workflows = registry.list(tags=["audit"])
        """
        workflows = list(self.index.values())

        if tags:
            workflows = [
                w for w in workflows
                if any(tag in w.get("tags", []) for tag in tags)
            ]

        return workflows

    def remove(self, name: str) -> None:
        """
        Remove workflow from registry.

        Args:
            name: Workflow name to remove

        Example:
            registry.remove("old-workflow")
        """
        if name not in self.index:
            raise KeyError(f"Workflow not found: {name}")

        entry = self.index[name]
        source_location = Path(entry["source_location"])

        # Remove file
        if source_location.exists():
            source_location.unlink()

        # Remove from index
        del self.index[name]
        self._save_index()

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search workflows by name or description.

        Args:
            query: Search query
            tags: Optional tags to filter by

        Returns:
            List of matching workflow metadata

        Example:
            results = registry.search("audit", tags=["python"])
        """
        query_lower = query.lower()
        workflows = self.list(tags=tags)

        results = []
        for w in workflows:
            name_match = query_lower in w["name"].lower()
            desc_match = query_lower in (w.get("description") or "").lower()

            if name_match or desc_match:
                results.append(w)

        return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_registry: Optional[WorkflowRegistry] = None


def get_registry() -> WorkflowRegistry:
    """
    Get global workflow registry.

    Returns:
        Global WorkflowRegistry instance

    Example:
        from metacli.meta import get_registry

        registry = get_registry()
        registry.register("my-workflow", "./workflow.yaml")
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = WorkflowRegistry()
    return _global_registry
