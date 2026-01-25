"""Unit tests for the model factory."""

from unittest.mock import patch


class TestCreateAgentModel:
    """Tests for create_agent_model function."""

    def test_create_agent_model_without_allowed_tools(self) -> None:
        """Test that create_agent_model works without allowed_tools."""
        from endless8.agents.model_factory import create_agent_model

        with (
            patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True),
            patch("endless8.agents.model_factory.ClaudeCodeModel") as mock_model,
        ):
            mock_model.return_value = "mock_model"
            model = create_agent_model("test-model", max_turns=10)

            mock_model.assert_called_once_with(
                max_turns=10, allowed_tools=None, timeout=300.0, message_callback=None
            )
            assert model == "mock_model"

    def test_create_agent_model_with_allowed_tools(self) -> None:
        """Test that create_agent_model passes allowed_tools to ClaudeCodeModel."""
        from endless8.agents.model_factory import create_agent_model

        allowed_tools = ["Read", "Edit", "Write"]

        with (
            patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True),
            patch("endless8.agents.model_factory.ClaudeCodeModel") as mock_model,
        ):
            mock_model.return_value = "mock_model"
            model = create_agent_model(
                "test-model", max_turns=10, allowed_tools=allowed_tools
            )

            mock_model.assert_called_once_with(
                max_turns=10,
                allowed_tools=allowed_tools,
                timeout=300.0,
                message_callback=None,
            )
            assert model == "mock_model"

    def test_create_agent_model_with_empty_allowed_tools(self) -> None:
        """Test that create_agent_model handles empty allowed_tools list."""
        from endless8.agents.model_factory import create_agent_model

        allowed_tools: list[str] = []

        with (
            patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True),
            patch("endless8.agents.model_factory.ClaudeCodeModel") as mock_model,
        ):
            mock_model.return_value = "mock_model"
            model = create_agent_model(
                "test-model", max_turns=10, allowed_tools=allowed_tools
            )

            mock_model.assert_called_once_with(
                max_turns=10,
                allowed_tools=allowed_tools,
                timeout=300.0,
                message_callback=None,
            )
            assert model == "mock_model"

    def test_create_agent_model_with_none_allowed_tools(self) -> None:
        """Test that create_agent_model handles None allowed_tools."""
        from endless8.agents.model_factory import create_agent_model

        with (
            patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True),
            patch("endless8.agents.model_factory.ClaudeCodeModel") as mock_model,
        ):
            mock_model.return_value = "mock_model"
            model = create_agent_model("test-model", max_turns=10, allowed_tools=None)

            mock_model.assert_called_once_with(
                max_turns=10, allowed_tools=None, timeout=300.0, message_callback=None
            )
            assert model == "mock_model"

    def test_create_agent_model_returns_model_name_when_claudecode_unavailable(
        self,
    ) -> None:
        """Test that create_agent_model returns model name when claudecode is unavailable."""
        from endless8.agents.model_factory import create_agent_model

        with patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", False):
            model = create_agent_model(
                "anthropic:claude-sonnet-4-5",
                max_turns=10,
                allowed_tools=["Read", "Edit"],
            )

            assert model == "anthropic:claude-sonnet-4-5"

    def test_create_agent_model_with_timeout(self) -> None:
        """Test that create_agent_model passes timeout to ClaudeCodeModel."""
        from endless8.agents.model_factory import create_agent_model

        with (
            patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True),
            patch("endless8.agents.model_factory.ClaudeCodeModel") as mock_model,
        ):
            mock_model.return_value = "mock_model"
            model = create_agent_model("test-model", max_turns=10, timeout=600.0)

            mock_model.assert_called_once_with(
                max_turns=10, allowed_tools=None, timeout=600.0, message_callback=None
            )
            assert model == "mock_model"

    def test_create_agent_model_with_message_callback(self) -> None:
        """Test that create_agent_model passes message_callback to ClaudeCodeModel."""
        from endless8.agents.model_factory import create_agent_model

        def callback(message: object) -> None:
            pass

        with (
            patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True),
            patch("endless8.agents.model_factory.ClaudeCodeModel") as mock_model,
        ):
            mock_model.return_value = "mock_model"
            model = create_agent_model(
                "test-model", max_turns=10, message_callback=callback
            )

            mock_model.assert_called_once_with(
                max_turns=10,
                allowed_tools=None,
                timeout=300.0,
                message_callback=callback,
            )
            assert model == "mock_model"

    def test_create_agent_model_message_callback_ignored_when_claudecode_unavailable(
        self,
    ) -> None:
        """Test that message_callback is ignored when claudecode is unavailable."""
        from endless8.agents.model_factory import create_agent_model

        def callback(message: object) -> None:
            pass

        with patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", False):
            model = create_agent_model(
                "anthropic:claude-sonnet-4-5",
                max_turns=10,
                message_callback=callback,
            )

            # Should return model string, callback is ignored
            assert model == "anthropic:claude-sonnet-4-5"


class TestIsClaudeCodeAvailable:
    """Tests for is_claudecode_available function."""

    def test_is_claudecode_available_returns_true_when_available(self) -> None:
        """Test that is_claudecode_available returns True when available."""
        from endless8.agents.model_factory import is_claudecode_available

        with patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", True):
            assert is_claudecode_available() is True

    def test_is_claudecode_available_returns_false_when_unavailable(self) -> None:
        """Test that is_claudecode_available returns False when unavailable."""
        from endless8.agents.model_factory import is_claudecode_available

        with patch("endless8.agents.model_factory._CLAUDECODE_AVAILABLE", False):
            assert is_claudecode_available() is False
