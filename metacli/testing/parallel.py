"""
Parallel Execution - Run multiple workflows concurrently

Supports:
- Sequential execution (one after another)
- Parallel execution (multiple concurrent workflows)
- Thread pool management
- Result aggregation
"""

from __future__ import annotations
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from queue import Queue


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution Pool
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ExecutionResult:
    """Result of a single workflow execution."""
    workflow_name: str
    scenario_name: str
    status: str  # "success", "failed", "error"
    duration: float
    output: Any
    error: Optional[str] = None
    started_at: float = 0.0
    completed_at: float = 0.0


class ExecutionPool:
    """
    Manage concurrent workflow executions.

    Supports both sequential and parallel execution modes.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor: Optional[ThreadPoolExecutor] = None
        self.futures: List[Future] = []
        self.results: List[ExecutionResult] = []

    def __enter__(self):
        """Enter context manager."""
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.executor:
            self.executor.shutdown(wait=True)
        return False

    def submit(
        self,
        workflow_callable: Callable,
        workflow_name: str,
        scenario_name: str,
        **kwargs
    ) -> Future:
        """
        Submit workflow for execution.

        Args:
            workflow_callable: Function that runs the workflow
            workflow_name: Workflow identifier
            scenario_name: Test scenario name
            **kwargs: Arguments to pass to workflow_callable

        Returns:
            Future object
        """
        if not self.executor:
            raise RuntimeError("ExecutionPool not initialized. Use 'with' statement.")

        # Wrap callable to capture execution metadata
        def wrapped_callable():
            started_at = time.time()
            try:
                output = workflow_callable(**kwargs)
                completed_at = time.time()

                return ExecutionResult(
                    workflow_name=workflow_name,
                    scenario_name=scenario_name,
                    status="success",
                    duration=completed_at - started_at,
                    output=output,
                    started_at=started_at,
                    completed_at=completed_at
                )
            except Exception as e:
                completed_at = time.time()
                return ExecutionResult(
                    workflow_name=workflow_name,
                    scenario_name=scenario_name,
                    status="error",
                    duration=completed_at - started_at,
                    output=None,
                    error=str(e),
                    started_at=started_at,
                    completed_at=completed_at
                )

        future = self.executor.submit(wrapped_callable)
        self.futures.append(future)
        return future

    def wait_all(self) -> List[ExecutionResult]:
        """Wait for all submitted workflows to complete."""
        results = []

        for future in as_completed(self.futures):
            result = future.result()
            results.append(result)
            self.results.append(result)

        self.futures.clear()
        return results

    def get_results(self) -> List[ExecutionResult]:
        """Get all results collected so far."""
        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary statistics."""
        total = len(self.results)
        if total == 0:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "error": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0
            }

        success_count = sum(1 for r in self.results if r.status == "success")
        failed_count = sum(1 for r in self.results if r.status == "failed")
        error_count = sum(1 for r in self.results if r.status == "error")
        avg_duration = sum(r.duration for r in self.results) / total

        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "error": error_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0.0,
            "avg_duration": avg_duration
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Parallel Executor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ParallelExecutor:
    """
    Execute multiple test scenarios in parallel or sequentially.

    Example:
        executor = ParallelExecutor(max_workers=4)

        # Sequential execution
        results = executor.run_sequential([scenario1, scenario2, scenario3])

        # Parallel execution
        results = executor.run_parallel([scenario1, scenario2, scenario3])
    """

    def __init__(
        self,
        simulator=None,
        template_library=None,
        test_database=None,
        max_workers: int = 4
    ):
        self.simulator = simulator
        self.template_library = template_library
        self.test_database = test_database
        self.max_workers = max_workers

    def run_sequential(
        self,
        scenarios: List,
        workflow_factory: Callable = None
    ) -> List[ExecutionResult]:
        """
        Run scenarios sequentially (one after another).

        Args:
            scenarios: List of TestScenario objects
            workflow_factory: Function to create workflow from scenario

        Returns:
            List of ExecutionResult objects
        """
        results = []

        for scenario in scenarios:
            started_at = time.time()

            try:
                # Run scenario
                if workflow_factory:
                    workflow = workflow_factory(scenario)
                    output = workflow.run(simulator=self.simulator)
                else:
                    output = self._run_scenario(scenario)

                completed_at = time.time()

                # Create result
                result = ExecutionResult(
                    workflow_name=scenario.name,
                    scenario_name=scenario.name,
                    status="success",
                    duration=completed_at - started_at,
                    output=output,
                    started_at=started_at,
                    completed_at=completed_at
                )

                # Save to database
                if self.test_database:
                    self._save_execution_to_db(scenario, result)

            except Exception as e:
                completed_at = time.time()
                result = ExecutionResult(
                    workflow_name=scenario.name,
                    scenario_name=scenario.name,
                    status="error",
                    duration=completed_at - started_at,
                    output=None,
                    error=str(e),
                    started_at=started_at,
                    completed_at=completed_at
                )

            results.append(result)

        return results

    def run_parallel(
        self,
        scenarios: List,
        workflow_factory: Callable = None
    ) -> List[ExecutionResult]:
        """
        Run scenarios in parallel (concurrent execution).

        Args:
            scenarios: List of TestScenario objects
            workflow_factory: Function to create workflow from scenario

        Returns:
            List of ExecutionResult objects
        """
        results = []

        with ExecutionPool(max_workers=self.max_workers) as pool:
            # Submit all scenarios
            for scenario in scenarios:
                if workflow_factory:
                    def run_with_factory(s=scenario):
                        workflow = workflow_factory(s)
                        return workflow.run(simulator=self.simulator)

                    pool.submit(
                        run_with_factory,
                        workflow_name=scenario.name,
                        scenario_name=scenario.name
                    )
                else:
                    pool.submit(
                        lambda s=scenario: self._run_scenario(s),
                        workflow_name=scenario.name,
                        scenario_name=scenario.name
                    )

            # Wait for all to complete
            results = pool.wait_all()

        # Save results to database
        if self.test_database:
            for i, result in enumerate(results):
                scenario = scenarios[i]
                self._save_execution_to_db(scenario, result)

        return results

    def _run_scenario(self, scenario) -> Dict[str, Any]:
        """
        Run a single test scenario.

        Executes each step and uses templates to generate follow-up commands.
        """
        from .simulator import SimulatedProcess

        results = {
            "scenario": scenario.name,
            "steps": [],
            "status": "success"
        }

        context = {}

        for i, step in enumerate(scenario.steps):
            # Get or create simulated process
            tool_name = step["tool"]
            if self.simulator:
                process = self.simulator.get_process(tool_name)
                if not process:
                    process = self.simulator.spawn(tool_name)
                    process.start()
            else:
                # No simulator, skip execution
                results["steps"].append({
                    "step": i,
                    "tool": tool_name,
                    "prompt": step["prompt"],
                    "output": "[NO SIMULATOR]",
                    "status": "skipped"
                })
                continue

            # Execute step
            prompt = step["prompt"]
            process.write(prompt)
            output = process.read()

            # Check against expected output
            expected = step.get("expected_output", "")
            step_status = "passed" if expected in output else "failed"

            if step_status == "failed":
                results["status"] = "failed"

            # Use template to generate next prompt (if available)
            next_prompt = None
            if self.template_library:
                category = step.get("category", "default")
                next_prompt = self.template_library.generate_response(
                    output,
                    category=category,
                    context=context
                )

            results["steps"].append({
                "step": i,
                "tool": tool_name,
                "prompt": prompt,
                "output": output,
                "expected": expected,
                "status": step_status,
                "next_prompt": next_prompt
            })

            # Update context
            context[f"step_{i}_output"] = output

        return results

    def _save_execution_to_db(self, scenario, result: ExecutionResult):
        """Save execution result to test database."""
        from .database import TestExecution

        # Convert result to TestExecution
        step_results = result.output.get("steps", []) if result.output else []

        execution = TestExecution(
            scenario_id=scenario.id or 0,
            scenario_name=scenario.name,
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration=result.duration,
            status=result.status,
            steps_executed=len(step_results),
            steps_passed=sum(1 for s in step_results if s.get("status") == "passed"),
            steps_failed=sum(1 for s in step_results if s.get("status") == "failed"),
            step_results=step_results,
            error_message=result.error
        )

        self.test_database.save_execution(execution)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_tests_parallel(
    scenarios: List,
    simulator,
    max_workers: int = 4
) -> List[ExecutionResult]:
    """
    Quick function to run test scenarios in parallel.

    Args:
        scenarios: List of TestScenario objects
        simulator: CLISimulator instance
        max_workers: Number of parallel workers

    Returns:
        List of ExecutionResult objects
    """
    executor = ParallelExecutor(
        simulator=simulator,
        max_workers=max_workers
    )

    return executor.run_parallel(scenarios)


def run_tests_sequential(
    scenarios: List,
    simulator
) -> List[ExecutionResult]:
    """
    Quick function to run test scenarios sequentially.

    Args:
        scenarios: List of TestScenario objects
        simulator: CLISimulator instance

    Returns:
        List of ExecutionResult objects
    """
    executor = ParallelExecutor(simulator=simulator, max_workers=1)
    return executor.run_sequential(scenarios)
