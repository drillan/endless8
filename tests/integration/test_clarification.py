"""Integration tests for clarification flow (User Story 2)."""

import pytest

from endless8.agents.intake import IntakeAgent
from endless8.models import IntakeStatus


class TestClarificationFlow:
    """Tests for clarification flow when task has ambiguous criteria."""

    @pytest.fixture
    def intake_agent(self) -> IntakeAgent:
        """Create intake agent."""
        return IntakeAgent()

    @pytest.mark.asyncio
    async def test_ambiguous_criteria_generates_questions(
        self, intake_agent: IntakeAgent
    ) -> None:
        """Test that ambiguous criteria generates clarification questions."""
        # Ambiguous criteria without clear measurable outcome
        result = await intake_agent.run(
            task="パフォーマンスを改善する",
            criteria=["十分に高速になったら完了"],
        )

        # Should require clarification due to vague criteria
        assert result.status == IntakeStatus.NEEDS_CLARIFICATION
        assert len(result.clarification_questions) > 0
        # Questions should ask for specific metrics
        questions_text = " ".join(result.clarification_questions)
        assert any(
            keyword in questions_text.lower()
            for keyword in ["具体", "数値", "測定", "指標", "基準"]
        )

    @pytest.mark.asyncio
    async def test_clear_criteria_accepted(self, intake_agent: IntakeAgent) -> None:
        """Test that clear criteria are accepted."""
        result = await intake_agent.run(
            task="テストカバレッジを改善する",
            criteria=["pytest --cov で90%以上のカバレッジを達成する"],
        )

        # Should be accepted with clear measurable criteria
        assert result.status == IntakeStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_multiple_ambiguous_criteria(self, intake_agent: IntakeAgent) -> None:
        """Test handling of multiple ambiguous criteria."""
        result = await intake_agent.run(
            task="コードをリファクタリングする",
            criteria=[
                "読みやすくなったら完了",
                "メンテナンスしやすくなったら完了",
                "十分にきれいになったら完了",
            ],
        )

        # Should require clarification for multiple vague criteria
        assert result.status == IntakeStatus.NEEDS_CLARIFICATION
        # Should have questions for each ambiguous criterion
        assert len(result.clarification_questions) >= 1

    @pytest.mark.asyncio
    async def test_mixed_clear_and_ambiguous_criteria(
        self, intake_agent: IntakeAgent
    ) -> None:
        """Test handling of mixed clear and ambiguous criteria."""
        result = await intake_agent.run(
            task="コードを改善する",
            criteria=[
                "全テストがパスする",  # Clear
                "十分にきれいになったら完了",  # Ambiguous
            ],
        )

        # Should ask for clarification on the ambiguous criterion
        assert result.status == IntakeStatus.NEEDS_CLARIFICATION


class TestRejectedTasks:
    """Tests for task rejection scenarios."""

    @pytest.fixture
    def intake_agent(self) -> IntakeAgent:
        """Create intake agent."""
        return IntakeAgent()

    @pytest.mark.asyncio
    async def test_empty_task_handled(self, intake_agent: IntakeAgent) -> None:
        """Test that empty task is rejected or needs clarification."""
        result = await intake_agent.run(
            task="",
            criteria=["条件1"],
        )

        # Empty task should be rejected or require clarification
        assert result.status in (
            IntakeStatus.REJECTED,
            IntakeStatus.NEEDS_CLARIFICATION,
        )

    @pytest.mark.asyncio
    async def test_empty_criteria_needs_clarification(
        self, intake_agent: IntakeAgent
    ) -> None:
        """Test that empty criteria needs clarification."""
        result = await intake_agent.run(
            task="タスクの説明",
            criteria=[],
        )

        # Empty criteria should require clarification
        assert result.status in (
            IntakeStatus.NEEDS_CLARIFICATION,
            IntakeStatus.REJECTED,
        )
