#!/usr/bin/env python3
"""
EATS Core Test Suite

CLI-only test framework for core functionality.
All tests are designed to run without external dependencies.

Usage:
    python tests/test_core.py           # Run all tests
    python tests/test_core.py -v        # Verbose output
    python tests/test_core.py TestDNA   # Run specific test class
"""

import sys
import os
import time
import traceback
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Test Framework
# ============================================================

@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    duration_ms: float
    error: Optional[str] = None
    traceback: Optional[str] = None


class TestRunner:
    """Simple test runner with reporting."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self._current_class: Optional[str] = None

    def run_test(self, name: str, func: Callable[[], None]) -> TestResult:
        """Run a single test function."""
        start = time.perf_counter()
        try:
            func()
            duration = (time.perf_counter() - start) * 1000
            result = TestResult(name=name, passed=True, duration_ms=duration)
            if self.verbose:
                print(f"  [PASS] {name} ({duration:.1f}ms)")
        except AssertionError as e:
            duration = (time.perf_counter() - start) * 1000
            result = TestResult(
                name=name,
                passed=False,
                duration_ms=duration,
                error=str(e) or "Assertion failed",
                traceback=traceback.format_exc(),
            )
            print(f"  [FAIL] {name}: {result.error}")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            result = TestResult(
                name=name,
                passed=False,
                duration_ms=duration,
                error=f"{type(e).__name__}: {e}",
                traceback=traceback.format_exc(),
            )
            print(f"  [ERROR] {name}: {result.error}")

        self.results.append(result)
        return result

    def run_class(self, test_class: type) -> List[TestResult]:
        """Run all test methods in a test class."""
        class_name = test_class.__name__
        self._current_class = class_name
        print(f"\n{class_name}:")

        instance = test_class()
        results = []

        # Run setup if exists
        if hasattr(instance, "setUp"):
            try:
                instance.setUp()
            except Exception as e:
                print(f"  [SETUP FAILED] {e}")
                return results

        # Find and run test methods
        for name in dir(instance):
            if name.startswith("test_"):
                method = getattr(instance, name)
                if callable(method):
                    result = self.run_test(name, method)
                    results.append(result)

        # Run teardown if exists
        if hasattr(instance, "tearDown"):
            try:
                instance.tearDown()
            except Exception as e:
                print(f"  [TEARDOWN FAILED] {e}")

        return results

    def summary(self) -> Dict[str, Any]:
        """Get test summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total_time = sum(r.duration_ms for r in self.results)

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "duration_ms": total_time,
        }

    def print_summary(self) -> None:
        """Print test summary."""
        s = self.summary()
        print("\n" + "=" * 60)
        print(f"Tests: {s['passed']}/{s['total']} passed ({s['duration_ms']:.1f}ms)")

        if s["failed"] > 0:
            print(f"\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.error}")

        print("=" * 60)


# ============================================================
# Test Classes
# ============================================================

class TestAgentDNA:
    """Tests for AgentDNA class."""

    def setUp(self):
        from eats_core.core import AgentDNA
        self.AgentDNA = AgentDNA

    def test_creation(self):
        """Test basic AgentDNA creation."""
        dna = self.AgentDNA(role="coder", system_prompt="You code.")
        assert dna.role == "coder"
        assert dna.system_prompt == "You code."
        assert dna.temperature == 0.7  # default
        assert dna.id is not None

    def test_mutation(self):
        """Test AgentDNA mutation."""
        dna = self.AgentDNA(role="coder", system_prompt="Original")
        mutated = dna.mutate()

        assert mutated.id != dna.id
        assert mutated.parent_id == dna.id
        assert mutated.generation == 1
        assert mutated.role == dna.role

    def test_mutation_temperature_bounds(self):
        """Test temperature stays in valid range after mutation."""
        dna = self.AgentDNA(role="test", system_prompt="Test", temperature=0.1)
        for _ in range(10):
            mutated = dna.mutate()
            assert 0.1 <= mutated.temperature <= 1.0

    def test_to_dict(self):
        """Test serialization to dict."""
        dna = self.AgentDNA(role="test", system_prompt="Test prompt here")
        d = dna.to_dict()
        assert d["role"] == "test"
        # Note: to_dict truncates system_prompt for display purposes
        assert "system_prompt" in d
        assert "id" in d
        assert "temperature" in d


