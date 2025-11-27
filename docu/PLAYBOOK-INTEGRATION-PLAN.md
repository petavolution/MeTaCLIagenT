# MeTaCLIagenT Playbook Integration Plan

**Vision**: Transform MeTaCLIagenT into a versioned, declarative orchestration system for AI-assisted development workflows

**Date**: 2025-11-27
**Status**: Planning Phase
**Priority**: High - Strategic Enhancement

---

## 🎯 EXECUTIVE SUMMARY

This document outlines how MeTaCLIagenT will integrate **Playbook-style workflows** - versioned, declarative recipes for repeatable AI-assisted development sessions. This transforms the framework from a CLI orchestration tool into a comprehensive **Development Session Automation Platform**.

### Key Benefits

✅ **Versioned Workflows**: Store your dev process in git, track changes over time
✅ **Reproducible Sessions**: Run the same workflow across projects with parameter substitution
✅ **Auditable Artifacts**: Every step produces tracked, diffable outputs
✅ **Controlled Autonomy**: Guardrails + diff budgets + DoD prevent runaway changes
✅ **Project Memory**: Artifacts become institutional knowledge
✅ **Modular Prompts**: Reusable prompt library that evolves with your needs

---

## 📚 CONCEPT MAPPING

### Playbook Concepts → MeTaCLIagenT Implementation

| Playbook Concept | Current MeTaCLIagenT | Enhancement Needed | Priority |
|------------------|---------------------|-------------------|----------|
| **Playbook** | CLISequence (code-based) | YAML/JSON declarative format | **P0** |
| **Workflow** | Hard-coded step sequences | Versioned `.ai/workflows/` directory | **P0** |
| **Step** | Step in CLISequence | Add inputs/outputs/checks | **P0** |
| **Artifact** | DB + text files | Structured artifact system | **P0** |
| **Prompt Pack** | Hard-coded prompts | `.ai/prompts/` library | **P1** |
| **Runner** | CLISequence.run() | Enhanced with resume/variables | **P0** |
| **Session** | Tracked in DB | Add comparison/resume | **P1** |
| **Variables** | No support | `{{VAR}}` substitution | **P0** |
| **Definition of Done** | Basic success/fail | Per-step DoD with checks | **P1** |
| **Guardrails** | Command allowlist only | Diff budget, file checks | **P1** |
| **Diff Budget** | Not implemented | Track changes per step/session | **P1** |
| **Rules File** | Not implemented | `.ai/rules.md` project guidance | **P1** |
| **Meta-Controller** | Basic orchestration | Smart playbook selection | **P2** |

---

## 🏗️ ENHANCED ARCHITECTURE

### New Directory Structure

```
project/
├── .ai/                          # AI orchestration config (NEW)
│   ├── workflows/                # Playbook definitions
│   │   ├── feature.yml           # Feature development workflow
│   │   ├── bugfix.yml            # Bug fixing workflow
│   │   ├── refactor.yml          # Refactoring workflow
│   │   ├── review.yml            # Code review workflow
│   │   └── deploy.yml            # Deployment workflow
│   │
│   ├── prompts/                  # Reusable prompt library
│   │   ├── scan.md               # Codebase scanning prompt
│   │   ├── plan.md               # Planning prompt
│   │   ├── implement.md          # Implementation prompt
│   │   ├── verify.md             # Verification prompt
│   │   ├── review.md             # Review prompt
│   │   └── common/               # Common prompt fragments
│   │       ├── architecture.md
│   │       ├── testing.md
│   │       └── security.md
│   │
│   ├── rules.md                  # Project-wide AI guidance
│   ├── config.yml                # Workflow configuration
│   └── sessions/                 # Session history (artifacts)
│       ├── 2025-11-27T10-30-00_feature-auth/
│       │   ├── session.yml       # Session metadata
│       │   ├── CONTEXT.md        # Generated context
│       │   ├── PLAN.md           # Generated plan
│       │   ├── REVIEW.md         # Generated review
│       │   ├── artifacts/        # Step artifacts
│       │   │   ├── 01_scan.log
│       │   │   ├── 02_plan.log
│       │   │   ├── 03_implement.log
│       │   │   ├── 04_verify.log
│       │   │   └── changes.diff
│       │   └── variables.yml     # Session variables
│       └── ...
│
├── .aiignore                     # Files to exclude from AI context
└── ...existing project files...
```

### MeTaCLIagenT Enhanced Components

