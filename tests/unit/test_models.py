"""Unit tests for data models."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from pathlib import Path

from endless8.models import (
    CriteriaEvaluation,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    Knowledge,
    KnowledgeConfidence,
    KnowledgeType,
    LoopResult,
    LoopStatus,
    SummaryMetadata,
    TaskInput,
)


class TestRawOutputContextConfig:
    """Tests for raw_output_context configuration field."""

    def test_raw_output_context_default_is_zero(self) -> None:
        """Test that raw_output_context defaults to 0."""
        from endless8.config import EngineConfig

        config = EngineConfig(task="テスト", criteria=["条件"])
        assert config.raw_output_context == 0

    def test_raw_output_context_configurable(self) -> None:
        """Test that raw_output_context can be set to 1."""
        from endless8.config import EngineConfig

        config = EngineConfig(task="テスト", criteria=["条件"], raw_output_context=1)
        assert config.raw_output_context == 1

    def test_raw_output_context_validation_rejects_invalid(self) -> None:
        """Test that values >= 2 and negative values are rejected."""
        from endless8.config import EngineConfig

        with pytest.raises(ValidationError):
            EngineConfig(task="テスト", criteria=["条件"], raw_output_context=2)

        with pytest.raises(ValidationError):
            EngineConfig(task="テスト", criteria=["条件"], raw_output_context=-1)

    def test_yaml_config_with_raw_output_context(self, tmp_path: Path) -> None:
        """Test that raw_output_context is parsed from YAML."""

        import yaml

        from endless8.config import load_config

        config_file = tmp_path / "config.yaml"
        config_data = {
            "task": "テスト",
            "criteria": ["条件"],
            "raw_output_context": 1,
        }
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        config = load_config(config_file)
        assert config.raw_output_context == 1

    def test_yaml_config_without_raw_output_context_defaults_to_zero(
        self, tmp_path: Path
    ) -> None:
        """Test that YAML without raw_output_context defaults to 0."""

        import yaml

        from endless8.config import load_config

        config_file = tmp_path / "config.yaml"
        config_data = {
            "task": "テスト",
            "criteria": ["条件"],
        }
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        config = load_config(config_file)
        assert config.raw_output_context == 0


class TestMaxTurnsConfig:
    """Tests for MaxTurnsConfig model."""

    def test_default_values(self) -> None:
        """Test that MaxTurnsConfig has correct default values."""
        from endless8.config import MaxTurnsConfig

        config = MaxTurnsConfig()
        assert config.intake == 10
        assert config.execution == 50
        assert config.summary == 10
        assert config.judgment == 10

    def test_partial_override(self) -> None:
        """Test that individual fields can be overridden."""
        from endless8.config import MaxTurnsConfig

        config = MaxTurnsConfig(judgment=25)
        assert config.intake == 10
        assert config.execution == 50
        assert config.summary == 10
        assert config.judgment == 25

    def test_full_override(self) -> None:
        """Test that all fields can be overridden."""
        from endless8.config import MaxTurnsConfig

        config = MaxTurnsConfig(intake=5, execution=100, summary=20, judgment=30)
        assert config.intake == 5
        assert config.execution == 100
        assert config.summary == 20
        assert config.judgment == 30

    def test_validation_min(self) -> None:
        """Test that values below 1 are rejected."""
        from endless8.config import MaxTurnsConfig

        with pytest.raises(ValidationError):
            MaxTurnsConfig(intake=0)
        with pytest.raises(ValidationError):
            MaxTurnsConfig(execution=-1)

    def test_validation_max(self) -> None:
        """Test that values above 200 are rejected."""
        from endless8.config import MaxTurnsConfig

        with pytest.raises(ValidationError):
            MaxTurnsConfig(intake=201)
        with pytest.raises(ValidationError):
            MaxTurnsConfig(judgment=300)

    def test_claude_options_dict_parse(self) -> None:
        """Test that ClaudeOptions accepts max_turns as dict."""
        from endless8.config import ClaudeOptions

        options = ClaudeOptions(max_turns={"judgment": 25})
        assert options.max_turns.judgment == 25
        assert options.max_turns.intake == 10  # default

    def test_engine_config_default_max_turns(self) -> None:
        """Test that EngineConfig has default MaxTurnsConfig."""
        from endless8.config import EngineConfig

        config = EngineConfig(task="テスト", criteria=["条件"])
        assert config.claude_options.max_turns.intake == 10
        assert config.claude_options.max_turns.execution == 50
        assert config.claude_options.max_turns.summary == 10
        assert config.claude_options.max_turns.judgment == 10

    def test_yaml_config_with_max_turns(self, tmp_path: Path) -> None:
        """Test that max_turns is parsed from YAML config."""
        import yaml

        from endless8.config import load_config

        config_data = {
            "task": "テスト",
            "criteria": ["条件"],
            "claude_options": {
                "max_turns": {
                    "judgment": 25,
                },
            },
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        config = load_config(config_file)
        assert config.claude_options.max_turns.judgment == 25
        assert config.claude_options.max_turns.intake == 10


class TestTaskInput:
    """Tests for TaskInput model."""

    def test_task_input_valid(self) -> None:
        """Test valid TaskInput creation."""
        task = TaskInput(
            task="テストカバレッジを向上",
            criteria=["90%以上"],
        )
        assert task.task == "テストカバレッジを向上"
        assert task.criteria == ["90%以上"]
        assert task.max_iterations == 10  # default

    def test_task_input_with_options(self) -> None:
        """Test TaskInput with custom options."""
        task = TaskInput(
            task="タスク",
            criteria=["条件1", "条件2"],
            max_iterations=5,
            history_context_size=10,
        )
        assert task.max_iterations == 5
        assert task.history_context_size == 10

    def test_task_input_empty_task_fails(self) -> None:
        """Test that empty task fails validation."""
        with pytest.raises(ValidationError):
            TaskInput(task="", criteria=["条件"])

    def test_task_input_empty_criteria_fails(self) -> None:
        """Test that empty criteria fails validation."""
        with pytest.raises(ValidationError):
            TaskInput(task="タスク", criteria=[])


class TestIntakeResult:
    """Tests for IntakeResult model."""

    def test_intake_result_accepted(self) -> None:
        """Test accepted IntakeResult."""
        result = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="タスク",
            criteria=["条件"],
        )
        assert result.status == IntakeStatus.ACCEPTED
        assert result.clarification_questions == []

    def test_intake_result_needs_clarification(self) -> None:
        """Test IntakeResult needing clarification."""
        result = IntakeResult(
            status=IntakeStatus.NEEDS_CLARIFICATION,
            task="タスク",
            criteria=["曖昧な条件"],
            clarification_questions=["具体的にどういう意味ですか？"],
        )
        assert result.status == IntakeStatus.NEEDS_CLARIFICATION
        assert len(result.clarification_questions) == 1


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_execution_result_success(self) -> None:
        """Test successful ExecutionResult."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了しました",
            artifacts=["file1.py", "file2.py"],
        )
        assert result.status == ExecutionStatus.SUCCESS
        assert len(result.artifacts) == 2

    def test_execution_result_failure(self) -> None:
        """Test failed ExecutionResult."""
        result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="エラーが発生",
            artifacts=[],
        )
        assert result.status == ExecutionStatus.FAILURE


