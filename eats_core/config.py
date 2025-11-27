# config.py - Configuration System
"""
Flexible configuration management for EATS.

Features:
- Environment variable loading
- Config file support (JSON, YAML-like)
- Type conversion and validation
- Default values
- Config inheritance/override
- Secrets management

Zero external dependencies beyond standard library.
"""

from __future__ import annotations
import os
import json
import re
from dataclasses import dataclass, field, asdict
from typing import (
    Dict, List, Optional, Any, Type, TypeVar, Callable,
    Union, Generic, get_type_hints
)
from pathlib import Path
from enum import Enum


T = TypeVar('T')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration Values
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConfigValue(Generic[T]):
    """
    A configuration value with type, default, and validation.

    Usage:
        port = ConfigValue(int, default=8080, env="PORT")
        api_key = ConfigValue(str, env="API_KEY", required=True, secret=True)
    """

    def __init__(
        self,
        type_: Type[T],
        default: Optional[T] = None,
        env: Optional[str] = None,
        required: bool = False,
        secret: bool = False,
        validator: Optional[Callable[[T], bool]] = None,
        choices: Optional[List[T]] = None,
        description: Optional[str] = None,
    ):
        self.type_ = type_
        self.default = default
        self.env = env
        self.required = required
        self.secret = secret
        self.validator = validator
        self.choices = choices
        self.description = description
        self._value: Optional[T] = None
        self._is_set = False

    def set(self, value: Any) -> None:
        """Set the value with type conversion."""
        converted = self._convert(value)

        if self.validator and not self.validator(converted):
            raise ValueError(f"Validation failed for value: {value}")

        if self.choices and converted not in self.choices:
            raise ValueError(f"Value must be one of: {self.choices}")

        self._value = converted
        self._is_set = True

    def get(self) -> T:
        """Get the value, checking env and default."""
        if self._is_set:
            return self._value

        # Check environment variable
        if self.env:
            env_value = os.environ.get(self.env)
            if env_value is not None:
                return self._convert(env_value)

        # Use default
        if self.default is not None:
            return self.default

        # Required but not set
        if self.required:
            raise ValueError(f"Required config not set (env: {self.env})")

        return None

    def _convert(self, value: Any) -> T:
        """Convert value to target type."""
        if isinstance(value, self.type_):
            return value

        if self.type_ == bool:
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1', 'on')
            return bool(value)
        elif self.type_ == int:
            return int(float(value))
        elif self.type_ == float:
            return float(value)
        elif self.type_ == str:
            return str(value)
        elif self.type_ == list:
            if isinstance(value, str):
                # Support comma-separated values
                return [v.strip() for v in value.split(',') if v.strip()]
            return list(value)
        elif self.type_ == dict:
            if isinstance(value, str):
                return json.loads(value)
            return dict(value)

        return value

    def __repr__(self) -> str:
        val = self.get() if self._is_set else self.default
        if self.secret and val:
            val = "***"
        return f"ConfigValue({self.type_.__name__}, value={val})"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration Classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 60.0
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        # Load from environment if not set
        if self.api_key is None:
            env_key = f"{self.provider.upper()}_API_KEY"
            self.api_key = os.environ.get(env_key) or os.environ.get("LLM_API_KEY")


@dataclass
class SwarmConfig:
    """Configuration for swarm behavior."""
    max_agents: int = 10
    max_depth: int = 5
    spawn_probability: float = 0.3
    prune_threshold: float = 0.3
    branch_weights: Dict[str, float] = field(default_factory=lambda: {
        "research": 0.3,
        "creative": 0.3,
        "execution": 0.4,
    })
    senescence_factor: float = 0.1
    fitness_window: int = 5


@dataclass
class EvolutionConfig:
    """Configuration for evolution engine."""
    population_size: int = 10
    generations: int = 20
    mutation_rate: float = 0.2
    crossover_rate: float = 0.7
    elite_count: int = 2
    tournament_size: int = 3
    selection_method: str = "tournament"  # tournament, roulette, rank