```
eats_core/
├── playbook.py              # NEW - Playbook parser and executor
├── artifact_manager.py      # NEW - Artifact tracking and versioning
├── variable_engine.py       # NEW - Variable substitution
├── diff_tracker.py          # NEW - Diff budget enforcement
├── rules_loader.py          # NEW - Load and inject project rules
├── session_manager.py       # NEW - Session lifecycle management
├── checks_runner.py         # NEW - Definition of Done validation
├── guardrail_enforcer.py    # NEW - Safety constraint enforcement
│
├── cli_orchestrator.py      # ENHANCED - Playbook integration
├── template_engine.py       # ENHANCED - Use prompt packs
└── ...existing modules...
```

---

## 📋 PLAYBOOK FORMAT SPECIFICATION

### Example: Feature Development Playbook

**File**: `.ai/workflows/feature.yml`

```yaml
# Feature Development Workflow
# Usage: ai run feature --var FEATURE="user authentication" --var MODULE="auth"

metadata:
  name: feature-development
  version: 2.1.0
  description: End-to-end feature development with AI assistance
  author: development-team
  tags: [development, feature, ai-assisted]

# Variables that must be provided at runtime
variables:
  required:
    - FEATURE        # Feature description
    - MODULE         # Module/component name
  optional:
    - BRANCH: "feature/{{MODULE}}-{{timestamp}}"
    - REVIEWER: "claude-code"
    - TESTER: "python"

# Project rules to inject into all prompts
rules_file: .ai/rules.md

# Guardrails for this workflow
guardrails:
  diff_budget:
    max_files_per_step: 8
    max_lines_per_step: 400
    max_files_total: 25
    max_lines_total: 1500

  protected_files:
    - package.json
    - requirements.txt
    - Cargo.toml
    - go.mod

  allowed_tools:
    - claude-code
    - gemini
    - aider
    - git
    - pytest
    - grep
    - rg

# Definition of Done for entire workflow
definition_of_done:
  - tests_pass: true
  - lint_clean: true
  - all_artifacts_present: true
  - diff_within_budget: true
  - review_completed: true

# Workflow steps
steps:
  # Step 1: Scan and understand codebase
  - id: scan
    name: "Scan codebase and build context"
    tool: claude-code
    prompt_file: .ai/prompts/scan.md

    variables:
      inject:
        MODULE: "{{MODULE}}"
        FOCUS_AREA: "{{MODULE}} module and related components"

    outputs:
      artifacts:
        - name: CONTEXT.md
          required: true
          description: "Codebase understanding and architecture"

      variables:
        - ARCHITECTURE_SUMMARY
        - KEY_FILES
        - DEPENDENCIES

    timeout: 120
    retry: 1

  # Step 2: Create implementation plan
  - id: plan
    name: "Create implementation plan"
    tool: claude-code
    prompt_file: .ai/prompts/plan.md

    variables:
      inject:
        FEATURE: "{{FEATURE}}"
        MODULE: "{{MODULE}}"
        CONTEXT: "{{artifacts.CONTEXT.md}}"
        ARCHITECTURE: "{{vars.ARCHITECTURE_SUMMARY}}"

    outputs:
      artifacts:
        - name: PLAN.md
          required: true
          description: "Phased implementation plan with risks"
          schema:
            sections:
              - Overview
              - Phases
              - Files to Change
              - Risks
              - Testing Strategy

      variables:
        - FILES_TO_CHANGE
        - PHASES
        - RISKS

    checks:
      - name: plan_has_phases
        condition: "len(vars.PHASES) >= 2"
        fail_message: "Plan must have at least 2 phases"

      - name: plan_identifies_tests
        condition: "'Testing Strategy' in artifacts['PLAN.md']"
        fail_message: "Plan must include testing strategy"

    timeout: 120
    retry: 1

  # Step 3: Implement feature
  - id: implement
    name: "Implement feature changes"
    tool: aider
    prompt_file: .ai/prompts/implement.md

    variables:
      inject:
        FEATURE: "{{FEATURE}}"
        PLAN: "{{artifacts.PLAN.md}}"
        FILES: "{{vars.FILES_TO_CHANGE}}"

    outputs:
      artifacts:
        - name: changes.diff
          required: true
          description: "Git diff of changes"
          capture: "git diff > artifacts/changes.diff"

        - name: implementation.log
          required: true
          description: "Implementation session log"

      variables:
        - FILES_CHANGED
        - LINES_ADDED
        - LINES_DELETED

    # Diff budget enforcement for this step
    diff_budget:
      max_files: 8
      max_lines: 400

    checks:
      - name: no_protected_files
        condition: "not any(f in vars.FILES_CHANGED for f in guardrails.protected_files)"
        fail_message: "Cannot modify protected dependency files"

      - name: changes_match_plan
        condition: "all(f in vars.FILES_TO_CHANGE for f in vars.FILES_CHANGED)"
        fail_message: "Changed files don't match plan"
        severity: warning

    timeout: 300
    retry: 2
    retry_on_failure: true

  # Step 4: Verify implementation
  - id: verify
    name: "Run tests and validation"

    # Parallel verification tasks
    parallel:
      - id: run_tests
        tool: pytest
        args: ["tests/", "-v", "--tb=short"]
        capture_output: artifacts/tests.log
        timeout: 180

      - id: run_lint
        tool: pylint
        args: ["{{vars.FILES_CHANGED}}"]
        capture_output: artifacts/lint.log
        timeout: 60

      - id: type_check
        tool: mypy
        args: ["{{vars.FILES_CHANGED}}"]
        capture_output: artifacts/typecheck.log
        timeout: 60

    outputs:
      artifacts:
        - name: tests.log
          required: true
        - name: lint.log
          required: true
        - name: typecheck.log
          required: true

      variables:
        - TESTS_PASSED
        - TESTS_FAILED
        - LINT_SCORE
        - TYPE_ERRORS

    checks:
      - name: tests_pass
        condition: "vars.TESTS_PASSED > 0 and vars.TESTS_FAILED == 0"
        fail_message: "Tests must pass before proceeding"
        blocking: true

      - name: lint_acceptable
        condition: "vars.LINT_SCORE >= 8.0"
        fail_message: "Lint score too low (minimum 8.0)"
        severity: warning

      - name: no_type_errors
        condition: "vars.TYPE_ERRORS == 0"
        fail_message: "Type errors must be fixed"
        blocking: true

    # If checks fail, branch to fix step
    on_failure:
      branch_to: fix_issues

  # Step 5: Fix issues (conditional)
  - id: fix_issues
    name: "Fix test/lint/type errors"
    tool: claude-code
    prompt_file: .ai/prompts/fix.md

    variables:
      inject:
        TESTS_LOG: "{{artifacts.tests.log}}"
        LINT_LOG: "{{artifacts.lint.log}}"
        TYPE_LOG: "{{artifacts.typecheck.log}}"
        CHANGES_DIFF: "{{artifacts.changes.diff}}"

    outputs:
      artifacts:
        - name: fixes.diff
          required: true

    # After fixing, retry verification
    on_success:
      branch_to: verify

    # Max 3 fix attempts
    max_retries: 3
    on_max_retries:
      action: abort
      message: "Failed to fix issues after 3 attempts. Manual intervention needed."

  # Step 6: Generate review document
  - id: review
    name: "Generate review document"
    tool: gemini
    prompt_file: .ai/prompts/review.md

    variables:
      inject:
        FEATURE: "{{FEATURE}}"
        PLAN: "{{artifacts.PLAN.md}}"
        CHANGES: "{{artifacts.changes.diff}}"
        TESTS: "{{artifacts.tests.log}}"
        CONTEXT: "{{artifacts.CONTEXT.md}}"

    outputs:
      artifacts:
        - name: REVIEW.md
          required: true
          description: "Comprehensive review of changes"
          schema:
            sections:
              - Summary
              - What Changed
              - Why These Changes
              - How to Test
              - Risks and Considerations
              - Next Steps

    timeout: 180

  # Step 7: Final verification
  - id: final_check
    name: "Verify Definition of Done"
    tool: internal
    action: check_dod

    checks:
      - name: all_tests_pass
        condition: "vars.TESTS_FAILED == 0"

      - name: lint_clean
        condition: "vars.LINT_SCORE >= 8.0"

      - name: artifacts_complete
        condition: |
          all(a in session.artifacts for a in [
            'CONTEXT.md', 'PLAN.md', 'REVIEW.md',
            'changes.diff', 'tests.log'
          ])

      - name: diff_budget_ok
        condition: "vars.LINES_ADDED + vars.LINES_DELETED <= 1500"

      - name: no_protected_modified
        condition: "not any(f in guardrails.protected_files for f in vars.FILES_CHANGED)"

    on_success:
      action: complete
      message: "✅ Feature development complete! Review REVIEW.md for summary."

    on_failure:
      action: abort
      message: "❌ Definition of Done not met. Check session artifacts for details."

# Session configuration
session:
  # Auto-create git branch for this session
  git:
    auto_branch: true
    branch_name: "{{BRANCH}}"
    auto_commit: false  # Manual review before commit

  # Workspace isolation
  workspace:
    use_worktree: true
    cleanup_on_success: false
    cleanup_on_failure: false

  # Artifact management
  artifacts:
    base_path: .ai/sessions
    compress_on_complete: false
    retention_days: 90

# Hooks for custom actions
hooks:
  on_start:
    - log: "Starting feature development: {{FEATURE}}"
    - notify: "slack://dev-channel"

  on_complete:
    - log: "Feature complete: {{FEATURE}}"
    - exec: "git add .ai/sessions/{{session.id}}"
    - notify: "slack://dev-channel"

  on_failure:
    - log: "Feature development failed: {{error}}"
    - exec: "git stash"
    - notify: "slack://dev-alerts"
```

