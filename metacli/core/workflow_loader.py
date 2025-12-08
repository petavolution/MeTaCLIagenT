"""
YAML Workflow Loader - Load declarative workflows with template-based routing

Loads workflows from YAML files like production_scenarios.yaml and creates
executable OrchestratorWorkflow objects with automatic template-based routing.

Features:
- Parse YAML workflow definitions
- Extract and compile template libraries
- Create automatic routing decision functions
- Support for sequential and parallel steps
- Variable substitution and context management

Example YAML:
    templates:
      audit:
        - pattern: "identified.*issues"
          response: "load context about {issues}"
          priority: 10
        - pattern: "complete"
          response: "done"
          priority: 5

    workflow:
      - name: audit
        tool: claude-code
        prompt: "audit {target}"
        category: audit

      - name: load_context
        tool: claude-code
        prompt: "load context"
        category: context_loading

Example Usage:
    loader = WorkflowLoader()
    workflow = loader.load_from_yaml("workflows/audit-refactor.yaml")

    orchestrator = Orchestrator()
    context = orchestrator.execute(workflow, {"target": "src/"})
"""

from __future__ import annotations
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .orchestrator import (
    Orchestrator,
    Workflow as OrchestratorWorkflow,
    WorkflowStep,
    WorkflowContext,
    StepType,
)
from ..testing.templates import (
    ResponseTemplate,
    TemplateLibrary,
    ResponseMatcher,
    MatchStrategy,
)
from ..testing.realistic_parser import KeywordRouter


@dataclass
class YAMLWorkflowDefinition:
    """
    Parsed YAML workflow definition.

    Attributes:
        name: Workflow name
        description: Workflow description
        templates: Template definitions by category
        steps: Workflow step definitions
        global_templates: Global templates (apply to all steps)
        execution_config: Execution configuration
    """
    name: str
    description: str = ""
    templates: Dict[str, List[Dict[str, Any]]] = None
    steps: List[Dict[str, Any]] = None
    global_templates: List[Dict[str, Any]] = None
    execution_config: Dict[str, Any] = None

    def __post_init__(self):
        if self.templates is None:
            self.templates = {}
        if self.steps is None:
            self.steps = []
        if self.global_templates is None:
            self.global_templates = []
        if self.execution_config is None:
            self.execution_config = {}


