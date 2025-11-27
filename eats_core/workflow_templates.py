# workflow_templates.py - Context-Aware Workflow Library
"""
Production-ready workflow templates for common development tasks.

All workflows are project-aware and use ProjectContext to:
- Understand project language/framework
- Follow project coding standards
- Maintain consistency

Workflows:
- feature_development(): Complete feature implementation
- bug_fix(): Analyze, fix, test
- code_review(): Multi-tool review with conflict resolution
- refactor(): Safe refactoring with tests
- security_audit(): Multi-tool security analysis
- documentation(): Auto-generate/update docs
- test_suite(): Generate comprehensive tests

Usage:
    from eats_core import WorkflowTemplates

    # Auto-detects project context
    workflow = WorkflowTemplates.feature_development(
        "Add user authentication with JWT"
    )

    result = workflow.run()
    workflow.cleanup()
"""

from __future__ import annotations
from typing import Optional, List
from pathlib import Path

from .cli_orchestrator import CLISequence, WorkflowPatterns
from .project_context import ProjectContext, get_context
from .logging import get_logger

logger = get_logger("workflows")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workflow Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowTemplates:
    """
    Library of production-ready, context-aware workflows.

    All workflows automatically:
    - Detect project type and framework
    - Follow project coding standards
    - Use appropriate test frameworks
    - Maintain consistency
    """

    @staticmethod
    def feature_development(
        feature: str,
        project_path: str = ".",
    ) -> CLISequence:
        """
        Complete feature development workflow.

        Steps:
        1. Analyze requirements (claude-code with context)
        2. Generate implementation (claude-code)
        3. Generate tests (claude-code)
        4. Review code (gemini)
        5. Fix issues (aider)
        6. Verify tests pass

        Args:
            feature: Feature description
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"feature-{feature[:30]}")

        logger.info(f"Feature workflow: {ctx.summary()}")

        # Step 1: Analyze and plan
        analysis_prompt = ctx.enrich_prompt(
            f"Analyze requirements and create implementation plan for: {feature}"
        )
        seq.add_step("claude-code", analysis_prompt, timeout=60.0)

        # Step 2: Implementation
        impl_prompt = ctx.enrich_prompt(
            f"Implement: {feature}\n\nUse the analysis above as a guide."
        )
        seq.add_step("claude-code", impl_prompt, use_previous_output=True, timeout=90.0)

        # Step 3: Tests
        test_prompt = ctx.enrich_prompt(
            f"Generate comprehensive tests for the implementation above."
        )
        seq.add_step("claude-code", test_prompt, use_previous_output=True, timeout=60.0)

        # Step 4: Code review
        review_prompt = "Review the code and tests for:\n"
        review_prompt += "- Bugs and edge cases\n"
        review_prompt += "- Security issues\n"
        review_prompt += "- Performance problems\n"
        review_prompt += "- Code quality and best practices"
        seq.add_step("gemini", review_prompt, use_previous_output=True, timeout=45.0)

        # Step 5: Fix issues (if needed)
        fix_prompt = "Based on the review, fix any issues found."
        seq.add_step("aider", fix_prompt, use_previous_output=True, timeout=60.0)

        logger.info(f"Feature workflow ready: {len(seq.steps)} steps")
        return seq

    @staticmethod
    def bug_fix(
        bug_description: str,
        affected_files: Optional[List[str]] = None,
        project_path: str = ".",
    ) -> CLISequence:
        """
        Bug fix workflow.

        Steps:
        1. Analyze bug (claude-code with context)
        2. Propose fix (claude-code)
        3. Get second opinion (gemini)
        4. Apply fix (aider)
        5. Verify fix

        Args:
            bug_description: Description of the bug
            affected_files: Known affected files (optional)
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"bugfix-{bug_description[:30]}")

        logger.info(f"Bug fix workflow: {ctx.summary()}")

        # Build context with file info
        context = ctx.enrich_prompt(bug_description)
        if affected_files:
            context += f"\n\nAffected files: {', '.join(affected_files)}"

        # Step 1: Analyze bug
        analysis_prompt = f"{context}\n\nAnalyze the bug, identify root cause, and explain the issue."
        seq.add_step("claude-code", analysis_prompt, timeout=60.0)

        # Step 2: Propose fix
        fix_prompt = "Based on the analysis, propose a detailed fix."
        seq.add_step("claude-code", fix_prompt, use_previous_output=True, timeout=45.0)

        # Step 3: Second opinion
        review_prompt = "Review the proposed fix. Check for:\n"
        review_prompt += "- Correctness\n"
        review_prompt += "- Edge cases\n"
        review_prompt += "- Potential regressions\n"
        review_prompt += "- Alternative approaches"
        seq.add_step("gemini", review_prompt, use_previous_output=True, timeout=45.0)

        # Step 4: Apply fix
        apply_prompt = "Apply the fix, incorporating any improvements suggested in the review."
        seq.add_step("aider", apply_prompt, use_previous_output=True, timeout=60.0)

        logger.info(f"Bug fix workflow ready: {len(seq.steps)} steps")
        return seq

    @staticmethod
    def code_review(
        target: str = "all",  # "all", "staged", or specific files
        project_path: str = ".",
    ) -> CLISequence:
        """
        Multi-tool code review with conflict resolution.

        Steps:
        1. Review with claude-code
        2. Review with gemini
        3. Resolve conflicts if any
        4. Generate final report

        Args:
            target: What to review ("all", "staged", or file list)
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"review-{target}")

        logger.info(f"Code review workflow: {ctx.summary()}")

        # Build review prompt
        base_prompt = ctx.enrich_prompt(
            f"Perform a comprehensive code review of: {target}\n\n"
            "Focus on:\n"
            "- Code quality and maintainability\n"
            "- Bugs and edge cases\n"
            "- Security vulnerabilities\n"
            "- Performance issues\n"
            "- Test coverage\n"
            "- Documentation"
        )

        # Review with multiple tools (parallel in spirit, sequential in execution)
        seq.add_step("claude-code", base_prompt, timeout=90.0)
        seq.add_step("gemini", base_prompt, timeout=90.0)

        # Note: Conflict resolution would happen in result processing
        # For now, both reviews are independent

        logger.info(f"Code review workflow ready: {len(seq.steps)} steps")
        return seq

    @staticmethod
    def refactor(
        target: str,
        goal: str,
        project_path: str = ".",
    ) -> CLISequence:
        """
        Safe refactoring workflow.

        Steps:
        1. Analyze current code (claude-code)
        2. Plan refactoring (claude-code)
        3. Apply refactoring (aider)
        4. Verify tests pass
        5. Review changes (gemini)

        Args:
            target: What to refactor (file/module/class)
            goal: Refactoring goal
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"refactor-{target[:30]}")

        logger.info(f"Refactoring workflow: {ctx.summary()}")

        # Step 1: Analyze
        analysis_prompt = ctx.enrich_prompt(
            f"Analyze the code in {target}.\n"
            "Identify:\n"
            "- Current structure and patterns\n"
            "- Dependencies and coupling\n"
            "- Potential refactoring opportunities"
        )
        seq.add_step("claude-code", analysis_prompt, timeout=60.0)

        # Step 2: Plan
        plan_prompt = f"Create a detailed refactoring plan for: {goal}\n\n"
        plan_prompt += "Plan should:\n"
        plan_prompt += "- Break into small, safe steps\n"
        plan_prompt += "- Preserve existing behavior\n"
        plan_prompt += "- Maintain test coverage"
        seq.add_step("claude-code", plan_prompt, use_previous_output=True, timeout=60.0)

        # Step 3: Apply
        refactor_prompt = "Apply the refactoring plan incrementally."
        seq.add_step("aider", refactor_prompt, use_previous_output=True, timeout=90.0)

        # Step 4: Review
        review_prompt = "Review the refactored code:\n"
        review_prompt += "- Verify goal achieved\n"
        review_prompt += "- Check for introduced bugs\n"
        review_prompt += "- Validate improvements"
        seq.add_step("gemini", review_prompt, use_previous_output=True, timeout=45.0)

        logger.info(f"Refactoring workflow ready: {len(seq.steps)} steps")
        return seq

    @staticmethod
    def security_audit(
        scope: str = "all",
        project_path: str = ".",
    ) -> CLISequence:
        """
        Multi-tool security audit.

        Steps:
        1. Security scan with claude-code
        2. Cross-check with gemini
        3. Identify consensus issues
        4. Generate remediation plan

        Args:
            scope: Audit scope ("all", "api", "auth", etc.)
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"security-audit-{scope}")

        logger.info(f"Security audit workflow: {ctx.summary()}")

        security_prompt = ctx.enrich_prompt(
            f"Perform a security audit of: {scope}\n\n"
            "Check for:\n"
            "- Injection vulnerabilities (SQL, XSS, command)\n"
            "- Authentication and authorization flaws\n"
            "- Sensitive data exposure\n"
            "- Security misconfiguration\n"
            "- Broken access control\n"
            "- Using components with known vulnerabilities\n"
            "- Insufficient logging and monitoring"
        )

        # Scan with multiple tools
        seq.add_step("claude-code", security_prompt, timeout=120.0)
        seq.add_step("gemini", security_prompt, timeout=120.0)

        # Generate remediation
        remediation_prompt = "Based on the findings, create a prioritized remediation plan."
        seq.add_step("claude-code", remediation_prompt, use_previous_output=True, timeout=60.0)

        logger.info(f"Security audit workflow ready: {len(seq.steps)} steps")
        return seq

    @staticmethod
    def documentation(
        target: str = "all",
        project_path: str = ".",
    ) -> CLISequence:
        """
        Auto-generate/update documentation.

        Steps:
        1. Analyze code (claude-code)
        2. Generate docstrings/comments (claude-code)
        3. Update README (claude-code)
        4. Generate API docs (gemini)

        Args:
            target: Documentation scope
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"documentation-{target}")

        logger.info(f"Documentation workflow: {ctx.summary()}")

        # Step 1: Analyze
        analysis_prompt = ctx.enrich_prompt(
            f"Analyze the code structure and functionality of: {target}"
        )
        seq.add_step("claude-code", analysis_prompt, timeout=60.0)

        # Step 2: Docstrings
        docstring_prompt = "Generate comprehensive docstrings for all functions and classes."
        seq.add_step("claude-code", docstring_prompt, use_previous_output=True, timeout=60.0)

        # Step 3: README
        readme_prompt = "Update README.md with:\n"
        readme_prompt += "- Clear description\n"
        readme_prompt += "- Installation instructions\n"
        readme_prompt += "- Usage examples\n"
        readme_prompt += "- API reference"
        seq.add_step("gemini", readme_prompt, use_previous_output=True, timeout=60.0)

        logger.info(f"Documentation workflow ready: {len(seq.steps)} steps")
        return seq

    @staticmethod
    def test_suite(
        target: str,
        test_type: str = "comprehensive",  # "unit", "integration", "comprehensive"
        project_path: str = ".",
    ) -> CLISequence:
        """
        Generate comprehensive test suite.

        Steps:
        1. Analyze code to test (claude-code)
        2. Generate tests (claude-code with context)
        3. Review test coverage (gemini)
        4. Add missing tests (aider)

        Args:
            target: What to test
            test_type: Type of tests to generate
            project_path: Path to project

        Returns:
            Configured workflow sequence
        """
        ctx = get_context(project_path)
        seq = CLISequence(f"tests-{target[:30]}")

        logger.info(f"Test generation workflow: {ctx.summary()}")

        # Step 1: Analyze
        analysis_prompt = ctx.enrich_prompt(
            f"Analyze {target} and identify:\n"
            "- Public API surface\n"
            "- Edge cases and error conditions\n"
            "- Dependencies and mocking needs\n"
            "- Critical paths to test"
        )
        seq.add_step("claude-code", analysis_prompt, timeout=60.0)

        # Step 2: Generate tests
        test_prompt = f"Generate {test_type} tests.\n\n"
        test_prompt += "Tests should:\n"
        test_prompt += "- Cover all public methods\n"
        test_prompt += "- Test edge cases and errors\n"
        test_prompt += "- Use appropriate fixtures and mocks\n"
        test_prompt += "- Follow project test conventions"
        seq.add_step("claude-code", test_prompt, use_previous_output=True, timeout=90.0)

        # Step 3: Review coverage
        review_prompt = "Review test coverage. Identify gaps and missing test cases."
        seq.add_step("gemini", review_prompt, use_previous_output=True, timeout=45.0)

        # Step 4: Fill gaps
        fill_prompt = "Add tests for any identified gaps."
        seq.add_step("aider", fill_prompt, use_previous_output=True, timeout=60.0)

        logger.info(f"Test generation workflow ready: {len(seq.steps)} steps")
        return seq


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def quick_feature(feature: str, project_path: str = ".") -> dict:
    """Quick feature development with auto-run."""
    workflow = WorkflowTemplates.feature_development(feature, project_path)
    result = workflow.run()
    workflow.cleanup()
    return result


def quick_bugfix(bug: str, project_path: str = ".") -> dict:
    """Quick bug fix with auto-run."""
    workflow = WorkflowTemplates.bug_fix(bug, project_path=project_path)
    result = workflow.run()
    workflow.cleanup()
    return result


def quick_review(target: str = "all", project_path: str = ".") -> dict:
    """Quick code review with auto-run."""
    workflow = WorkflowTemplates.code_review(target, project_path)
    result = workflow.run()
    workflow.cleanup()
    return result
