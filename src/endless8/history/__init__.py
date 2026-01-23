"""History management for endless8."""

from endless8.history.history import History
from endless8.history.knowledge_base import KnowledgeBase
from endless8.history.queries import (
    count_iterations,
    get_last_iteration,
    query_failures,
    query_history_context,
)

__all__ = [
    "History",
    "KnowledgeBase",
    "query_history_context",
    "query_failures",
    "count_iterations",
    "get_last_iteration",
]
