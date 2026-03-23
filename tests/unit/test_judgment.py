"""Tests for shared judgment logic."""

from unittest.mock import AsyncMock, patch

import pytest

from endless8.judgment import (
    build_judgment_result_from_commands,
    has_semantic_criteria,
    run_command_criteria,
    run_judgment_phase,
)
from endless8.models import (
    CommandCriterion,
    CommandResult,
    CriteriaEvaluation,
    CriterionType,
    ExecutionStatus,
    ExecutionSummary,
    JudgmentResult,
    SummaryMetadata,
)
from endless8.models.criteria import CriterionInput


class TestHasSemanticCriteria:
    def test_mixed_criteria(self) -> None:
        criteria: list[CriterionInput] = [
            "semantic",
            CommandCriterion(type="command", command="test"),
        ]
        assert has_semantic_criteria(criteria) is True

    def test_command_only(self) -> None:
        criteria = [CommandCriterion(type="command", command="test")]
        assert has_semantic_criteria(criteria) is False

    def test_semantic_only(self) -> None:
        assert has_semantic_criteria(["condition"]) is True

    def test_empty_list(self) -> None:
        assert has_semantic_criteria([]) is False

    def test_multiple_semantic(self) -> None:
        assert has_semantic_criteria(["cond1", "cond2"]) is True


class TestBuildJudgmentResultFromCommands:
    def test_all_met(self) -> None:
        evals = [
            CriteriaEvaluation(
                criterion="test passes",
                is_met=True,
                evidence="exit_code=0",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=0, execution_time_sec=1.0),
            )
        ]
        result = build_judgment_result_from_commands(evals)
        assert result.is_complete is True
        assert result.suggested_next_action is None

    def test_partial_failure(self) -> None:
        evals = [
            CriteriaEvaluation(
                criterion="test passes",
                is_met=False,
                evidence="exit_code=1",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=1, execution_time_sec=1.0),
            )
        ]
        result = build_judgment_result_from_commands(evals)
        assert result.is_complete is False
        assert result.suggested_next_action is not None

    def test_all_failed(self) -> None:
        evals = [
            CriteriaEvaluation(
                criterion="cond1",
                is_met=False,
                evidence="exit_code=1",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=1, execution_time_sec=0.5),
            ),
            CriteriaEvaluation(
                criterion="cond2",
                is_met=False,
                evidence="exit_code=2",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=2, execution_time_sec=0.5),
            ),
        ]
        result = build_judgment_result_from_commands(evals)
        assert result.is_complete is False
        assert "cond1" in result.overall_reason
        assert "cond2" in result.overall_reason

    def test_mixed_met_and_not_met(self) -> None:
        evals = [
            CriteriaEvaluation(
                criterion="passes",
                is_met=True,
                evidence="exit_code=0",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=0, execution_time_sec=0.5),
            ),
            CriteriaEvaluation(
                criterion="fails",
                is_met=False,
                evidence="exit_code=1",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=1, execution_time_sec=0.5),
            ),
        ]
        result = build_judgment_result_from_commands(evals)
        assert result.is_complete is False

    def test_evaluations_preserved(self) -> None:
        evals = [
            CriteriaEvaluation(
                criterion="test passes",
                is_met=True,
                evidence="exit_code=0",
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=CommandResult(exit_code=0, execution_time_sec=1.0),
            )
        ]
        result = build_judgment_result_from_commands(evals)
        assert result.evaluations == evals


