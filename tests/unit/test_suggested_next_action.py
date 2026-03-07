"""Unit tests for suggested_next_action flow from judgment to execution agent."""

from unittest.mock import AsyncMock

import pytest

from endless8.agents import ExecutionContext
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


class TestExecutionContextSuggestedNextAction:
    """Tests for suggested_next_action field in ExecutionContext."""

    def test_execution_context_accepts_suggested_next_action(self) -> None:
        """Test that ExecutionContext accepts suggested_next_action field."""
        context = ExecutionContext(
            task="テスト",
            criteria=["条件"],
            iteration=2,
            history_context="履歴",
            knowledge_context="ナレッジ",
            working_directory="/tmp/test",
            suggested_next_action="異なるアルゴリズムを検討してください",
        )
        assert context.suggested_next_action == "異なるアルゴリズムを検討してください"

    def test_execution_context_suggested_next_action_defaults_to_none(self) -> None:
        """Test that suggested_next_action defaults to None."""
        context = ExecutionContext(
            task="テスト",
            criteria=["条件"],
            iteration=1,
            history_context="履歴",
            knowledge_context="ナレッジ",
            working_directory="/tmp/test",
        )
        assert context.suggested_next_action is None


class TestBuildPromptSuggestedNextAction:
    """Tests for suggested_next_action in prompt generation."""

    async def test_prompt_includes_suggested_next_action_when_provided(self) -> None:
        """Test that prompt includes judgment feedback section."""
        from endless8.agents.execution import ExecutionAgent

        context = ExecutionContext(
            task="パフォーマンス最適化",
            criteria=["実行時間を改善する"],
            iteration=3,
            history_context="履歴",
            knowledge_context="ナレッジ",
            working_directory="/tmp/test",
            suggested_next_action="セグメント化篩やビット操作を検討してください",
        )

        agent = ExecutionAgent()
        prompt = agent._build_prompt(context)

        assert "前回の判定フィードバック" in prompt
        assert "セグメント化篩やビット操作を検討してください" in prompt

    async def test_prompt_excludes_suggested_next_action_when_none(self) -> None:
        """Test that prompt does not include judgment feedback section when None."""
        from endless8.agents.execution import ExecutionAgent

        context = ExecutionContext(
            task="テスト",
            criteria=["条件"],
            iteration=1,
            history_context="履歴",
            knowledge_context="ナレッジ",
            working_directory="/tmp/test",
        )

        agent = ExecutionAgent()
        prompt = agent._build_prompt(context)

        assert "前回の判定フィードバック" not in prompt


class TestEngineSuggestedNextActionFlow:
    """Tests for suggested_next_action flow through engine loop."""

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="パフォーマンスを最適化する",
            criteria=["実行時間が改善される"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.raw_log_collector = None
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="最適化を実施しました",
            artifacts=[],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="bytearray + 偶数除外",
                result=ExecutionStatus.SUCCESS,
                reason="最適化完了",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
            [],
        )
        return agent

    def _make_judgment(
        self, *, is_complete: bool, suggested_next_action: str | None = None
    ) -> JudgmentResult:
        """Create a JudgmentResult with given parameters."""
        return JudgmentResult(
            is_complete=is_complete,
            evaluations=[
                CriteriaEvaluation(
                    criterion="実行時間が改善される",
                    is_met=is_complete,
                    evidence="テスト結果",
                    confidence=0.9,
                )
            ],
            overall_reason="判定理由",
            suggested_next_action=suggested_next_action,
        )

    async def test_suggested_next_action_passed_to_execution_context(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Test that judgment's suggested_next_action is passed to next iteration's execution context."""
        from endless8.engine import Engine

        suggestion = "セグメント化篩を試してください"

        # First iteration: incomplete with suggestion
        # Second iteration: complete
        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = [
            self._make_judgment(is_complete=False, suggested_next_action=suggestion),
            self._make_judgment(is_complete=True),
        ]

        config = EngineConfig(
            task="パフォーマンスを最適化する",
            criteria=["実行時間が改善される"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(
            task="パフォーマンスを最適化する",
            criteria=["実行時間が改善される"],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used == 2

        # Verify the second call to execution agent received suggested_next_action
        calls = mock_execution_agent.run.call_args_list
        assert len(calls) == 2

        # First iteration: no suggested_next_action
        first_context = calls[0].args[0]
        assert isinstance(first_context, ExecutionContext)
        assert first_context.suggested_next_action is None

        # Second iteration: should have the suggestion from judgment
        second_context = calls[1].args[0]
        assert isinstance(second_context, ExecutionContext)
        assert second_context.suggested_next_action == suggestion

    async def test_suggested_next_action_none_when_judgment_has_none(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Test that suggested_next_action is None when judgment doesn't provide one."""
        from endless8.engine import Engine

        # First iteration: incomplete without suggestion
        # Second iteration: complete
        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = [
            self._make_judgment(is_complete=False, suggested_next_action=None),
            self._make_judgment(is_complete=True),
        ]

        config = EngineConfig(
            task="パフォーマンスを最適化する",
            criteria=["実行時間が改善される"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(
            task="パフォーマンスを最適化する",
            criteria=["実行時間が改善される"],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED

        # Second iteration should have None for suggested_next_action
        calls = mock_execution_agent.run.call_args_list
        second_context = calls[1].args[0]
        assert second_context.suggested_next_action is None

    async def test_suggested_next_action_cleared_after_complete(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Test that suggested_next_action from iteration N is only passed to iteration N+1."""
        from endless8.engine import Engine

        # Three iterations:
        # 1: incomplete with suggestion A
        # 2: incomplete with suggestion B
        # 3: complete
        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = [
            self._make_judgment(is_complete=False, suggested_next_action="提案A"),
            self._make_judgment(is_complete=False, suggested_next_action="提案B"),
            self._make_judgment(is_complete=True),
        ]

        config = EngineConfig(
            task="パフォーマンスを最適化する",
            criteria=["実行時間が改善される"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(
            task="タスク",
            criteria=["条件"],
            max_iterations=5,
        )

        await engine.run(task_input)

        calls = mock_execution_agent.run.call_args_list
        assert len(calls) == 3

        # Iteration 1: no previous suggestion
        assert calls[0].args[0].suggested_next_action is None
        # Iteration 2: suggestion A from iteration 1
        assert calls[1].args[0].suggested_next_action == "提案A"
        # Iteration 3: suggestion B from iteration 2
        assert calls[2].args[0].suggested_next_action == "提案B"