---

## 🔧 IMPLEMENTATION COMPONENTS

### 1. Playbook Parser (`eats_core/playbook.py`)

```python
"""
Playbook parser and validator.

Loads YAML workflow definitions, validates structure,
resolves variables, and creates executable workflow.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import yaml
import re

@dataclass
class PlaybookMetadata:
    """Metadata about the playbook."""
    name: str
    version: str
    description: str
    author: str
    tags: List[str] = field(default_factory=list)

@dataclass
class VariableDefinition:
    """Variable definition in playbook."""
    required: List[str] = field(default_factory=list)
    optional: Dict[str, str] = field(default_factory=dict)  # name: default

@dataclass
class Guardrails:
    """Safety constraints for workflow."""
    diff_budget: Dict[str, int]
    protected_files: List[str]
    allowed_tools: List[str]
    max_execution_time: Optional[int] = None
    require_human_approval: bool = False

@dataclass
class DefinitionOfDone:
    """Success criteria for workflow."""
    tests_pass: bool = True
    lint_clean: bool = True
    all_artifacts_present: bool = True
    diff_within_budget: bool = True
    review_completed: bool = False

@dataclass
class ArtifactDefinition:
    """Expected artifact output from step."""
    name: str
    required: bool
    description: str
    capture: Optional[str] = None  # Command to capture artifact
    schema: Optional[Dict] = None  # Expected structure

@dataclass
class StepCheck:
    """Validation check for step."""
    name: str
    condition: str  # Python expression
    fail_message: str
    severity: str = "error"  # "error" or "warning"
    blocking: bool = True

@dataclass
class PlaybookStep:
    """Single step in playbook."""
    id: str
    name: str
    tool: str
    prompt_file: Optional[str] = None
    prompt: Optional[str] = None
    args: List[str] = field(default_factory=list)

    # Variable injection
    variables: Dict[str, Any] = field(default_factory=dict)

    # Outputs
    outputs: Dict[str, Any] = field(default_factory=dict)

    # Checks
    checks: List[StepCheck] = field(default_factory=list)

    # Diff budget for this step
    diff_budget: Optional[Dict[str, int]] = None

    # Execution control
    timeout: int = 60
    retry: int = 0
    retry_on_failure: bool = False

    # Branching
    on_success: Optional[Dict] = None
    on_failure: Optional[Dict] = None
    max_retries: Optional[int] = None
    on_max_retries: Optional[Dict] = None

    # Parallel execution
    parallel: Optional[List[Dict]] = None

@dataclass
class Playbook:
    """Complete playbook definition."""
    metadata: PlaybookMetadata
    variables: VariableDefinition
    rules_file: Optional[str]
    guardrails: Guardrails
    definition_of_done: DefinitionOfDone
    steps: List[PlaybookStep]
    session: Dict[str, Any]
    hooks: Dict[str, List[Dict]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Playbook":
        """Load playbook from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            metadata=PlaybookMetadata(**data['metadata']),
            variables=VariableDefinition(**data['variables']),
            rules_file=data.get('rules_file'),
            guardrails=Guardrails(**data['guardrails']),
            definition_of_done=DefinitionOfDone(**data['definition_of_done']),
            steps=[PlaybookStep(**s) for s in data['steps']],
            session=data['session'],
            hooks=data.get('hooks', {})
        )

    def validate(self) -> List[str]:
        """Validate playbook structure and references."""
        errors = []

        # Check step IDs are unique
        step_ids = [s.id for s in self.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")

        # Check branch targets exist
        for step in self.steps:
            if step.on_success and 'branch_to' in step.on_success:
                target = step.on_success['branch_to']
                if target not in step_ids:
                    errors.append(f"Step {step.id}: branch target '{target}' not found")

            if step.on_failure and 'branch_to' in step.on_failure:
                target = step.on_failure['branch_to']
                if target not in step_ids:
                    errors.append(f"Step {step.id}: branch target '{target}' not found")

        # Check prompt files exist
        for step in self.steps:
            if step.prompt_file:
                if not Path(step.prompt_file).exists():
                    errors.append(f"Step {step.id}: prompt file '{step.prompt_file}' not found")

        # Check rules file exists
        if self.rules_file and not Path(self.rules_file).exists():
            errors.append(f"Rules file '{self.rules_file}' not found")

        return errors


class PlaybookRunner:
    """
    Execute playbooks with full variable substitution,
    artifact tracking, and guardrail enforcement.
    """

    def __init__(self, playbook: Playbook, variables: Dict[str, str]):
        self.playbook = playbook
        self.variables = variables
        self.session = None
        self.current_step_index = 0
        self.retry_count = {}

        # Managers
        self.artifact_manager = None  # Will be ArtifactManager
        self.diff_tracker = None  # Will be DiffTracker
        self.guardrail_enforcer = None  # Will be GuardrailEnforcer
        self.variable_engine = None  # Will be VariableEngine

    def run(self) -> SessionResult:
        """Execute playbook from start to finish."""
        # 1. Validate required variables
        self._validate_variables()

        # 2. Initialize session
        self.session = self._create_session()

        # 3. Run on_start hooks
        self._run_hooks('on_start')

        # 4. Execute steps
        try:
            while self.current_step_index < len(self.playbook.steps):
                step = self.playbook.steps[self.current_step_index]
                result = self._execute_step(step)

                if not result.success:
                    self._handle_step_failure(step, result)
                else:
                    self._handle_step_success(step, result)

                self.current_step_index += 1

            # 5. Check Definition of Done
            dod_result = self._check_definition_of_done()

            if dod_result.passed:
                self._run_hooks('on_complete')
                return SessionResult(success=True, session=self.session)
            else:
                return SessionResult(
                    success=False,
                    reason="Definition of Done not met",
                    details=dod_result.failures
                )

        except Exception as e:
            self._run_hooks('on_failure')
            return SessionResult(success=False, error=str(e))

    def resume(self, session_id: str, from_step: str) -> SessionResult:
        """Resume playbook execution from a specific step."""
        # Load previous session
        self.session = self._load_session(session_id)

        # Find step index
        step_ids = [s.id for s in self.playbook.steps]
        self.current_step_index = step_ids.index(from_step)

        # Continue execution
        return self.run()

    def _execute_step(self, step: PlaybookStep) -> StepResult:
        """Execute a single step with all checks and guardrails."""
        # 1. Substitute variables in prompt
        if step.prompt_file:
            prompt = self._load_and_substitute_prompt(step.prompt_file, step.variables)
        else:
            prompt = self.variable_engine.substitute(step.prompt, self.variables)

        # 2. Check guardrails BEFORE execution
        if not self.guardrail_enforcer.check_tool_allowed(step.tool):
            return StepResult(
                success=False,
                reason=f"Tool {step.tool} not in allowed list"
            )

        # 3. Execute tool
        if step.parallel:
            result = self._execute_parallel(step)
        else:
            result = self._execute_single(step, prompt)

        # 4. Track diff budget
        if step.diff_budget:
            diff_stats = self.diff_tracker.get_current_diff()
            if not self._check_diff_budget(diff_stats, step.diff_budget):
                return StepResult(
                    success=False,
                    reason="Diff budget exceeded"
                )

        # 5. Capture artifacts
        for artifact_def in step.outputs.get('artifacts', []):
            self.artifact_manager.capture(
                name=artifact_def['name'],
                content=result.output,
                required=artifact_def.get('required', False)
            )

        # 6. Extract variables
        for var in step.outputs.get('variables', []):
            self.variables[var] = self._extract_variable(var, result.output)

        # 7. Run checks
        for check in step.checks:
            check_result = self._run_check(check)
            if not check_result.passed and check.blocking:
                return StepResult(
                    success=False,
                    reason=f"Check failed: {check.name}",
                    details=check.fail_message
                )

        return result
```

