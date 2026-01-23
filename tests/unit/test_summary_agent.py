"""Unit tests for the Summary Agent."""

import pytest

from endless8.models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    KnowledgeType,
    SemanticMetadata,
)


class TestSummaryAgent:
    """Tests for SummaryAgent class."""

    @pytest.fixture
    def execution_result(self) -> ExecutionResult:
        """Create sample execution result."""
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テストを追加しました。カバレッジが向上しました。",
            artifacts=["tests/test_main.py", "src/main.py"],
            semantic_metadata=SemanticMetadata(
                approach="TDD approach",
                strategy_tags=["test-first", "coverage"],
                discoveries=["新しいパターンを発見"],
            ),
        )

    async def test_summary_agent_returns_summary_and_knowledge(
        self,
        execution_result: ExecutionResult,
    ) -> None:
        """Test that summary agent returns summary and extracted knowledge."""
        from endless8.agents.summary import SummaryAgent

        agent = SummaryAgent(task_description="テストカバレッジ向上")
        summary, knowledge_list = await agent.run(execution_result, iteration=1)

        assert isinstance(summary, ExecutionSummary)
        assert summary.iteration == 1
        assert isinstance(knowledge_list, list)

    async def test_summary_agent_extracts_metadata_from_result(
        self,
        execution_result: ExecutionResult,
    ) -> None:
        """Test that summary agent extracts metadata from execution result."""
        from endless8.agents.summary import SummaryAgent

        agent = SummaryAgent(task_description="テスト")
        summary, _ = await agent.run(execution_result, iteration=1)

        assert summary.approach == "TDD approach"
        assert "test-first" in summary.metadata.strategy_tags

    async def test_summary_agent_extracts_knowledge_from_discoveries(
        self,
        execution_result: ExecutionResult,
    ) -> None:
        """Test that summary agent extracts knowledge from discoveries."""
        from endless8.agents.summary import SummaryAgent

        agent = SummaryAgent(task_description="テスト")
        _, knowledge_list = await agent.run(execution_result, iteration=1)

        # Knowledge should be extracted from discoveries
        assert len(knowledge_list) >= 1
        discovery_knowledge = [
            k for k in knowledge_list if k.type == KnowledgeType.DISCOVERY
        ]
        assert len(discovery_knowledge) >= 1

    async def test_summary_agent_handles_failure_result(
        self,
    ) -> None:
        """Test that summary agent handles failure results properly."""
        from endless8.agents.summary import SummaryAgent

        failure_result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="テストが失敗しました: assertion error",
            artifacts=[],
        )

        agent = SummaryAgent(task_description="テスト")
        summary, knowledge_list = await agent.run(failure_result, iteration=1)

        assert summary.result == ExecutionStatus.FAILURE
        # Lessons should be extracted from failures
        lessons = [k for k in knowledge_list if k.type == KnowledgeType.LESSON]
        assert len(lessons) >= 1

    async def test_summary_agent_parses_raw_log(
        self,
        execution_result: ExecutionResult,
    ) -> None:
        """Test that summary agent can parse raw log content."""
        from endless8.agents.summary import SummaryAgent

        raw_log = """
        {"type":"tool_use","name":"Read","input":{"path":"src/main.py"}}
        {"type":"tool_use","name":"Edit","input":{"path":"tests/test_main.py"}}
        {"type":"tool_result","name":"Bash","content":"Tests passed"}
        """

        agent = SummaryAgent(task_description="テスト")
        summary, _ = await agent.run(
            execution_result, iteration=1, raw_log_content=raw_log
        )

        # Tools should be extracted from raw log
        assert "Read" in summary.metadata.tools_used
        assert "Edit" in summary.metadata.tools_used

    async def test_summary_agent_includes_next_action(
        self,
    ) -> None:
        """Test that summary agent includes next action suggestions for failures."""
        from endless8.agents.summary import SummaryAgent

        result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="一部失敗",
            artifacts=["src/main.py"],
        )

        agent = SummaryAgent(task_description="テスト")
        summary, _ = await agent.run(result, iteration=1)

        # Failure should have next action
        assert summary.next is not None
        assert summary.next.suggested_action is not None
