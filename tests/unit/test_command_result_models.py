"""Unit tests for CommandResult model and CriteriaEvaluation extension (T003).

Tests CommandResult model, CriteriaEvaluation with evaluation_method and command_result,
and cross-field validation rules.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestCommandResult:
    """Tests for CommandResult model."""

    def test_command_result_valid(self) -> None:
        """Test valid CommandResult creation."""
        from endless8.models.results import CommandResult

        result = CommandResult(
            exit_code=0,
            stdout="All tests passed",
            stderr="",
            execution_time_sec=1.5,
        )
        assert result.exit_code == 0
        assert result.stdout == "All tests passed"
        assert result.stderr == ""
        assert result.execution_time_sec == 1.5

    def test_command_result_nonzero_exit(self) -> None:
        """Test CommandResult with non-zero exit code."""
        from endless8.models.results import CommandResult

        result = CommandResult(
            exit_code=1,
            stdout="",
            stderr="FAILED tests/test_foo.py",
            execution_time_sec=2.0,
        )
        assert result.exit_code == 1
        assert result.stderr == "FAILED tests/test_foo.py"

    def test_command_result_default_stdout_stderr(self) -> None:
        """Test that stdout and stderr default to empty string."""
        from endless8.models.results import CommandResult

        result = CommandResult(exit_code=0, execution_time_sec=0.1)
        assert result.stdout == ""
        assert result.stderr == ""

    def test_command_result_negative_execution_time_rejected(self) -> None:
        """Test that negative execution time is rejected."""
        from endless8.models.results import CommandResult

        with pytest.raises(ValidationError):
            CommandResult(exit_code=0, execution_time_sec=-1.0)

    def test_command_result_exit_code_127(self) -> None:
        """Test CommandResult with exit code 127 (command not found)."""
        from endless8.models.results import CommandResult

        result = CommandResult(
            exit_code=127,
            stdout="",
            stderr="bash: no_such_command: command not found",
            execution_time_sec=0.01,
        )
        assert result.exit_code == 127


class TestCriteriaEvaluationExtension:
    """Tests for CriteriaEvaluation with evaluation_method and command_result."""

    def test_semantic_evaluation_valid(self) -> None:
        """Test valid semantic CriteriaEvaluation."""
        from endless8.models.criteria import CriterionType
        from endless8.models.results import CriteriaEvaluation

        evaluation = CriteriaEvaluation(
            criterion="コードが読みやすい",
            is_met=True,
            evidence="変数名が明確",
            confidence=0.9,
            evaluation_method=CriterionType.SEMANTIC,
        )
        assert evaluation.evaluation_method == CriterionType.SEMANTIC
        assert evaluation.command_result is None

    def test_command_evaluation_valid(self) -> None:
        """Test valid command CriteriaEvaluation."""
        from endless8.models.criteria import CriterionType
        from endless8.models.results import CommandResult, CriteriaEvaluation

        cmd_result = CommandResult(
            exit_code=0,
            stdout="OK",
            stderr="",
            execution_time_sec=1.0,
        )
        evaluation = CriteriaEvaluation(
            criterion="pytest tests/",
            is_met=True,
            evidence="Exit code 0",
            confidence=1.0,
            evaluation_method=CriterionType.COMMAND,
            command_result=cmd_result,
        )
        assert evaluation.evaluation_method == CriterionType.COMMAND
        assert evaluation.command_result is not None
        assert evaluation.command_result.exit_code == 0

    def test_command_evaluation_confidence_must_be_1(self) -> None:
        """Test that command evaluation confidence must be 1.0 (FR-011)."""
        from endless8.models.criteria import CriterionType
        from endless8.models.results import CommandResult, CriteriaEvaluation

        cmd_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.5
        )
        with pytest.raises(ValidationError, match="FR-011"):
            CriteriaEvaluation(
                criterion="pytest",
                is_met=True,
                evidence="Exit code 0",
                confidence=0.9,  # Must be 1.0 for command
                evaluation_method=CriterionType.COMMAND,
                command_result=cmd_result,
            )

    def test_command_evaluation_requires_command_result(self) -> None:
        """Test that command evaluation requires command_result."""
        from endless8.models.criteria import CriterionType
        from endless8.models.results import CriteriaEvaluation

        with pytest.raises(ValidationError, match="command_result is required"):
            CriteriaEvaluation(
                criterion="pytest",
                is_met=True,
                evidence="Exit code 0",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=None,
            )

    def test_semantic_evaluation_rejects_command_result(self) -> None:
        """Test that semantic evaluation must not have command_result."""
        from endless8.models.criteria import CriterionType
        from endless8.models.results import CommandResult, CriteriaEvaluation

        cmd_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.5
        )
        with pytest.raises(ValidationError, match="must be None"):
            CriteriaEvaluation(
                criterion="コードが読みやすい",
                is_met=True,
                evidence="OK",
                confidence=0.9,
                evaluation_method=CriterionType.SEMANTIC,
                command_result=cmd_result,
            )

    def test_backward_compatible_evaluation_defaults_to_semantic(self) -> None:
        """Test that evaluation_method defaults to SEMANTIC for backward compatibility."""
        from endless8.models.criteria import CriterionType
        from endless8.models.results import CriteriaEvaluation

        evaluation = CriteriaEvaluation(
            criterion="条件",
            is_met=True,
            evidence="証拠",
            confidence=0.9,
        )
        assert evaluation.evaluation_method == CriterionType.SEMANTIC
        assert evaluation.command_result is None