---

### 2. Artifact Manager (`eats_core/artifact_manager.py`)

```python
"""
Artifact management system.

Tracks, versions, and stores artifacts produced by workflow steps.
Artifacts become project memory and audit trail.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import json
import hashlib
from datetime import datetime

@dataclass
class Artifact:
    """A single artifact produced by a step."""
    name: str
    content: str
    step_id: str
    timestamp: datetime
    hash: str
    required: bool
    description: Optional[str] = None
    schema_validated: bool = False

class ArtifactManager:
    """
    Manage artifacts for a session.

    Responsibilities:
    - Store artifacts in session directory
    - Track artifact versions
    - Validate artifact schemas
    - Enable artifact-as-input for next steps
    - Generate artifact index
    """

    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.artifacts_path = session_path / "artifacts"
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        self.artifacts: Dict[str, Artifact] = {}
        self.index_path = self.session_path / "artifacts_index.json"

    def capture(
        self,
        name: str,
        content: str,
        step_id: str,
        required: bool = False,
        description: Optional[str] = None
    ) -> Artifact:
        """Capture an artifact from step output."""
        # Hash content for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Create artifact
        artifact = Artifact(
            name=name,
            content=content,
            step_id=step_id,
            timestamp=datetime.now(),
            hash=content_hash,
            required=required,
            description=description
        )

        # Save to disk
        artifact_file = self.artifacts_path / name
        artifact_file.write_text(content)

        # Track in memory
        self.artifacts[name] = artifact

        # Update index
        self._update_index()

        return artifact

    def get(self, name: str) -> Optional[Artifact]:
        """Retrieve artifact by name."""
        return self.artifacts.get(name)

    def get_content(self, name: str) -> Optional[str]:
        """Get artifact content."""
        artifact = self.get(name)
        return artifact.content if artifact else None

    def validate_schema(self, artifact: Artifact, schema: Dict) -> bool:
        """
        Validate artifact structure against schema.

        For markdown files, checks for required sections.
        For JSON, validates structure.
        """
        if artifact.name.endswith('.md'):
            # Check for required sections
            required_sections = schema.get('sections', [])
            for section in required_sections:
                if f"## {section}" not in artifact.content:
                    return False
            return True

        elif artifact.name.endswith('.json'):
            # Validate JSON structure
            try:
                data = json.loads(artifact.content)
                # Simple schema validation (could use jsonschema library)
                return True
            except:
                return False

        return True

    def list_artifacts(self) -> List[str]:
        """List all artifact names."""
        return list(self.artifacts.keys())

    def check_required_artifacts(self, required: List[str]) -> List[str]:
        """Check which required artifacts are missing."""
        missing = []
        for name in required:
            if name not in self.artifacts:
                missing.append(name)
        return missing

    def _update_index(self):
        """Update artifacts index file."""
        index = {
            name: {
                'step_id': art.step_id,
                'timestamp': art.timestamp.isoformat(),
                'hash': art.hash,
                'required': art.required,
                'description': art.description
            }
            for name, art in self.artifacts.items()
        }

        self.index_path.write_text(json.dumps(index, indent=2))
```

