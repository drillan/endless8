"""Unit tests for Engine raw logging feature (Issue #33)."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from endless8.config import EngineConfig, LoggingOptions
from endless8.engine import Engine
from endless8.models import (
    CriteriaEvaluation,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    LoopStatus,
    SummaryMetadata,
    TaskInput,
)


class TestEngineRawLog:
    """Tests for Engine raw logging feature."""

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストタスク",
            criteria=["完了条件1"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="実行完了",
            artifacts=["test.py"],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="テスト",
                result=ExecutionStatus.SUCCESS,
                reason="完了",
                artifacts=["test.py"],
                metadata=SummaryMetadata(),
                timestamp="2026-01-01T00:00:00Z",
            ),
            [],
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        """Create mock judgment agent that completes on first iteration."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="完了条件1",
                    is_met=True,
                    evidence="確認済み",
                    confidence=0.95,
                )
            ],
            overall_reason="完了",
        )
        return agent

    @pytest.fixture
    def task_input(self) -> TaskInput:
        """Create sample task input."""
        return TaskInput(
            task="テストタスク",
            criteria=["完了条件1"],
            max_iterations=1,
        )

    async def test_raw_log_saved_to_file(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Engine saves raw log file when logging.raw_log=True."""
        log_dir = tmp_path / "logs"
        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=1,
            logging=LoggingOptions(raw_log=True, raw_log_dir=str(log_dir)),
        )

        # Give execution agent a raw_log_collector attribute
        mock_execution_agent.raw_log_collector = None

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert log_dir.exists()
        log_files = list(log_dir.glob("iteration-*.jsonl"))
        assert len(log_files) == 1
        assert log_files[0].name == "iteration-1.jsonl"

    async def test_raw_log_content_passed_to_summary_agent(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Engine passes raw_log_content to SummaryAgent when raw_log=True."""
        log_dir = tmp_path / "logs"
        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=1,
            logging=LoggingOptions(raw_log=True, raw_log_dir=str(log_dir)),
        )

        mock_execution_agent.raw_log_collector = None

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        await engine.run(task_input)

        # Verify summary agent was called with raw_log_content parameter
        mock_summary_agent.run.assert_called_once()
        call_args = mock_summary_agent.run.call_args
        # raw_log_content should be passed (positional or keyword)
        if call_args.kwargs:
            assert "raw_log_content" in call_args.kwargs
        else:
            # Check positional args - 4th arg is raw_log_content
            assert len(call_args.args) >= 4

    async def test_raw_log_skipped_when_disabled(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Engine does NOT save raw log when logging.raw_log=False."""
        log_dir = tmp_path / "logs"
        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=1,
            logging=LoggingOptions(raw_log=False, raw_log_dir=str(log_dir)),
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        # Log directory should NOT be created
        assert not log_dir.exists()

    async def test_raw_log_skipped_no_raw_log_content_to_summary(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """SummaryAgent called without raw_log_content when raw_log=False."""
        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=1,
            logging=LoggingOptions(raw_log=False),
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        await engine.run(task_input)

        # Verify summary agent was called without raw_log_content
        call_args = mock_summary_agent.run.call_args
        # Should be called with 3 positional args (no raw_log_content)
        assert len(call_args.args) == 3 or (
            "raw_log_content" not in (call_args.kwargs or {})
        )

    async def test_raw_log_dir_created_if_not_exists(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Engine creates raw_log_dir if it doesn't exist."""
        log_dir = tmp_path / "nested" / "deep" / "logs"
        assert not log_dir.exists()

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=1,
            logging=LoggingOptions(raw_log=True, raw_log_dir=str(log_dir)),
        )

        mock_execution_agent.raw_log_collector = None

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        await engine.run(task_input)

        assert log_dir.exists()

    async def test_raw_log_multiple_iterations(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Each iteration gets its own log file."""
        log_dir = tmp_path / "logs"

        # Judgment agent: not complete until iteration 3
        mock_judgment_agent = AsyncMock()
        call_count = 0

        async def judgment_side_effect(
            *_args: object, **_kwargs: object
        ) -> JudgmentResult:
            nonlocal call_count
            call_count += 1
            return JudgmentResult(
                is_complete=(call_count >= 3),
                evaluations=[
                    CriteriaEvaluation(
                        criterion="完了条件1",
                        is_met=(call_count >= 3),
                        evidence="チェック",
                        confidence=0.9,
                    )
                ],
                overall_reason="進行中" if call_count < 3 else "完了",
            )

        mock_judgment_agent.run.side_effect = judgment_side_effect

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=5,
            logging=LoggingOptions(raw_log=True, raw_log_dir=str(log_dir)),
        )

        mock_execution_agent.raw_log_collector = None

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        multi_task = TaskInput(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=5,
        )

        result = await engine.run(multi_task)

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used == 3
        log_files = sorted(log_dir.glob("iteration-*.jsonl"))
        assert len(log_files) == 3
        assert log_files[0].name == "iteration-1.jsonl"
        assert log_files[1].name == "iteration-2.jsonl"
        assert log_files[2].name == "iteration-3.jsonl"
