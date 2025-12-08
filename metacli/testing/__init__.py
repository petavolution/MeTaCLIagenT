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
- Realistic two-part output parsing (base64 + hex)
- Keyword detection and intelligent routing

Example:
    from metacli.testing import CLISimulator, ResponseTemplate

    # Create simulator with response templates
    simulator = CLISimulator.from_templates("tests/responses.yaml")

    # Run workflow with simulated tools
    workflow = Workflow("test-workflow")
    workflow.add_step("audit", "claude-code", "Audit code")
    result = workflow.run(simulator=simulator)

    # Parse realistic AI CLI output
    from metacli.testing import RealisticOutputParser, parse_and_route

    parser = RealisticOutputParser()
    parsed = parser.parse(cli_output)

    if parsed.has_error:
        print("Error detected, routing to fix...")
"""

from .simulator import CLISimulator, SimulatedProcess
from .templates import ResponseTemplate, TemplateLibrary, ResponseMatcher
from .database import TestDatabase, TestScenario, TestExecution
from .parallel import ParallelExecutor, ExecutionPool
from .terminal import TerminalEmulator, KeyboardInput
from .realistic_parser import (
    RealisticOutputParser,
    ParsedOutput,
    KeywordRouter,
    RoutingRule,
    parse_and_route,
    create_audit_refactor_router,
    create_test_fix_router,
)

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

    # Realistic output parsing
    "RealisticOutputParser",
    "ParsedOutput",
    "KeywordRouter",
    "RoutingRule",
    "parse_and_route",
    "create_audit_refactor_router",
    "create_test_fix_router",
]

__version__ = "1.0.0-alpha"