---

### 3. Variable Engine (`eats_core/variable_engine.py`)

```python
"""
Variable substitution engine.

Handles {{variable}} placeholders in prompts and configs.
Supports:
- Simple variables: {{FEATURE}}
- Nested access: {{artifacts.PLAN.md}}
- Functions: {{timestamp}}, {{uuid}}
- Expressions: {{vars.FILES | length}}
"""

import re
from typing import Dict, Any
from datetime import datetime
import uuid

class VariableEngine:
    """
    Substitute variables in templates.

    Syntax:
        {{VAR}}                  - Simple variable
        {{vars.key}}             - Nested access
        {{artifacts.FILE}}       - Artifact content
        {{timestamp}}            - Current timestamp
        {{uuid}}                 - Random UUID
        {{VAR | default("x")}}   - Default value
    """

    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')

    def __init__(self, variables: Dict[str, Any], artifacts: Dict[str, str]):
        self.variables = variables
        self.artifacts = artifacts

        # Built-in variables
        self.builtins = {
            'timestamp': lambda: datetime.now().strftime('%Y-%m-%dT%H-%M-%S'),
            'date': lambda: datetime.now().strftime('%Y-%m-%d'),
            'uuid': lambda: str(uuid.uuid4())[:8],
        }

    def substitute(self, template: str) -> str:
        """Replace all {{var}} placeholders in template."""
        def replacer(match):
            expr = match.group(1).strip()
            return self._evaluate_expression(expr)

        return self.VARIABLE_PATTERN.sub(replacer, template)

    def _evaluate_expression(self, expr: str) -> str:
        """Evaluate a variable expression."""
        # Handle default values: {{VAR | default("fallback")}}
        if '|' in expr:
            var_part, filter_part = expr.split('|', 1)
            var_part = var_part.strip()
            filter_part = filter_part.strip()

            try:
                value = self._get_value(var_part)
                return str(value)
            except KeyError:
                # Apply default filter
                if filter_part.startswith('default('):
                    default = filter_part[8:-1].strip('"\'')
                    return default
                raise

        # Simple variable lookup
        value = self._get_value(expr)
        return str(value)

    def _get_value(self, path: str) -> Any:
        """Get value from dotted path."""
        parts = path.split('.')

        # Check builtins first
        if parts[0] in self.builtins:
            return self.builtins[parts[0]]()

        # Check artifacts: artifacts.PLAN.md
        if parts[0] == 'artifacts':
            artifact_name = '.'.join(parts[1:])
            if artifact_name in self.artifacts:
                return self.artifacts[artifact_name]
            raise KeyError(f"Artifact not found: {artifact_name}")

        # Check variables: vars.key or just key
        if parts[0] == 'vars':
            key = '.'.join(parts[1:])
        else:
            key = path

        # Navigate nested dict
        value = self.variables
        for part in key.split('.'):
            if isinstance(value, dict):
                value = value[part]
            else:
                raise KeyError(f"Cannot access {part} in {type(value)}")

        return value

    def validate_template(self, template: str) -> List[str]:
        """Find all variables referenced in template."""
        matches = self.VARIABLE_PATTERN.findall(template)
        return [m.strip() for m in matches]

    def check_required_variables(
        self,
        template: str,
        required: List[str]
    ) -> List[str]:
        """Check which required variables are missing."""
        missing = []
        for var in required:
            if var not in self.variables:
                missing.append(var)
        return missing
```

