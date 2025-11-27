# prompts.py - Prompt Template System
"""
Flexible prompt template system for EATS agents.

Features:
- Variable substitution with {var} syntax
- Prompt library with common templates
- Chain-of-thought formatting
- Few-shot example management
- System/user message composition
- Template inheritance and composition

Zero external dependencies beyond standard library.
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum, auto


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PromptStyle(Enum):
    """Prompt formatting styles."""
    DIRECT = auto()        # Simple direct instruction
    CHAIN_OF_THOUGHT = auto()  # Step-by-step reasoning
    FEW_SHOT = auto()      # Examples before task
    STRUCTURED = auto()    # JSON/structured output
    PERSONA = auto()       # Role-based prompting


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class Example:
    """A few-shot example."""
    input: str
    output: str
    explanation: Optional[str] = None

    def format(self, input_label: str = "Input", output_label: str = "Output") -> str:
        parts = [f"{input_label}: {self.input}"]
        if self.explanation:
            parts.append(f"Reasoning: {self.explanation}")
        parts.append(f"{output_label}: {self.output}")
        return "\n".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Template
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PromptTemplate:
    """
    Flexible prompt template with variable substitution.

    Usage:
        template = PromptTemplate(
            "Analyze this code and find bugs:\\n\\n{code}\\n\\nFocus on: {focus_areas}"
        )

        prompt = template.format(
            code="def foo(): pass",
            focus_areas="security, performance"
        )
    """

    # Regex for {variable} and {variable:default} patterns
    VAR_PATTERN = re.compile(r'\{(\w+)(?::([^}]*))?\}')

    def __init__(
        self,
        template: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        required_vars: Optional[List[str]] = None,
        defaults: Optional[Dict[str, Any]] = None,
        validators: Optional[Dict[str, Callable[[Any], bool]]] = None,
    ):
        self.template = template
        self.name = name
        self.description = description
        self.defaults = defaults or {}
        self.validators = validators or {}

        # Extract variables from template
        self._variables = self._extract_variables()

        # Override with explicit required vars if provided
        self.required_vars = set(required_vars) if required_vars else self._variables

    def _extract_variables(self) -> set:
        """Extract variable names from template."""
        variables = set()
        for match in self.VAR_PATTERN.finditer(self.template):
            var_name = match.group(1)
            default = match.group(2)
            variables.add(var_name)
            if default is not None:
                self.defaults[var_name] = default
        return variables

    def format(self, **kwargs) -> str:
        """Format template with provided variables."""
        # Merge defaults with provided kwargs
        values = {**self.defaults, **kwargs}

        # Check required variables
        missing = self.required_vars - set(values.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Validate values
        for var, validator in self.validators.items():
            if var in values and not validator(values[var]):
                raise ValueError(f"Validation failed for variable: {var}")

        # Perform substitution
        def replace(match):
            var_name = match.group(1)
            value = values.get(var_name, match.group(0))
            return str(value) if value is not None else ""

        return self.VAR_PATTERN.sub(replace, self.template)

    def partial(self, **kwargs) -> 'PromptTemplate':
        """Create a new template with some variables filled in."""
        new_defaults = {**self.defaults, **kwargs}
        new_required = self.required_vars - set(kwargs.keys())

        return PromptTemplate(
            template=self.template,
            name=self.name,
            description=self.description,
            required_vars=list(new_required),
            defaults=new_defaults,
            validators=self.validators,
        )

    def __add__(self, other: Union[str, 'PromptTemplate']) -> 'PromptTemplate':
        """Concatenate templates."""
        if isinstance(other, str):
            return PromptTemplate(self.template + other)
        return PromptTemplate(
            self.template + other.template,
            defaults={**self.defaults, **other.defaults},
        )

    def __repr__(self) -> str:
        return f"PromptTemplate(name={self.name!r}, vars={self._variables})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Builder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PromptBuilder:
    """
    Fluent interface for building complex prompts.

    Usage:
        prompt = (
            PromptBuilder()
            .system("You are an expert code reviewer.")
            .context("Repository: {repo_name}")
            .task("Review this code for bugs and improvements.")
            .input_section("Code to review:", "{code}")
            .output_format("json", {"bugs": [], "suggestions": []})
            .chain_of_thought()
            .build()
        )
    """

    def __init__(self):
        self._system: Optional[str] = None
        self._context: List[str] = []
        self._task: Optional[str] = None
        self._examples: List[Example] = []
        self._input_sections: List[tuple] = []
        self._output_format: Optional[str] = None
        self._constraints: List[str] = []
        self._chain_of_thought: bool = False
        self._persona: Optional[str] = None
        self._variables: Dict[str, Any] = {}

    def system(self, instruction: str) -> 'PromptBuilder':
        """Set system instruction."""
        self._system = instruction
        return self

    def persona(self, role: str, expertise: Optional[str] = None) -> 'PromptBuilder':
        """Set agent persona/role."""
        if expertise:
            self._persona = f"You are a {role} with expertise in {expertise}."
        else:
            self._persona = f"You are a {role}."
        return self

    def context(self, ctx: str) -> 'PromptBuilder':
        """Add context information."""
        self._context.append(ctx)
        return self

    def task(self, description: str) -> 'PromptBuilder':
        """Set the main task description."""
        self._task = description
        return self

    def example(
        self,
        input_text: str,
        output_text: str,
        explanation: Optional[str] = None
    ) -> 'PromptBuilder':
        """Add a few-shot example."""
        self._examples.append(Example(input_text, output_text, explanation))
        return self

    def examples(self, examples: List[Example]) -> 'PromptBuilder':
        """Add multiple examples."""
        self._examples.extend(examples)
        return self

    def input_section(self, label: str, content: str) -> 'PromptBuilder':
        """Add an input section."""
        self._input_sections.append((label, content))
        return self

    def output_format(
        self,
        format_type: str,
        schema: Optional[Dict] = None,
        example: Optional[str] = None
    ) -> 'PromptBuilder':
        """Specify expected output format."""
        if format_type == "json" and schema:
            schema_str = json.dumps(schema, indent=2)
            self._output_format = f"Respond with valid JSON matching this schema:\n```json\n{schema_str}\n```"
        elif format_type == "markdown":
            self._output_format = "Format your response in Markdown."
        elif format_type == "code":
            lang = schema.get("language", "") if schema else ""
            self._output_format = f"Respond with code only, no explanation. Use ```{lang}``` blocks."
        elif example:
            self._output_format = f"Format your response like this example:\n{example}"
        else:
            self._output_format = format_type
        return self

    def constraint(self, rule: str) -> 'PromptBuilder':
        """Add a constraint/rule."""
        self._constraints.append(rule)
        return self

    def constraints(self, rules: List[str]) -> 'PromptBuilder':
        """Add multiple constraints."""
        self._constraints.extend(rules)
        return self

    def chain_of_thought(self, enabled: bool = True) -> 'PromptBuilder':
        """Enable chain-of-thought reasoning."""
        self._chain_of_thought = enabled
        return self

    def var(self, name: str, value: Any) -> 'PromptBuilder':
        """Set a template variable."""
        self._variables[name] = value
        return self

    def vars(self, **kwargs) -> 'PromptBuilder':
        """Set multiple template variables."""
        self._variables.update(kwargs)
        return self

    def build(self) -> PromptTemplate:
        """Build the final prompt template."""
        parts = []

        # Persona/System
        if self._persona:
            parts.append(self._persona)
        if self._system:
            parts.append(self._system)

        # Context
        if self._context:
            parts.append("\n## Context\n" + "\n".join(self._context))

        # Task
        if self._task:
            parts.append(f"\n## Task\n{self._task}")

        # Examples (few-shot)
        if self._examples:
            parts.append("\n## Examples")
            for i, ex in enumerate(self._examples, 1):
                parts.append(f"\n### Example {i}")
                parts.append(ex.format())

        # Input sections
        for label, content in self._input_sections:
            parts.append(f"\n## {label}\n{content}")

        # Constraints
        if self._constraints:
            parts.append("\n## Constraints")
            for c in self._constraints:
                parts.append(f"- {c}")

        # Output format
        if self._output_format:
            parts.append(f"\n## Output Format\n{self._output_format}")

        # Chain of thought
        if self._chain_of_thought:
            parts.append("\n## Instructions\nThink through this step-by-step:")
            parts.append("1. First, understand the problem")
            parts.append("2. Break it down into parts")
            parts.append("3. Solve each part")
            parts.append("4. Synthesize the final answer")

        template_str = "\n".join(parts)

        return PromptTemplate(
            template=template_str,
            defaults=self._variables,
        )

    def build_messages(self) -> List[Message]:
        """Build as a list of messages for chat APIs."""
        messages = []

        # System message
        system_parts = []
        if self._persona:
            system_parts.append(self._persona)
        if self._system:
            system_parts.append(self._system)
        if self._constraints:
            system_parts.append("Constraints: " + "; ".join(self._constraints))
        if self._output_format:
            system_parts.append(self._output_format)

        if system_parts:
            messages.append(Message("system", "\n\n".join(system_parts)))

        # Few-shot examples as conversation
        for ex in self._examples:
            messages.append(Message("user", ex.input))
            messages.append(Message("assistant", ex.output))

        # User message with context, task, and inputs
        user_parts = []
        if self._context:
            user_parts.append("Context:\n" + "\n".join(self._context))
        if self._task:
            user_parts.append(f"Task: {self._task}")
        for label, content in self._input_sections:
            user_parts.append(f"{label}\n{content}")
        if self._chain_of_thought:
            user_parts.append("Think step-by-step before providing your answer.")

        if user_parts:
            messages.append(Message("user", "\n\n".join(user_parts)))

        return messages


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Prompt Library - Common Templates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PromptLibrary:
    """
    Collection of pre-built prompt templates for common tasks.

    Usage:
        lib = PromptLibrary()

        # Use a built-in template
        prompt = lib.code_review.format(code="...", language="python")

        # Register custom template
        lib.register("my_template", PromptTemplate("..."))
    """

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default templates."""

        # Code review
        self._templates["code_review"] = PromptTemplate(
            """Review this {language} code for:
1. Bugs and potential errors
2. Security vulnerabilities
3. Performance issues
4. Code style and best practices

Code:
```{language}
{code}
```

Provide specific, actionable feedback with line numbers where applicable.""",
            name="code_review",
            description="General code review template",
        )

        # Bug fix
        self._templates["bug_fix"] = PromptTemplate(
            """Fix the bug in this code.

Error message:
{error}

Code:
```{language}
{code}
```

Provide:
1. Root cause analysis
2. Fixed code
3. Explanation of the fix""",
            name="bug_fix",
            description="Bug fixing template",
        )

        # Code generation
        self._templates["code_gen"] = PromptTemplate(
            """Write {language} code that implements the following:

{specification}

Requirements:
{requirements:- Follow best practices}

Provide clean, well-documented code.""",
            name="code_gen",
            description="Code generation template",
        )

        # Explanation
        self._templates["explain"] = PromptTemplate(
            """Explain this code in detail:

```{language}
{code}
```

Explain:
1. What the code does at a high level
2. How it works step by step
3. Any notable patterns or techniques used
4. Potential edge cases or limitations""",
            name="explain",
            description="Code explanation template",
        )

        # Refactor
        self._templates["refactor"] = PromptTemplate(
            """Refactor this code to improve {focus}:

```{language}
{code}
```

Focus areas: {focus}

Constraints:
- Maintain existing functionality
- Keep the same interface/API
{additional_constraints:}

Provide the refactored code with explanations for each change.""",
            name="refactor",
            description="Code refactoring template",
        )

        # Test generation
        self._templates["test_gen"] = PromptTemplate(
            """Generate comprehensive tests for this code:

```{language}
{code}
```

Use testing framework: {framework:pytest}

Include:
- Unit tests for each function/method
- Edge cases
- Error conditions
- Integration tests if applicable""",
            name="test_gen",
            description="Test generation template",
        )

        # Documentation
        self._templates["document"] = PromptTemplate(
            """Generate documentation for this code:

```{language}
{code}
```

Documentation style: {style:docstring}

Include:
- Module/class/function descriptions
- Parameter documentation
- Return value documentation
- Usage examples""",
            name="document",
            description="Documentation generation template",
        )

        # Comparison/Analysis
        self._templates["compare"] = PromptTemplate(
            """Compare these two solutions:

Solution A:
```
{solution_a}
```

Solution B:
```
{solution_b}
```

Evaluate based on: {criteria:correctness, efficiency, readability, maintainability}

Provide a detailed comparison and recommend which solution is better.""",
            name="compare",
            description="Solution comparison template",
        )

        # Planning
        self._templates["plan"] = PromptTemplate(
            """Create an implementation plan for:

{task_description}

Context:
{context:Not provided}

Provide:
1. High-level approach
2. Step-by-step implementation plan
3. Potential challenges and mitigations
4. Estimated complexity""",
            name="plan",
            description="Implementation planning template",
        )

        # Chain of thought reasoning
        self._templates["reason"] = PromptTemplate(
            """Solve this problem step by step:

{problem}

Think through each step carefully:
1. Understand what's being asked
2. Identify key information and constraints
3. Consider possible approaches
4. Work through the solution
5. Verify the answer

Show your reasoning at each step.""",
            name="reason",
            description="Chain-of-thought reasoning template",
        )

        # JSON extraction
        self._templates["extract_json"] = PromptTemplate(
            """Extract structured information from this text:

{text}

Extract into this JSON format:
```json
{schema}
```

Return ONLY valid JSON, no additional text.""",
            name="extract_json",
            description="JSON extraction template",
        )

        # Summarization
        self._templates["summarize"] = PromptTemplate(
            """Summarize the following content:

{content}

Summary requirements:
- Length: {length:medium} ({length_hint:2-3 paragraphs})
- Focus on: {focus:key points}
- Style: {style:professional}""",
            name="summarize",
            description="Summarization template",
        )

    def register(self, name: str, template: PromptTemplate) -> None:
        """Register a new template."""
        self._templates[name] = template

    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def __getattr__(self, name: str) -> PromptTemplate:
        """Access templates as attributes."""
        if name.startswith('_'):
            raise AttributeError(name)
        template = self._templates.get(name)
        if template is None:
            raise AttributeError(f"No template named: {name}")
        return template

    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self._templates.keys())

    def describe(self, name: str) -> Optional[str]:
        """Get template description."""
        template = self._templates.get(name)
        return template.description if template else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent-Specific Prompts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AgentPromptConfig:
    """Configuration for agent-specific prompts."""
    role: str
    base_system: str
    task_template: PromptTemplate
    examples: List[Example] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    output_format: Optional[str] = None


