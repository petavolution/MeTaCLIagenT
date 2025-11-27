#!/usr/bin/env python3
"""
Tool Detection and Auto-Fallback Utility

Automatically detects available tools and provides fallbacks to mock tools.
Makes the system work out-of-the-box without requiring tool installation.
"""

import shutil
from typing import Optional, List, Dict
from pathlib import Path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tool Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_tool_available(tool_name: str) -> bool:
    """Check if a CLI tool is available in PATH."""
    return shutil.which(tool_name) is not None


def detect_available_tools() -> Dict[str, bool]:
    """Detect which AI coding tools are available."""
    tools_to_check = {
        'ollama': 'ollama',
        'claude-code': 'claude-code',
        'codex': 'codex',
        'aider': 'aider',
    }

    available = {}
    for tool_id, command in tools_to_check.items():
        available[tool_id] = is_tool_available(command)

    return available


def get_tool_with_fallback(preferred_tool: str, fallback_category: str = "coder") -> str:
    """
    Get tool name with automatic fallback to mock tool.

    Args:
        preferred_tool: Desired tool (e.g., 'ollama', 'claude-code')
        fallback_category: Mock tool category (coder, reviewer, fixer)

    Returns:
        Tool name to use (original or mock fallback)
    """
    # Check if preferred tool is available
    if is_tool_available(preferred_tool):
        return preferred_tool

    # Fallback to mock tool
    mock_tools = {
        'coder': 'mock-coder',
        'reviewer': 'mock-reviewer',
        'fixer': 'mock-fixer',
    }

    return mock_tools.get(fallback_category, 'mock-coder')


def get_available_ai_tools() -> List[str]:
    """Get list of available AI coding tools."""
    available = detect_available_tools()
    return [tool for tool, is_available in available.items() if is_available]


def suggest_tool_installation(tool_name: str) -> str:
    """Get installation suggestion for a tool."""
    suggestions = {
        'ollama': 'curl https://ollama.ai/install.sh | sh',
        'claude-code': 'pip install anthropic-cli',
        'codex': 'pip install openai-cli',
        'aider': 'pip install aider-chat',
    }

    return suggestions.get(tool_name, f'Install {tool_name}')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Smart Tool Selection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ToolSelector:
    """
    Smart tool selector with automatic fallback.

    Provides transparent fallback to mock tools when real tools
    aren't available, with user notification.
    """

    def __init__(self, notify: bool = True):
        """
        Initialize tool selector.

        Args:
            notify: Whether to notify user about fallbacks
        """
        self.notify = notify
        self.available_tools = detect_available_tools()
        self.fallback_used = {}

    def select(self, tool_name: str, category: str = "coder") -> str:
        """
        Select tool with automatic fallback.

        Args:
            tool_name: Preferred tool name
            category: Tool category for fallback

        Returns:
            Tool name to use (may be mock tool)
        """
        # If it's already a mock tool, use it
        if tool_name.startswith('mock-'):
            return tool_name

        # Check if real tool is available
        if self.available_tools.get(tool_name, False):
            return tool_name

        # Fallback to mock tool
        mock_tool = get_tool_with_fallback(tool_name, category)

        # Notify user (only once per tool)
        if self.notify and tool_name not in self.fallback_used:
            print(f"ℹ  {tool_name} not found, using {mock_tool} for testing")
            print(f"   Install with: {suggest_tool_installation(tool_name)}")
            self.fallback_used[tool_name] = True

        return mock_tool

    def get_status(self) -> Dict[str, str]:
        """Get status of all tools (available, fallback, mock)."""
        status = {}
        for tool, available in self.available_tools.items():
            if available:
                status[tool] = 'available'
            else:
                status[tool] = 'using mock fallback'
        return status


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_setup() -> Dict[str, any]:
    """
    Check setup status and provide recommendations.

    Returns:
        Dictionary with setup status and recommendations
    """
    available = detect_available_tools()

    setup_status = {
        'ready': any(available.values()),
        'available_tools': [t for t, a in available.items() if a],
        'missing_tools': [t for t, a in available.items() if not a],
        'can_run': True,  # Can always run with mock tools
    }

    if not setup_status['ready']:
        setup_status['message'] = (
            "No AI tools detected. Using mock tools for testing.\n"
            "Install tools for production use:\n"
            f"  Ollama: {suggest_tool_installation('ollama')}\n"
            f"  Claude Code: {suggest_tool_installation('claude-code')}\n"
            f"  Codex: {suggest_tool_installation('codex')}"
        )
    else:
        setup_status['message'] = (
            f"✓ Found {len(setup_status['available_tools'])} AI tool(s): "
            f"{', '.join(setup_status['available_tools'])}"
        )

    return setup_status


if __name__ == "__main__":
    # Demo
    print("Tool Detection Demo")
    print("=" * 60)

    # Detect available tools
    available = detect_available_tools()
    print("\nAvailable AI Tools:")
    for tool, is_available in available.items():
        status = "✓" if is_available else "✗"
        print(f"  {status} {tool}")

    # Test smart selection
    print("\nSmart Tool Selection:")
    selector = ToolSelector(notify=False)

    test_cases = [
        ('ollama', 'coder'),
        ('claude-code', 'reviewer'),
        ('codex', 'coder'),
    ]

    for tool, category in test_cases:
        selected = selector.select(tool, category)
        print(f"  {tool} → {selected}")

    # Check setup status
    print("\nSetup Status:")
    status = check_setup()
    print(f"  {status['message']}")
