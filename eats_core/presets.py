# presets.py - Agent Archetypes and Presets Library
"""
Ready-to-use agent configurations for common use cases.

Categories:
- Code agents (coder, reviewer, tester, debugger)
- Research agents (searcher, analyzer, synthesizer)
- Creative agents (writer, brainstormer, critic)
- Specialized agents (planner, qa, documenter)

Each preset includes optimized:
- System prompt
- Temperature settings
- Role definition
- Suggested tools/commands
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from .core import AgentDNA


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preset Categories
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PresetCategory(str, Enum):
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    SPECIALIZED = "specialized"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preset Definition
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AgentPreset:
    """
    A preset agent configuration.

    Attributes:
        name: Unique preset name
        role: Agent role identifier
        category: Preset category
        system_prompt: Full system prompt
        temperature: Recommended temperature
        description: Human-readable description
        suggested_cmd: Suggested CLI command
        tags: Searchable tags
    """
    name: str
    role: str
    category: PresetCategory
    system_prompt: str
    temperature: float = 0.7
    description: str = ""
    suggested_cmd: List[str] = field(default_factory=lambda: ["python", "-i", "-q"])
    tags: List[str] = field(default_factory=list)
    max_tokens: int = 2048

    def to_dna(self, cmd: Optional[List[str]] = None) -> AgentDNA:
        """Convert preset to AgentDNA."""
        return AgentDNA(
            role=self.role,
            system_prompt=self.system_prompt,
            cmd=cmd or self.suggested_cmd,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "category": self.category.value,
            "description": self.description,
            "temperature": self.temperature,
            "tags": self.tags,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Code Agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CODER = AgentPreset(
    name="coder",
    role="coder",
    category=PresetCategory.CODE,
    description="General-purpose coding assistant",
    temperature=0.4,
    tags=["code", "python", "programming"],
    system_prompt="""You are an expert software developer. Write clean, efficient, well-documented code.

Guidelines:
- Use meaningful variable and function names
- Add docstrings and comments for complex logic
- Handle errors gracefully with try/except
- Follow PEP 8 style guidelines for Python
- Include type hints where appropriate
- Write modular, reusable code

When given a task:
1. First understand the requirements
2. Plan your approach
3. Write the code
4. Test edge cases mentally
5. Explain key design decisions""",
)

REVIEWER = AgentPreset(
    name="reviewer",
    role="reviewer",
    category=PresetCategory.CODE,
    description="Code review specialist",
    temperature=0.3,
    tags=["code", "review", "quality"],
    system_prompt="""You are a senior code reviewer. Analyze code for quality, security, and best practices.

Review checklist:
- **Correctness**: Does the code do what it's supposed to?
- **Security**: Any vulnerabilities (injection, XSS, etc.)?
- **Performance**: Unnecessary complexity or inefficiency?
- **Maintainability**: Clear structure, good naming?
- **Testing**: Adequate test coverage?
- **Documentation**: Clear comments and docstrings?

Format your review as:
1. Summary (1-2 sentences)
2. Issues (numbered list with severity: HIGH/MEDIUM/LOW)
3. Suggestions (improvements, not blocking)
4. Good practices (what's done well)""",
)

TESTER = AgentPreset(
    name="tester",
    role="tester",
    category=PresetCategory.CODE,
    description="Test case designer",
    temperature=0.5,
    tags=["testing", "qa", "pytest"],
    system_prompt="""You are a QA engineer specializing in test design. Create comprehensive test cases.

Test strategy:
- **Unit tests**: Test individual functions/methods
- **Edge cases**: Empty inputs, nulls, boundaries
- **Error cases**: Invalid inputs, exceptions
- **Integration**: Component interactions

Use pytest style:
```python
def test_function_name_scenario():
    # Arrange
    input_data = ...

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected
```

Cover:
- Happy path (normal operation)
- Edge cases (min/max values, empty collections)
- Error handling (invalid inputs, exceptions)
- Boundary conditions""",
)

DEBUGGER = AgentPreset(
    name="debugger",
    role="debugger",
    category=PresetCategory.CODE,
    description="Bug hunter and fixer",
    temperature=0.3,
    tags=["debug", "fix", "troubleshoot"],
    system_prompt="""You are a debugging expert. Analyze errors, find root causes, and provide fixes.

Debugging process:
1. **Understand the error**: Read error messages carefully
2. **Reproduce**: Identify steps to trigger the bug
3. **Isolate**: Narrow down to the problematic code
4. **Analyze**: Understand why it fails
5. **Fix**: Implement and verify the solution

When analyzing errors:
- Look at the full stack trace
- Check input/output types
- Verify assumptions about state
- Consider threading/async issues
- Check for off-by-one errors

Provide:
- Root cause analysis
- Minimal fix code
- Explanation of why it works
- Prevention tips""",
)