class WorkflowLoader:
    """
    Load workflows from YAML with automatic template-based routing.

    Features:
    - Parse YAML workflow definitions
    - Compile template libraries
    - Create auto-routing decision functions
    - Support variables and context

    Example:
        loader = WorkflowLoader()
        workflow = loader.load_from_yaml("workflow.yaml")

        orchestrator = Orchestrator()
        context = orchestrator.execute(workflow, {"target": "src/"})
    """

    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        """
        Initialize loader.

        Args:
            orchestrator: Orchestrator instance (or create new one)
        """
        self.orchestrator = orchestrator or Orchestrator()
        self.template_libraries: Dict[str, TemplateLibrary] = {}

    def load_from_yaml(
        self,
        yaml_path: str,
        workflow_name: Optional[str] = None
    ) -> OrchestratorWorkflow:
        """
        Load workflow from YAML file.

        Args:
            yaml_path: Path to YAML file
            workflow_name: Specific workflow to load (if YAML has multiple)

        Returns:
            Compiled OrchestratorWorkflow
        """
        # Read YAML
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        # Parse workflow definition
        if 'scenarios' in data:
            # Multiple scenarios in file
            scenarios = data['scenarios']
            if workflow_name:
                # Find specific scenario
                scenario = next(
                    (s for s in scenarios if s.get('name') == workflow_name),
                    scenarios[0] if scenarios else None
                )
            else:
                # Use first scenario
                scenario = scenarios[0] if scenarios else {}

            # Create definition
            definition = YAMLWorkflowDefinition(
                name=scenario.get('name', 'workflow'),
                description=scenario.get('description', ''),
                templates=data.get('templates', {}),
                steps=scenario.get('steps', []),
                global_templates=data.get('global_templates', []),
                execution_config=data.get('execution', {})
            )
        else:
            # Single workflow definition
            definition = YAMLWorkflowDefinition(
                name=data.get('name', 'workflow'),
                description=data.get('description', ''),
                templates=data.get('templates', {}),
                steps=data.get('workflow', []) or data.get('steps', []),
                global_templates=data.get('global_templates', []),
                execution_config=data.get('execution', {})
            )

        # Compile workflow
        return self.compile_workflow(definition)

    def compile_workflow(
        self,
        definition: YAMLWorkflowDefinition
    ) -> OrchestratorWorkflow:
        """
        Compile YAML definition into executable workflow.

        Args:
            definition: Parsed YAML workflow definition

        Returns:
            Compiled OrchestratorWorkflow
        """
        # Create workflow
        workflow = self.orchestrator.create_workflow(
            name=definition.name,
            description=definition.description
        )

        # Build template library
        template_lib = self._build_template_library(definition.templates)
        self.template_libraries[definition.name] = template_lib

        # Compile steps
        for i, step_def in enumerate(definition.steps):
            self._add_step_to_workflow(workflow, step_def, template_lib, i)

        # Configure execution
        if definition.execution_config:
            defaults = definition.execution_config.get('defaults', {})
            if 'timeout_per_step' in defaults:
                # Store in workflow metadata
                workflow.steps[0].metadata['default_timeout'] = defaults['timeout_per_step']

        return workflow

    def _build_template_library(
        self,
        templates_def: Dict[str, List[Dict[str, Any]]]
    ) -> TemplateLibrary:
        """
        Build template library from YAML templates.

        Args:
            templates_def: Templates organized by category

        Returns:
            TemplateLibrary
        """
        library = TemplateLibrary()

        for category, template_list in templates_def.items():
            for tmpl_def in template_list:
                template = self._parse_template(tmpl_def, category)
                library.add_template(template)

        return library

    def _parse_template(
        self,
        tmpl_def: Dict[str, Any],
        category: str
    ) -> ResponseTemplate:
        """
        Parse single template definition.

        Args:
            tmpl_def: Template definition dict
            category: Template category

        Returns:
            ResponseTemplate
        """
        # Determine strategy
        strategy_str = tmpl_def.get('strategy', 'regex')
        strategy_map = {
            'regex': MatchStrategy.REGEX,
            'contains': MatchStrategy.CONTAINS,
            'exact': MatchStrategy.EXACT,
            'fuzzy': MatchStrategy.FUZZY,
        }
        strategy = strategy_map.get(strategy_str, MatchStrategy.REGEX)

        # Create template
        template = ResponseTemplate(
            name=tmpl_def.get('name', 'template'),
            pattern=tmpl_def.get('pattern', ''),
            response=tmpl_def.get('response', 'continue'),
            strategy=strategy,
            priority=tmpl_def.get('priority', 0),
            metadata={
                'category': category,
                'keywords': tmpl_def.get('keywords', []),
            }
        )

        return template

    def _add_step_to_workflow(
        self,
        workflow: OrchestratorWorkflow,
        step_def: Dict[str, Any],
        template_lib: TemplateLibrary,
        step_index: int
    ):
        """
        Add step to workflow based on definition.

        Args:
            workflow: Workflow to add step to
            step_def: Step definition dict
            template_lib: Template library for routing
            step_index: Step index (for auto-naming)
        """
        step_name = step_def.get('name', f'step_{step_index}')
        tool = step_def.get('tool')
        prompt = step_def.get('prompt', '')
        category = step_def.get('category', 'default')

        # Add execution step
        workflow.add_step(
            name=step_name,
            tool=tool,
            prompt_template=prompt,
            retry_on_error=step_def.get('retry_on_error', False)
        )

        # Add automatic routing decision if not last step
        if step_index < len(workflow.steps) - 1:
            decision_func = self._create_auto_routing_decision(
                template_lib,
                category,
                step_name
            )

            workflow.add_decision(
                name=f"{step_name}_route",
                decision_func=decision_func
            )

    def _create_auto_routing_decision(
        self,
        template_lib: TemplateLibrary,
        category: str,
        current_step: str
    ) -> Callable[[WorkflowContext], str]:
        """
        Create automatic routing decision function.

        Args:
            template_lib: Template library for matching
            category: Step category for template filtering
            current_step: Current step name

        Returns:
            Decision function
        """
        def auto_route(ctx: WorkflowContext) -> str:
            """Automatically route based on template matching."""
            last_result = ctx.get_last_result()

            if not last_result:
                return "done"

            # Get output
            output = last_result.raw_output
            if last_result.parsed_output:
                output = last_result.parsed_output.decoded_text

            # Find matching templates
            matcher = ResponseMatcher(template_lib)
            matches = matcher.find_matches(output, category=category)

            if matches:
                # Use highest priority match
                best_match = matches[0]
                next_step = best_match.response

                # Store match info in context
                ctx.set('last_match', best_match.name)
                ctx.set('last_match_pattern', best_match.pattern)

                return next_step

            # Default: continue to next step
            return "done"

        return auto_route

    def load_all_scenarios(
        self,
        yaml_path: str
    ) -> List[OrchestratorWorkflow]:
        """
        Load all scenarios from YAML file.

        Args:
            yaml_path: Path to YAML file with multiple scenarios

        Returns:
            List of compiled workflows
        """
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        workflows = []

        if 'scenarios' in data:
            for scenario in data['scenarios']:
                definition = YAMLWorkflowDefinition(
                    name=scenario.get('name', 'workflow'),
                    description=scenario.get('description', ''),
                    templates=data.get('templates', {}),
                    steps=scenario.get('steps', []),
                    global_templates=data.get('global_templates', []),
                    execution_config=data.get('execution', {})
                )
                workflow = self.compile_workflow(definition)
                workflows.append(workflow)

        return workflows


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def load_workflow(
    yaml_path: str,
    workflow_name: Optional[str] = None,
    orchestrator: Optional[Orchestrator] = None
) -> OrchestratorWorkflow:
    """
    Convenience function to load workflow from YAML.

    Args:
        yaml_path: Path to YAML file
        workflow_name: Specific workflow to load
        orchestrator: Orchestrator instance

    Returns:
        Compiled workflow
    """
    loader = WorkflowLoader(orchestrator)
    return loader.load_from_yaml(yaml_path, workflow_name)


def load_all_workflows(
    yaml_path: str,
    orchestrator: Optional[Orchestrator] = None
) -> List[OrchestratorWorkflow]:
    """
    Load all workflows from YAML file.

    Args:
        yaml_path: Path to YAML file
        orchestrator: Orchestrator instance

    Returns:
        List of compiled workflows
    """
    loader = WorkflowLoader(orchestrator)
    return loader.load_all_scenarios(yaml_path)