class TestEvolutionConfig:
    """Tests for EvolutionConfig."""

    def setUp(self):
        from eats_core.core import EvolutionConfig
        self.EvolutionConfig = EvolutionConfig

    def test_defaults(self):
        """Test default configuration."""
        config = self.EvolutionConfig()
        assert config.population_size == 4
        assert config.generations == 3
        assert config.mutation_rate > 0

    def test_custom_values(self):
        """Test custom configuration."""
        config = self.EvolutionConfig(
            population_size=10,
            generations=5,
            mutation_rate=0.5,
        )
        assert config.population_size == 10
        assert config.generations == 5
        assert config.mutation_rate == 0.5


class TestSwarmController:
    """Tests for SwarmController."""

    def setUp(self):
        from eats_core.swarm import SwarmController
        self.SwarmController = SwarmController
        self.swarm = None

    def tearDown(self):
        if self.swarm:
            self.swarm.shutdown()

    def test_initialization(self):
        """Test swarm initialization."""
        self.swarm = self.SwarmController()
        root_id = self.swarm.initialize_tree()
        assert root_id is not None
        assert len(self.swarm._nodes) == 10  # Default tree size

    def test_tree_structure(self):
        """Test hierarchical tree structure."""
        self.swarm = self.SwarmController()
        self.swarm.initialize_tree()

        # Find root
        root = None
        for node in self.swarm._nodes.values():
            if node.parent_id is None:
                root = node
                break

        assert root is not None
        assert root.depth == 0

    def test_get_node(self):
        """Test getting nodes by ID."""
        self.swarm = self.SwarmController()
        root_id = self.swarm.initialize_tree()
        node = self.swarm.get_node(root_id)
        assert node is not None
        assert node.id == root_id


class TestLLMJudge:
    """Tests for LLMJudge."""

    def setUp(self):
        from eats_core.judge import LLMJudge
        self.LLMJudge = LLMJudge

    def test_heuristic_evaluation(self):
        """Test heuristic fitness evaluation."""
        judge = self.LLMJudge()
        fitness = judge.evaluate(
            "Write a hello world function",
            "def hello():\n    print('Hello World')",
        )
        assert fitness.score > 0
        assert fitness.method == "heuristic"

    def test_code_detection(self):
        """Test that code is detected and scored higher."""
        judge = self.LLMJudge()

        # Response with code
        code_fitness = judge.evaluate(
            "Write code",
            "```python\ndef foo():\n    pass\n```",
        )

        # Response without code
        text_fitness = judge.evaluate(
            "Write code",
            "You should write a function that does something.",
        )

        assert code_fitness.score > text_fitness.score

    def test_empty_response(self):
        """Test handling of empty response."""
        judge = self.LLMJudge()
        fitness = judge.evaluate("Do something", "")
        assert fitness.score == 0


class TestResultPipeline:
    """Tests for ResultPipeline."""

    def setUp(self):
        from eats_core.pipeline import ResultPipeline, FusionMethod
        self.ResultPipeline = ResultPipeline
        self.FusionMethod = FusionMethod

    def test_add_output(self):
        """Test adding outputs to pipeline."""
        pipeline = self.ResultPipeline()
        pipeline.add("agent-1", "Response 1", fitness=7.5)
        stats = pipeline.stats()
        assert stats["total_outputs"] == 1

    def test_fusion_vote(self):
        """Test vote fusion method."""
        pipeline = self.ResultPipeline()
        pipeline.add("agent-1", "Response 1", fitness=7.0)
        pipeline.add("agent-2", "Response 2", fitness=8.0)
        pipeline.add("agent-3", "Response 3", fitness=6.0)

        fused = pipeline.fuse(
            ["agent-1", "agent-2", "agent-3"],
            method=self.FusionMethod.VOTE,
        )
        assert fused is not None
        assert fused.fitness >= 8.0  # Should pick highest

    def test_get_top(self):
        """Test getting top outputs."""
        pipeline = self.ResultPipeline()
        pipeline.add("agent-1", "Low", fitness=5.0)
        pipeline.add("agent-2", "High", fitness=9.0)
        pipeline.add("agent-3", "Medium", fitness=7.0)

        top = pipeline.get_top(2)
        assert len(top) == 2
        assert top[0].fitness > top[1].fitness


