"""Unit tests for the Engine class."""

from unittest.mock import AsyncMock

import pytest

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


class TestEngine:
    """Tests for Engine class."""

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テストを追加しました",
            artifacts=["tests/test_main.py"],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="テストを追加",
                result=ExecutionStatus.SUCCESS,
                reason="テストファイル作成完了",
                artifacts=["tests/test_main.py"],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
            [],  # No knowledge extracted
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        """Create mock judgment agent."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="pytest --cov で90%以上",
                    is_met=True,
                    evidence="カバレッジレポートで92%を確認",
                    confidence=0.95,
                )
            ],
            overall_reason="すべての完了条件を満たしています",
        )
        return agent

    @pytest.fixture
    def task_input(self) -> TaskInput:
        """Create sample task input."""
        return TaskInput(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            max_iterations=10,
        )

    async def test_engine_run_completes_on_success(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine completes when judgment returns is_complete=True."""
        # Import here to allow tests to run before Engine is implemented
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
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
        assert result.iterations_used >= 1
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is True

    async def test_engine_run_stops_at_max_iterations(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine stops at max iterations when not complete."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Make judgment always return not complete
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="pytest --cov で90%以上",
                    is_met=False,
                    evidence="現在のカバレッジは80%",
                    confidence=0.9,
                )
            ],
            overall_reason="カバレッジが不足しています",
            suggested_next_action="edge case のテストを追加",
        )

        task_input_limited = TaskInput(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=3,  # Limit iterations
        )

        config = EngineConfig(
            task=task_input_limited.task,
            criteria=task_input_limited.criteria,
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input_limited)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.iterations_used == 3
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False

    async def test_engine_run_iter_yields_summaries(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that run_iter yields execution summaries."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        summaries: list[ExecutionSummary] = []
        async for summary in engine.run_iter(task_input):
            summaries.append(summary)

        assert len(summaries) >= 1
        assert all(isinstance(s, ExecutionSummary) for s in summaries)

    async def test_engine_cancel_stops_execution(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that cancel stops the execution loop."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Make judgment always return not complete
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[],
            overall_reason="Not complete",
        )

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=100,  # High limit
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        # Start running and cancel after first iteration
        summaries: list[ExecutionSummary] = []
        async for summary in engine.run_iter(task_input):
            summaries.append(summary)
            await engine.cancel()
            break

        assert engine.is_running is False

    async def test_engine_current_iteration_property(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that current_iteration property reflects execution state."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        assert engine.current_iteration == 0

        await engine.run(task_input)

        assert engine.current_iteration >= 1
