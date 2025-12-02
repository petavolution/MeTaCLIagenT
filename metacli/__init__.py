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

    # Layer 1: Orchestration
    from metacli.core import CLISequence
    seq = CLISequence("code-review")
    seq.add_step("claude-code", "Write API")
    seq.add_step("aider", "Fix bugs", use_previous=True)
    result = seq.run()
    seq.cleanup()

Version: 2.0.0-alpha (Kernel + Core Layers)
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
        ProcessError,
        SecurityError,
    )
    KERNEL_AVAILABLE = True
except ImportError:
    KERNEL_AVAILABLE = False

# Layer 1 exports (Core)
try:
    from .core import (
        CLISequence,
        SequenceStep,
        OutputParser,
        Persistence,
        get_persistence,
        run_sequence,
        quick_chain,
    )
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

# Build __all__
__all__ = []

if KERNEL_AVAILABLE:
    __all__.extend([
        "Process",
        "PTYProcess",
        "SubProcess",
        "TmuxProcess",
        "Security",
        "ProcessError",
        "SecurityError",
    ])

if CORE_AVAILABLE:
    __all__.extend([
        "CLISequence",
        "SequenceStep",
        "OutputParser",
        "Persistence",
        "get_persistence",
        "run_sequence",
        "quick_chain",
    ])