class TestEventBus:
    """Tests for EventBus."""

    def setUp(self):
        from eats_core.events import EventBus, Event, EventType
        self.EventBus = EventBus
        self.Event = Event
        self.EventType = EventType

    def test_creation(self):
        """Test EventBus creation."""
        bus = self.EventBus()
        assert bus is not None

    def test_emit_stores_history(self):
        """Test that sync emit stores in history."""
        bus = self.EventBus(enable_history=True)
        event = self.Event(
            type=self.EventType.TASK_COMPLETED,
            data={"test": 1},
        )
        bus.emit(event)

        history = bus.get_history()
        assert len(history) == 1
        assert history[0].data["test"] == 1

    def test_history_filtering(self):
        """Test history filtering by event type."""
        bus = self.EventBus()
        bus.emit(self.Event(type=self.EventType.TASK_COMPLETED, data={}))
        bus.emit(self.Event(type=self.EventType.AGENT_SPAWNED, data={}))
        bus.emit(self.Event(type=self.EventType.TASK_COMPLETED, data={}))

        task_events = bus.get_history(event_type=self.EventType.TASK_COMPLETED)
        assert len(task_events) == 2


class TestMockProvider:
    """Tests for MockProvider."""

    def setUp(self):
        from eats_core.providers import MockProvider
        self.MockProvider = MockProvider

    def test_basic_response(self):
        """Test basic mock response."""
        provider = self.MockProvider(responses=["Hello!"])
        response = provider.chat("Hi")
        assert response == "Hello!"

    def test_multiple_responses(self):
        """Test cycling through responses."""
        provider = self.MockProvider(responses=["First", "Second"])
        assert provider.chat("1") == "First"
        assert provider.chat("2") == "Second"
        assert provider.chat("3") == "First"  # Cycles

    def test_call_count(self):
        """Test call counting."""
        provider = self.MockProvider()
        assert provider.call_count == 0
        provider.chat("test")
        assert provider.call_count == 1


class TestPersistence:
    """Tests for persistence layer."""

    def setUp(self):
        from eats_core.persistence import MemoryStorage, StateManager
        self.MemoryStorage = MemoryStorage
        self.StateManager = StateManager

    def test_memory_storage(self):
        """Test in-memory storage."""
        storage = self.MemoryStorage()
        storage.save("key1", {"data": "value"})
        loaded = storage.load("key1")
        assert loaded["data"] == "value"

    def test_storage_delete(self):
        """Test storage deletion."""
        storage = self.MemoryStorage()
        storage.save("key1", "value")
        assert storage.exists("key1")
        storage.delete("key1")
        assert not storage.exists("key1")

    def test_state_manager(self):
        """Test StateManager with memory storage."""
        storage = self.MemoryStorage()
        manager = self.StateManager(storage=storage)

        from eats_core.core import AgentDNA
        dna = AgentDNA(role="test", system_prompt="Test")
        manager.save_dna(dna)

        loaded = manager.load_dna(dna.id)
        assert loaded is not None
        assert loaded.role == "test"


class TestLogging:
    """Tests for logging module."""

    def setUp(self):
        from eats_core import logging as eats_logging
        self.logging = eats_logging

    def test_get_logger(self):
        """Test logger creation."""
        logger = self.logging.get_logger("test")
        assert logger is not None

    def test_error_tracker(self):
        """Test error tracking."""
        tracker = self.logging.ErrorTracker()
        try:
            raise ValueError("Test error")
        except Exception as e:
            record = tracker.record(e, module="test", context={"key": "value"})

        assert tracker.count == 1
        assert record.error_type == "ValueError"
        assert record.context["key"] == "value"


