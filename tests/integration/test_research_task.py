"""Integration tests for research tasks (User Story 6)."""

from datetime import datetime

import pytest

from endless8.agents import ExecutionContext, JudgmentContext
from endless8.agents.intake import IntakeAgent
from endless8.models import (
    ExecutionStatus,
    ExecutionSummary,
    IntakeStatus,
    SummaryMetadata,
)


class TestResearchTaskIntake:
    """Tests for research task intake handling."""

    @pytest.fixture
    def intake_agent(self) -> IntakeAgent:
        """Create intake agent."""
        return IntakeAgent()

    @pytest.mark.asyncio
    async def test_research_task_accepted(self, intake_agent: IntakeAgent) -> None:
        """Test that research tasks are accepted."""
        result = await intake_agent.run(
            task="プロンプト最適化に関する論文を検索",
            criteria=[
                "3件以上の関連論文を発見",
                "各論文の概要をまとめる",
            ],
        )

        assert result.status == IntakeStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_documentation_task_handled(self, intake_agent: IntakeAgent) -> None:
        """Test that documentation tasks are handled appropriately."""
        result = await intake_agent.run(
            task="APIドキュメントを調査",
            criteria=[
                "主要なエンドポイントを5つ以上リスト",
                "各エンドポイントの説明を記載",
            ],
        )

        # Documentation task should be accepted or may need clarification
        assert result.status in (
            IntakeStatus.ACCEPTED,
            IntakeStatus.NEEDS_CLARIFICATION,
        )

    @pytest.mark.asyncio
    async def test_analysis_task_handled(self, intake_agent: IntakeAgent) -> None:
        """Test that analysis tasks are handled appropriately."""
        result = await intake_agent.run(
            task="競合製品を分析",
            criteria=[
                "3社以上の競合を特定",
                "機能比較表を作成",
                "強みと弱みを分析",
            ],
        )

        # Analysis task should be accepted or may need clarification
        # due to subjective criteria like "強みと弱み"
        assert result.status in (
            IntakeStatus.ACCEPTED,
            IntakeStatus.NEEDS_CLARIFICATION,
        )


class TestResearchTaskExecution:
    """Tests for research task execution."""

    def test_research_context_properly_structured(self) -> None:
        """Test that research context is properly structured for execution."""
        context = ExecutionContext(
            task="プロンプト最適化に関する論文を検索し概要をまとめる",
            criteria=[
                "3件以上の関連論文を発見",
                "各論文の概要をまとめる",
            ],
            iteration=1,
            history_context="履歴なし",
            knowledge_context="ナレッジなし",
        )

        # Context should be properly formatted for research task
        assert "論文" in context.task
        assert len(context.criteria) == 2


class TestResearchTaskJudgment:
    """Tests for research task judgment context structure."""

    def test_judgment_context_structure(self) -> None:
        """Test that judgment context is properly structured for research tasks."""
        summary = ExecutionSummary(
            iteration=1,
            approach="WebSearchを使用して論文を検索",
            result=ExecutionStatus.SUCCESS,
            reason="3件の論文を発見し概要をまとめた",
            artifacts=["research_summary.md"],
            metadata=SummaryMetadata(
                tools_used=["web_search", "read_file"],
                files_modified=["research_summary.md"],
                strategy_tags=["research", "documentation"],
            ),
            timestamp=datetime.now().isoformat(),
        )

        context = JudgmentContext(
            task="プロンプト最適化に関する論文を検索",
            criteria=[
                "3件以上の関連論文を発見",
                "各論文の概要をまとめる",
            ],
            execution_summary=summary,
        )

        # Context should be properly structured
        assert context.task == "プロンプト最適化に関する論文を検索"
        assert len(context.criteria) == 2
        assert context.execution_summary.result == ExecutionStatus.SUCCESS


class TestNonProgrammingCriteria:
    """Tests for non-programming criteria context structure."""

    def test_qualitative_criteria_context(self) -> None:
        """Test that qualitative criteria context is properly structured."""
        summary = ExecutionSummary(
            iteration=1,
            approach="競合分析レポートを作成",
            result=ExecutionStatus.SUCCESS,
            reason="3社の競合を分析し、機能比較表を作成",
            artifacts=["competitive_analysis.md"],
            metadata=SummaryMetadata(
                tools_used=["web_search", "write_file"],
                files_modified=["competitive_analysis.md"],
                strategy_tags=["analysis", "research"],
            ),
            timestamp=datetime.now().isoformat(),
        )

        context = JudgmentContext(
            task="競合製品を分析",
            criteria=[
                "3社以上の競合を特定",
                "機能比較表を作成",
            ],
            execution_summary=summary,
        )

        # Context should properly represent qualitative criteria
        assert "競合" in context.task
        assert len(context.criteria) == 2
        assert "competitive_analysis.md" in context.execution_summary.artifacts
