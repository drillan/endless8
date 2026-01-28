"""Configuration management for endless8."""

from pathlib import Path

import yaml

from endless8.config.settings import (
    ClaudeOptions,
    EngineConfig,
    LoggingOptions,
    MaxTurnsConfig,
    PromptsConfig,
)

__all__ = [
    "ClaudeOptions",
    "EngineConfig",
    "LoggingOptions",
    "MaxTurnsConfig",
    "PromptsConfig",
    "load_config",
]


def load_config(path: str | Path) -> EngineConfig:
    """Load configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        EngineConfig: Parsed configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration is invalid.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration format in {config_path}")

    return EngineConfig.model_validate(data)