@dataclass
class TransportConfig:
    """Configuration for agent transport."""
    transport_type: str = "pty"  # pty, tmux, mock
    shell: str = "/bin/bash"
    timeout: float = 30.0
    buffer_size: int = 65536
    tmux_session: Optional[str] = None


@dataclass
class PersistenceConfig:
    """Configuration for state persistence."""
    enabled: bool = True
    storage_type: str = "file"  # file, memory
    base_dir: str = ".eats_data"
    auto_snapshot: bool = False
    snapshot_interval: int = 300


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    enabled: bool = True
    export_format: str = "json"  # json, prometheus
    export_interval: int = 60
    histogram_buckets: List[float] = field(default_factory=lambda: [
        0.1, 0.5, 1.0, 2.0, 5.0, 10.0
    ])


@dataclass
class ServerConfig:
    """Configuration for the EATS server."""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    auth_enabled: bool = False
    auth_token: Optional[str] = None


@dataclass
class EATSConfig:
    """Main EATS configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    swarm: SwarmConfig = field(default_factory=SwarmConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    transport: TransportConfig = field(default_factory=TransportConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    log_level: str = "INFO"
    environment: str = "development"  # development, staging, production

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EATSConfig':
        """Create from dictionary."""
        return cls(
            llm=LLMConfig(**data.get('llm', {})),
            swarm=SwarmConfig(**data.get('swarm', {})),
            evolution=EvolutionConfig(**data.get('evolution', {})),
            transport=TransportConfig(**data.get('transport', {})),
            persistence=PersistenceConfig(**data.get('persistence', {})),
            metrics=MetricsConfig(**data.get('metrics', {})),
            server=ServerConfig(**data.get('server', {})),
            log_level=data.get('log_level', 'INFO'),
            environment=data.get('environment', 'development'),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config Loader
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConfigLoader:
    """
    Load configuration from multiple sources.

    Priority (highest to lowest):
    1. Programmatic overrides
    2. Environment variables
    3. Config files (eats.json, eats.yaml)
    4. Default values

    Usage:
        loader = ConfigLoader()
        config = loader.load()

        # Or with explicit file
        config = loader.load("custom_config.json")
    """

    DEFAULT_FILES = ["eats.json", "eats.yaml", "eats.yml", ".eatsrc"]
    ENV_PREFIX = "EATS_"

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()

    def load(
        self,
        config_file: Optional[str] = None,
        overrides: Optional[Dict] = None
    ) -> EATSConfig:
        """Load configuration from all sources."""
        config_data = {}

        # 1. Load from file
        file_data = self._load_file(config_file)
        if file_data:
            config_data = self._deep_merge(config_data, file_data)

        # 2. Load from environment
        env_data = self._load_env()
        config_data = self._deep_merge(config_data, env_data)

        # 3. Apply overrides
        if overrides:
            config_data = self._deep_merge(config_data, overrides)

        return EATSConfig.from_dict(config_data)

    def _load_file(self, config_file: Optional[str] = None) -> Dict:
        """Load from config file."""
        if config_file:
            path = Path(config_file)
            if path.exists():
                return self._parse_file(path)
            return {}

        # Search for default files
        for filename in self.DEFAULT_FILES:
            path = self.base_path / filename
            if path.exists():
                return self._parse_file(path)

        return {}

    def _parse_file(self, path: Path) -> Dict:
        """Parse a config file."""
        content = path.read_text()

        if path.suffix == '.json':
            return json.loads(content)

        # Simple YAML-like parsing (no external dependency)
        if path.suffix in ('.yaml', '.yml'):
            return self._parse_simple_yaml(content)

        # Try JSON first, then YAML-like
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return self._parse_simple_yaml(content)

    def _parse_simple_yaml(self, content: str) -> Dict:
        """Simple YAML-like parser (handles basic cases)."""
        result = {}
        current_section = result
        current_indent = 0
        stack = [(0, result)]

        for line in content.split('\n'):
            # Skip comments and empty lines
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue

            # Calculate indent
            indent = len(line) - len(line.lstrip())

            # Handle dedent
            while stack and indent <= stack[-1][0] and len(stack) > 1:
                stack.pop()
            current_section = stack[-1][1]

            # Parse key: value
            if ':' in line_stripped:
                key, _, value = line_stripped.partition(':')
                key = key.strip()
                value = value.strip()

                if value:
                    # Inline value
                    current_section[key] = self._parse_yaml_value(value)
                else:
                    # New section
                    current_section[key] = {}
                    stack.append((indent, current_section[key]))
                    current_section = current_section[key]

        return result

    def _parse_yaml_value(self, value: str) -> Any:
        """Parse a YAML value."""
        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # Boolean
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False

        # Null
        if value.lower() in ('null', 'none', '~'):
            return None

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # List (inline)
        if value.startswith('[') and value.endswith(']'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value

    def _load_env(self) -> Dict:
        """Load from environment variables."""
        result = {}

        for key, value in os.environ.items():
            if not key.startswith(self.ENV_PREFIX):
                continue

            # Convert EATS_LLM_MODEL -> llm.model
            parts = key[len(self.ENV_PREFIX):].lower().split('_')

            # Navigate/create nested structure
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value
            current[parts[-1]] = self._parse_env_value(value)

        return result

    def _parse_env_value(self, value: str) -> Any:
        """Parse an environment variable value."""
        # Boolean
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Environment Profiles
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Environment(Enum):
    """Environment profiles."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# Pre-defined environment configurations