# Pre-configured agent prompts
AGENT_PROMPTS: Dict[str, AgentPromptConfig] = {
    "coder": AgentPromptConfig(
        role="Senior Software Engineer",
        base_system="You are an expert programmer. Write clean, efficient, well-documented code.",
        task_template=PromptTemplate(
            "Implement the following:\n\n{specification}\n\nLanguage: {language:python}"
        ),
        constraints=[
            "Follow language-specific best practices",
            "Include error handling",
            "Write self-documenting code",
        ],
    ),
    "reviewer": AgentPromptConfig(
        role="Code Review Specialist",
        base_system="You are an expert code reviewer focused on quality, security, and best practices.",
        task_template=PromptTemplate(
            "Review this code:\n```{language}\n{code}\n```"
        ),
        constraints=[
            "Be specific and actionable",
            "Reference line numbers",
            "Suggest improvements, not just criticisms",
        ],
        output_format="json",
    ),
    "tester": AgentPromptConfig(
        role="QA Engineer",
        base_system="You are a testing expert who writes comprehensive test suites.",
        task_template=PromptTemplate(
            "Write tests for:\n```{language}\n{code}\n```\n\nFramework: {framework:pytest}"
        ),
        constraints=[
            "Cover edge cases",
            "Test error conditions",
            "Use meaningful test names",
        ],
    ),
    "architect": AgentPromptConfig(
        role="Software Architect",
        base_system="You are a senior architect who designs scalable, maintainable systems.",
        task_template=PromptTemplate(
            "Design a solution for:\n\n{requirements}\n\nConstraints: {constraints:none specified}"
        ),
        constraints=[
            "Consider scalability",
            "Plan for extensibility",
            "Document trade-offs",
        ],
    ),
    "debugger": AgentPromptConfig(
        role="Debug Specialist",
        base_system="You are an expert at finding and fixing bugs in code.",
        task_template=PromptTemplate(
            "Debug this issue:\n\nError: {error}\n\nCode:\n```{language}\n{code}\n```"
        ),
        constraints=[
            "Identify root cause",
            "Explain the bug clearly",
            "Provide a tested fix",
        ],
    ),
}


