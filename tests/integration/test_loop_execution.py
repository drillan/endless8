"""Integration tests for the task execution loop."""

from unittest.mock import AsyncMock

import pytest

from endless8.config import EngineConfig
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


class TestBasicLoopExecution:
    """Integration tests for basic loop execution."""

    @pytest.fixture
    def mock_agents(self) -> dict[str, AsyncMock]:
        """Create mock agents for integration testing."""
        intake = AsyncMock()
        intake.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
        )

        execution = AsyncMock()
        execution.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テストを追加しました",
            artifacts=["tests/test_main.py"],
        )

        summary = AsyncMock()
        summary.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="テストを追加",
                result=ExecutionStatus.SUCCESS,
                reason="テストファイル作成完了",
                artifacts=["tests/test_main.py"],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
            [],
        )

        judgment = AsyncMock()
        judgment.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="pytest --cov で90%以上",
                    is_met=True,
                    evidence="カバレッジレポートで92%を確認",
                    confidence=0.95,
                )
            ],
            overall_reason="完了",
        )

        return {
            "intake": intake,
            "execution": execution,
            "summary": summary,
            "judgment": judgment,
        }

    async def test_full_loop_execution_completes(
        self,
        mock_agents: dict[str, AsyncMock],
    ) -> None:
        """Test that full loop executes and completes successfully."""
        from endless8.engine import Engine

        config = EngineConfig(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            max_iterations=10,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_agents["intake"],
            execution_agent=mock_agents["execution"],
            summary_agent=mock_agents["summary"],
            judgment_agent=mock_agents["judgment"],
        )

        task_input = TaskInput(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            max_iterations=10,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used >= 1
        assert mock_agents["execution"].run.called
        assert mock_agents["judgment"].run.called

    async def test_loop_respects_max_iterations(
        self,
        mock_agents: dict[str, AsyncMock],
    ) -> None:
        """Test that loop stops at max iterations."""
        from endless8.engine import Engine

        # Make judgment always return not complete
        mock_agents["judgment"].run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="pytest --cov で90%以上",
                    is_met=False,
                    evidence="カバレッジ80%",
                    confidence=0.9,
                )
            ],
            overall_reason="未完了",
        )

        config = EngineConfig(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_agents["intake"],
            execution_agent=mock_agents["execution"],
            summary_agent=mock_agents["summary"],
            judgment_agent=mock_agents["judgment"],
        )

        task_input = TaskInput(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.iterations_used == 3

    async def test_loop_handles_multiple_iterations(
        self,
        mock_agents: dict[str, AsyncMock],
    ) -> None:
        """Test that loop handles multiple iterations correctly."""
        from endless8.engine import Engine

        # First two iterations: not complete, third: complete
        call_count = 0

        def judgment_side_effect(*_args: object, **_kwargs: object) -> JudgmentResult:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return JudgmentResult(
                    is_complete=False,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件",
                            is_met=False,
                            evidence="まだ",
                            confidence=0.8,
                        )
                    ],
                    overall_reason="未完了",
                )
            return JudgmentResult(
                is_complete=True,
                evaluations=[
                    CriteriaEvaluation(
                        criterion="条件",
                        is_met=True,
                        evidence="完了",
                        confidence=0.95,
                    )
                ],
                overall_reason="完了",
            )

        mock_agents["judgment"].run.side_effect = judgment_side_effect

        config = EngineConfig(
            task="タスク",
            criteria=["条件"],
            max_iterations=10,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_agents["intake"],
            execution_agent=mock_agents["execution"],
            summary_agent=mock_agents["summary"],
            judgment_agent=mock_agents["judgment"],
        )

        task_input = TaskInput(
            task="タスク",
            criteria=["条件"],
            max_iterations=10,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used == 3

    async def test_loop_streams_summaries(
        self,
        mock_agents: dict[str, AsyncMock],
    ) -> None:
        """Test that loop streams summaries via run_iter."""
        from endless8.engine import Engine

        config = EngineConfig(
            task="タスク",
            criteria=["条件"],
            max_iterations=10,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_agents["intake"],
            execution_agent=mock_agents["execution"],
            summary_agent=mock_agents["summary"],
            judgment_agent=mock_agents["judgment"],
        )

        task_input = TaskInput(
            task="タスク",
            criteria=["条件"],
            max_iterations=10,
        )

        summaries = []
        async for summary in engine.run_iter(task_input):
            summaries.append(summary)

        assert len(summaries) >= 1
        assert all(isinstance(s, ExecutionSummary) for s in summaries)

    async def test_loop_coordinates_agents_correctly(
        self,
        mock_agents: dict[str, AsyncMock],
    ) -> None:
        """Test that agents are called in the correct order."""
        from endless8.engine import Engine

        call_order: list[str] = []

        async def intake_wrapper(*_args: object, **_kwargs: object) -> IntakeResult:
            call_order.append("intake")
            result: IntakeResult = await mock_agents["intake"].run.return_value
            return result

        async def execution_wrapper(
            *_args: object, **_kwargs: object
        ) -> ExecutionResult:
            call_order.append("execution")
            result: ExecutionResult = mock_agents["execution"].run.return_value
            return result

        async def summary_wrapper(
            *_args: object, **_kwargs: object
        ) -> tuple[ExecutionSummary, list[object]]:
            call_order.append("summary")
            result: tuple[ExecutionSummary, list[object]] = mock_agents[
                "summary"
            ].run.return_value
            return result

        async def judgment_wrapper(*_args: object, **_kwargs: object) -> JudgmentResult:
            call_order.append("judgment")
            result: JudgmentResult = mock_agents["judgment"].run.return_value
            return result

        mock_agents["intake"].run = intake_wrapper
        mock_agents["execution"].run = execution_wrapper
        mock_agents["summary"].run = summary_wrapper
        mock_agents["judgment"].run = judgment_wrapper

        config = EngineConfig(
            task="タスク",
            criteria=["条件"],
            max_iterations=10,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_agents["intake"],
            execution_agent=mock_agents["execution"],
            summary_agent=mock_agents["summary"],
            judgment_agent=mock_agents["judgment"],
        )

        task_input = TaskInput(
            task="タスク",
            criteria=["条件"],
            max_iterations=10,
        )

        await engine.run(task_input)

        # Verify order: intake -> (execution -> summary -> judgment)+
        assert call_order[0] == "intake"
        # After intake, it should be execution, summary, judgment
        remaining = call_order[1:]
        expected_cycle = ["execution", "summary", "judgment"]
        for i, agent in enumerate(remaining):
            assert agent == expected_cycle[i % 3]