ENVIRONMENT_DEFAULTS: Dict[Environment, Dict] = {
    Environment.DEVELOPMENT: {
        "log_level": "DEBUG",
        "server": {"debug": True},
        "metrics": {"enabled": True},
        "persistence": {"auto_snapshot": False},
    },
    Environment.STAGING: {
        "log_level": "INFO",
        "server": {"debug": False},
        "metrics": {"enabled": True},
        "persistence": {"auto_snapshot": True},
    },
    Environment.PRODUCTION: {
        "log_level": "WARNING",
        "server": {"debug": False, "auth_enabled": True},
        "metrics": {"enabled": True, "export_format": "prometheus"},
        "persistence": {"auto_snapshot": True, "snapshot_interval": 60},
    },
    Environment.TESTING: {
        "log_level": "DEBUG",
        "transport": {"transport_type": "mock"},
        "persistence": {"storage_type": "memory"},
        "llm": {"provider": "mock"},
    },
}


def get_environment() -> Environment:
    """Get current environment from env var."""
    env_str = os.environ.get("EATS_ENVIRONMENT", "development").lower()
    try:
        return Environment(env_str)
    except ValueError:
        return Environment.DEVELOPMENT


def get_environment_config() -> Dict:
    """Get configuration defaults for current environment."""
    return ENVIRONMENT_DEFAULTS.get(get_environment(), {})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Secrets Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SecretsManager:
    """
    Simple secrets management.

    Supports:
    - Environment variables
    - .env files
    - Secret files (e.g., Docker secrets)
    """

    def __init__(self, secrets_dir: Optional[str] = None):
        self.secrets_dir = Path(secrets_dir) if secrets_dir else None
        self._cache: Dict[str, str] = {}

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret by name."""
        # Check cache
        if name in self._cache:
            return self._cache[name]

        # Check environment
        value = os.environ.get(name)
        if value:
            self._cache[name] = value
            return value

        # Check secrets directory
        if self.secrets_dir:
            secret_file = self.secrets_dir / name
            if secret_file.exists():
                value = secret_file.read_text().strip()
                self._cache[name] = value
                return value

        return default

    def load_env_file(self, path: str = ".env") -> None:
        """Load secrets from .env file."""
        env_path = Path(path)
        if not env_path.exists():
            return

        for line in env_path.read_text().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()

                # Remove quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                self._cache[key] = value
                # Optionally set in environment
                if key not in os.environ:
                    os.environ[key] = value


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ValidationError:
    """Configuration validation error."""
    path: str
    message: str
    value: Any = None


class ConfigValidator:
    """Validate configuration values."""

    def validate(self, config: EATSConfig) -> List[ValidationError]:
        """Validate configuration and return errors."""
        errors = []

        # LLM validation
        if config.llm.provider not in ('openai', 'anthropic', 'ollama', 'mock'):
            errors.append(ValidationError(
                "llm.provider",
                f"Unknown provider: {config.llm.provider}",
                config.llm.provider
            ))

        if config.llm.temperature < 0 or config.llm.temperature > 2:
            errors.append(ValidationError(
                "llm.temperature",
                "Temperature must be between 0 and 2",
                config.llm.temperature
            ))

        if config.llm.max_tokens < 1:
            errors.append(ValidationError(
                "llm.max_tokens",
                "max_tokens must be positive",
                config.llm.max_tokens
            ))

        # Swarm validation
        if config.swarm.max_agents < 1:
            errors.append(ValidationError(
                "swarm.max_agents",
                "max_agents must be at least 1",
                config.swarm.max_agents
            ))

        if not 0 <= config.swarm.spawn_probability <= 1:
            errors.append(ValidationError(
                "swarm.spawn_probability",
                "spawn_probability must be between 0 and 1",
                config.swarm.spawn_probability
            ))

        # Evolution validation
        if config.evolution.population_size < 2:
            errors.append(ValidationError(
                "evolution.population_size",
                "population_size must be at least 2",
                config.evolution.population_size
            ))

        if config.evolution.elite_count >= config.evolution.population_size:
            errors.append(ValidationError(
                "evolution.elite_count",
                "elite_count must be less than population_size",
                config.evolution.elite_count
            ))

        # Server validation
        if not 1 <= config.server.port <= 65535:
            errors.append(ValidationError(
                "server.port",
                "port must be between 1 and 65535",
                config.server.port
            ))

        return errors


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Global Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_global_config: Optional[EATSConfig] = None


def get_config() -> EATSConfig:
    """Get global configuration."""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def set_config(config: EATSConfig) -> None:
    """Set global configuration."""
    global _global_config
    _global_config = config


def load_config(
    config_file: Optional[str] = None,
    overrides: Optional[Dict] = None,
    validate: bool = True
) -> EATSConfig:
    """Load and optionally validate configuration."""
    loader = ConfigLoader()

    # Start with environment defaults
    env_defaults = get_environment_config()

    # Merge with loader results
    config = loader.load(config_file, overrides)

    # Apply environment defaults for unset values
    if env_defaults:
        config_dict = config.to_dict()
        merged = loader._deep_merge(env_defaults, config_dict)
        config = EATSConfig.from_dict(merged)

    # Validate
    if validate:
        validator = ConfigValidator()
        errors = validator.validate(config)
        if errors:
            error_msgs = [f"{e.path}: {e.message}" for e in errors]
            raise ValueError(f"Configuration errors: {'; '.join(error_msgs)}")

    return config


def reset_config() -> None:
    """Reset global configuration."""
    global _global_config
    _global_config = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Convenience Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return get_config().llm


def get_swarm_config() -> SwarmConfig:
    """Get swarm configuration."""
    return get_config().swarm


def get_evolution_config() -> EvolutionConfig:
    """Get evolution configuration."""
    return get_config().evolution


def is_production() -> bool:
    """Check if running in production."""
    return get_environment() == Environment.PRODUCTION


def is_development() -> bool:
    """Check if running in development."""
    return get_environment() == Environment.DEVELOPMENT
