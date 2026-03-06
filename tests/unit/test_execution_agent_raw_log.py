"""Unit tests for ExecutionAgent raw log collector support (Issue #33)."""

from unittest.mock import AsyncMock, MagicMock, patch

from endless8.agents import ExecutionContext
from endless8.agents.execution import ExecutionAgent
from endless8.raw_log import RawLogCollector


class TestExecutionAgentRawLog:
    """Tests for ExecutionAgent raw_log_collector property."""

    def test_raw_log_collector_default_none(self) -> None:
        """raw_log_collector defaults to None."""
        agent = ExecutionAgent()
        assert agent.raw_log_collector is None

    def test_raw_log_collector_settable(self) -> None:
        """raw_log_collector can be set."""
        agent = ExecutionAgent()
        collector = RawLogCollector()
        agent.raw_log_collector = collector
        assert agent.raw_log_collector is collector

    def test_raw_log_collector_clearable(self) -> None:
        """raw_log_collector can be cleared."""
        agent = ExecutionAgent()
        collector = RawLogCollector()
        agent.raw_log_collector = collector
        agent.raw_log_collector = None
        assert agent.raw_log_collector is None

    async def test_callback_composition_with_collector(self) -> None:
        """When raw_log_collector is set, it receives messages alongside original callback."""
        original_callback = MagicMock()
        agent = ExecutionAgent(message_callback=original_callback)
        collector = RawLogCollector()
        agent.raw_log_collector = collector

        # Verify the composed callback will call both
        # We test this by checking that create_agent_model is called with a composed callback
        context = ExecutionContext(
            task="test",
            criteria=["c1"],
            iteration=1,
            history_context="none",
            knowledge_context="none",
            working_directory="/tmp/test",
        )

        with patch("endless8.agents.execution.create_agent_model") as mock_factory:
            mock_model = MagicMock()
            mock_factory.return_value = mock_model

            with patch("endless8.agents.execution.Agent") as mock_agent_cls:
                mock_agent = AsyncMock()
                mock_agent_cls.return_value = mock_agent
                mock_run_result = MagicMock()
                mock_run_result.output = MagicMock()
                mock_agent.run.return_value = mock_run_result

                await agent.run(context)

                # Verify create_agent_model was called with a callback
                call_kwargs = mock_factory.call_args.kwargs
                assert "message_callback" in call_kwargs
                composed_cb = call_kwargs["message_callback"]
                # The composed callback should not be None
                assert composed_cb is not None
                # It should be different from the original (it's composed)
                assert composed_cb is not original_callback

    async def test_no_collector_uses_original_callback(self) -> None:
        """Without raw_log_collector, original callback is used directly."""
        original_callback = MagicMock()
        agent = ExecutionAgent(message_callback=original_callback)

        context = ExecutionContext(
            task="test",
            criteria=["c1"],
            iteration=1,
            history_context="none",
            knowledge_context="none",
            working_directory="/tmp/test",
        )

        with patch("endless8.agents.execution.create_agent_model") as mock_factory:
            mock_model = MagicMock()
            mock_factory.return_value = mock_model

            with patch("endless8.agents.execution.Agent") as mock_agent_cls:
                mock_agent = AsyncMock()
                mock_agent_cls.return_value = mock_agent
                mock_run_result = MagicMock()
                mock_run_result.output = MagicMock()
                mock_agent.run.return_value = mock_run_result

                await agent.run(context)

                call_kwargs = mock_factory.call_args.kwargs
                assert call_kwargs["message_callback"] is original_callback
