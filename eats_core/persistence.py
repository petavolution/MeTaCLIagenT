# persistence.py - State Persistence Layer
"""
Save and load system state for:
- Swarm configuration
- Evolution history
- Agent DNA library
- Pipeline results
- Workflow definitions

Supports:
- JSON file storage
- In-memory cache
- Optional SQLite for larger datasets
"""

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Type, TypeVar
from pathlib import Path
import hashlib

from .core import AgentDNA


T = TypeVar('T')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Storage Interface
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Storage:
    """Abstract storage interface."""

    def save(self, key: str, data: Any) -> None:
        raise NotImplementedError

    def load(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def list_keys(self, prefix: str = "") -> List[str]:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Memory Storage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MemoryStorage(Storage):
    """In-memory storage (non-persistent)."""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    def save(self, key: str, data: Any) -> None:
        self._data[key] = data

    def load(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    def list_keys(self, prefix: str = "") -> List[str]:
        return [k for k in self._data.keys() if k.startswith(prefix)]

    def exists(self, key: str) -> bool:
        return key in self._data

    def clear(self) -> None:
        self._data.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# File Storage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FileStorage(Storage):
    """JSON file-based storage."""

    def __init__(self, base_dir: str = ".eats_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        """Convert key to file path."""
        # Sanitize key for filesystem
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_key}.json"

    def save(self, key: str, data: Any) -> None:
        path = self._key_to_path(key)

        # Handle dataclasses
        if hasattr(data, '__dataclass_fields__'):
            data = asdict(data)

        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load(self, key: str) -> Optional[Any]:
        path = self._key_to_path(key)
        if not path.exists():
            return None

        with open(path, 'r') as f:
            return json.load(f)

    def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_keys(self, prefix: str = "") -> List[str]:
        keys = []
        for path in self.base_dir.glob("*.json"):
            key = path.stem
            if key.startswith(prefix):
                keys.append(key)
        return keys

    def exists(self, key: str) -> bool:
        return self._key_to_path(key).exists()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# State Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Snapshot:
    """Point-in-time snapshot of system state."""
    id: str
    timestamp: float
    swarm_state: Optional[Dict] = None
    evolution_state: Optional[Dict] = None
    pipeline_state: Optional[Dict] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "swarm_state": self.swarm_state,
            "evolution_state": self.evolution_state,
            "pipeline_state": self.pipeline_state,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, d: Dict) -> Snapshot:
        return cls(
            id=d["id"],
            timestamp=d["timestamp"],
            swarm_state=d.get("swarm_state"),
            evolution_state=d.get("evolution_state"),
            pipeline_state=d.get("pipeline_state"),
            metadata=d.get("metadata"),
        )


class StateManager:
    """
    Manages persistence of EATS system state.

    Usage:
        manager = StateManager()

        # Save current state
        manager.save_swarm("my_swarm", swarm.to_dict())

        # Load state
        state = manager.load_swarm("my_swarm")

        # Create snapshot
        snapshot = manager.create_snapshot(swarm, evolution, pipeline)
        manager.save_snapshot(snapshot)

        # Restore from snapshot
        snapshot = manager.load_snapshot(snapshot_id)
    """

    def __init__(
        self,
        storage: Optional[Storage] = None,
        auto_snapshot: bool = False,
        snapshot_interval: int = 300,  # seconds
    ):
        self.storage = storage or FileStorage()
        self.auto_snapshot = auto_snapshot
        self.snapshot_interval = snapshot_interval
        self._last_snapshot = 0.0

    # ─────────────────────────────────────────────────────
    # DNA Library
    # ─────────────────────────────────────────────────────

    def save_dna(self, dna: AgentDNA, name: Optional[str] = None) -> str:
        """Save agent DNA to library."""
        key = f"dna/{name or dna.id}"
        # Save full data, not the truncated to_dict() version
        full_data = {
            "id": dna.id,
            "role": dna.role,
            "system_prompt": dna.system_prompt,  # Full prompt, not truncated
            "cmd": dna.cmd,
            "temperature": dna.temperature,
            "max_tokens": dna.max_tokens,
            "timeout": dna.timeout,
            "parent_id": dna.parent_id,
            "generation": dna.generation,
            "fitness_history": dna.fitness_history,
        }
        self.storage.save(key, full_data)
        return key

    def load_dna(self, name: str) -> Optional[AgentDNA]:
        """Load agent DNA from library."""
        data = self.storage.load(f"dna/{name}")
        if data:
            # Filter to only valid AgentDNA constructor fields
            valid_fields = {
                'id', 'role', 'system_prompt', 'cmd', 'temperature',
                'max_tokens', 'timeout', 'parent_id', 'generation', 'fitness_history'
            }
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return AgentDNA(**filtered)
        return None

    def list_dna(self) -> List[str]:
        """List all saved DNA."""
        keys = self.storage.list_keys("dna/")
        return [k.replace("dna/", "") for k in keys]

    def delete_dna(self, name: str) -> bool:
        """Delete DNA from library."""
        return self.storage.delete(f"dna/{name}")

    # ─────────────────────────────────────────────────────
    # Swarm State
    # ─────────────────────────────────────────────────────

    def save_swarm(self, name: str, state: Dict) -> None:
        """Save swarm state."""
        self.storage.save(f"swarm/{name}", {
            "state": state,
            "saved_at": time.time(),
        })

    def load_swarm(self, name: str) -> Optional[Dict]:
        """Load swarm state."""
        data = self.storage.load(f"swarm/{name}")
        return data.get("state") if data else None

    def list_swarms(self) -> List[str]:
        """List saved swarms."""
        keys = self.storage.list_keys("swarm/")
        return [k.replace("swarm/", "") for k in keys]

    # ─────────────────────────────────────────────────────
    # Evolution History
    # ─────────────────────────────────────────────────────

    def save_evolution(self, name: str, history: List[Dict]) -> None:
        """Save evolution history."""
        self.storage.save(f"evolution/{name}", {
            "history": history,
            "saved_at": time.time(),
        })

    def load_evolution(self, name: str) -> Optional[List[Dict]]:
        """Load evolution history."""
        data = self.storage.load(f"evolution/{name}")
        return data.get("history") if data else None

    def append_evolution(self, name: str, generation_result: Dict) -> None:
        """Append to existing evolution history."""
        history = self.load_evolution(name) or []
        history.append(generation_result)
        self.save_evolution(name, history)

    # ─────────────────────────────────────────────────────
    # Pipeline Results
    # ─────────────────────────────────────────────────────

    def save_pipeline(self, name: str, state: Dict) -> None:
        """Save pipeline state."""
        self.storage.save(f"pipeline/{name}", {
            "state": state,
            "saved_at": time.time(),
        })

    def load_pipeline(self, name: str) -> Optional[Dict]:
        """Load pipeline state."""
        data = self.storage.load(f"pipeline/{name}")
        return data.get("state") if data else None

    # ─────────────────────────────────────────────────────
    # Snapshots
    # ─────────────────────────────────────────────────────

    def create_snapshot(
        self,
        swarm_state: Optional[Dict] = None,
        evolution_state: Optional[Dict] = None,
        pipeline_state: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> Snapshot:
        """Create a new snapshot."""
        snapshot_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

        return Snapshot(
            id=snapshot_id,
            timestamp=time.time(),
            swarm_state=swarm_state,
            evolution_state=evolution_state,
            pipeline_state=pipeline_state,
            metadata=metadata,
        )

    def save_snapshot(self, snapshot: Snapshot) -> str:
        """Save snapshot to storage."""
        key = f"snapshot/{snapshot.id}"
        self.storage.save(key, snapshot.to_dict())
        self._last_snapshot = time.time()
        return key

    def load_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Load snapshot from storage."""
        data = self.storage.load(f"snapshot/{snapshot_id}")
        if data:
            return Snapshot.from_dict(data)
        return None

    def list_snapshots(self) -> List[Dict]:
        """List all snapshots with metadata."""
        keys = self.storage.list_keys("snapshot/")
        snapshots = []
        for key in keys:
            data = self.storage.load(key)
            if data:
                snapshots.append({
                    "id": data["id"],
                    "timestamp": data["timestamp"],
                    "metadata": data.get("metadata", {}),
                })
        return sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)

    def get_latest_snapshot(self) -> Optional[Snapshot]:
        """Get the most recent snapshot."""
        snapshots = self.list_snapshots()
        if snapshots:
            return self.load_snapshot(snapshots[0]["id"])
        return None

    def should_snapshot(self) -> bool:
        """Check if auto-snapshot should trigger."""
        if not self.auto_snapshot:
            return False
        return time.time() - self._last_snapshot > self.snapshot_interval

    # ─────────────────────────────────────────────────────
    # Export/Import
    # ─────────────────────────────────────────────────────

    def export_all(self, output_path: str) -> None:
        """Export all data to a single JSON file."""
        export_data = {
            "version": "2.0",
            "exported_at": time.time(),
            "dna": {},
            "swarms": {},
            "evolutions": {},
            "pipelines": {},
            "snapshots": {},
        }

        # Collect all data
        for name in self.list_dna():
            data = self.storage.load(f"dna/{name}")
            if data:
                export_data["dna"][name] = data

        for name in self.list_swarms():
            data = self.storage.load(f"swarm/{name}")
            if data:
                export_data["swarms"][name] = data

        for key in self.storage.list_keys("evolution/"):
            name = key.replace("evolution/", "")
            data = self.storage.load(key)
            if data:
                export_data["evolutions"][name] = data

        for key in self.storage.list_keys("pipeline/"):
            name = key.replace("pipeline/", "")
            data = self.storage.load(key)
            if data:
                export_data["pipelines"][name] = data

        for key in self.storage.list_keys("snapshot/"):
            name = key.replace("snapshot/", "")
            data = self.storage.load(key)
            if data:
                export_data["snapshots"][name] = data

        # Write to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

    def import_all(self, input_path: str, overwrite: bool = False) -> Dict[str, int]:
        """Import data from export file."""
        with open(input_path, 'r') as f:
            data = json.load(f)

        counts = {"dna": 0, "swarms": 0, "evolutions": 0, "pipelines": 0, "snapshots": 0}

        # Import DNA
        for name, dna_data in data.get("dna", {}).items():
            key = f"dna/{name}"
            if overwrite or not self.storage.exists(key):
                self.storage.save(key, dna_data)
                counts["dna"] += 1

        # Import swarms
        for name, swarm_data in data.get("swarms", {}).items():
            key = f"swarm/{name}"
            if overwrite or not self.storage.exists(key):
                self.storage.save(key, swarm_data)
                counts["swarms"] += 1

        # Import evolutions
        for name, evo_data in data.get("evolutions", {}).items():
            key = f"evolution/{name}"
            if overwrite or not self.storage.exists(key):
                self.storage.save(key, evo_data)
                counts["evolutions"] += 1

        # Import pipelines
        for name, pipe_data in data.get("pipelines", {}).items():
            key = f"pipeline/{name}"
            if overwrite or not self.storage.exists(key):
                self.storage.save(key, pipe_data)
                counts["pipelines"] += 1

        # Import snapshots
        for name, snap_data in data.get("snapshots", {}).items():
            key = f"snapshot/{name}"
            if overwrite or not self.storage.exists(key):
                self.storage.save(key, snap_data)
                counts["snapshots"] += 1

        return counts


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global State Manager
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get global state manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = StateManager()
    return _global_manager


def save(key: str, data: Any) -> None:
    """Save data to global storage."""
    get_state_manager().storage.save(key, data)


def load(key: str) -> Optional[Any]:
    """Load data from global storage."""
    return get_state_manager().storage.load(key)
