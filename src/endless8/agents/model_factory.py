"""Model factory for creating agent models.

Provides a centralized factory function for creating pydantic-ai compatible models,
with support for claudecode-model when available.
"""

import logging
from typing import TYPE_CHECKING, Union

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from claudecode_model import MessageCallbackType

# Import claudecode-model adapter
try:
    from claudecode_model import ClaudeCodeModel

    _CLAUDECODE_AVAILABLE = True
except ImportError:
    logger.warning("claudecode-model not found, using default model string")
    _CLAUDECODE_AVAILABLE = False
    ClaudeCodeModel = None  # type: ignore[assignment, misc]


def create_agent_model(
    model_name: str,
    max_turns: int = 10,
    allowed_tools: list[str] | None = None,
    timeout: float = 300.0,
    message_callback: "MessageCallbackType | None" = None,
) -> Union["ClaudeCodeModel", str]:
    """Create an agent model for pydantic-ai.

    If claudecode-model is available, returns a ClaudeCodeModel instance.
    Otherwise, returns the model name string for direct use with pydantic-ai.

    Args:
        model_name: Name of the model to use (e.g., "anthropic:claude-sonnet-4-5").
        max_turns: Maximum number of conversation turns for ClaudeCodeModel.
        allowed_tools: List of allowed tool names for ClaudeCodeModel.
        timeout: Timeout in seconds for SDK queries.
        message_callback: Optional callback for message events.

    Returns:
        ClaudeCodeModel instance or model name string.
    """
    if _CLAUDECODE_AVAILABLE and ClaudeCodeModel is not None:
        return ClaudeCodeModel(
            max_turns=max_turns,
            allowed_tools=allowed_tools,
            timeout=timeout,
            message_callback=message_callback,
        )

    # claudecode-model is not available
    if message_callback is not None:
        logger.warning(
            "message_callback was specified but claudecode-model is not available. "
            "Verbose output will not be displayed."
        )
    return model_name


def is_claudecode_available() -> bool:
    """Check if claudecode-model is available.

    Returns:
        True if claudecode-model is installed, False otherwise.
    """
    return _CLAUDECODE_AVAILABLE


__all__ = ["create_agent_model", "is_claudecode_available"]