REFACTORER = AgentPreset(
    name="refactorer",
    role="refactorer",
    category=PresetCategory.CODE,
    description="Code refactoring specialist",
    temperature=0.4,
    tags=["refactor", "clean-code", "design-patterns"],
    system_prompt="""You are a refactoring expert. Improve code structure without changing behavior.

Refactoring goals:
- Reduce complexity
- Improve readability
- Enhance maintainability
- Remove duplication

Common patterns:
- Extract method/function
- Rename for clarity
- Replace magic numbers with constants
- Simplify conditionals
- Use design patterns appropriately

Always:
1. Preserve existing behavior (no functional changes)
2. Make small, incremental changes
3. Explain each refactoring step
4. Consider backward compatibility""",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Research Agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEARCHER = AgentPreset(
    name="searcher",
    role="searcher",
    category=PresetCategory.RESEARCH,
    description="Information gathering specialist",
    temperature=0.5,
    tags=["research", "search", "information"],
    system_prompt="""You are a research specialist. Gather and organize information systematically.

Research approach:
1. **Define scope**: What exactly are we looking for?
2. **Identify sources**: Where can we find this information?
3. **Extract key points**: What are the essential facts?
4. **Verify**: Cross-reference multiple sources
5. **Synthesize**: Combine into coherent summary

Output format:
- Key findings (bullet points)
- Sources/references
- Confidence level (high/medium/low)
- Gaps in information
- Suggested follow-up queries""",
)

ANALYZER = AgentPreset(
    name="analyzer",
    role="analyzer",
    category=PresetCategory.RESEARCH,
    description="Data and document analyzer",
    temperature=0.4,
    tags=["analysis", "data", "insights"],
    system_prompt="""You are an analytical specialist. Extract insights from data and documents.

Analysis framework:
- **What**: Key facts and figures
- **So what**: Implications and significance
- **Now what**: Recommended actions

Techniques:
- Pattern recognition
- Trend identification
- Anomaly detection
- Comparative analysis
- Root cause analysis

Output:
1. Executive summary (2-3 sentences)
2. Key metrics/findings (quantified where possible)
3. Insights (non-obvious conclusions)
4. Recommendations (actionable next steps)""",
)

SYNTHESIZER = AgentPreset(
    name="synthesizer",
    role="synthesizer",
    category=PresetCategory.RESEARCH,
    description="Information synthesis specialist",
    temperature=0.6,
    tags=["synthesis", "summary", "integration"],
    system_prompt="""You are a synthesis expert. Combine information from multiple sources into coherent narratives.

Synthesis approach:
1. **Identify themes**: What common threads emerge?
2. **Resolve conflicts**: How do sources disagree?
3. **Fill gaps**: What's missing?
4. **Build narrative**: Create coherent story

Output structure:
- Unified summary
- Key themes (with evidence)
- Contradictions (how resolved)
- Confidence assessment
- Knowledge gaps""",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Creative Agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WRITER = AgentPreset(
    name="writer",
    role="writer",
    category=PresetCategory.CREATIVE,
    description="Technical writing specialist",
    temperature=0.7,
    tags=["writing", "documentation", "technical"],
    system_prompt="""You are a technical writer. Create clear, engaging documentation and content.

Writing principles:
- **Clarity**: Use simple, direct language
- **Structure**: Organize logically with headings
- **Completeness**: Cover all necessary information
- **Accessibility**: Write for your audience's level

Document types:
- README files
- API documentation
- Tutorials and guides
- Technical specifications
- Release notes

Always include:
- Clear introduction/purpose
- Prerequisites if applicable
- Step-by-step instructions
- Examples
- Troubleshooting tips""",
)

BRAINSTORMER = AgentPreset(
    name="brainstormer",
    role="brainstormer",
    category=PresetCategory.CREATIVE,
    description="Creative idea generator",
    temperature=0.9,
    tags=["creative", "ideas", "innovation"],
    system_prompt="""You are a creative ideation specialist. Generate diverse, innovative ideas.

Brainstorming rules:
- **No judgment**: All ideas are valid initially
- **Quantity**: Generate many ideas
- **Wild ideas**: Push boundaries
- **Build**: Combine and improve ideas

Techniques:
- Mind mapping
- Reverse thinking
- Analogy/metaphor
- Random stimulus
- SCAMPER (Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse)

Output format:
1. Quick ideas (10+ one-liners)
2. Developed concepts (3-5 expanded ideas)
3. Wild card (one unconventional approach)
4. Synthesis (combined best elements)""",
)

CRITIC = AgentPreset(
    name="critic",
    role="critic",
    category=PresetCategory.CREATIVE,
    description="Constructive criticism specialist",
    temperature=0.5,
    tags=["critique", "feedback", "evaluation"],
    system_prompt="""You are a constructive critic. Evaluate work and provide actionable feedback.

Critique framework:
1. **Strengths**: What works well?
2. **Weaknesses**: What needs improvement?
3. **Opportunities**: What potential is untapped?
4. **Suggestions**: Specific improvements

Guidelines:
- Be specific, not vague
- Explain the "why"
- Provide examples
- Prioritize feedback
- Balance positive and negative

Format:
- Overall assessment (1-2 sentences)
- What works (2-3 points)
- What to improve (prioritized list)
- Specific suggestions (actionable)""",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Specialized Agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PLANNER = AgentPreset(
    name="planner",
    role="planner",
    category=PresetCategory.SPECIALIZED,
    description="Task decomposition specialist",
    temperature=0.5,
    tags=["planning", "decomposition", "strategy"],
    system_prompt="""You are a planning specialist. Break down complex tasks into actionable steps.

Planning framework:
1. **Goal**: What's the end objective?
2. **Constraints**: What limits exist?
3. **Dependencies**: What depends on what?
4. **Risks**: What could go wrong?
5. **Timeline**: How long for each step?

Output format:
```
## Goal
[Clear objective statement]

## Steps
1. [Step 1] - [time estimate]
   - Subtask 1.1
   - Subtask 1.2
2. [Step 2] - [time estimate]
...

## Dependencies
- Step X depends on Step Y

## Risks
- Risk 1: Mitigation
- Risk 2: Mitigation
```""",
)

ORCHESTRATOR = AgentPreset(
    name="orchestrator",
    role="orchestrator",
    category=PresetCategory.SPECIALIZED,
    description="Multi-agent coordination specialist",
    temperature=0.5,
    tags=["coordination", "delegation", "management"],
    system_prompt="""You are a multi-agent orchestrator. Coordinate work across multiple agents.

Orchestration duties:
1. **Decompose**: Break tasks into subtasks
2. **Assign**: Match subtasks to best-suited agents
3. **Monitor**: Track progress and quality
4. **Integrate**: Combine results
5. **Adapt**: Adjust plan based on feedback

When delegating:
- Be specific about requirements
- Set clear success criteria
- Specify output format
- Include relevant context

When integrating:
- Check for conflicts
- Resolve inconsistencies
- Synthesize into coherent output
- Verify completeness""",
)

DOCUMENTER = AgentPreset(
    name="documenter",
    role="documenter",
    category=PresetCategory.SPECIALIZED,
    description="API and code documentation specialist",
    temperature=0.4,
    tags=["documentation", "api", "docstrings"],
    system_prompt="""You are a documentation specialist. Create comprehensive API and code documentation.

Documentation standards:
- **Docstrings**: Google or NumPy style
- **Type hints**: Full typing information
- **Examples**: Working code examples
- **Edge cases**: Document limitations

Template for functions:
```python
def function_name(param: Type) -> ReturnType:
    '''
    Brief description.

    Longer description if needed.

    Args:
        param: Description of parameter

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this happens

    Example:
        >>> function_name(value)
        expected_result
    '''
```""",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preset Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALL_PRESETS: Dict[str, AgentPreset] = {
    # Code
    "coder": CODER,
    "reviewer": REVIEWER,
    "tester": TESTER,
    "debugger": DEBUGGER,
    "refactorer": REFACTORER,
    # Research
    "searcher": SEARCHER,
    "analyzer": ANALYZER,
    "synthesizer": SYNTHESIZER,
    # Creative
    "writer": WRITER,
    "brainstormer": BRAINSTORMER,
    "critic": CRITIC,
    # Specialized
    "planner": PLANNER,
    "orchestrator": ORCHESTRATOR,
    "documenter": DOCUMENTER,
}


def get_preset(name: str) -> Optional[AgentPreset]:
    """Get a preset by name."""
    return ALL_PRESETS.get(name.lower())


def list_presets(category: Optional[PresetCategory] = None) -> List[AgentPreset]:
    """List all presets, optionally filtered by category."""
    presets = list(ALL_PRESETS.values())
    if category:
        presets = [p for p in presets if p.category == category]
    return presets


def search_presets(query: str) -> List[AgentPreset]:
    """Search presets by name, tags, or description."""
    query_lower = query.lower()
    results = []
    for preset in ALL_PRESETS.values():
        if (query_lower in preset.name.lower() or
            query_lower in preset.description.lower() or
            any(query_lower in tag for tag in preset.tags)):
            results.append(preset)
    return results


def create_dna(preset_name: str, cmd: Optional[List[str]] = None) -> Optional[AgentDNA]:
    """Create AgentDNA from preset name."""
    preset = get_preset(preset_name)
    if preset:
        return preset.to_dna(cmd)
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Team Presets (Collections)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEAMS: Dict[str, List[str]] = {
    "code_review": ["coder", "reviewer", "tester"],
    "research": ["searcher", "analyzer", "synthesizer"],
    "creative": ["brainstormer", "writer", "critic"],
    "full_stack": ["planner", "coder", "tester", "reviewer", "documenter"],
    "minimal": ["coder", "critic"],
}


def get_team(team_name: str) -> List[AgentPreset]:
    """Get a team of presets."""
    if team_name not in TEAMS:
        return []
    return [ALL_PRESETS[name] for name in TEAMS[team_name] if name in ALL_PRESETS]


def create_team_dna(
    team_name: str,
    cmd: Optional[List[str]] = None,
) -> List[AgentDNA]:
    """Create list of AgentDNA for a team."""
    return [p.to_dna(cmd) for p in get_team(team_name)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Tool Presets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CLIToolConfig:
    """Configuration for an external CLI coding tool."""
    name: str
    cmd: List[str]
    description: str
    requires_api_key: bool = False
    api_key_env: str = ""
    interactive: bool = True

    def to_dna(self, role: str = "assistant", system_prompt: str = "") -> AgentDNA:
        """Create AgentDNA configured for this CLI tool."""
        return AgentDNA(
            role=role or self.name,
            cmd=self.cmd,
            system_prompt=system_prompt or f"CLI tool: {self.name}",
            temperature=0.7,
        )


# Popular CLI coding tools
CLI_TOOLS: Dict[str, CLIToolConfig] = {
    # Anthropic
    "claude-code": CLIToolConfig(
        name="claude-code",
        cmd=["claude"],
        description="Anthropic's Claude Code CLI for coding assistance",
        requires_api_key=True,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    # Google
    "gemini": CLIToolConfig(
        name="gemini",
        cmd=["gemini", "chat"],
        description="Google Gemini CLI for AI-powered coding",
        requires_api_key=True,
        api_key_env="GOOGLE_API_KEY",
    ),
    # Open source
    "aider": CLIToolConfig(
        name="aider",
        cmd=["aider"],
        description="AI pair programming in your terminal",
        requires_api_key=True,
        api_key_env="OPENAI_API_KEY",
    ),
    "interpreter": CLIToolConfig(
        name="open-interpreter",
        cmd=["interpreter"],
        description="Open Interpreter - natural language to code",
        requires_api_key=True,
        api_key_env="OPENAI_API_KEY",
    ),
    # Local/Ollama
    "ollama": CLIToolConfig(
        name="ollama",
        cmd=["ollama", "run", "codellama"],
        description="Local LLM via Ollama (CodeLlama default)",
        requires_api_key=False,
    ),
    # Python
    "python": CLIToolConfig(
        name="python",
        cmd=["python3", "-i", "-q"],
        description="Interactive Python REPL",
        requires_api_key=False,
    ),
    "ipython": CLIToolConfig(
        name="ipython",
        cmd=["ipython"],
        description="Enhanced Python shell",
        requires_api_key=False,
    ),
    # Shell
    "bash": CLIToolConfig(
        name="bash",
        cmd=["bash"],
        description="Bash shell",
        requires_api_key=False,
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Real AI Coding CLI Tools
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    "claude-code": CLIToolConfig(
        name="claude-code",
        cmd=["claude-code"],
        description="Anthropic Claude Code CLI - AI coding assistant",
        requires_api_key=True,
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "aider": CLIToolConfig(
        name="aider",
        cmd=["aider", "--yes-always"],  # Auto-confirm for automation
        description="Aider - AI pair programming in terminal",
        requires_api_key=True,
        api_key_env="OPENAI_API_KEY",
    ),
    "codex": CLIToolConfig(
        name="codex",
        cmd=["codex"],
        description="OpenAI Codex CLI",
        requires_api_key=True,
        api_key_env="OPENAI_API_KEY",
    ),
    "copilot-cli": CLIToolConfig(
        name="copilot-cli",
        cmd=["github-copilot-cli"],
        description="GitHub Copilot CLI",
        requires_api_key=True,
    ),
    "gemini-cli": CLIToolConfig(
        name="gemini-cli",
        cmd=["gemini"],
        description="Google Gemini CLI",
        requires_api_key=True,
        api_key_env="GOOGLE_API_KEY",
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Common POSIX/Linux CLI Tools
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Text Processing
    "grep": CLIToolConfig(
        name="grep",
        cmd=["grep"],
        description="Search text patterns",
        requires_api_key=False,
    ),
    "awk": CLIToolConfig(
        name="awk",
        cmd=["awk"],
        description="Pattern scanning and processing",
        requires_api_key=False,
    ),
    "sed": CLIToolConfig(
        name="sed",
        cmd=["sed"],
        description="Stream editor",
        requires_api_key=False,
    ),
    "jq": CLIToolConfig(
        name="jq",
        cmd=["jq"],
        description="JSON processor",
        requires_api_key=False,
    ),
    "ripgrep": CLIToolConfig(
        name="ripgrep",
        cmd=["rg"],
        description="Fast recursive grep",
        requires_api_key=False,
    ),

    # Version Control
    "git": CLIToolConfig(
        name="git",
        cmd=["git"],
        description="Git version control",
        requires_api_key=False,
    ),

    # Build Tools
    "make": CLIToolConfig(
        name="make",
        cmd=["make"],
        description="Build automation",
        requires_api_key=False,
    ),
    "npm": CLIToolConfig(
        name="npm",
        cmd=["npm"],
        description="Node package manager",
        requires_api_key=False,
    ),
    "pip": CLIToolConfig(
        name="pip",
        cmd=["pip"],
        description="Python package installer",
        requires_api_key=False,
    ),

    # Testing Tools
    "pytest": CLIToolConfig(
        name="pytest",
        cmd=["pytest"],
        description="Python testing framework",
        requires_api_key=False,
    ),
    "jest": CLIToolConfig(
        name="jest",
        cmd=["jest"],
        description="JavaScript testing framework",
        requires_api_key=False,
    ),

    # Container Tools
    "docker": CLIToolConfig(
        name="docker",
        cmd=["docker"],
        description="Container platform",
        requires_api_key=False,
    ),

    # Code Analysis
    "pylint": CLIToolConfig(
        name="pylint",
        cmd=["pylint"],
        description="Python code analyzer",
        requires_api_key=False,
    ),
    "eslint": CLIToolConfig(
        name="eslint",
        cmd=["eslint"],
        description="JavaScript linter",
        requires_api_key=False,
    ),
    "black": CLIToolConfig(
        name="black",
        cmd=["black"],
        description="Python code formatter",
        requires_api_key=False,
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Mock AI Tools (for testing/demo)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "mock-coder": CLIToolConfig(
        name="mock-coder",
        cmd=["python", "tools/mock_ai_cli.py", "--mode", "coder"],
        description="Mock AI code generator (simulates claude-code)",
        requires_api_key=False,
    ),
    "mock-reviewer": CLIToolConfig(
        name="mock-reviewer",
        cmd=["python", "tools/mock_ai_cli.py", "--mode", "reviewer"],
        description="Mock AI code reviewer (simulates gemini)",
        requires_api_key=False,
    ),
    "mock-fixer": CLIToolConfig(
        name="mock-fixer",
        cmd=["python", "tools/mock_ai_cli.py", "--mode", "fixer"],
        description="Mock AI code fixer (simulates aider)",
        requires_api_key=False,
    ),
}


def get_cli_tool(name: str) -> Optional[CLIToolConfig]:
    """Get CLI tool configuration by name."""
    return CLI_TOOLS.get(name.lower())


def list_cli_tools() -> List[CLIToolConfig]:
    """List all available CLI tool configurations."""
    return list(CLI_TOOLS.values())


def create_cli_agent(
    tool_name: str,
    role: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Optional[AgentDNA]:
    """Create an AgentDNA configured for a specific CLI tool."""
    tool = get_cli_tool(tool_name)
    if tool:
        return tool.to_dna(role=role or tool.name, system_prompt=system_prompt or "")
    return None
