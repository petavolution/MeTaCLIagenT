# EATS - Evolutionary Agent Tree System (Legacy v1.0)
"""
DEPRECATED: This is the legacy v1.0 implementation.

For new projects, use eats_core/ instead:
    from eats_core import SwarmController, AgentDNA, Evolution

This module is kept for backward compatibility and provides:
- GhostSwarm: Visual multi-terminal orchestration
- TmuxTransport: Enhanced tmux control

Migration guide:
    # Old (eats/)
    from eats.evolution_engine import EvolutionEngine
    from eats.manager import MetaManager

    # New (eats_core/)
    from eats_core import Evolution, SwarmController
"""

import warnings

warnings.warn(
    "eats module is deprecated. Use eats_core for new code: "
    "from eats_core import SwarmController, AgentDNA, Evolution",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = "1.0.0"
__status__ = "deprecated"

# Re-export key classes for backward compatibility
from .ghost_swarm import GhostSwarm
from .tmux_transport import TmuxTransport

__all__ = [
    "GhostSwarm",
    "TmuxTransport",
    "__version__",
    "__status__",
]
