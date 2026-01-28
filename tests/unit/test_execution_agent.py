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

    async def test_execution_agent_passes_allowed_tools(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent passes allowed_tools to model factory."""
        from endless8.agents.execution import ExecutionAgent

        allowed_tools = ["Read", "Edit", "Write", "Bash"]

        with (
            patch("endless8.agents.execution.Agent") as mock_agent_class,
            patch("endless8.agents.execution.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="完了",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = ExecutionAgent(allowed_tools=allowed_tools)
            await agent.run(execution_context)

            # Verify create_agent_model was called with allowed_tools
            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("allowed_tools") == allowed_tools

    async def test_execution_agent_without_allowed_tools(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent works without allowed_tools."""
        from endless8.agents.execution import ExecutionAgent

        with (
            patch("endless8.agents.execution.Agent") as mock_agent_class,
            patch("endless8.agents.execution.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="完了",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = ExecutionAgent()  # No allowed_tools
            await agent.run(execution_context)

            # Verify create_agent_model was called without allowed_tools or with None
            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("allowed_tools") is None

    async def test_execution_agent_passes_message_callback(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent passes message_callback to model factory."""
        from endless8.agents.execution import ExecutionAgent

        def callback(message: object) -> None:
            pass

        with (
            patch("endless8.agents.execution.Agent") as mock_agent_class,
            patch("endless8.agents.execution.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="完了",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = ExecutionAgent(message_callback=callback)
            await agent.run(execution_context)

            # Verify create_agent_model was called with message_callback
            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("message_callback") is callback

    async def test_execution_agent_without_message_callback(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that execution agent works without message_callback."""
        from endless8.agents.execution import ExecutionAgent

        with (
            patch("endless8.agents.execution.Agent") as mock_agent_class,
            patch("endless8.agents.execution.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="完了",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = ExecutionAgent()  # No message_callback
            await agent.run(execution_context)

            # Verify create_agent_model was called with message_callback=None
            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("message_callback") is None


class TestExecutionAgentMaxTurnsValidation:
    """Tests for ExecutionAgent max_turns validation."""

    def test_max_turns_zero_raises_value_error(self) -> None:
        """Test that max_turns=0 raises ValueError."""
        from endless8.agents.execution import ExecutionAgent

        with pytest.raises(ValueError, match="max_turns must be >= 1"):
            ExecutionAgent(max_turns=0)

    def test_max_turns_negative_raises_value_error(self) -> None:
        """Test that negative max_turns raises ValueError."""
        from endless8.agents.execution import ExecutionAgent

        with pytest.raises(ValueError, match="max_turns must be >= 1"):
            ExecutionAgent(max_turns=-5)


class TestExecutionAgentMaxTurns:
    """Tests for ExecutionAgent max_turns parameter."""

    @pytest.fixture
    def execution_context(self) -> ExecutionContext:
        """Create sample execution context."""
        return ExecutionContext(
            task="テスト",
            criteria=["条件"],
            iteration=1,
            history_context="なし",
            knowledge_context="なし",
        )

    async def test_max_turns_custom_value(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that custom max_turns is passed to create_agent_model."""
        from endless8.agents.execution import ExecutionAgent

        with (
            patch("endless8.agents.execution.Agent") as mock_agent_class,
            patch("endless8.agents.execution.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="完了",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = ExecutionAgent(max_turns=100)
            await agent.run(execution_context)

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 100

    async def test_max_turns_default_value(
        self,
        execution_context: ExecutionContext,
    ) -> None:
        """Test that default max_turns is 50."""
        from endless8.agents.execution import ExecutionAgent

        with (
            patch("endless8.agents.execution.Agent") as mock_agent_class,
            patch("endless8.agents.execution.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output="完了",
                    artifacts=[],
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = ExecutionAgent()
            await agent.run(execution_context)

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 50


class TestRawOutputContextPrompt:
    """Tests for raw_output_context in prompt generation."""

    async def test_prompt_includes_raw_output_when_provided(self) -> None:
        """Test that prompt includes raw output section when provided."""
        from endless8.agents.execution import ExecutionAgent

        context = ExecutionContext(
            task="テスト",
            criteria=["条件"],
            iteration=2,
            history_context="履歴",
            knowledge_context="ナレッジ",
            raw_output_context="前回の出力テキスト",
        )

        agent = ExecutionAgent()
        prompt = agent._build_prompt(context)

        assert "前回の生出力" in prompt
        assert "前回の出力テキスト" in prompt

    async def test_prompt_excludes_raw_output_when_none(self) -> None:
        """Test that prompt does not include raw output section when None."""
        from endless8.agents.execution import ExecutionAgent

        context = ExecutionContext(
            task="テスト",
            criteria=["条件"],
            iteration=1,
            history_context="履歴",
            knowledge_context="ナレッジ",
        )

        agent = ExecutionAgent()
        prompt = agent._build_prompt(context)

        assert "前回の生出力" not in prompt
