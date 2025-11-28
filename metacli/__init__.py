"""
MetaCLI: Layered Meta-Framework for CLI Tool Orchestration

A simple, powerful framework for orchestrating CLI tools (AI assistants,
POSIX utilities, custom scripts) with a clean layered architecture.

Layers:
    kernel   - Execution primitives (Process, I/O, Security)
    core     - Orchestration patterns (Sequence, Parser, Persistence)
    meta     - Declarative workflows (Playbooks, Templates, Events)
    autonomous - Advanced features (Evolution, Swarm, LLM-Judge)

Quick Start:
    # Layer 0: Raw process execution
    from metacli.kernel import Process
    proc = Process.spawn(["python", "-c", "print('hi')"])
    proc.start()
    output = proc.read()
    proc.terminate()

    # Layer 1: Simple orchestration (coming in Phase 2)
    from metacli.core import CLISequence
    seq = CLISequence("task")
    seq.add_step("claude-code", "Write API")
    seq.run()

Version: 2.0.0-alpha (Kernel Layer)
"""

__version__ = "2.0.0-alpha"
__author__ = "MetaCLI Contributors"

# Layer 0 exports (Kernel)
try:
    from .kernel import (
        Process,
        PTYProcess,
        SubProcess,
        TmuxProcess,
        Security,
        IOBuffer,
        setup_logging,
    )

    __all__ = [
        "Process",
        "PTYProcess",
        "SubProcess",
        "TmuxProcess",
        "Security",
        "IOBuffer",
        "setup_logging",
    ]
except ImportError:
    # Kernel not yet implemented
    __all__ = []
