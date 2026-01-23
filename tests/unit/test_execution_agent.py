"""Unit tests for the Execution Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from endless8.agents import ExecutionContext
from endless8.models import ExecutionResult, ExecutionStatus, SemanticMetadata


class TestExecutionAgent:
    """Tests for ExecutionAgent class."""

    @pytest.fixture
    def execution_context(self) -> ExecutionContext:
        """Create sample execution context."""
        return ExecutionContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            iteration=1,
            history_context="前回の履歴なし",
            knowledge_context="関連するナレッジなし",
        )

    async def test_execution_agent_returns_result(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent returns valid ExecutionResult."""
        from endless8.agents.execution import ExecutionAgent

        # Mock the pydantic-ai Agent class
        with patch("endless8.agents.execution.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="テストを追加しました",
                    artifacts=["tests/test_main.py"],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = ExecutionAgent()
            result = await agent.run(execution_context)

            assert isinstance(result, ExecutionResult)
            assert result.status in [
                ExecutionStatus.SUCCESS,
                ExecutionStatus.FAILURE,
                ExecutionStatus.ERROR,
            ]
            assert result.output is not None

    async def test_execution_agent_includes_semantic_metadata(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent can include semantic metadata."""
        from endless8.agents.execution import ExecutionAgent

        with patch("endless8.agents.execution.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="テストを追加しました",
                    artifacts=["tests/test_main.py"],
                    semantic_metadata=SemanticMetadata(
                        approach="TDD approach",
                        strategy_tags=["test-first"],
                        discoveries=["discovered pattern"],
                    ),
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = ExecutionAgent()
            result = await agent.run(execution_context)

            assert result.semantic_metadata is not None
            assert result.semantic_metadata.approach is not None

    async def test_execution_agent_handles_failure(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent handles failures gracefully."""
        from endless8.agents.execution import ExecutionAgent

        with patch("endless8.agents.execution.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    output="テストが失敗しました",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = ExecutionAgent()
            result = await agent.run(execution_context)

            assert result.status == ExecutionStatus.FAILURE
            assert result.output is not None

    async def test_execution_agent_includes_history_context(
        self,
    ) -> None:
        """Test that execution agent receives and uses history context."""
        from endless8.agents.execution import ExecutionAgent

        context_with_history = ExecutionContext(
            task="バグを修正",
            criteria=["テストがパスする"],
            iteration=3,
            history_context="Iteration 1: 認証機能を追加\nIteration 2: テスト追加",
            knowledge_context="パターン: テストファースト",
        )

        with patch("endless8.agents.execution.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="バグを修正しました",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = ExecutionAgent()
            result = await agent.run(context_with_history)

            # Verify the agent was called (context is passed to the model)
            assert mock_agent.run.called
            assert result.status == ExecutionStatus.SUCCESS
