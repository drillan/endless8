"""Unit tests for EngineConfig criteria type and load_config with command criteria."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from endless8.config import EngineConfig, load_config
from endless8.models.criteria import CommandCriterion


class TestEngineConfigCriteria:
    """Tests for EngineConfig.criteria accepting CriterionInput."""

    def test_string_only_criteria(self) -> None:
        """EngineConfig accepts list[str] criteria (backward compat)."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件1", "条件2"],
        )
        assert config.criteria == ["条件1", "条件2"]

    def test_command_only_criteria(self) -> None:
        """EngineConfig accepts command-only criteria."""
        config = EngineConfig(
            task="テスト",
            criteria=[
                {"type": "command", "command": "pytest"},
                {"type": "command", "command": "mypy .", "description": "型チェック"},
            ],
        )
        assert len(config.criteria) == 2
        assert isinstance(config.criteria[0], CommandCriterion)
        assert config.criteria[0].command == "pytest"
        assert isinstance(config.criteria[1], CommandCriterion)
        assert config.criteria[1].description == "型チェック"

    def test_mixed_criteria(self) -> None:
        """EngineConfig accepts mixed str + CommandCriterion criteria."""
        config = EngineConfig(
            task="テスト",
            criteria=[
                "コードが読みやすい",
                {"type": "command", "command": "pytest --tb=short"},
            ],
        )
        assert len(config.criteria) == 2
        assert config.criteria[0] == "コードが読みやすい"
        assert isinstance(config.criteria[1], CommandCriterion)
        assert config.criteria[1].command == "pytest --tb=short"

    def test_empty_criteria_rejected(self) -> None:
        """EngineConfig rejects empty criteria list."""
        with pytest.raises(ValidationError):
            EngineConfig(task="テスト", criteria=[])

    def test_command_timeout_default(self) -> None:
        """EngineConfig has default command_timeout of 30.0."""
        config = EngineConfig(task="テスト", criteria=["条件"])
        assert config.command_timeout == 30.0

    def test_command_timeout_custom(self) -> None:
        """EngineConfig accepts custom command_timeout."""
        config = EngineConfig(task="テスト", criteria=["条件"], command_timeout=60.0)
        assert config.command_timeout == 60.0


class TestLoadConfigWithCommandCriteria:
    """Tests for load_config parsing YAML with command criteria."""

    def test_load_command_only_yaml(self, tmp_path: Path) -> None:
        """load_config parses YAML with command-only criteria."""
        config_data = {
            "task": "CI修正",
            "criteria": [
                {"type": "command", "command": "pytest", "description": "テスト"},
                {"type": "command", "command": "mypy ."},
            ],
            "command_timeout": 60,
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data, allow_unicode=True))

        config = load_config(config_file)
        assert len(config.criteria) == 2
        assert isinstance(config.criteria[0], CommandCriterion)
        assert config.criteria[0].command == "pytest"
        assert config.criteria[0].description == "テスト"
        assert isinstance(config.criteria[1], CommandCriterion)
        assert config.command_timeout == 60.0

    def test_load_mixed_yaml(self, tmp_path: Path) -> None:
        """load_config parses YAML with mixed criteria."""
        config_data = {
            "task": "品質改善",
            "criteria": [
                "docstring が適切",
                {"type": "command", "command": "pytest -v", "timeout": 90},
            ],
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data, allow_unicode=True))

        config = load_config(config_file)
        assert len(config.criteria) == 2
        assert config.criteria[0] == "docstring が適切"
        assert isinstance(config.criteria[1], CommandCriterion)
        assert config.criteria[1].timeout == 90

    def test_load_example_ci_pipeline(self) -> None:
        """load_config successfully parses examples/ci-pipeline.yaml."""
        config_file = Path("examples/ci-pipeline.yaml")
        if not config_file.exists():
            pytest.skip("examples/ci-pipeline.yaml not found")

        config = load_config(config_file)
        assert len(config.criteria) == 4
        for criterion in config.criteria:
            assert isinstance(criterion, CommandCriterion)
        assert config.command_timeout == 60

    def test_load_example_code_quality(self) -> None:
        """load_config successfully parses examples/code-quality.yaml."""
        config_file = Path("examples/code-quality.yaml")
        if not config_file.exists():
            pytest.skip("examples/code-quality.yaml not found")

        config = load_config(config_file)
        # 2 semantic + 2 command = 4 criteria
        assert len(config.criteria) == 4
        assert isinstance(config.criteria[0], str)
        assert isinstance(config.criteria[1], str)
        assert isinstance(config.criteria[2], CommandCriterion)
        assert isinstance(config.criteria[3], CommandCriterion)
