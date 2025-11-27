# project_context.py - Project-Aware Intelligence
"""
Project Context Management for AI-assisted development.

Makes AI tools project-aware by:
- Detecting project type (language, framework, tools)
- Loading coding standards (.editorconfig, style guides)
- Understanding project structure
- Remembering previous decisions
- Building enriched prompts with context

Usage:
    ctx = ProjectContext("./my-project")

    # Get enriched prompt
    prompt = ctx.enrich_prompt("Add user authentication")
    # Returns: "This is a Python/FastAPI project using PostgreSQL...
    #           Follow PEP 8, use type hints, pytest for tests...
    #           Task: Add user authentication"

    # Remember decisions
    ctx.remember("auth", "Using JWT tokens with refresh")

    # Get relevant files
    files = ctx.get_relevant_files("authentication")
"""

from __future__ import annotations
import os
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum

from .logging import get_logger

logger = get_logger("project_context")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Project Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProjectLanguage(str, Enum):
    """Detected project language."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    CSHARP = "csharp"
    CPP = "cpp"
    UNKNOWN = "unknown"


@dataclass
class ProjectInfo:
    """Detected project information."""
    language: ProjectLanguage
    framework: Optional[str] = None
    test_framework: Optional[str] = None
    package_manager: Optional[str] = None
    database: Optional[str] = None
    web_server: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Project Context
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProjectContext:
    """
    Understand and maintain project context for AI interactions.

    Features:
    - Auto-detect language, framework, tools
    - Load coding standards (editorconfig, style guides)
    - Parse project structure
    - Remember decisions (stored in .eats/context.json)
    - Build enriched prompts
    """

    def __init__(self, project_path: str = "."):
        self.path = Path(project_path).resolve()
        self.eats_dir = self.path / ".eats"
        self.context_file = self.eats_dir / "context.json"

        # Ensure .eats directory exists
        self.eats_dir.mkdir(exist_ok=True)

        # Detect project
        self.info = self._detect_project()
        self.standards = self._load_standards()
        self.memory = self._load_memory()

        logger.info(f"Project context loaded: {self.info.language.value} project")

    # ─────────────────────────────────────────────────────
    # Detection
    # ─────────────────────────────────────────────────────

    def _detect_project(self) -> ProjectInfo:
        """Detect project type and framework."""
        # Check for common files
        files = set(f.name for f in self.path.iterdir() if f.is_file())

        # Python
        if "setup.py" in files or "pyproject.toml" in files or "requirements.txt" in files:
            return self._detect_python_project()

        # JavaScript/TypeScript
        if "package.json" in files:
            return self._detect_js_project()

        # Java
        if "pom.xml" in files or "build.gradle" in files:
            return self._detect_java_project()

        # Go
        if "go.mod" in files:
            return self._detect_go_project()

        # Rust
        if "Cargo.toml" in files:
            return self._detect_rust_project()

        # Default
        return ProjectInfo(language=ProjectLanguage.UNKNOWN)

    def _detect_python_project(self) -> ProjectInfo:
        """Detect Python project details."""
        info = ProjectInfo(language=ProjectLanguage.PYTHON)

        # Check for frameworks
        dependencies = self._get_python_dependencies()

        if "fastapi" in dependencies:
            info.framework = "FastAPI"
            info.web_server = "uvicorn"
        elif "flask" in dependencies:
            info.framework = "Flask"
        elif "django" in dependencies:
            info.framework = "Django"

        # Test framework
        if "pytest" in dependencies:
            info.test_framework = "pytest"
        elif "unittest" in dependencies:
            info.test_framework = "unittest"

        # Database
        if "sqlalchemy" in dependencies:
            info.database = "SQLAlchemy"
        elif "psycopg2" in dependencies or "psycopg" in dependencies:
            info.database = "PostgreSQL"
        elif "pymongo" in dependencies:
            info.database = "MongoDB"

        # Package manager
        if (self.path / "poetry.lock").exists():
            info.package_manager = "poetry"
        elif (self.path / "Pipfile").exists():
            info.package_manager = "pipenv"
        else:
            info.package_manager = "pip"

        info.dependencies = dependencies
        return info

    def _detect_js_project(self) -> ProjectInfo:
        """Detect JavaScript/TypeScript project details."""
        # Check if TypeScript
        is_ts = (self.path / "tsconfig.json").exists()
        info = ProjectInfo(
            language=ProjectLanguage.TYPESCRIPT if is_ts else ProjectLanguage.JAVASCRIPT
        )

        # Parse package.json
        package_json = self.path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                    # Framework
                    if "react" in deps:
                        info.framework = "React"
                    elif "vue" in deps:
                        info.framework = "Vue"
                    elif "angular" in deps:
                        info.framework = "Angular"
                    elif "next" in deps:
                        info.framework = "Next.js"
                    elif "express" in deps:
                        info.framework = "Express"

                    # Test framework
                    if "jest" in deps:
                        info.test_framework = "Jest"
                    elif "mocha" in deps:
                        info.test_framework = "Mocha"
                    elif "vitest" in deps:
                        info.test_framework = "Vitest"

                    info.dependencies = list(deps.keys())
            except:
                pass

        # Package manager
        if (self.path / "yarn.lock").exists():
            info.package_manager = "yarn"
        elif (self.path / "pnpm-lock.yaml").exists():
            info.package_manager = "pnpm"
        else:
            info.package_manager = "npm"

        return info

    def _detect_java_project(self) -> ProjectInfo:
        """Detect Java project details."""
        info = ProjectInfo(language=ProjectLanguage.JAVA)

        if (self.path / "pom.xml").exists():
            info.package_manager = "maven"
        elif (self.path / "build.gradle").exists():
            info.package_manager = "gradle"

        # TODO: Parse pom.xml/build.gradle for frameworks
        return info

    def _detect_go_project(self) -> ProjectInfo:
        """Detect Go project details."""
        return ProjectInfo(
            language=ProjectLanguage.GO,
            package_manager="go modules"
        )

    def _detect_rust_project(self) -> ProjectInfo:
        """Detect Rust project details."""
        return ProjectInfo(
            language=ProjectLanguage.RUST,
            package_manager="cargo"
        )

    def _get_python_dependencies(self) -> List[str]:
        """Get Python dependencies from various sources."""
        deps = set()

        # requirements.txt
        req_file = self.path / "requirements.txt"
        if req_file.exists():
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract package name
                        pkg = re.split(r'[=<>!]', line)[0].strip()
                        deps.add(pkg.lower())

        # pyproject.toml
        pyproject = self.path / "pyproject.toml"
        if pyproject.exists():
            # Simple parsing (could use tomli for full parsing)
            with open(pyproject) as f:
                content = f.read()
                # Extract from dependencies section
                deps_section = re.search(r'\[tool\.poetry\.dependencies\](.*?)(\[|$)', content, re.DOTALL)
                if deps_section:
                    for line in deps_section.group(1).split('\n'):
                        match = re.match(r'(\w+)\s*=', line.strip())
                        if match:
                            deps.add(match.group(1).lower())

        return list(deps)

    # ─────────────────────────────────────────────────────
    # Standards
    # ─────────────────────────────────────────────────────

    def _load_standards(self) -> Dict[str, Any]:
        """Load coding standards from various sources."""
        standards = {}

        # .editorconfig
        editorconfig = self.path / ".editorconfig"
        if editorconfig.exists():
            standards["editorconfig"] = self._parse_editorconfig(editorconfig)

        # Python-specific
        if self.info.language == ProjectLanguage.PYTHON:
            # Check for Black
            if "black" in self.info.dependencies:
                standards["formatter"] = "Black"

            # Check for isort
            if "isort" in self.info.dependencies:
                standards["import_sorter"] = "isort"

            # Check for mypy
            if "mypy" in self.info.dependencies:
                standards["type_checker"] = "mypy"

            # Check for flake8/pylint
            if "flake8" in self.info.dependencies:
                standards["linter"] = "flake8"
            elif "pylint" in self.info.dependencies:
                standards["linter"] = "pylint"

        # JavaScript/TypeScript
        elif self.info.language in [ProjectLanguage.JAVASCRIPT, ProjectLanguage.TYPESCRIPT]:
            # Check for ESLint
            if ".eslintrc" in [f.name for f in self.path.iterdir()]:
                standards["linter"] = "ESLint"

            # Check for Prettier
            if "prettier" in self.info.dependencies:
                standards["formatter"] = "Prettier"

        return standards

    def _parse_editorconfig(self, path: Path) -> Dict[str, str]:
        """Parse .editorconfig file."""
        config = {}
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('['):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except:
            pass
        return config

    # ─────────────────────────────────────────────────────
    # Memory
    # ─────────────────────────────────────────────────────

    def _load_memory(self) -> Dict[str, Any]:
        """Load project memory (previous decisions)."""
        if self.context_file.exists():
            try:
                with open(self.context_file) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_memory(self):
        """Save project memory."""
        try:
            with open(self.context_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    def remember(self, key: str, value: Any):
        """Remember a decision or fact about the project."""
        self.memory[key] = {
            "value": value,
            "timestamp": __import__('time').time()
        }
        self._save_memory()
        logger.info(f"Remembered: {key} = {value}")

    def recall(self, key: str) -> Optional[Any]:
        """Recall a previous decision."""
        if key in self.memory:
            return self.memory[key]["value"]
        return None

    # ─────────────────────────────────────────────────────
    # Prompt Enrichment
    # ─────────────────────────────────────────────────────

    def enrich_prompt(self, task: str) -> str:
        """
        Build enriched prompt with project context.

        Args:
            task: The task to perform

        Returns:
            Enriched prompt with full context
        """
        parts = []

        # Project info
        parts.append(f"PROJECT CONTEXT:")
        parts.append(f"- Language: {self.info.language.value.title()}")

        if self.info.framework:
            parts.append(f"- Framework: {self.info.framework}")

        if self.info.test_framework:
            parts.append(f"- Testing: {self.info.test_framework}")

        if self.info.database:
            parts.append(f"- Database: {self.info.database}")

        # Coding standards
        if self.standards:
            parts.append(f"\nCODING STANDARDS:")

            if "formatter" in self.standards:
                parts.append(f"- Formatter: {self.standards['formatter']}")

            if "linter" in self.standards:
                parts.append(f"- Linter: {self.standards['linter']}")

            if "type_checker" in self.standards:
                parts.append(f"- Type Checker: {self.standards['type_checker']}")

            # Language-specific standards
            if self.info.language == ProjectLanguage.PYTHON:
                parts.append(f"- Follow PEP 8 style guide")
                parts.append(f"- Use type hints")
                parts.append(f"- Write docstrings for all functions")

        # Previous decisions
        if self.memory:
            parts.append(f"\nPREVIOUS DECISIONS:")
            for key, data in list(self.memory.items())[:5]:  # Last 5
                parts.append(f"- {key}: {data['value']}")

        # The actual task
        parts.append(f"\nTASK:")
        parts.append(task)

        return "\n".join(parts)

    # ─────────────────────────────────────────────────────
    # File Discovery
    # ─────────────────────────────────────────────────────

    def get_relevant_files(
        self,
        keyword: str,
        max_files: int = 10
    ) -> List[Path]:
        """
        Find files relevant to a keyword.

        Args:
            keyword: Search term (e.g., "auth", "user", "api")
            max_files: Maximum files to return

        Returns:
            List of relevant file paths
        """
        relevant = []
        keyword_lower = keyword.lower()

        # Common directories to search
        search_dirs = ["src", "app", "lib", "tests", "."]

        for dir_name in search_dirs:
            dir_path = self.path / dir_name
            if not dir_path.exists():
                continue

            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip common ignores
                if any(p in file_path.parts for p in [".git", "__pycache__", "node_modules", ".venv"]):
                    continue

                # Check filename
                if keyword_lower in file_path.name.lower():
                    relevant.append(file_path.relative_to(self.path))

                    if len(relevant) >= max_files:
                        return relevant

        return relevant

    def get_project_structure(self, max_depth: int = 3) -> str:
        """
        Get project structure as a tree.

        Args:
            max_depth: Maximum directory depth

        Returns:
            Tree representation of project
        """
        lines = []
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", ".eats", "dist", "build"}

        def walk(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return

            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))

            for i, item in enumerate(items):
                if item.name.startswith(".") and item.name not in {".editorconfig", ".gitignore"}:
                    continue

                if item.name in ignore_dirs:
                    continue

                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                lines.append(f"{prefix}{current_prefix}{item.name}")

                if item.is_dir() and depth < max_depth:
                    extension = "    " if is_last else "│   "
                    walk(item, prefix + extension, depth + 1)

        lines.append(self.path.name + "/")
        walk(self.path)
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────

    def summary(self) -> str:
        """Get a human-readable summary of project context."""
        parts = [
            f"Project: {self.path.name}",
            f"Language: {self.info.language.value.title()}",
        ]

        if self.info.framework:
            parts.append(f"Framework: {self.info.framework}")

        if self.info.test_framework:
            parts.append(f"Tests: {self.info.test_framework}")

        if self.info.package_manager:
            parts.append(f"Package Manager: {self.info.package_manager}")

        if self.standards:
            parts.append(f"Standards: {', '.join(self.standards.values())}")

        return " | ".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_project(path: str = ".") -> ProjectInfo:
    """Quick project detection."""
    ctx = ProjectContext(path)
    return ctx.info


def get_context(path: str = ".") -> ProjectContext:
    """Get project context (cached)."""
    return ProjectContext(path)