class TestConflictResolution:
    """Tests for conflict detection and resolution."""

    def setUp(self):
        from eats_core.conflict import (
            ConflictDetector, ConflictResolver, ConflictType, detect_conflicts
        )
        from eats_core.pipeline import FusedOutput, ResultPipeline, FusionMethod
        self.ConflictDetector = ConflictDetector
        self.ConflictResolver = ConflictResolver
        self.ConflictType = ConflictType
        self.FusedOutput = FusedOutput
        self.ResultPipeline = ResultPipeline
        self.FusionMethod = FusionMethod
        self.detect_conflicts = detect_conflicts

    def test_boolean_contradiction(self):
        """Test detection of boolean contradictions."""
        detector = self.ConflictDetector()

        out1 = self.FusedOutput(
            agent_id="agent1",
            content="The answer is yes. This is correct.",
            fitness=7.0,
        )
        out2 = self.FusedOutput(
            agent_id="agent2",
            content="The answer is no. This is incorrect.",
            fitness=6.0,
        )

        conflicts = detector.detect([out1, out2])
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == self.ConflictType.BOOLEAN
        assert conflicts[0].severity > 0.5

    def test_numerical_divergence(self):
        """Test detection of numerical conflicts."""
        detector = self.ConflictDetector()

        out1 = self.FusedOutput(
            agent_id="agent1",
            content="The result is 100 units.",
            fitness=7.0,
        )
        out2 = self.FusedOutput(
            agent_id="agent2",
            content="The result is 200 units.",
            fitness=7.0,
        )

        conflicts = detector.detect([out1, out2])
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == self.ConflictType.NUMERICAL
        assert conflicts[0].severity > 0.4

    def test_no_conflict(self):
        """Test when no conflict exists."""
        detector = self.ConflictDetector()

        out1 = self.FusedOutput(
            agent_id="agent1",
            content="The weather is sunny today.",
            fitness=7.0,
        )
        out2 = self.FusedOutput(
            agent_id="agent2",
            content="It's a beautiful sunny day.",
            fitness=7.0,
        )

        conflicts = detector.detect([out1, out2])
        # Should find no significant conflicts
        assert all(c.conflict_type == self.ConflictType.NONE for c in conflicts)

    def test_conflict_resolver(self):
        """Test conflict resolution."""
        from eats_core.conflict import Conflict

        resolver = self.ConflictResolver()

        out1 = self.FusedOutput(
            agent_id="agent1",
            content="The capital of France is Paris.",
            fitness=8.0,
        )
        out2 = self.FusedOutput(
            agent_id="agent2",
            content="The capital of France is Lyon.",
            fitness=5.0,
        )

        conflict = Conflict(
            outputs=[out1, out2],
            conflict_type=self.ConflictType.FACTUAL,
            severity=0.8,
            description="Contradictory capital cities",
        )

        resolution = resolver.resolve(conflict)
        assert resolution.agent_id == "conflict_resolver"
        assert resolution.fitness >= 0.0
        assert len(resolution.content) > 50  # Should be substantial
        assert len(resolution.source_ids) == 2

    def test_pipeline_integration(self):
        """Test conflict resolution integrated with ResultPipeline."""
        pipeline = self.ResultPipeline()

        # Add contradictory outputs
        out1 = pipeline.add("agent1", "The answer is yes.", fitness=7.0)
        out2 = pipeline.add("agent2", "The answer is no.", fitness=7.0)

        # Fuse with arbitration
        result = pipeline.fuse(
            ["agent1", "agent2"],
            method=self.FusionMethod.ARBITRATION,
        )

        assert result is not None
        assert len(result.content) > 0
        assert result.fitness >= 0.0

    def test_convenience_functions(self):
        """Test convenience functions."""
        out1 = self.FusedOutput(
            agent_id="agent1",
            content="True statement.",
            fitness=7.0,
        )
        out2 = self.FusedOutput(
            agent_id="agent2",
            content="False statement.",
            fitness=7.0,
        )

        conflicts = self.detect_conflicts([out1, out2])
        assert isinstance(conflicts, list)


# ============================================================
# Main
# ============================================================

ALL_TEST_CLASSES = [
    TestAgentDNA,
    TestEvolutionConfig,
    TestSwarmController,
    TestLLMJudge,
    TestResultPipeline,
    TestEventBus,
    TestMockProvider,
    TestPersistence,
    TestLogging,
    TestConflictResolution,
]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="EATS Core Test Suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("tests", nargs="*", help="Specific test classes to run")
    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    # Filter test classes if specified
    test_classes = ALL_TEST_CLASSES
    if args.tests:
        test_classes = [
            tc for tc in ALL_TEST_CLASSES
            if tc.__name__ in args.tests
        ]
        if not test_classes:
            print(f"No matching test classes found. Available:")
            for tc in ALL_TEST_CLASSES:
                print(f"  - {tc.__name__}")
            sys.exit(1)

    print("=" * 60)
    print("EATS Core Test Suite")
    print("=" * 60)

    # Run tests
    for test_class in test_classes:
        runner.run_class(test_class)

    # Print summary
    runner.print_summary()

    # Write results to log
    from eats_core.logging import get_logger
    logger = get_logger("tests")
    summary = runner.summary()
    logger.info(
        f"Test run complete: {summary['passed']}/{summary['total']} passed "
        f"({summary['duration_ms']:.1f}ms)"
    )

    # Exit with error code if tests failed
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
