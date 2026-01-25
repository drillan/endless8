"""DuckDB query utilities for endless8.

Provides functions to query JSONL history and knowledge files.
"""

import logging
from datetime import datetime
from pathlib import Path

import duckdb
from duckdb import Error as DuckDBError

from endless8.models import ExecutionStatus, ExecutionSummary

logger = logging.getLogger(__name__)


def query_history_context(
    history_path: str | Path,
    limit: int = 5,
) -> list[ExecutionSummary]:
    """Query history for context generation.

    Gets recent summaries plus past failures for execution context.

    Args:
        history_path: Path to history.jsonl file.
        limit: Number of recent summaries to include.

    Returns:
        List of ExecutionSummary objects.
    """
    path = Path(history_path)
    if not path.exists():
        return []

    query = """
    WITH ranked AS (
        SELECT *,
               ROW_NUMBER() OVER (ORDER BY iteration DESC) as rn
        FROM read_ndjson_auto(?)
        WHERE type = 'summary'
    )
    SELECT iteration, approach, result, reason, artifacts, timestamp
    FROM ranked
    WHERE rn <= ?
    ORDER BY iteration ASC
    """

    try:
        result = duckdb.execute(query, [str(path), limit]).fetchall()
        summaries = []
        for row in result:
            iteration, approach, result_status, reason, artifacts, timestamp = row
            # Convert datetime to ISO string if needed
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp) if timestamp else ""
            summary = ExecutionSummary(
                iteration=iteration,
                approach=approach,
                result=ExecutionStatus(result_status),
                reason=reason,
                artifacts=artifacts if artifacts else [],
                timestamp=timestamp_str,
            )
            summaries.append(summary)
        return summaries
    except DuckDBError as e:
        logger.error(
            "DuckDB query failed in query_history_context (path: %s): %s",
            path,
            e,
        )
        return []
    except Exception:
        logger.exception(
            "Unexpected error in query_history_context (path: %s)",
            path,
        )
        return []


def query_failures(
    history_path: str | Path,
    exclude_iterations: list[int] | None = None,
) -> list[ExecutionSummary]:
    """Query past failures from history.

    Args:
        history_path: Path to history.jsonl file.
        exclude_iterations: Iterations to exclude (already in recent context).

    Returns:
        List of failed ExecutionSummary objects.
    """
    path = Path(history_path)
    if not path.exists():
        return []

    exclude = exclude_iterations or []

    # Build query with optional NOT IN clause
    if exclude:
        placeholders = ",".join(["?"] * len(exclude))
        query = f"""
        SELECT iteration, approach, result, reason, artifacts, timestamp
        FROM read_ndjson_auto(?)
        WHERE type = 'summary'
          AND result = 'failure'
          AND iteration NOT IN ({placeholders})
        ORDER BY iteration DESC
        LIMIT 5
        """
        params: list[str | int] = [str(path)]
        params.extend(exclude)
    else:
        query = """
        SELECT iteration, approach, result, reason, artifacts, timestamp
        FROM read_ndjson_auto(?)
        WHERE type = 'summary'
          AND result = 'failure'
        ORDER BY iteration DESC
        LIMIT 5
        """
        params = [str(path)]

    try:
        result = duckdb.execute(query, params).fetchall()
        summaries = []
        for row in result:
            iteration, approach, result_status, reason, artifacts, timestamp = row
            # Convert datetime to ISO string if needed
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp) if timestamp else ""
            summary = ExecutionSummary(
                iteration=iteration,
                approach=approach,
                result=ExecutionStatus(result_status),
                reason=reason,
                artifacts=artifacts if artifacts else [],
                timestamp=timestamp_str,
            )
            summaries.append(summary)
        return summaries
    except DuckDBError as e:
        logger.error(
            "DuckDB query failed in query_failures (path: %s): %s",
            path,
            e,
        )
        return []
    except Exception:
        logger.exception(
            "Unexpected error in query_failures (path: %s)",
            path,
        )
        return []


def count_iterations(history_path: str | Path) -> int:
    """Count total iterations in history.

    Args:
        history_path: Path to history.jsonl file.

    Returns:
        Number of iterations.
    """
    path = Path(history_path)
    if not path.exists():
        return 0

    query = """
    SELECT COUNT(*) as cnt
    FROM read_ndjson_auto(?)
    WHERE type = 'summary'
    """

    try:
        result = duckdb.execute(query, [str(path)]).fetchone()
        return result[0] if result else 0
    except DuckDBError as e:
        logger.error(
            "DuckDB query failed in count_iterations (path: %s): %s",
            path,
            e,
        )
        return 0
    except Exception:
        logger.exception(
            "Unexpected error in count_iterations (path: %s)",
            path,
        )
        return 0


def get_last_iteration(history_path: str | Path) -> int:
    """Get the last iteration number.

    Args:
        history_path: Path to history.jsonl file.

    Returns:
        Last iteration number (0 if no history).
    """
    path = Path(history_path)
    if not path.exists():
        return 0

    query = """
    SELECT MAX(iteration) as last
    FROM read_ndjson_auto(?)
    WHERE type = 'summary'
    """

    try:
        result = duckdb.execute(query, [str(path)]).fetchone()
        return result[0] if result and result[0] else 0
    except DuckDBError as e:
        logger.error(
            "DuckDB query failed in get_last_iteration (path: %s): %s",
            path,
            e,
        )
        return 0
    except Exception:
        logger.exception(
            "Unexpected error in get_last_iteration (path: %s)",
            path,
        )
        return 0


__all__ = [
    "query_history_context",
    "query_failures",
    "count_iterations",
    "get_last_iteration",
]
