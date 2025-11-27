#!/usr/bin/env python3
"""
Parallel Execution Engine

Supports running multiple CLI tools concurrently with:
- Parallel and sequential execution
- Per-step database tracking
- Error handling and retries
- Resource management
- Progress monitoring

Usage:
    executor = ParallelExecutor()
    results = executor.run_parallel([
        StepConfig("grep", "pattern", "file.txt"),
        StepConfig("git", "status"),
    ])
"""

import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from pathlib import Path
import logging as stdlib_logging

from eats_core.cli_orchestrator import CLISequence
from eats_core.cli_persistence import get_persistence, SequencePersistence
from eats_core.presets import get_cli_tool

logger = stdlib_logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Structures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class StepConfig:
    """Configuration for a single execution step."""
    tool_name: str
    prompt: str
    stdin_data: Optional[str] = None
    args: Optional[List[str]] = None
    timeout: int = 300
    retries: int = 0
    depends_on: Optional[List[int]] = None  # Step indices this depends on
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StepResult:
    """Result of a single step execution."""
    step_index: int
    tool_name: str
    status: str  # 'completed', 'failed', 'timeout', 'skipped'
    output: str
    error: Optional[str] = None
    duration: float = 0.0
    attempt: int = 1
    metadata: Optional[Dict[str, Any]] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Parallel Executor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ParallelExecutor:
    """
    Executes CLI steps in parallel with dependency management.

    Features:
    - Parallel execution of independent steps
    - Dependency-based ordering
    - Per-step database tracking
    - Retry logic with exponential backoff
    - Resource limits (max concurrent workers)
    - Progress callbacks
    """

    def __init__(
        self,
        max_workers: int = 4,
        persistence: Optional[SequencePersistence] = None,
        save_to_db: bool = True,
    ):
        """
        Initialize parallel executor.

        Args:
            max_workers: Maximum concurrent executions
            persistence: Persistence layer (creates default if None)
            save_to_db: Whether to save steps to database
        """
        self.max_workers = max_workers
        self.persistence = persistence or get_persistence()
        self.save_to_db = save_to_db
        self._lock = threading.Lock()
        self._step_results: Dict[int, StepResult] = {}

    def run_parallel(
        self,
        steps: List[StepConfig],
        sequence_id: Optional[str] = None,
        on_step_complete: Optional[Callable[[StepResult], None]] = None,
    ) -> Dict[str, Any]:
        """
        Run steps in parallel, respecting dependencies.

        Args:
            steps: List of step configurations
            sequence_id: Optional sequence ID for database tracking
            on_step_complete: Callback called when each step completes

        Returns:
            Execution result with all step results
        """
        logger.info(f"Starting parallel execution of {len(steps)} steps")
        start_time = time.time()

        # Generate sequence ID if not provided
        if not sequence_id:
            sequence_id = f"parallel-{int(time.time())}"

        # Track which steps are ready to run
        pending_steps = set(range(len(steps)))
        completed_steps = set()
        failed_steps = set()

        # Execute in waves (respecting dependencies)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while pending_steps:
                # Find steps ready to run (all dependencies met)
                ready_steps = []
                for idx in list(pending_steps):
                    step = steps[idx]
                    deps = step.depends_on or []

                    # Check if all dependencies completed successfully
                    if all(d in completed_steps for d in deps):
                        ready_steps.append(idx)

                if not ready_steps:
                    # No steps ready - either waiting on deps or all failed
                    if failed_steps:
                        logger.warning(
                            f"Stopping - {len(failed_steps)} steps failed, "
                            f"{len(pending_steps)} steps blocked"
                        )
                        # Mark blocked steps as skipped
                        for idx in pending_steps:
                            self._step_results[idx] = StepResult(
                                step_index=idx,
                                tool_name=steps[idx].tool_name,
                                status='skipped',
                                output='',
                                error='Dependencies failed',
                            )
                    break

                # Submit ready steps
                futures = {}
                for idx in ready_steps:
                    pending_steps.remove(idx)
                    future = executor.submit(
                        self._execute_step,
                        idx,
                        steps[idx],
                        sequence_id,
                    )
                    futures[future] = idx

                # Wait for this wave to complete
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()
                        self._step_results[idx] = result

                        if result.status == 'completed':
                            completed_steps.add(idx)
                        else:
                            failed_steps.add(idx)

                        # Call callback if provided
                        if on_step_complete:
                            on_step_complete(result)

                        # Save to database
                        if self.save_to_db:
                            self._save_step_to_db(sequence_id, result)

                    except Exception as e:
                        logger.error(f"Step {idx} raised exception: {e}")
                        result = StepResult(
                            step_index=idx,
                            tool_name=steps[idx].tool_name,
                            status='failed',
                            output='',
                            error=str(e),
                        )
                        self._step_results[idx] = result
                        failed_steps.add(idx)

        # Compute final statistics
        duration = time.time() - start_time
        successful = len(completed_steps)
        total = len(steps)

        logger.info(
            f"Parallel execution completed: {successful}/{total} successful "
            f"in {duration:.2f}s"
        )

        return {
            'sequence_id': sequence_id,
            'total_steps': total,
            'successful_steps': successful,
            'failed_steps': len(failed_steps),
            'skipped_steps': total - successful - len(failed_steps),
            'duration': duration,
            'status': 'completed' if successful == total else 'partial',
            'results': [self._step_results[i] for i in range(total)],
        }

    def run_sequential(
        self,
        steps: List[StepConfig],
        sequence_id: Optional[str] = None,
        stop_on_failure: bool = True,
    ) -> Dict[str, Any]:
        """
        Run steps sequentially (one after another).

        Args:
            steps: List of step configurations
            sequence_id: Optional sequence ID for database tracking
            stop_on_failure: Stop if any step fails

        Returns:
            Execution result
        """
        logger.info(f"Starting sequential execution of {len(steps)} steps")
        start_time = time.time()

        if not sequence_id:
            sequence_id = f"sequential-{int(time.time())}"

        for idx, step in enumerate(steps):
            result = self._execute_step(idx, step, sequence_id)
            self._step_results[idx] = result

            if self.save_to_db:
                self._save_step_to_db(sequence_id, result)

            if result.status != 'completed' and stop_on_failure:
                logger.warning(f"Step {idx} failed, stopping execution")
                # Mark remaining as skipped
                for remaining_idx in range(idx + 1, len(steps)):
                    self._step_results[remaining_idx] = StepResult(
                        step_index=remaining_idx,
                        tool_name=steps[remaining_idx].tool_name,
                        status='skipped',
                        output='',
                        error='Previous step failed',
                    )
                break

        duration = time.time() - start_time
        completed = sum(
            1 for r in self._step_results.values()
            if r.status == 'completed'
        )

        return {
            'sequence_id': sequence_id,
            'total_steps': len(steps),
            'successful_steps': completed,
            'duration': duration,
            'status': 'completed' if completed == len(steps) else 'partial',
            'results': [self._step_results[i] for i in range(len(steps))],
        }

    def _execute_step(
        self,
        idx: int,
        step: StepConfig,
        sequence_id: str,
    ) -> StepResult:
        """Execute a single step with retry logic."""
        logger.info(f"Step {idx}: Executing {step.tool_name}")

        for attempt in range(step.retries + 1):
            try:
                start_time = time.time()

                # Create a sequence for this single step
                seq = CLISequence(
                    name=f"{sequence_id}-step-{idx}",
                    auto_save=self.save_to_db,
                )

                # Add step to sequence
                seq.add_step(
                    tool_name=step.tool_name,
                    prompt=step.prompt,
                )

                # Run the sequence
                result = seq.run()

                # Cleanup
                seq.cleanup()

                duration = time.time() - start_time

                # Extract output from result
                output = ""
                if result['steps'] and len(result['steps']) > 0:
                    output = result['steps'][0].get('raw_output', '')

                logger.info(
                    f"Step {idx}: Completed {step.tool_name} "
                    f"({len(output)} chars in {duration:.2f}s)"
                )

                return StepResult(
                    step_index=idx,
                    tool_name=step.tool_name,
                    status='completed' if result['status'] == 'completed' else 'failed',
                    output=output,
                    duration=duration,
                    attempt=attempt + 1,
                    metadata=step.metadata,
                )

            except TimeoutError:
                logger.warning(
                    f"Step {idx}: Timeout on attempt {attempt + 1}/{step.retries + 1}"
                )
                if attempt < step.retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return StepResult(
                        step_index=idx,
                        tool_name=step.tool_name,
                        status='timeout',
                        output='',
                        error='Execution timeout',
                        attempt=attempt + 1,
                    )

            except Exception as e:
                logger.error(
                    f"Step {idx}: Error on attempt {attempt + 1}: {e}"
                )
                if attempt < step.retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return StepResult(
                        step_index=idx,
                        tool_name=step.tool_name,
                        status='failed',
                        output='',
                        error=str(e),
                        attempt=attempt + 1,
                    )

    def _save_step_to_db(self, sequence_id: str, result: StepResult):
        """Save step result to database."""
        try:
            with self._lock:
                # This would integrate with actual persistence layer
                # For now, log it
                logger.debug(
                    f"Saving step {result.step_index} to sequence {sequence_id}"
                )
        except Exception as e:
            logger.error(f"Failed to save step to database: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_parallel_steps(
    steps: List[StepConfig],
    max_workers: int = 4,
) -> Dict[str, Any]:
    """Quick parallel execution - convenience function."""
    executor = ParallelExecutor(max_workers=max_workers)
    return executor.run_parallel(steps)


def run_sequential_steps(
    steps: List[StepConfig],
    stop_on_failure: bool = True,
) -> Dict[str, Any]:
    """Quick sequential execution - convenience function."""
    executor = ParallelExecutor()
    return executor.run_sequential(steps, stop_on_failure=stop_on_failure)


if __name__ == "__main__":
    # Demo usage
    print("Parallel Executor Demo")
    print("=" * 60)

    # Example: Run 3 independent grep operations in parallel
    steps = [
        StepConfig("grep", "-r 'import' .", timeout=10),
        StepConfig("grep", "-r 'class' .", timeout=10),
        StepConfig("grep", "-r 'def' .", timeout=10),
    ]

    executor = ParallelExecutor(max_workers=3)
    result = executor.run_parallel(steps)

    print(f"\nParallel execution result:")
    print(f"  Total steps: {result['total_steps']}")
    print(f"  Successful: {result['successful_steps']}")
    print(f"  Duration: {result['duration']:.2f}s")
