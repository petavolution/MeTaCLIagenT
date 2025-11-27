#!/usr/bin/env python3
"""
EATS CLI - Easy AI Tool Sequencer

Command-line interface for orchestrating AI coding tools:
- Ollama (local LLM)
- Claude Code CLI
- Codex CLI

Usage:
    eats run <workflow> [options]
    eats list [tools|workflows]
    eats config [get|set|init]
    eats status [sequence-id]
    eats interactive

Examples:
    # Run pre-built workflow
    eats run code-review --file main.py

    # List available tools
    eats list tools

    # Configure API keys
    eats config set ANTHROPIC_API_KEY sk-...

    # Interactive mode
    eats interactive
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
import json

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from eats_core.parallel_executor import ParallelExecutor, StepConfig
from eats_core.cli_orchestrator import CLISequence
from eats_core.cli_persistence import get_persistence
from eats_core.presets import list_cli_tools, get_cli_tool
from eats_core.template_engine import TemplateEngine
from eats_core.tool_detection import ToolSelector, check_setup


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EATSConfig:
    """Manages EATS configuration."""

    DEFAULT_CONFIG = {
        'api_keys': {
            'anthropic': None,  # For Claude Code CLI
            'openai': None,     # For Codex CLI
        },
        'tools': {
            'ollama': {
                'model': 'codellama',  # Default model
                'host': 'http://localhost:11434',
            },
            'claude-code': {
                'enabled': True,
            },
            'codex': {
                'enabled': True,
            },
        },
        'defaults': {
            'max_workers': 4,
            'timeout': 300,
            'save_to_db': True,
            'auto_retry': True,
            'max_retries': 2,
        },
        'paths': {
            'logs': './logs',
            'db': './logs/sequences.db',
            'workflows': './workflows',
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager."""
        self.config_path = config_path or Path.home() / '.eats' / 'config.yaml'
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                user_config = yaml.safe_load(f) or {}
            # Merge with defaults
            config = self.DEFAULT_CONFIG.copy()
            self._deep_merge(config, user_config)
            return config
        return self.DEFAULT_CONFIG.copy()

    def _deep_merge(self, base: Dict, updates: Dict):
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base:
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def save(self):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def get(self, key: str, default=None):
        """Get config value by dot-notation key."""
        parts = key.split('.')
        value = self.config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set config value by dot-notation key."""
        parts = key.split('.')
        config = self.config
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        config[parts[-1]] = value

    def init_default(self):
        """Initialize default configuration file."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()
        print(f"✓ Initialized configuration at {self.config_path}")
        print("\nNext steps:")
        print("1. Set API keys:")
        print("   eats config set api_keys.anthropic YOUR_KEY")
        print("   eats config set api_keys.openai YOUR_KEY")
        print("\n2. Verify Ollama is running:")
        print("   ollama serve")
        print("\n3. Run a workflow:")
        print("   eats run code-review --file main.py")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pre-built Workflows
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WORKFLOWS = {
    'code-review': {
        'name': 'Code Review',
        'description': 'AI-powered code review with Ollama → Claude Code → fixes',
        'steps': [
            {
                'tool': 'ollama',
                'prompt_template': 'Review this code for bugs and issues:\n{input}',
                'description': 'Quick review with local Ollama',
            },
            {
                'tool': 'claude-code',
                'prompt_template': 'Deep security and architecture review:\n{input}',
                'description': 'Detailed review with Claude Code',
            },
        ],
    },
    'code-generate': {
        'name': 'Code Generation',
        'description': 'Generate code with Ollama, review with Claude Code',
        'steps': [
            {
                'tool': 'ollama',
                'prompt_template': 'Write Python code for: {input}',
                'description': 'Generate initial code',
            },
            {
                'tool': 'claude-code',
                'prompt_template': 'Review and improve this code:\n{previous_output}',
                'use_previous_output': True,
                'description': 'Review and refine',
            },
        ],
    },
    'explain-code': {
        'name': 'Code Explanation',
        'description': 'Get multiple AI perspectives on code',
        'parallel': True,
        'steps': [
            {
                'tool': 'ollama',
                'prompt_template': 'Explain this code:\n{input}',
                'description': 'Ollama explanation',
            },
            {
                'tool': 'claude-code',
                'prompt_template': 'Explain this code:\n{input}',
                'description': 'Claude Code explanation',
            },
            {
                'tool': 'codex',
                'prompt_template': 'Explain this code:\n{input}',
                'description': 'Codex explanation',
            },
        ],
    },
    'refactor': {
        'name': 'Code Refactoring',
        'description': 'Refactor code with AI assistance',
        'steps': [
            {
                'tool': 'claude-code',
                'prompt_template': 'Suggest refactoring improvements for:\n{input}',
                'description': 'Get refactoring suggestions',
            },
            {
                'tool': 'ollama',
                'prompt_template': 'Apply these refactorings to the code:\n{previous_output}',
                'use_previous_output': True,
                'description': 'Apply refactorings',
            },
        ],
    },
    'debug': {
        'name': 'Debug Assistant',
        'description': 'Debug code with AI help',
        'steps': [
            {
                'tool': 'ollama',
                'prompt_template': 'Identify bugs in this code:\n{input}',
                'description': 'Find bugs',
            },
            {
                'tool': 'claude-code',
                'prompt_template': 'Suggest fixes for these bugs:\n{previous_output}',
                'use_previous_output': True,
                'description': 'Suggest fixes',
            },
        ],
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_run(args, config: EATSConfig):
    """Run a workflow."""
    workflow_name = args.workflow

    if workflow_name not in WORKFLOWS:
        print(f"❌ Unknown workflow: {workflow_name}")
        print(f"\nAvailable workflows:")
        for name in WORKFLOWS.keys():
            print(f"  - {name}")
        return 1

    workflow = WORKFLOWS[workflow_name]

    print(f"\n{'='*60}")
    print(f"Running workflow: {workflow['name']}")
    print(f"Description: {workflow['description']}")
    print(f"{'='*60}\n")

    # Initialize tool selector for automatic fallback
    tool_selector = ToolSelector(notify=True)

    # Get input
    input_text = args.input
    if args.file:
        with open(args.file) as f:
            input_text = f.read()

    if not input_text:
        print("❌ No input provided. Use --input or --file")
        return 1

    # Check if parallel workflow
    is_parallel = workflow.get('parallel', False)

    if is_parallel:
        # Run steps in parallel
        steps = []
        for i, step_def in enumerate(workflow['steps']):
            # Select tool with automatic fallback to mock tool
            tool_name = tool_selector.select(step_def['tool'], category='coder')

            prompt = step_def['prompt_template'].format(input=input_text)
            steps.append(StepConfig(
                tool_name=tool_name,
                prompt=prompt,
                timeout=config.get('defaults.timeout', 300),
                retries=config.get('defaults.max_retries', 2) if config.get('defaults.auto_retry') else 0,
                metadata={'description': step_def['description']},
            ))

        executor = ParallelExecutor(
            max_workers=config.get('defaults.max_workers', 4),
            save_to_db=config.get('defaults.save_to_db', True),
        )

        print(f"Running {len(steps)} steps in parallel...\n")
        result = executor.run_parallel(steps)

    else:
        # Run steps sequentially
        seq = CLISequence(
            name=f"workflow-{workflow_name}",
            auto_save=config.get('defaults.save_to_db', True),
        )

        previous_output = None
        for i, step_def in enumerate(workflow['steps'], 1):
            print(f"Step {i}/{len(workflow['steps'])}: {step_def['description']}")

            # Select tool with automatic fallback
            tool_name = tool_selector.select(step_def['tool'], category='coder')

            # Build prompt
            if step_def.get('use_previous_output') and previous_output:
                prompt = step_def['prompt_template'].format(
                    input=input_text,
                    previous_output=previous_output,
                )
            else:
                # Provide empty previous_output for templates that reference it
                prompt = step_def['prompt_template'].format(
                    input=input_text,
                    previous_output=""
                )

            seq.add_step(
                tool_name=tool_name,
                prompt=prompt,
            )

        result = seq.run()
        seq.cleanup()

    # Display results
    print(f"\n{'='*60}")
    print(f"Workflow Complete!")
    print(f"{'='*60}")
    print(f"Status: {result['status']}")
    print(f"Steps: {result.get('successful_steps', 0)}/{result.get('total_steps', 0)}")
    print(f"Duration: {result.get('duration', 0):.2f}s")

    if result.get('id'):
        print(f"Sequence ID: {result['id']}")
        print(f"\nView details with: eats status {result['id']}")

    return 0


def cmd_list(args, config: EATSConfig):
    """List tools or workflows."""
    what = args.what or 'tools'

    if what == 'tools':
        print("\n" + "="*60)
        print("Available Tools")
        print("="*60 + "\n")

        tools = list_cli_tools()

        # Group by category
        ai_tools = [t for t in tools if t.name in ['ollama', 'claude-code', 'codex', 'aider']]
        posix_tools = [t for t in tools if not t.requires_api_key and 'mock' not in t.name]
        mock_tools = [t for t in tools if 'mock' in t.name]

        print("AI Coding Tools:")
        for tool in ai_tools:
            enabled = "✓" if config.get(f'tools.{tool.name}.enabled', True) else "✗"
            print(f"  {enabled} {tool.name}: {tool.description}")

        print(f"\nPOSIX/Linux Tools ({len(posix_tools)} available):")
        for tool in posix_tools[:5]:
            print(f"  • {tool.name}: {tool.description}")
        if len(posix_tools) > 5:
            print(f"  ... and {len(posix_tools) - 5} more")

        print(f"\nMock Tools (for testing):")
        for tool in mock_tools:
            print(f"  • {tool.name}: {tool.description}")

    elif what == 'workflows':
        print("\n" + "="*60)
        print("Available Workflows")
        print("="*60 + "\n")

        for name, workflow in WORKFLOWS.items():
            print(f"{name}")
            print(f"  {workflow['description']}")
            print(f"  Steps: {len(workflow['steps'])}")
            if workflow.get('parallel'):
                print(f"  Execution: Parallel")
            print()

    return 0


def cmd_config(args, config: EATSConfig):
    """Manage configuration."""
    action = args.action

    if action == 'init':
        config.init_default()
        return 0

    elif action == 'get':
        if not args.key:
            # Show all config
            print(yaml.dump(config.config, default_flow_style=False))
        else:
            value = config.get(args.key)
            print(value)
        return 0

    elif action == 'set':
        if not args.key or args.value is None:
            print("❌ Usage: eats config set <key> <value>")
            return 1
        config.set(args.key, args.value)
        config.save()
        print(f"✓ Set {args.key} = {args.value}")
        return 0

    elif action == 'path':
        print(config.config_path)
        return 0

    return 0


def cmd_status(args, config: EATSConfig):
    """Show sequence status."""
    persistence = get_persistence()

    # Show recent sequences (simplified - no individual sequence lookup for now)
    sequences = persistence.query_sequences(limit=10)

    print("\n" + "="*60)
    print("Recent Sequences")
    print("="*60 + "\n")

    if not sequences:
        print("No sequences found. Run a workflow first:")
        print("  eats run code-review --file mycode.py")
        return 0

    for seq in sequences:
        print(f"{seq['id']}: {seq['name']}")
        print(f"  Status: {seq['status']}")
        print(f"  Steps: {seq['successful_steps']}/{seq['total_steps']}")
        if 'duration' in seq and seq['duration']:
            print(f"  Duration: {seq['duration']:.2f}s")
        print()

    return 0


def cmd_interactive(args, config: EATSConfig):
    """Interactive mode."""
    print("\n" + "="*60)
    print("EATS Interactive Mode")
    print("="*60 + "\n")
    print("Coming soon: Interactive workflow builder")
    print("\nFor now, use:")
    print("  eats run <workflow> --input 'your input'")
    print("  eats list workflows")
    return 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='EATS - Easy AI Tool Sequencer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run code review
  eats run code-review --file main.py

  # Generate code
  eats run code-generate --input "Create a REST API"

  # List available workflows
  eats list workflows

  # Configure API keys
  eats config set api_keys.anthropic sk-...
        ''',
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run a workflow')
    run_parser.add_argument('workflow', help='Workflow name')
    run_parser.add_argument('--input', '-i', help='Input text')
    run_parser.add_argument('--file', '-f', help='Input file')
    run_parser.add_argument('--config', help='Config file path')

    # List command
    list_parser = subparsers.add_parser('list', help='List tools or workflows')
    list_parser.add_argument('what', nargs='?', choices=['tools', 'workflows'], default='tools')

    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('action', choices=['init', 'get', 'set', 'path'])
    config_parser.add_argument('key', nargs='?', help='Config key (dot notation)')
    config_parser.add_argument('value', nargs='?', help='Config value')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show execution status')
    status_parser.add_argument('sequence_id', nargs='?', help='Sequence ID')

    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive mode')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Load config
    config_path = getattr(args, 'config', None)
    config = EATSConfig(Path(config_path) if config_path else None)

    # Dispatch command
    commands = {
        'run': cmd_run,
        'list': cmd_list,
        'config': cmd_config,
        'status': cmd_status,
        'interactive': cmd_interactive,
    }

    try:
        return commands[args.command](args, config)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
