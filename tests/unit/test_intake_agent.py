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

    async def test_intake_agent_suggests_tools_for_code_task(
        self,
    ) -> None:
        """Test that intake agent suggests appropriate tools for code-related tasks."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="認証機能を実装する",
                    criteria=["ログイン機能が動作する", "テストがパスする"],
                    suggested_tools=["Read", "Edit", "Write", "Bash"],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="認証機能を実装する",
                criteria=["ログイン機能が動作する", "テストがパスする"],
            )

            assert result.status == IntakeStatus.ACCEPTED
            assert result.suggested_tools is not None
            assert len(result.suggested_tools) > 0
            assert "Read" in result.suggested_tools
            assert "Edit" in result.suggested_tools

    async def test_intake_agent_suggests_tools_for_web_research_task(
        self,
    ) -> None:
        """Test that intake agent suggests WebSearch/WebFetch for research tasks."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="最新のPython 3.13の新機能を調査する",
                    criteria=["主要な新機能をリストアップ"],
                    suggested_tools=["WebSearch", "WebFetch", "Read", "Write"],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="最新のPython 3.13の新機能を調査する",
                criteria=["主要な新機能をリストアップ"],
            )

            assert result.status == IntakeStatus.ACCEPTED
            assert result.suggested_tools is not None
            assert "WebSearch" in result.suggested_tools
            assert "WebFetch" in result.suggested_tools

    async def test_intake_agent_minimal_tools_for_creative_task(
        self,
    ) -> None:
        """Test that intake agent suggests minimal tools for creative/writing tasks."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="秋の季語を使った俳句を3つ作成する",
                    criteria=[
                        "5-7-5の音数律に従っている",
                        "歳時記に掲載されている正式な秋の季語を使用している",
                        "3つの俳句が作成されている",
                    ],
                    suggested_tools=[],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="秋の季語を使った俳句を3つ作成する",
                criteria=[
                    "5-7-5の音数律に従っている",
                    "歳時記に掲載されている正式な秋の季語を使用している",
                    "3つの俳句が作成されている",
                ],
            )

            assert result.status == IntakeStatus.ACCEPTED
            # Creative/writing tasks should not suggest WebSearch or WebFetch
            assert "WebSearch" not in (result.suggested_tools or [])
            assert "WebFetch" not in (result.suggested_tools or [])

    async def test_intake_agent_default_empty_suggested_tools(
        self,
    ) -> None:
        """Test that suggested_tools defaults to empty list."""
        from endless8.agents.intake import IntakeAgent

        with patch("endless8.agents.intake.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            # Return IntakeResult without suggested_tools
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="シンプルなタスク",
                    criteria=["完了条件"],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = IntakeAgent()
            result = await agent.run(
                task="シンプルなタスク",
                criteria=["完了条件"],
            )

            assert result.suggested_tools == []


class TestIntakeAgentMaxTurns:
    """Tests for IntakeAgent max_turns parameter."""

    async def test_max_turns_custom_value(self) -> None:
        """Test that custom max_turns is passed to create_agent_model."""
        from endless8.agents.intake import IntakeAgent

        with (
            patch("endless8.agents.intake.Agent") as mock_agent_class,
            patch("endless8.agents.intake.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="タスク",
                    criteria=["条件"],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = IntakeAgent(max_turns=20)
            await agent.run(task="タスク", criteria=["条件"])

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 20

    async def test_max_turns_default_value(self) -> None:
        """Test that default max_turns is 10."""
        from endless8.agents.intake import IntakeAgent

        with (
            patch("endless8.agents.intake.Agent") as mock_agent_class,
            patch("endless8.agents.intake.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=IntakeResult(
                    status=IntakeStatus.ACCEPTED,
                    task="タスク",
                    criteria=["条件"],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = IntakeAgent()
            await agent.run(task="タスク", criteria=["条件"])

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 10