def get_agent_prompt(
    agent_type: str,
    **kwargs
) -> str:
    """Get a formatted prompt for a specific agent type."""
    config = AGENT_PROMPTS.get(agent_type)
    if not config:
        raise ValueError(f"Unknown agent type: {agent_type}")

    builder = PromptBuilder()
    builder.persona(config.role)
    builder.system(config.base_system)
    builder.constraints(config.constraints)

    if config.output_format:
        builder.output_format(config.output_format)

    for ex in config.examples:
        builder.example(ex.input, ex.output, ex.explanation)

    # Build base and format with kwargs
    base_prompt = builder.build()
    task_prompt = config.task_template.format(**kwargs)

    return base_prompt.format() + "\n\n" + task_prompt


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Utility Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def chain_prompts(*templates: PromptTemplate, separator: str = "\n\n") -> PromptTemplate:
    """Chain multiple templates together."""
    combined = separator.join(t.template for t in templates)
    merged_defaults = {}
    for t in templates:
        merged_defaults.update(t.defaults)
    return PromptTemplate(combined, defaults=merged_defaults)


def format_code_block(code: str, language: str = "") -> str:
    """Format code in a markdown code block."""
    return f"```{language}\n{code}\n```"


def format_json_schema(schema: Dict) -> str:
    """Format a JSON schema for inclusion in prompts."""
    return f"```json\n{json.dumps(schema, indent=2)}\n```"


