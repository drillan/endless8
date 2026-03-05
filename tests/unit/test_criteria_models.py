"""Unit tests for Criterion type models (T002).

Tests CriterionType, CommandCriterion, CriterionInput discriminator, and validation.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from endless8.models.criteria import CriterionInput


class TestCriterionType:
    """Tests for CriterionType StrEnum."""

    def test_criterion_type_values(self) -> None:
        """Test that CriterionType has semantic and command values."""
        from endless8.models.criteria import CriterionType

        assert CriterionType.SEMANTIC.value == "semantic"
        assert CriterionType.COMMAND.value == "command"

    def test_criterion_type_is_str(self) -> None:
        """Test that CriterionType values are strings (StrEnum)."""
        from endless8.models.criteria import CriterionType

        assert isinstance(CriterionType.SEMANTIC, str)
        assert isinstance(CriterionType.COMMAND, str)

    def test_criterion_type_has_exactly_two_members(self) -> None:
        """Test that CriterionType has exactly 2 members."""
        from endless8.models.criteria import CriterionType

        assert len(CriterionType) == 2


class TestCommandCriterion:
    """Tests for CommandCriterion model."""

    def test_command_criterion_valid(self) -> None:
        """Test valid CommandCriterion creation."""
        from endless8.models.criteria import CommandCriterion

        criterion = CommandCriterion(
            type="command",
            command="pytest tests/",
        )
        assert criterion.type == "command"
        assert criterion.command == "pytest tests/"
        assert criterion.description is None
        assert criterion.timeout is None

    def test_command_criterion_with_description_and_timeout(self) -> None:
        """Test CommandCriterion with optional fields."""
        from endless8.models.criteria import CommandCriterion

        criterion = CommandCriterion(
            type="command",
            command="pytest --cov=src",
            description="テストカバレッジ90%以上",
            timeout=60.0,
        )
        assert criterion.description == "テストカバレッジ90%以上"
        assert criterion.timeout == 60.0

    def test_command_criterion_empty_command_rejected(self) -> None:
        """Test that empty command string is rejected (Edge Case)."""
        from endless8.models.criteria import CommandCriterion

        with pytest.raises(ValidationError, match="string_too_short"):
            CommandCriterion(type="command", command="")

    def test_command_criterion_invalid_type_rejected(self) -> None:
        """Test that type must be 'command'."""
        from endless8.models.criteria import CommandCriterion

        with pytest.raises(ValidationError):
            CommandCriterion(type="semantic", command="echo hello")

    def test_command_criterion_negative_timeout_rejected(self) -> None:
        """Test that negative timeout is rejected."""
        from endless8.models.criteria import CommandCriterion

        with pytest.raises(ValidationError):
            CommandCriterion(type="command", command="echo", timeout=-1.0)

    def test_command_criterion_zero_timeout_rejected(self) -> None:
        """Test that zero timeout is rejected (gt=0)."""
        from endless8.models.criteria import CommandCriterion

        with pytest.raises(ValidationError):
            CommandCriterion(type="command", command="echo", timeout=0.0)


class TestCriterionDiscriminator:
    """Tests for _criterion_discriminator function."""

    def test_discriminator_str_input(self) -> None:
        """Test that str input returns 'str' tag."""
        from endless8.models.criteria import _criterion_discriminator

        assert _criterion_discriminator("テストが通る") == "str"

    def test_discriminator_dict_command_input(self) -> None:
        """Test that dict with type='command' returns 'command' tag."""
        from endless8.models.criteria import _criterion_discriminator

        result = _criterion_discriminator({"type": "command", "command": "pytest"})
        assert result == "command"

    def test_discriminator_dict_without_type_raises(self) -> None:
        """Test that dict without type='command' raises ValueError."""
        from endless8.models.criteria import _criterion_discriminator

        with pytest.raises(ValueError, match="must have type='command'"):
            _criterion_discriminator({"command": "pytest"})

    def test_discriminator_dict_wrong_type_raises(self) -> None:
        """Test that dict with wrong type value raises ValueError."""
        from endless8.models.criteria import _criterion_discriminator

        with pytest.raises(ValueError, match="must have type='command'"):
            _criterion_discriminator({"type": "semantic", "command": "pytest"})

    def test_discriminator_command_criterion_instance(self) -> None:
        """Test that CommandCriterion instance returns 'command' tag."""
        from endless8.models.criteria import CommandCriterion, _criterion_discriminator

        criterion = CommandCriterion(type="command", command="pytest")
        assert _criterion_discriminator(criterion) == "command"

    def test_discriminator_unsupported_type_raises(self) -> None:
        """Test that unsupported types raise ValueError."""
        from endless8.models.criteria import _criterion_discriminator

        with pytest.raises(ValueError, match="Cannot discriminate"):
            _criterion_discriminator(42)

        with pytest.raises(ValueError, match="Cannot discriminate"):
            _criterion_discriminator([1, 2, 3])


class _CriteriaContainer(BaseModel):
    """Helper model for CriterionInput tests."""

    criteria: list[CriterionInput] = Field(...)


class TestCriterionInput:
    """Tests for CriterionInput discriminated union type."""

    def test_str_criterion_accepted(self) -> None:
        """Test that plain string is accepted as semantic criterion (FR-004)."""
        container = _CriteriaContainer(criteria=["テストが通る"])
        assert container.criteria[0] == "テストが通る"
        assert isinstance(container.criteria[0], str)

    def test_command_criterion_dict_accepted(self) -> None:
        """Test that command dict is accepted."""
        from endless8.models.criteria import CommandCriterion

        container = _CriteriaContainer(
            criteria=[{"type": "command", "command": "pytest tests/"}]
        )
        assert isinstance(container.criteria[0], CommandCriterion)
        assert container.criteria[0].command == "pytest tests/"

    def test_mixed_criteria_accepted(self) -> None:
        """Test that mixed str and command criteria are accepted (FR-001)."""
        from endless8.models.criteria import CommandCriterion

        container = _CriteriaContainer(
            criteria=[
                "コードが読みやすい",
                {"type": "command", "command": "pytest"},
                "ドキュメントが正しい",
            ]
        )
        assert isinstance(container.criteria[0], str)
        assert isinstance(container.criteria[1], CommandCriterion)
        assert isinstance(container.criteria[2], str)

    def test_invalid_criterion_type_rejected(self) -> None:
        """Test that invalid criterion types are rejected."""
        with pytest.raises((ValidationError, ValueError)):
            _CriteriaContainer(criteria=[42])

    def test_dict_without_command_type_rejected(self) -> None:
        """Test that dict without type='command' is rejected."""
        with pytest.raises((ValidationError, ValueError)):
            _CriteriaContainer(criteria=[{"type": "semantic", "command": "echo"}])

    def test_backward_compatibility_all_strings(self) -> None:
        """Test that all-string criteria (existing format) still work."""
        container = _CriteriaContainer(criteria=["条件1", "条件2", "条件3"])
        assert all(isinstance(c, str) for c in container.criteria)
        assert len(container.criteria) == 3
