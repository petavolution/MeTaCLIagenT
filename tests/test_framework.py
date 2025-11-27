#!/usr/bin/env python3
"""
Intelligent Test Framework for CLI Orchestration

This framework:
1. Generates test prompts from the library
2. Runs them through mock CLI tools
3. Analyzes outputs for patterns
4. Chooses appropriate follow-up prompts
5. Saves everything to database
6. Generates test reports

Usage:
    from tests.test_framework import TestFramework

    framework = TestFramework()
    result = framework.run_intelligent_test(max_steps=5)
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from eats_core.cli_orchestrator import CLISequence
from eats_core.cli_persistence import get_persistence, SequencePersistence
from tests.test_prompts import (
    get_random_prompt,
    get_prompts_by_category,
    find_patterns_in_output,
    get_follow_up_prompt,
    get_test_workflow,
    get_library_stats,
    TestPrompt,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Test Framework
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFramework:
    """
    Intelligent test framework that generates prompts, analyzes outputs,
    and creates multi-step workflows based on pattern matching.
    """

    def __init__(self, persistence: Optional[SequencePersistence] = None):
        """
        Initialize test framework.

        Args:
            persistence: Optional persistence instance (creates default if None)
        """
        self.persistence = persistence or get_persistence()
        self.test_history: List[Dict] = []

    def run_simple_test(
        self,
        prompt: str,
        tool_name: str = "mock-coder",
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Run a simple single-prompt test.

        Args:
            prompt: Test prompt to send
            tool_name: CLI tool to use
            save_to_db: Whether to save to database

        Returns:
            Test result dictionary
        """
        print(f"\n{'='*60}")
        print(f"Running simple test: {tool_name}")
        print(f"{'='*60}")
        print(f"Prompt: {prompt[:80]}...")

        seq = CLISequence(f"test-{int(time.time())}", auto_save=save_to_db)
        seq.add_step(tool_name, prompt)

        result = seq.run()

        print(f"Status: {result['status']}")
        print(f"Duration: {result['duration']:.2f}s")

        seq.cleanup()

        return result

    def run_workflow_test(
        self,
        workflow_type: str = "generate_review_fix",
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Run a pre-defined workflow test.

        Args:
            workflow_type: Type of workflow (generate_review_fix, code_test_doc, etc.)
            save_to_db: Whether to save to database

        Returns:
            Test result dictionary
        """
        print(f"\n{'='*60}")
        print(f"Running workflow test: {workflow_type}")
        print(f"{'='*60}")

        workflow = get_test_workflow(workflow_type)
        if not workflow:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        print(f"Workflow has {len(workflow)} steps:")
        for i, prompt_obj in enumerate(workflow, 1):
            print(f"  {i}. {prompt_obj.description}")

        seq = CLISequence(f"workflow-test-{int(time.time())}", auto_save=save_to_db)

        # Add all workflow steps
        for i, prompt_obj in enumerate(workflow):
            # First step gets no previous output, rest chain outputs
            use_previous = (i > 0)

            # Choose appropriate tool based on category
            tool_map = {
                "code_generation": "mock-coder",
                "code_review": "mock-reviewer",
                "bug_fix": "mock-fixer",
                "testing": "mock-coder",
                "documentation": "mock-coder",
            }
            tool_name = tool_map.get(prompt_obj.category, "mock-coder")

            seq.add_step(
                tool_name=tool_name,
                prompt=prompt_obj.prompt,
                use_previous_output=use_previous
            )

        print(f"\nRunning workflow...")
        result = seq.run()

        print(f"\nWorkflow completed!")
        print(f"  Status: {result['status']}")
        print(f"  Steps: {result['successful_steps']}/{result['total_steps']}")
        print(f"  Duration: {result['duration']:.2f}s")

        seq.cleanup()

        return result

    def run_intelligent_test(
        self,
        initial_prompt: Optional[str] = None,
        initial_category: Optional[str] = None,
        max_steps: int = 5,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        Run an intelligent test that analyzes outputs and chooses follow-ups.

        This is the KEY feature - it demonstrates the pattern-matching
        and intelligent follow-up selection.

        Args:
            initial_prompt: Starting prompt (random if None)
            initial_category: Category for random prompt (if initial_prompt is None)
            max_steps: Maximum number of steps to run
            save_to_db: Whether to save to database

        Returns:
            Test result with pattern analysis
        """
        print(f"\n{'='*60}")
        print(f"Running INTELLIGENT test (max {max_steps} steps)")
        print(f"{'='*60}")
        print("\nThis test:")
        print("  1. Sends initial prompt to mock CLI")
        print("  2. Analyzes output for patterns")
        print("  3. Chooses appropriate follow-up based on patterns")
        print("  4. Repeats until max steps or no patterns found")
        print()

        # Get initial prompt
        if initial_prompt:
            prompt = initial_prompt
            category = initial_category or "unknown"
            print(f"Using provided prompt: {prompt[:80]}...")
        else:
            prompt_obj = get_random_prompt(initial_category)
            prompt = prompt_obj.prompt
            category = prompt_obj.category
            print(f"Random prompt from '{category}': {prompt[:80]}...")

        seq = CLISequence(f"intelligent-test-{int(time.time())}", auto_save=save_to_db)

        # Track pattern matches for analysis
        pattern_history = []

        # Step 1: Initial prompt
        tool_name = self._choose_tool_for_category(category)
        print(f"\nStep 1: {tool_name}")
        print(f"  Prompt: {prompt[:80]}...")

        seq.add_step(tool_name, prompt)

        # Run first step
        result = seq.run()
        if result['status'] != 'completed' or not result['steps']:
            print(f"  ✗ Step 1 failed")
            seq.cleanup()
            return result

        step1_output = result['steps'][0].get('raw_output', '')
        print(f"  ✓ Output: {len(step1_output)} chars")

        # Analyze patterns and continue
        for step_num in range(2, max_steps + 1):
            # Get last step's output
            last_output = result['steps'][-1].get('raw_output', '')

            # Find patterns in output
            patterns = find_patterns_in_output(last_output)

            if not patterns:
                print(f"\n  No patterns found in step {step_num-1} output - stopping")
                break

            print(f"\n  Patterns found in step {step_num-1}:")
            for p in patterns[:3]:  # Show first 3
                print(f"    - '{p.pattern}' → {p.description}")

            # Record pattern match
            pattern_history.append({
                'step': step_num - 1,
                'patterns_found': [p.pattern for p in patterns],
                'chosen_pattern': patterns[0].pattern,
                'follow_up_description': patterns[0].description,
            })

            # Get follow-up prompt
            follow_up = get_follow_up_prompt(last_output)
            if not follow_up:
                print(f"  No follow-up prompt available - stopping")
                break

            # Choose tool for follow-up (based on pattern category)
            next_category = patterns[0].category
            tool_name = self._choose_tool_for_pattern_category(next_category)

            print(f"\nStep {step_num}: {tool_name}")
            print(f"  Prompt: {follow_up[:80]}...")

            # Add step with previous output
            seq.add_step(
                tool_name=tool_name,
                prompt=follow_up,
                use_previous_output=True
            )

            # Run sequence (runs only new step)
            result = seq.run()

            if result['status'] != 'completed':
                print(f"  ✗ Step {step_num} failed")
                break

            step_output = result['steps'][-1].get('raw_output', '')
            print(f"  ✓ Output: {len(step_output)} chars")

        # Final summary
        print(f"\n{'='*60}")
        print(f"Intelligent test completed!")
        print(f"{'='*60}")
        print(f"  Total steps: {len(result['steps'])}")
        print(f"  Successful: {result['successful_steps']}")
        print(f"  Duration: {result['duration']:.2f}s")
        print(f"  Pattern matches: {len(pattern_history)}")

        if pattern_history:
            print(f"\nPattern match history:")
            for entry in pattern_history:
                print(f"  Step {entry['step']}: {entry['follow_up_description']}")

        seq.cleanup()

        # Add pattern history to result
        result['pattern_history'] = pattern_history

        return result

    def run_batch_tests(
        self,
        num_tests: int = 10,
        test_type: str = "intelligent",
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        Run multiple tests in batch.

        Args:
            num_tests: Number of tests to run
            test_type: Type of test (simple, workflow, intelligent)
            save_to_db: Whether to save to database

        Returns:
            Batch test results
        """
        print(f"\n{'='*60}")
        print(f"Running batch tests: {num_tests} x {test_type}")
        print(f"{'='*60}")

        results = []
        start_time = time.time()

        for i in range(num_tests):
            print(f"\n--- Test {i+1}/{num_tests} ---")

            try:
                if test_type == "simple":
                    prompt_obj = get_random_prompt()
                    result = self.run_simple_test(
                        prompt=prompt_obj.prompt,
                        tool_name="mock-coder",
                        save_to_db=save_to_db
                    )
                elif test_type == "workflow":
                    workflows = ["generate_review_fix", "code_test_doc", "review_optimize_test"]
                    import random
                    workflow = random.choice(workflows)
                    result = self.run_workflow_test(
                        workflow_type=workflow,
                        save_to_db=save_to_db
                    )
                elif test_type == "intelligent":
                    result = self.run_intelligent_test(
                        max_steps=3,
                        save_to_db=save_to_db
                    )
                else:
                    raise ValueError(f"Unknown test type: {test_type}")

                results.append(result)

            except Exception as e:
                print(f"  ✗ Test {i+1} failed: {e}")
                results.append({'status': 'failed', 'error': str(e)})

        # Compute statistics
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r.get('status') == 'completed')

        print(f"\n{'='*60}")
        print(f"Batch test results")
        print(f"{'='*60}")
        print(f"  Total tests: {num_tests}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {num_tests - successful}")
        print(f"  Success rate: {(successful/num_tests)*100:.1f}%")
        print(f"  Total duration: {total_time:.2f}s")
        print(f"  Average per test: {total_time/num_tests:.2f}s")

        return {
            'num_tests': num_tests,
            'test_type': test_type,
            'results': results,
            'successful': successful,
            'failed': num_tests - successful,
            'total_duration': total_time,
        }

    def generate_test_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive test report from database.

        Args:
            output_file: Optional file to save report JSON

        Returns:
            Report dictionary
        """
        print(f"\n{'='*60}")
        print(f"Generating test report")
        print(f"{'='*60}")

        # Get statistics from persistence layer
        stats = self.persistence.get_statistics()

        # Get recent test sequences
        sequences = self.persistence.query_sequences(limit=20)

        # Get prompt library stats
        library_stats = get_library_stats()

        report = {
            'generated_at': datetime.now().isoformat(),
            'database_statistics': stats,
            'recent_sequences': len(sequences),
            'prompt_library': library_stats,
        }

        print(f"\nDatabase Statistics:")
        print(f"  Total sequences: {stats.get('total_sequences', 0)}")
        print(f"  Total steps: {stats.get('total_steps', 0)}")
        print(f"  Success rate: {stats.get('success_rate', 0):.1f}%")

        print(f"\nPrompt Library:")
        print(f"  Total prompts: {library_stats['total_prompts']}")
        print(f"  Pattern rules: {library_stats['total_pattern_rules']}")

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {output_file}")

        return report

    def _choose_tool_for_category(self, category: str) -> str:
        """Choose appropriate mock tool for a prompt category."""
        tool_map = {
            "code_generation": "mock-coder",
            "code_review": "mock-reviewer",
            "bug_fix": "mock-fixer",
            "testing": "mock-coder",
            "documentation": "mock-coder",
        }
        return tool_map.get(category, "mock-coder")

    def _choose_tool_for_pattern_category(self, pattern_category: str) -> str:
        """Choose appropriate tool based on pattern category."""
        tool_map = {
            "code_to_review": "mock-reviewer",
            "review_to_fix": "mock-fixer",
            "fix_to_test": "mock-coder",
            "fix_to_docs": "mock-coder",
            "test_to_review": "mock-reviewer",
            "docs_to_examples": "mock-coder",
            "docs_to_types": "mock-coder",
        }
        return tool_map.get(pattern_category, "mock-coder")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def quick_test(max_steps: int = 3) -> Dict[str, Any]:
    """Quick intelligent test - convenience function."""
    framework = TestFramework()
    return framework.run_intelligent_test(max_steps=max_steps)


def batch_test(num_tests: int = 5, test_type: str = "intelligent") -> Dict[str, Any]:
    """Quick batch test - convenience function."""
    framework = TestFramework()
    return framework.run_batch_tests(num_tests=num_tests, test_type=test_type)


if __name__ == "__main__":
    # Demo usage
    print("\n" + "="*60)
    print("TEST FRAMEWORK DEMO")
    print("="*60)

    framework = TestFramework()

    # Run one intelligent test
    print("\n1. Running intelligent test (demonstrates pattern matching)...")
    result = framework.run_intelligent_test(max_steps=3, save_to_db=True)

    print(f"\n✓ Intelligent test completed: {result['successful_steps']} steps")

    # Generate report
    print("\n2. Generating test report...")
    report = framework.generate_test_report()

    print(f"\n✓ Test framework demo completed!")
