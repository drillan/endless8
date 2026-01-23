"""Unit tests for the Intake Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

from endless8.models import (
    IntakeResult,
    IntakeStatus,
)


class TestIntakeAgent:
    """Tests for IntakeAgent class."""

    async def test_intake_agent_accepts_clear_criteria(
        self,
    ) -> None:
        """Test that intake agent accepts clear, measurable criteria."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="テストカバレッジを90%以上にする",
                    criteria=["pytest --cov で90%以上"],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="テストカバレッジを90%以上にする",
                criteria=["pytest --cov で90%以上"],
            )

            assert result.status == IntakeStatus.ACCEPTED
            assert result.task == "テストカバレッジを90%以上にする"
            assert result.criteria == ["pytest --cov で90%以上"]
            assert result.clarification_questions == []

    async def test_intake_agent_requests_clarification_for_ambiguous_criteria(
        self,
    ) -> None:
        """Test that intake agent generates clarification questions for ambiguous criteria."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.NEEDS_CLARIFICATION,
                    task="パフォーマンスを改善する",
                    criteria=["十分に高速になったら完了"],
                    clarification_questions=[
                        "「十分に高速」とは具体的にどのような指標ですか？",
                        "現在の応答時間と目標の応答時間を教えてください",
                        "どのエンドポイントのパフォーマンスを改善しますか？",
                    ],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="パフォーマンスを改善する",
                criteria=["十分に高速になったら完了"],
            )

            assert result.status == IntakeStatus.NEEDS_CLARIFICATION
            assert result.clarification_questions is not None
            assert len(result.clarification_questions) > 0

    async def test_intake_agent_refines_criteria_with_answers(
        self,
    ) -> None:
        """Test that intake agent refines criteria when answers are provided."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="パフォーマンスを改善する",
                    criteria=[
                        "APIレスポンス時間が200ms以下",
                        "負荷テストで1000リクエスト/秒を処理可能",
                    ],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="パフォーマンスを改善する",
                criteria=["十分に高速になったら完了"],
                clarification_answers={
                    "「十分に高速」とは具体的にどのような指標ですか？": "APIレスポンス時間が200ms以下",
                    "現在の応答時間と目標の応答時間を教えてください": "現在500ms、目標200ms",
                    "どのエンドポイントのパフォーマンスを改善しますか？": "全エンドポイント",
                },
            )

            assert result.status == IntakeStatus.ACCEPTED
            assert len(result.criteria) >= 1
            # Criteria should be more specific than the original
            assert result.criteria != ["十分に高速になったら完了"]

    async def test_intake_agent_rejects_invalid_task(
        self,
    ) -> None:
        """Test that intake agent rejects invalid or empty tasks."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.REJECTED,
                    task="",
                    criteria=[],
                    rejection_reason="タスクが空または無効です",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="",
                criteria=[],
            )

            assert result.status == IntakeStatus.REJECTED
            assert result.rejection_reason is not None

    async def test_intake_agent_validates_multiple_criteria(
        self,
    ) -> None:
        """Test that intake agent validates each criterion individually."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.NEEDS_CLARIFICATION,
                    task="アプリを改善する",
                    criteria=[
                        "テストカバレッジ90%以上",  # Clear
                        "使いやすくする",  # Ambiguous
                        "バグがないこと",  # Ambiguous
                    ],
                    clarification_questions=[
                        "「使いやすくする」の具体的な改善点は何ですか？",
                        "「バグがないこと」をどのように検証しますか？",
                    ],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="アプリを改善する",
                criteria=[
                    "テストカバレッジ90%以上",
                    "使いやすくする",
                    "バグがないこと",
                ],
            )

            assert result.status == IntakeStatus.NEEDS_CLARIFICATION
            # Should generate questions for ambiguous criteria
            assert result.clarification_questions is not None
            assert len(result.clarification_questions) >= 2
