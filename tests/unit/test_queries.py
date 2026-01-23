"""Tests for DuckDB query utilities."""

import json
from pathlib import Path

import pytest

from endless8.history.queries import (
    count_iterations,
    get_last_iteration,
    query_failures,
    query_history_context,
)
from endless8.models import ExecutionStatus


@pytest.fixture
def valid_history_jsonl(tmp_path: Path) -> Path:
    """Create a valid history JSONL file."""
    history_path = tmp_path / "history.jsonl"
    records = [
        {
            "type": "summary",
            "iteration": 1,
            "approach": "Initial approach",
            "result": "success",
            "reason": "Completed successfully",
            "artifacts": ["file1.py"],
            "timestamp": "2026-01-23T10:00:00Z",
        },
        {
            "type": "summary",
            "iteration": 2,
            "approach": "Second approach",
            "result": "failure",
            "reason": "Failed to complete",
            "artifacts": [],
            "timestamp": "2026-01-23T10:01:00Z",
        },
        {
            "type": "summary",
            "iteration": 3,
            "approach": "Third approach",
            "result": "success",
            "reason": "Fixed the issue",
            "artifacts": ["file2.py"],
            "timestamp": "2026-01-23T10:02:00Z",
        },
        {
            "type": "summary",
            "iteration": 4,
            "approach": "Fourth approach",
            "result": "failure",
            "reason": "Another failure",
            "artifacts": [],
            "timestamp": "2026-01-23T10:03:00Z",
        },
        {
            "type": "summary",
            "iteration": 5,
            "approach": "Fifth approach",
            "result": "success",
            "reason": "Final success",
            "artifacts": ["file3.py"],
            "timestamp": "2026-01-23T10:04:00Z",
        },
    ]
    with history_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return history_path


@pytest.fixture
def empty_history_jsonl(tmp_path: Path) -> Path:
    """Create an empty history JSONL file."""
    history_path = tmp_path / "history.jsonl"
    history_path.touch()
    return history_path


@pytest.fixture
def invalid_history_jsonl(tmp_path: Path) -> Path:
    """Create a history JSONL file with invalid JSON."""
    history_path = tmp_path / "history.jsonl"
    with history_path.open("w", encoding="utf-8") as f:
        f.write("not valid json\n")
        f.write('{"type": "summary", "iteration": 1}\n')  # Incomplete record
    return history_path


class TestQueryHistoryContext:
    """Tests for query_history_context function."""

    def test_returns_recent_summaries(self, valid_history_jsonl: Path) -> None:
        """Should return recent summaries up to limit."""
        summaries = query_history_context(valid_history_jsonl, limit=3)

        assert len(summaries) == 3
        # Should return the most recent 3, ordered ASC by iteration
        assert summaries[0].iteration == 3
        assert summaries[1].iteration == 4
        assert summaries[2].iteration == 5

    def test_returns_all_summaries_when_less_than_limit(
        self, valid_history_jsonl: Path
    ) -> None:
        """Should return all summaries when count is less than limit."""
        summaries = query_history_context(valid_history_jsonl, limit=10)

        assert len(summaries) == 5

    def test_returns_empty_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Should return empty list for nonexistent file."""
        nonexistent_path = tmp_path / "nonexistent.jsonl"
        summaries = query_history_context(nonexistent_path, limit=5)

        assert summaries == []

    def test_returns_empty_for_empty_file(self, empty_history_jsonl: Path) -> None:
        """Should return empty list for empty file."""
        summaries = query_history_context(empty_history_jsonl, limit=5)

        assert summaries == []

    def test_returns_empty_for_invalid_jsonl(self, invalid_history_jsonl: Path) -> None:
        """Should return empty list when DuckDB query fails."""
        summaries = query_history_context(invalid_history_jsonl, limit=5)

        assert summaries == []

    def test_returns_correct_execution_status(self, valid_history_jsonl: Path) -> None:
        """Should correctly parse execution status enum."""
        summaries = query_history_context(valid_history_jsonl, limit=5)

        # Check status parsing
        success_summaries = [
            s for s in summaries if s.result == ExecutionStatus.SUCCESS
        ]
        failure_summaries = [
            s for s in summaries if s.result == ExecutionStatus.FAILURE
        ]

        assert len(success_summaries) == 3
        assert len(failure_summaries) == 2


class TestQueryFailures:
    """Tests for query_failures function."""

    def test_returns_failure_summaries(self, valid_history_jsonl: Path) -> None:
        """Should return only failure summaries."""
        failures = query_failures(valid_history_jsonl)

        assert len(failures) == 2
        for failure in failures:
            assert failure.result == ExecutionStatus.FAILURE

    def test_excludes_specified_iterations(self, valid_history_jsonl: Path) -> None:
        """Should exclude specified iterations."""
        failures = query_failures(valid_history_jsonl, exclude_iterations=[2])

        assert len(failures) == 1
        assert failures[0].iteration == 4

    def test_returns_empty_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Should return empty list for nonexistent file."""
        nonexistent_path = tmp_path / "nonexistent.jsonl"
        failures = query_failures(nonexistent_path)

        assert failures == []

    def test_returns_empty_for_empty_file(self, empty_history_jsonl: Path) -> None:
        """Should return empty list for empty file."""
        failures = query_failures(empty_history_jsonl)

        assert failures == []

    def test_returns_empty_for_invalid_jsonl(self, invalid_history_jsonl: Path) -> None:
        """Should return empty list when DuckDB query fails."""
        failures = query_failures(invalid_history_jsonl)

        assert failures == []


class TestCountIterations:
    """Tests for count_iterations function."""

    def test_returns_correct_count(self, valid_history_jsonl: Path) -> None:
        """Should return correct iteration count."""
        count = count_iterations(valid_history_jsonl)

        assert count == 5

    def test_returns_zero_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Should return 0 for nonexistent file."""
        nonexistent_path = tmp_path / "nonexistent.jsonl"
        count = count_iterations(nonexistent_path)

        assert count == 0

    def test_returns_zero_for_empty_file(self, empty_history_jsonl: Path) -> None:
        """Should return 0 for empty file."""
        count = count_iterations(empty_history_jsonl)

        assert count == 0

    def test_returns_zero_for_invalid_jsonl(self, invalid_history_jsonl: Path) -> None:
        """Should return 0 when DuckDB query fails."""
        count = count_iterations(invalid_history_jsonl)

        assert count == 0


class TestGetLastIteration:
    """Tests for get_last_iteration function."""

    def test_returns_last_iteration_number(self, valid_history_jsonl: Path) -> None:
        """Should return the last iteration number."""
        last_iter = get_last_iteration(valid_history_jsonl)

        assert last_iter == 5

    def test_returns_zero_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Should return 0 for nonexistent file."""
        nonexistent_path = tmp_path / "nonexistent.jsonl"
        last_iter = get_last_iteration(nonexistent_path)

        assert last_iter == 0

    def test_returns_zero_for_empty_file(self, empty_history_jsonl: Path) -> None:
        """Should return 0 for empty file."""
        last_iter = get_last_iteration(empty_history_jsonl)

        assert last_iter == 0

    def test_returns_zero_for_invalid_jsonl(self, invalid_history_jsonl: Path) -> None:
        """Should return 0 when DuckDB query fails."""
        last_iter = get_last_iteration(invalid_history_jsonl)

        assert last_iter == 0