---

## 🎯 USAGE EXAMPLES

### Example 1: Run Feature Development Workflow

```bash
# Navigate to project
cd my-project

# Initialize AI orchestration (one-time setup)
ai init

# Run feature workflow with variables
ai run feature \
  --var FEATURE="Add OAuth2 authentication" \
  --var MODULE="auth" \
  --var REVIEWER="gemini"

# Output:
# ✓ Session created: 2025-11-27T14-30-00_feature-auth
# ✓ Step 1/7: Scan codebase and build context... Done (45s)
#   → Artifact: CONTEXT.md (2.3 KB)
# ✓ Step 2/7: Create implementation plan... Done (32s)
#   → Artifact: PLAN.md (1.8 KB)
# ✓ Step 3/7: Implement feature changes... Done (127s)
#   → Changed 6 files (+289 lines, -12 lines)
#   → Artifact: changes.diff (8.4 KB)
# ✓ Step 4/7: Run tests and validation... Done (18s)
#   → All tests passed (34 passed, 0 failed)
# ⚠ Step 5/7: Fix issues... Skipped (no issues found)
# ✓ Step 6/7: Generate review document... Done (28s)
#   → Artifact: REVIEW.md (3.1 KB)
# ✓ Step 7/7: Verify Definition of Done... Passed
#
# ✅ Feature development complete!
#
# Session artifacts saved to: .ai/sessions/2025-11-27T14-30-00_feature-auth
# Review file: .ai/sessions/2025-11-27T14-30-00_feature-auth/REVIEW.md
#
# Next steps:
#   1. Review changes: git diff
#   2. Review artifacts: cat .ai/sessions/.../REVIEW.md
#   3. Test manually if needed
#   4. Commit: git commit -m "feat(auth): Add OAuth2 authentication"
```