def truncate_for_prompt(text: str, max_length: int = 4000, suffix: str = "...") -> str:
    """Truncate text to fit in prompt, preserving structure."""
    if len(text) <= max_length:
        return text

    # Try to truncate at a natural boundary
    truncate_at = max_length - len(suffix)

    # Look for paragraph break
    last_para = text.rfind("\n\n", 0, truncate_at)
    if last_para > truncate_at * 0.5:
        return text[:last_para] + suffix

    # Look for line break
    last_line = text.rfind("\n", 0, truncate_at)
    if last_line > truncate_at * 0.5:
        return text[:last_line] + suffix

    # Hard truncate
    return text[:truncate_at] + suffix


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Library Instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_library: Optional[PromptLibrary] = None


def get_prompt_library() -> PromptLibrary:
    """Get the global prompt library instance."""
    global _library
    if _library is None:
        _library = PromptLibrary()
    return _library


def get_template(name: str) -> PromptTemplate:
    """Get a template from the global library."""
    return get_prompt_library().get(name)


# Convenience exports
def code_review(code: str, language: str = "python") -> str:
    """Generate a code review prompt."""
    return get_prompt_library().code_review.format(code=code, language=language)


def bug_fix(code: str, error: str, language: str = "python") -> str:
    """Generate a bug fix prompt."""
    return get_prompt_library().bug_fix.format(code=code, error=error, language=language)


def explain(code: str, language: str = "python") -> str:
    """Generate a code explanation prompt."""
    return get_prompt_library().explain.format(code=code, language=language)