class TestJudgmentResult:
    """Tests for JudgmentResult model."""

    def test_judgment_result_complete(self) -> None:
        """Test complete JudgmentResult."""
        result = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=True,
                    evidence="証拠",
                    confidence=0.95,
                )
            ],
            overall_reason="完了",
        )
        assert result.is_complete is True
        assert result.suggested_next_action is None

    def test_judgment_result_incomplete(self) -> None:
        """Test incomplete JudgmentResult."""
        result = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=False,
                    evidence="未達成",
                    confidence=0.8,
                )
            ],
            overall_reason="未完了",
            suggested_next_action="次のステップ",
        )
        assert result.is_complete is False
        assert result.suggested_next_action is not None


class TestCriteriaEvaluation:
    """Tests for CriteriaEvaluation model."""

    def test_criteria_evaluation_valid(self) -> None:
        """Test valid CriteriaEvaluation."""
        evaluation = CriteriaEvaluation(
            criterion="テストが通る",
            is_met=True,
            evidence="pytest passed",
            confidence=0.95,
        )
        assert evaluation.criterion == "テストが通る"
        assert evaluation.is_met is True
        assert evaluation.confidence == 0.95

    def test_criteria_evaluation_confidence_bounds(self) -> None:
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            CriteriaEvaluation(
                criterion="条件",
                is_met=True,
                evidence="証拠",
                confidence=1.5,  # Invalid
            )


