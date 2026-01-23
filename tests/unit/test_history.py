"""Unit tests for the History class."""

from pathlib import Path

import pytest

from endless8.models import ExecutionStatus, ExecutionSummary, SummaryMetadata


class TestHistory:
    """Tests for History class."""

    @pytest.fixture
    def temp_history_path(self, tmp_path: Path) -> Path:
        """Create temporary history file path."""
        return tmp_path / ".e8" / "history.jsonl"

    @pytest.fixture
    def sample_summary(self) -> ExecutionSummary:
        """Create sample execution summary."""
        return ExecutionSummary(
            iteration=1,
            approach="テスト追加",
            result=ExecutionStatus.SUCCESS,
            reason="テストファイル作成完了",
            artifacts=["tests/test_main.py"],
            metadata=SummaryMetadata(
                tools_used=["Read", "Edit"],
                files_modified=["tests/test_main.py"],
                tokens_used=10000,
            ),
            timestamp="2026-01-23T10:00:00Z",
        )

    async def test_history_append_and_retrieve(
        self,
        temp_history_path: Path,
        sample_summary: ExecutionSummary,
    ) -> None:
        """Test that history can append and retrieve summaries."""
        from endless8.history import History

        history = History(history_path=temp_history_path)
        await history.append(sample_summary)

        summaries = await history.get_recent(limit=5)
        assert len(summaries) == 1
        assert summaries[0].iteration == 1
        assert summaries[0].approach == "テスト追加"

    async def test_history_get_recent_respects_limit(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that get_recent respects limit parameter."""
        from endless8.history import History

        history = History(history_path=temp_history_path)

        # Add 10 summaries
        for i in range(1, 11):
            summary = ExecutionSummary(
                iteration=i,
                approach=f"アプローチ {i}",
                result=ExecutionStatus.SUCCESS,
                reason=f"理由 {i}",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp=f"2026-01-23T10:0{i}:00Z",
            )
            await history.append(summary)

        summaries = await history.get_recent(limit=5)
        assert len(summaries) == 5
        # Should return most recent 5 (iterations 6-10)
        assert summaries[0].iteration == 6
        assert summaries[-1].iteration == 10

    async def test_history_get_failures(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that history can retrieve failure summaries."""
        from endless8.history import History

        history = History(history_path=temp_history_path)

        # Add mixed results
        for i in range(1, 6):
            status = ExecutionStatus.FAILURE if i % 2 == 0 else ExecutionStatus.SUCCESS
            summary = ExecutionSummary(
                iteration=i,
                approach=f"アプローチ {i}",
                result=status,
                reason=f"理由 {i}",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp=f"2026-01-23T10:0{i}:00Z",
            )
            await history.append(summary)

        failures = await history.get_failures(limit=10)
        assert len(failures) == 2  # Iterations 2 and 4
        assert all(f.result == ExecutionStatus.FAILURE for f in failures)

    async def test_history_generates_context_string(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that history generates context string for execution agent."""
        from endless8.history import History

        history = History(history_path=temp_history_path)

        for i in range(1, 4):
            summary = ExecutionSummary(
                iteration=i,
                approach=f"アプローチ {i}",
                result=ExecutionStatus.SUCCESS,
                reason=f"理由 {i}",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp=f"2026-01-23T10:0{i}:00Z",
            )
            await history.append(summary)

        context = await history.get_context_string(limit=5)
        assert "アプローチ 1" in context
        assert "アプローチ 2" in context
        assert "アプローチ 3" in context

    async def test_history_count_iterations(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that history correctly counts iterations."""
        from endless8.history import History

        history = History(history_path=temp_history_path)

        for i in range(1, 6):
            summary = ExecutionSummary(
                iteration=i,
                approach=f"アプローチ {i}",
                result=ExecutionStatus.SUCCESS,
                reason=f"理由 {i}",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp=f"2026-01-23T10:0{i}:00Z",
            )
            await history.append(summary)

        count = await history.count()
        assert count == 5

    async def test_history_get_last_iteration(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that history returns last iteration number."""
        from endless8.history import History

        history = History(history_path=temp_history_path)

        # Empty history
        last = await history.get_last_iteration()
        assert last == 0

        # Add some summaries
        for i in range(1, 4):
            summary = ExecutionSummary(
                iteration=i,
                approach=f"アプローチ {i}",
                result=ExecutionStatus.SUCCESS,
                reason=f"理由 {i}",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp=f"2026-01-23T10:0{i}:00Z",
            )
            await history.append(summary)

        last = await history.get_last_iteration()
        assert last == 3

    async def test_history_persists_to_file(
        self,
        temp_history_path: Path,
        sample_summary: ExecutionSummary,
    ) -> None:
        """Test that history persists to JSONL file."""
        from endless8.history import History

        history = History(history_path=temp_history_path)
        await history.append(sample_summary)

        # File should exist and contain data
        assert temp_history_path.exists()
        content = temp_history_path.read_text()
        assert "テスト追加" in content

        # New history instance should load existing data
        history2 = History(history_path=temp_history_path)
        summaries = await history2.get_recent(limit=5)
        assert len(summaries) == 1