### Example 2: Resume Failed Session

```bash
# Session failed at step "verify"
ai resume 2025-11-27T14-30-00_feature-auth --from-step verify

# Or resume from last failed step automatically
ai resume 2025-11-27T14-30-00_feature-auth --continue
```

### Example 3: Compare Sessions

```bash
# Compare two feature development sessions
ai diff-sessions \
  2025-11-25T10-00-00_feature-auth \
  2025-11-27T14-30-00_feature-auth

# Output:
# Session Comparison
# ==================
#
# Execution Time:
#   2025-11-25: 8m 32s
#   2025-11-27: 4m 15s (50% faster)
#
# Diff Budget:
#   2025-11-25: 12 files, +487/-45 lines
#   2025-11-27: 6 files, +289/-12 lines (40% smaller)
#
# Artifacts:
#   Both sessions produced all required artifacts
#
# Tests:
#   2025-11-25: 32 passed, 2 failed (had to retry)
#   2025-11-27: 34 passed, 0 failed
#
# Quality Improvements:
#   - Fewer files changed (better scoping)
#   - No test failures (better implementation)
#   - Faster execution (better prompts?)
```

---

## 📊 BENEFITS ANALYSIS

### For Individual Developers

**Before** (Manual AI Interaction):
- Copy/paste prompts repeatedly
- Forget steps in workflow
- No record of what worked
- Reinvent process each time
- Hard to onboard teammates

**After** (Playbook-Driven):
- One command runs entire workflow
- Consistent, repeatable process
- Full audit trail in `.ai/sessions/`
- Share workflows via git
- Teammates use same playbooks

### For Teams