class TestLoopResult:
    """Tests for LoopResult model."""

    def test_loop_result_completed(self) -> None:
        """Test completed LoopResult."""
        final_judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="テスト条件",
                    is_met=True,
                    evidence="条件を満たしています",
                    confidence=0.95,
                )
            ],
            overall_reason="完了",
        )
        result = LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=3,
            final_judgment=final_judgment,
        )
        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used == 3
        assert result.final_judgment is not None

    def test_loop_result_max_iterations(self) -> None:
        """Test max iterations LoopResult."""
        result = LoopResult(
            status=LoopStatus.MAX_ITERATIONS,
            iterations_used=10,
        )
        assert result.status == LoopStatus.MAX_ITERATIONS

    def test_loop_result_error_requires_error_message(self) -> None:
        """Test that ERROR status requires error_message."""
        with pytest.raises(ValidationError, match="error_message required"):
            LoopResult(
                status=LoopStatus.ERROR,
                iterations_used=1,
            )

    def test_loop_result_error_with_message(self) -> None:
        """Test ERROR status with error_message."""
        result = LoopResult(
            status=LoopStatus.ERROR,
            iterations_used=1,
            error_message="Something went wrong",
        )
        assert result.status == LoopStatus.ERROR
        assert result.error_message == "Something went wrong"

    def test_loop_result_completed_requires_final_judgment(self) -> None:
        """Test that COMPLETED status requires final_judgment."""
        with pytest.raises(ValidationError, match="final_judgment required"):
            LoopResult(
                status=LoopStatus.COMPLETED,
                iterations_used=3,
            )


class TestExecutionSummary:
    """Tests for ExecutionSummary model."""

    def test_execution_summary_basic(self) -> None:
        """Test basic ExecutionSummary."""
        summary = ExecutionSummary(
            iteration=1,
            approach="テストファースト",
            result=ExecutionStatus.SUCCESS,
            reason="完了",
            artifacts=["test.py"],
            metadata=SummaryMetadata(),
            timestamp="2026-01-23T10:00:00Z",
        )
        assert summary.iteration == 1
        assert summary.result == ExecutionStatus.SUCCESS


class TestKnowledge:
    """Tests for Knowledge model."""

    def test_knowledge_basic(self) -> None:
        """Test basic Knowledge creation."""
        knowledge = Knowledge(
            type=KnowledgeType.DISCOVERY,
            category="testing",
            content="テストパターンを発見",
            source_task="テスト実装",
        )
        assert knowledge.type == KnowledgeType.DISCOVERY
        assert knowledge.confidence == KnowledgeConfidence.MEDIUM  # default

    def test_knowledge_types(self) -> None:
        """Test all knowledge types."""
        for ktype in KnowledgeType:
            knowledge = Knowledge(
                type=ktype,
                category="general",
                content="テスト",
                source_task="タスク",
            )
            assert knowledge.type == ktype
