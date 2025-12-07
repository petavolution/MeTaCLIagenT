"""
MetaCLI Testing Framework

Simulate CLI tool interactions for testing workflows without running real tools.

Features:
- CLI simulators for AI coding tools (claude-code, codex, aider)
- Response templates with pattern matching
- Hash-based output lookup for fast response selection
- Test scenario database
- Sequential and parallel execution
- Support for both stdin/stdout and interactive terminal emulation

Example:
    from metacli.testing import CLISimulator, ResponseTemplate

    # Create simulator with response templates
    simulator = CLISimulator.from_templates("tests/responses.yaml")

    # Run workflow with simulated tools
    workflow = Workflow("test-workflow")
    workflow.add_step("audit", "claude-code", "Audit code")
    result = workflow.run(simulator=simulator)
"""

from .simulator import CLISimulator, SimulatedProcess
from .templates import ResponseTemplate, TemplateLibrary, ResponseMatcher
from .database import TestDatabase, TestScenario, TestExecution
from .parallel import ParallelExecutor, ExecutionPool
from .terminal import TerminalEmulator, KeyboardInput

__all__ = [
    # Core simulator
    "CLISimulator",
    "SimulatedProcess",

    # Templates
    "ResponseTemplate",
    "TemplateLibrary",
    "ResponseMatcher",

    # Database
    "TestDatabase",
    "TestScenario",
    "TestExecution",

    # Parallel execution
    "ParallelExecutor",
    "ExecutionPool",

    # Terminal emulation
    "TerminalEmulator",
    "KeyboardInput",
]

__version__ = "1.0.0-alpha"