**Before**:
- Everyone has their own "AI workflow"
- Inconsistent code quality
- No visibility into AI usage
- Hard to review AI-generated code
- Can't replay or debug sessions

**After**:
- Standardized workflows in `.ai/workflows/`
- Consistent quality via DoD checks
- Full transparency (artifacts + logs)
- Easy to review REVIEW.md artifacts
- Can replay any session exactly

### For Projects

**Before**:
- AI sessions are ephemeral knowledge
- No institutional memory
- Can't compare approaches
- Hard to improve over time
- Risky autonomous changes

**After**:
- Sessions become project memory
- Artifacts tracked in git
- Can diff and analyze sessions
- Continuous improvement via workflow evolution
- Guardrails prevent runaway changes

---

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: Foundation (4 weeks) - P0

**Week 1-2: Core Playbook System**
- ✓ playbook.py - Parser and validator
- ✓ variable_engine.py - {{var}} substitution
- ✓ artifact_manager.py - Artifact tracking
- ✓ session_manager.py - Session lifecycle
- ✓ Enhanced cli_orchestrator.py integration

**Week 3-4: Guardrails & Safety**
- ✓ diff_tracker.py - Track changes per step/session
- ✓ guardrail_enforcer.py - Safety constraints
- ✓ checks_runner.py - DoD validation
- ✓ rules_loader.py - Project rules injection

**Deliverables**:
- Basic playbook execution working
- Variable substitution functional
- Artifacts captured and stored
- Diff budget enforced
- Documentation + examples

### Phase 2: Advanced Features (3 weeks) - P1

**Week 5-6: Enhanced Capabilities**
- Resume from failed step
- Session comparison
- Parallel step execution
- Conditional branching (on_success, on_failure)
- Retry logic with backoff

**Week 7: Playbook Library**
- feature.yml - Feature development
- bugfix.yml - Bug fixing
- refactor.yml - Safe refactoring
- review.yml - Code review
- deploy.yml - Deployment checks
- testing.yml - Test generation

**Deliverables**:
- Resume/replay working
- 6+ production-ready playbooks
- Session diff tool
- Enhanced documentation

### Phase 3: Polish & Integration (2 weeks) - P1

**Week 8: CLI Enhancement**
```bash
ai init                    # Initialize .ai/ structure
ai list-workflows          # Show available playbooks
ai run <workflow>          # Execute playbook
ai resume <session>        # Resume from failure
ai diff-sessions <s1> <s2> # Compare sessions
ai show <session>          # Show session details
ai clean --days 90         # Clean old sessions
```

**Week 9: Documentation & Examples**
- Complete playbook guide
- Prompt pack documentation
- Migration guide (existing → playbook)
- Video tutorials
- Best practices guide

### Phase 4: Ecosystem (Ongoing) - P2

**Community Playbooks**:
- Public playbook repository
- Sharing and discovery
- Ratings and reviews
- Community contributions

**Integrations**:
- GitHub Actions (run playbooks in CI)
- VS Code extension (playbook runner)
- Slack notifications (session updates)
- Web dashboard (session history)

---

## 📈 SUCCESS METRICS

### Technical Metrics

- ✅ Can execute playbook from YAML in <100ms
- ✅ Variable substitution <1ms per variable
- ✅ Artifact capture <10ms per artifact
- ✅ Diff tracking <100ms
- ✅ Session resume from any step
- ✅ 100% playbook syntax validation

### Quality Metrics

- ✅ 10+ production-ready playbooks
- ✅ DoD checks prevent 90%+ of bad sessions
- ✅ Diff budget prevents scope creep
- ✅ All sessions fully auditable
- ✅ Session replay 100% deterministic

### User Experience Metrics

- ✅ Workflow setup <5 minutes
- ✅ Playbook creation <30 minutes
- ✅ Session comparison <10 seconds
- ✅ Clear error messages
- ✅ Comprehensive documentation

---

## 🎬 CONCLUSION

Integrating playbook concepts transforms MeTaCLIagenT from a CLI orchestration tool into a **comprehensive development session automation platform**. This provides:

✅ **Versioned, repeatable workflows** stored in git
✅ **Project memory** via artifacts
✅ **Controlled autonomy** via guardrails
✅ **Institutional knowledge** that evolves
✅ **Team standardization** on AI workflows

The implementation is well-scoped (9 weeks), builds on the solid existing foundation (70% complete), and delivers immediate value to both individual developers and teams.

**Next step**: Begin Phase 1 implementation (playbook parser + variable engine + artifact manager).

---

**Document Version**: 1.0.0
**Status**: Ready for Implementation
**Owner**: Development Team
**Timeline**: 9 weeks to production-ready
