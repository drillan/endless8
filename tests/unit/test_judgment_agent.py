"""Unit tests for the Judgment Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from endless8.agents import JudgmentContext
from endless8.models import (
    CriteriaEvaluation,
    ExecutionStatus,
    ExecutionSummary,
    JudgmentResult,
    SummaryMetadata,
)


class TestJudgmentAgent:
    """Tests for JudgmentAgent class."""

    @pytest.fixture
    def execution_summary(self) -> ExecutionSummary:
        """Create sample execution summary."""
        return ExecutionSummary(
            iteration=1,
            approach="テストを追加",
            result=ExecutionStatus.SUCCESS,
            reason="テストファイル作成完了",
            artifacts=["tests/test_main.py"],
            metadata=SummaryMetadata(
                tools_used=["Read", "Edit"],
                files_modified=["tests/test_main.py"],
                tokens_used=10000,
            ),
            timestamp="2026-01-23T10:00:00Z",
        )

    @pytest.fixture
    def judgment_context(self, execution_summary: ExecutionSummary) -> JudgmentContext:
        """Create sample judgment context."""
        return JudgmentContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            execution_summary=execution_summary,
        )

    async def test_judgment_agent_returns_result(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that judgment agent returns valid JudgmentResult."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
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
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(judgment_context)

            assert isinstance(result, JudgmentResult)
            assert isinstance(result.is_complete, bool)
            assert len(result.evaluations) == len(judgment_context.criteria)

    async def test_judgment_agent_evaluates_each_criterion(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent evaluates each criterion individually."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="複数の条件を持つタスク",
            criteria=[
                "条件1: テストがパスする",
                "条件2: ドキュメントが更新される",
                "条件3: lintエラーがない",
            ],
            execution_summary=execution_summary,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=False,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件1: テストがパスする",
                            is_met=True,
                            evidence="テストパス",
                            confidence=0.9,
                        ),
                        CriteriaEvaluation(
                            criterion="条件2: ドキュメントが更新される",
                            is_met=False,
                            evidence="ドキュメント未更新",
                            confidence=0.8,
                        ),
                        CriteriaEvaluation(
                            criterion="条件3: lintエラーがない",
                            is_met=True,
                            evidence="lintパス",
                            confidence=0.95,
                        ),
                    ],
                    overall_reason="一部の条件が未達成",
                    suggested_next_action="ドキュメントを更新",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            assert len(result.evaluations) == 3
            assert result.is_complete is False
            assert result.suggested_next_action is not None

    async def test_judgment_agent_includes_confidence(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that each evaluation includes a confidence score."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="pytest --cov で90%以上",
                            is_met=True,
                            evidence="カバレッジ92%",
                            confidence=0.95,
                        )
                    ],
                    overall_reason="完了",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(judgment_context)

            for evaluation in result.evaluations:
                assert 0.0 <= evaluation.confidence <= 1.0

    async def test_judgment_agent_respects_custom_prompt(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent can use custom prompts."""
        from endless8.agents.judgment import JudgmentAgent

        custom_prompt = """
        以下の基準で厳密に評価してください：
        - テスト実行結果を確認
        - カバレッジレポートを検証
        """

        context = JudgmentContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            execution_summary=execution_summary,
            custom_prompt=custom_prompt,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="pytest --cov で90%以上",
                            is_met=True,
                            evidence="カバレッジ92%",
                            confidence=0.98,
                        )
                    ],
                    overall_reason="厳密評価で完了確認",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            # Verify agent was created/called (custom prompt is used internally)
            assert mock_agent.run.called
            assert result.is_complete is True

    async def test_judgment_agent_suggests_next_action_when_incomplete(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent suggests next action when not complete."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            execution_summary=execution_summary,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=False,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="pytest --cov で90%以上",
                            is_met=False,
                            evidence="現在のカバレッジは85%",
                            confidence=0.9,
                        )
                    ],
                    overall_reason="カバレッジが不足",
                    suggested_next_action="edge case のテストを追加してカバレッジを向上させる",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            assert result.is_complete is False
            assert result.suggested_next_action is not None
            assert len(result.suggested_next_action) > 0

    async def test_judgment_agent_evaluates_research_task(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent can evaluate non-coding research tasks."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="プロンプト最適化に関する論文を検索",
            criteria=[
                "3件以上の関連論文を発見",
                "各論文の概要をまとめる",
            ],
            execution_summary=execution_summary,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="3件以上の関連論文を発見",
                            is_met=True,
                            evidence="5件の論文を発見: Paper1, Paper2, Paper3, Paper4, Paper5",
                            confidence=0.9,
                        ),
                        CriteriaEvaluation(
                            criterion="各論文の概要をまとめる",
                            is_met=True,
                            evidence="全5件の論文について概要を作成",
                            confidence=0.85,
                        ),
                    ],
                    overall_reason="リサーチタスクの完了条件をすべて満たしました",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            assert result.is_complete is True
            assert len(result.evaluations) == 2
            # Research task should be evaluated correctly
            assert all(e.is_met for e in result.evaluations)


class TestJudgmentAgentMaxTurns:
    """Tests for JudgmentAgent max_turns parameter."""

    @pytest.fixture
    def judgment_context(self) -> JudgmentContext:
        """Create sample judgment context."""
        return JudgmentContext(
            task="テスト",
            criteria=["条件"],
            execution_summary=ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
        )

    async def test_max_turns_custom_value(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that custom max_turns is passed to create_agent_model."""
        from endless8.agents.judgment import JudgmentAgent

        with (
            patch("endless8.agents.judgment.Agent") as mock_agent_class,
            patch("endless8.agents.judgment.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件",
                            is_met=True,
                            evidence="証拠",
                            confidence=0.9,
                        )
                    ],
                    overall_reason="完了",
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = JudgmentAgent(max_turns=25)
            await agent.run(judgment_context)

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 25

    async def test_max_turns_default_value(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that default max_turns is 10."""
        from endless8.agents.judgment import JudgmentAgent

        with (
            patch("endless8.agents.judgment.Agent") as mock_agent_class,
            patch("endless8.agents.judgment.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件",
                            is_met=True,
                            evidence="証拠",
                            confidence=0.9,
                        )
                    ],
                    overall_reason="完了",
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = JudgmentAgent()
            await agent.run(judgment_context)

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 10