class TestRunCommandCriteria:
    @pytest.mark.asyncio
    async def test_executes_command_criteria(self) -> None:
        criteria: list[CriterionInput] = [
            "semantic condition",
            CommandCriterion(
                type="command", command="pytest", description="tests pass"
            ),
        ]
        mock_result = CommandResult(
            exit_code=0, stdout="ok", stderr="", execution_time_sec=0.5
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            evals, results = await run_command_criteria(criteria, "/tmp", 30.0)

        assert len(evals) == 1
        assert evals[0].is_met is True
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_skips_semantic_criteria(self) -> None:
        criteria = ["only semantic"]
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock()
            evals, results = await run_command_criteria(criteria, "/tmp", 30.0)
        assert len(evals) == 0
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_includes_stderr_in_evidence(self) -> None:
        criteria = [
            CommandCriterion(type="command", command="failing", description="test"),
        ]
        mock_result = CommandResult(
            exit_code=1, stdout="", stderr="error msg", execution_time_sec=0.1
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            evals, _ = await run_command_criteria(criteria, "/tmp", 30.0)

        assert "stderr:" in evals[0].evidence

    @pytest.mark.asyncio
    async def test_uses_description_as_criterion(self) -> None:
        criteria = [
            CommandCriterion(
                type="command", command="pytest", description="tests must pass"
            ),
        ]
        mock_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.2
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            evals, _ = await run_command_criteria(criteria, "/tmp", 30.0)

        assert evals[0].criterion == "tests must pass"

    @pytest.mark.asyncio
    async def test_uses_command_as_criterion_when_no_description(self) -> None:
        criteria = [
            CommandCriterion(type="command", command="pytest"),
        ]
        mock_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.2
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            evals, _ = await run_command_criteria(criteria, "/tmp", 30.0)

        assert evals[0].criterion == "pytest"

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_is_not_met(self) -> None:
        criteria = [
            CommandCriterion(type="command", command="exit 1"),
        ]
        mock_result = CommandResult(
            exit_code=1, stdout="", stderr="", execution_time_sec=0.1
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            evals, _ = await run_command_criteria(criteria, "/tmp", 30.0)

        assert evals[0].is_met is False

    @pytest.mark.asyncio
    async def test_criterion_index_in_results(self) -> None:
        """CommandCriterionResult stores correct criterion_index (skip semantics)."""
        criteria: list[CriterionInput] = [
            "semantic",
            CommandCriterion(type="command", command="cmd1"),
            CommandCriterion(type="command", command="cmd2"),
        ]
        mock_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.1
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            _, cmd_results = await run_command_criteria(criteria, "/tmp", 30.0)

        assert cmd_results[0].criterion_index == 1
        assert cmd_results[1].criterion_index == 2


class TestRunJudgmentPhase:
    @pytest.fixture
    def summary(self) -> ExecutionSummary:
        return ExecutionSummary(
            iteration=1,
            approach="test approach",
            result=ExecutionStatus.SUCCESS,
            reason="done",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-03-23T10:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_command_only_skips_llm(self, summary: ExecutionSummary) -> None:
        criteria = [
            CommandCriterion(type="command", command="pytest", description="test")
        ]
        mock_result = CommandResult(
            exit_code=0, stdout="ok", stderr="", execution_time_sec=0.5
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            result = await run_judgment_phase(
                criteria=criteria,
                task="task",
                summary=summary,
                cwd="/tmp",
                default_timeout=30.0,
                judgment_agent_run=None,
            )
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_command_only_no_agent_needed(
        self, summary: ExecutionSummary
    ) -> None:
        """Passing judgment_agent_run=None is valid for command-only criteria."""
        criteria = [CommandCriterion(type="command", command="true")]
        mock_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.1
        )
        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_result)
            result = await run_judgment_phase(
                criteria=criteria,
                task="task",
                summary=summary,
                cwd="/tmp",
                default_timeout=30.0,
                judgment_agent_run=None,
            )
        assert result is not None

    @pytest.mark.asyncio
    async def test_semantic_only_calls_agent(self, summary: ExecutionSummary) -> None:
        mock_judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="cond",
                    is_met=True,
                    evidence="ok",
                    confidence=0.9,
                )
            ],
            overall_reason="done",
        )
        mock_run = AsyncMock(return_value=mock_judgment)
        with patch("endless8.judgment.CommandExecutor"):
            result = await run_judgment_phase(
                criteria=["semantic condition"],
                task="task",
                summary=summary,
                cwd="/tmp",
                default_timeout=30.0,
                judgment_agent_run=mock_run,
            )
        assert result.is_complete is True
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_semantic_without_agent_raises(
        self, summary: ExecutionSummary
    ) -> None:
        with (
            patch("endless8.judgment.CommandExecutor"),
            pytest.raises(RuntimeError, match="Judgment agent not configured"),
        ):
            await run_judgment_phase(
                criteria=["semantic condition"],
                task="task",
                summary=summary,
                cwd="/tmp",
                default_timeout=30.0,
                judgment_agent_run=None,
            )

    @pytest.mark.asyncio
    async def test_mixed_criteria_merges_results(
        self, summary: ExecutionSummary
    ) -> None:
        cmd_criterion = CommandCriterion(
            type="command", command="pytest", description="tests pass"
        )
        mock_cmd_result = CommandResult(
            exit_code=0, stdout="", stderr="", execution_time_sec=0.5
        )
        mock_judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="semantic cond",
                    is_met=True,
                    evidence="looks good",
                    confidence=0.9,
                )
            ],
            overall_reason="all good",
        )
        mock_run = AsyncMock(return_value=mock_judgment)

        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_cmd_result)
            result = await run_judgment_phase(
                criteria=["semantic cond", cmd_criterion],
                task="task",
                summary=summary,
                cwd="/tmp",
                default_timeout=30.0,
                judgment_agent_run=mock_run,
            )

        assert result.is_complete is True
        assert len(result.evaluations) == 2

    @pytest.mark.asyncio
    async def test_mixed_command_fails_returns_incomplete(
        self, summary: ExecutionSummary
    ) -> None:
        cmd_criterion = CommandCriterion(
            type="command", command="pytest", description="tests pass"
        )
        mock_cmd_result = CommandResult(
            exit_code=1, stdout="", stderr="FAILED", execution_time_sec=0.5
        )
        mock_judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="semantic cond",
                    is_met=True,
                    evidence="looks good",
                    confidence=0.9,
                )
            ],
            overall_reason="semantic ok",
        )
        mock_run = AsyncMock(return_value=mock_judgment)

        with patch("endless8.judgment.CommandExecutor") as MockExecutor:
            MockExecutor.return_value.execute = AsyncMock(return_value=mock_cmd_result)
            result = await run_judgment_phase(
                criteria=["semantic cond", cmd_criterion],
                task="task",
                summary=summary,
                cwd="/tmp",
                default_timeout=30.0,
                judgment_agent_run=mock_run,
            )

        assert result.is_complete is False
        assert result.suggested_next_action is not None
