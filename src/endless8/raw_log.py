"""Raw log collector for capturing execution agent stream output.

Serializes claude_agent_sdk Message objects to JSONL format
compatible with SummaryAgent's metadata parsers.
"""

import json
import logging

from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    StreamEvent,
    TextBlock,
    ToolUseBlock,
)

logger = logging.getLogger(__name__)


class RawLogCollector:
    """Collects raw messages from execution agent and serializes to JSONL.

    The JSONL output is compatible with SummaryAgent's parsers:
    - _parse_tools_from_log: expects {"type": "tool_use", "name": "..."}
    - _parse_files_from_log: expects {"type": "tool_use", "name": "Edit/Write", "input": {"file_path": "..."}}
    - _parse_tokens_from_log: expects {"usage": {"input_tokens": N, "output_tokens": N}}
    """

    def __init__(self) -> None:
        self._lines: list[str] = []

    def on_message(self, message: Message) -> None:
        """Process a message and serialize to JSONL line(s).

        Args:
            message: A claude_agent_sdk Message object.
        """
        if isinstance(message, AssistantMessage):
            self._handle_assistant_message(message)
        elif isinstance(message, StreamEvent):
            self._handle_stream_event(message)

    def _handle_assistant_message(self, message: AssistantMessage) -> None:
        """Serialize AssistantMessage content blocks."""
        for block in message.content or []:
            if isinstance(block, ToolUseBlock):
                data: dict[str, object] = {
                    "type": "tool_use",
                    "name": block.name,
                    "input": block.input,
                }
                self._append_json(data)
            elif isinstance(block, TextBlock):
                data = {
                    "type": "text",
                    "text": block.text,
                }
                self._append_json(data)

    def _handle_stream_event(self, message: StreamEvent) -> None:
        """Serialize StreamEvent's event dict."""
        event = message.event
        if isinstance(event, dict):
            self._append_json(event)

    def _append_json(self, data: object) -> None:
        """Serialize data to JSON and append to lines."""
        try:
            line = json.dumps(data, ensure_ascii=False)
            self._lines.append(line)
        except (TypeError, ValueError):
            logger.warning("Failed to serialize message to JSON", exc_info=True)

    def get_content(self) -> str:
        """Return collected log as JSONL string.

        Returns:
            Newline-separated JSON lines, or empty string if no messages collected.
        """
        if not self._lines:
            return ""
        return "\n".join(self._lines) + "\n"

    def clear(self) -> None:
        """Clear all collected log lines."""
        self._lines.clear()


__all__ = ["RawLogCollector"]
