"""Unit tests for RawLogCollector."""

import json
from unittest.mock import MagicMock

from endless8.raw_log import RawLogCollector


class TestRawLogCollector:
    """Tests for RawLogCollector class."""

    def test_serializes_tool_use_block(self) -> None:
        """AssistantMessage with ToolUseBlock is serialized to JSONL."""
        collector = RawLogCollector()

        # Create mock AssistantMessage with ToolUseBlock
        tool_block = MagicMock()
        tool_block.name = "Edit"
        tool_block.input = {"file_path": "/tmp/test.py"}

        message = MagicMock()
        message.__class__.__name__ = "AssistantMessage"
        message.content = [tool_block]

        # Mock isinstance checks
        from claude_agent_sdk.types import AssistantMessage, ToolUseBlock

        real_message = MagicMock(spec=AssistantMessage)
        real_message.content = [MagicMock(spec=ToolUseBlock)]
        real_message.content[0].name = "Edit"
        real_message.content[0].input = {"file_path": "/tmp/test.py"}

        collector.on_message(real_message)

        content = collector.get_content()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) >= 1

        found_tool_use = False
        for line in lines:
            data = json.loads(line)
            if data.get("type") == "tool_use":
                assert data["name"] == "Edit"
                assert data["input"]["file_path"] == "/tmp/test.py"
                found_tool_use = True
        assert found_tool_use

    def test_serializes_stream_event_with_usage(self) -> None:
        """StreamEvent with usage data is serialized for token parsing."""
        collector = RawLogCollector()

        from claude_agent_sdk.types import StreamEvent

        event_data = {
            "type": "message_delta",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        event = MagicMock(spec=StreamEvent)
        event.event = event_data

        collector.on_message(event)

        content = collector.get_content()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert "usage" in data
        assert data["usage"]["input_tokens"] == 100
        assert data["usage"]["output_tokens"] == 50

    def test_clear_resets_content(self) -> None:
        """clear() removes all collected log lines."""
        collector = RawLogCollector()

        from claude_agent_sdk.types import StreamEvent

        event = MagicMock(spec=StreamEvent)
        event.event = {"type": "test"}

        collector.on_message(event)
        assert collector.get_content() != ""

        collector.clear()
        assert collector.get_content() == ""

    def test_get_content_returns_jsonl(self) -> None:
        """get_content() returns newline-separated JSONL."""
        collector = RawLogCollector()

        from claude_agent_sdk.types import StreamEvent

        for i in range(3):
            event = MagicMock(spec=StreamEvent)
            event.event = {"type": "test", "index": i}
            collector.on_message(event)

        content = collector.get_content()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 3

        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["index"] == i

    def test_serializes_text_block(self) -> None:
        """AssistantMessage with TextBlock is serialized."""
        collector = RawLogCollector()

        from claude_agent_sdk.types import AssistantMessage, TextBlock

        text_block = MagicMock(spec=TextBlock)
        text_block.text = "Hello world"

        message = MagicMock(spec=AssistantMessage)
        message.content = [text_block]

        collector.on_message(message)

        content = collector.get_content()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["type"] == "text"
        assert data["text"] == "Hello world"

    def test_serializes_mixed_content_blocks(self) -> None:
        """AssistantMessage with mixed blocks produces multiple JSONL lines."""
        collector = RawLogCollector()

        from claude_agent_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

        text_block = MagicMock(spec=TextBlock)
        text_block.text = "Working on it"

        tool_block = MagicMock(spec=ToolUseBlock)
        tool_block.name = "Write"
        tool_block.input = {"file_path": "/tmp/new.py"}

        message = MagicMock(spec=AssistantMessage)
        message.content = [text_block, tool_block]

        collector.on_message(message)

        content = collector.get_content()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 2

    def test_ignores_unknown_message_types(self) -> None:
        """Unknown message types are silently ignored."""
        collector = RawLogCollector()

        unknown = MagicMock()
        # Not an AssistantMessage or StreamEvent
        collector.on_message(unknown)

        assert collector.get_content() == ""
