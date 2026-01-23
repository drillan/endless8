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

    async def test_append_judgment(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that history can append and retrieve judgment results."""
        from endless8.history import History
        from endless8.models import CriteriaEvaluation, JudgmentResult

        history = History(history_path=temp_history_path)

        # Create a judgment result
        judgment = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="テストカバレッジ90%以上",
                    is_met=False,
                    evidence="現在のカバレッジは75%",
                    confidence=0.9,
                ),
                CriteriaEvaluation(
                    criterion="型チェックエラーなし",
                    is_met=True,
                    evidence="mypyチェックパス",
                    confidence=1.0,
                ),
            ],
            overall_reason="カバレッジ目標未達成",
            suggested_next_action="追加テストの作成",
        )

        await history.append_judgment(judgment, iteration=3)

        # File should exist and contain judgment data
        assert temp_history_path.exists()
        content = temp_history_path.read_text()
        assert '"type": "judgment"' in content
        assert '"iteration": 3' in content
        assert "カバレッジ目標未達成" in content
        assert "追加テストの作成" in content

    async def test_append_judgment_with_complete_status(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that completed judgment is saved correctly."""
        from endless8.history import History
        from endless8.models import CriteriaEvaluation, JudgmentResult

        history = History(history_path=temp_history_path)

        judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="すべてのテストがパス",
                    is_met=True,
                    evidence="pytest 全パス",
                    confidence=1.0,
                ),
            ],
            overall_reason="タスク完了",
        )

        await history.append_judgment(judgment, iteration=5)

        content = temp_history_path.read_text()
        assert '"is_complete": true' in content
        assert '"iteration": 5' in content

    async def test_append_final_result_completed(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that final result (completed) is saved correctly."""
        from endless8.history import History
        from endless8.models import (
            CriteriaEvaluation,
            JudgmentResult,
            LoopResult,
            LoopStatus,
        )

        history = History(history_path=temp_history_path)

        final_judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=True,
                    evidence="達成済み",
                    confidence=1.0,
                ),
            ],
            overall_reason="すべての条件を達成",
        )

        result = LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=5,
            final_judgment=final_judgment,
            history_path=str(temp_history_path),
        )

        await history.append_final_result(result)

        # File should exist and contain final result data
        assert temp_history_path.exists()
        content = temp_history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "completed"' in content
        assert '"iterations_used": 5' in content

    async def test_append_final_result_max_iterations(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that final result (max iterations) is saved correctly."""
        from endless8.history import History
        from endless8.models import LoopResult, LoopStatus

        history = History(history_path=temp_history_path)

        result = LoopResult(
            status=LoopStatus.MAX_ITERATIONS,
            iterations_used=10,
            history_path=str(temp_history_path),
        )

        await history.append_final_result(result)

        content = temp_history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "max_iterations"' in content
        assert '"iterations_used": 10' in content

    async def test_append_final_result_error(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that final result (error) is saved correctly."""
        from endless8.history import History
        from endless8.models import LoopResult, LoopStatus

        history = History(history_path=temp_history_path)

        result = LoopResult(
            status=LoopStatus.ERROR,
            iterations_used=3,
            error_message="RuntimeError: 実行エージェントが設定されていません",
        )

        await history.append_final_result(result)

        content = temp_history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "error"' in content
        assert "RuntimeError" in content

    async def test_append_final_result_cancelled(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that final result (cancelled) is saved correctly."""
        from endless8.history import History
        from endless8.models import LoopResult, LoopStatus

        history = History(history_path=temp_history_path)

        result = LoopResult(
            status=LoopStatus.CANCELLED,
            iterations_used=2,
        )

        await history.append_final_result(result)

        content = temp_history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "cancelled"' in content
        assert '"iterations_used": 2' in content

    async def test_mixed_record_types_in_history(
        self,
        temp_history_path: Path,
        sample_summary: ExecutionSummary,
    ) -> None:
        """Test that history can contain summary, judgment, and final_result records."""
        from endless8.history import History
        from endless8.models import (
            CriteriaEvaluation,
            JudgmentResult,
            LoopResult,
            LoopStatus,
        )

        history = History(history_path=temp_history_path)

        # Add a summary
        await history.append(sample_summary)

        # Add a judgment
        judgment = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=False,
                    evidence="未達成",
                    confidence=0.8,
                ),
            ],
            overall_reason="条件未達成",
            suggested_next_action="再試行",
        )
        await history.append_judgment(judgment, iteration=1)

        # Add final result
        final_result = LoopResult(
            status=LoopStatus.MAX_ITERATIONS,
            iterations_used=10,
        )
        await history.append_final_result(final_result)

        # Verify file contains all types
        content = temp_history_path.read_text()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 3

        # Verify record types
        assert '"type": "summary"' in content
        assert '"type": "judgment"' in content
        assert '"type": "final_result"' in content


class TestHistoryWriteErrors:
    """Tests for history write error handling."""

    @pytest.fixture
    def temp_history_path(self, tmp_path: Path) -> Path:
        """Create temporary history file path."""
        return tmp_path / ".e8" / "history.jsonl"

    @pytest.fixture
    def sample_summary(self) -> ExecutionSummary:
        """Create sample execution summary."""
        return ExecutionSummary(
            iteration=1,
            approach="テスト",
            result=ExecutionStatus.SUCCESS,
            reason="テスト理由",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-01-23T10:00:00Z",
        )

    async def test_append_raises_on_write_error(
        self,
        temp_history_path: Path,
        sample_summary: ExecutionSummary,
    ) -> None:
        """Test that append raises OSError when write fails."""
        from unittest.mock import patch

        from endless8.history import History

        history = History(history_path=temp_history_path)

        # Ensure parent directory exists but write fails
        temp_history_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(Path, "open", side_effect=OSError("Disk full")),
            pytest.raises(OSError, match="Disk full"),
        ):
            await history.append(sample_summary)

    async def test_append_judgment_raises_on_write_error(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that append_judgment raises OSError when write fails."""
        from unittest.mock import patch

        from endless8.history import History
        from endless8.models import CriteriaEvaluation, JudgmentResult

        history = History(history_path=temp_history_path)

        judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="達成",
                    confidence=1.0,
                ),
            ],
            overall_reason="完了",
        )

        # Ensure parent directory exists but write fails
        temp_history_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(Path, "open", side_effect=OSError("Permission denied")),
            pytest.raises(OSError, match="Permission denied"),
        ):
            await history.append_judgment(judgment, iteration=1)

    async def test_append_final_result_raises_on_write_error(
        self,
        temp_history_path: Path,
    ) -> None:
        """Test that append_final_result raises OSError when write fails."""
        from unittest.mock import patch

        from endless8.history import History
        from endless8.models import LoopResult, LoopStatus

        history = History(history_path=temp_history_path)

        # Use MAX_ITERATIONS status which doesn't require final_judgment
        result = LoopResult(
            status=LoopStatus.MAX_ITERATIONS,
            iterations_used=1,
        )

        # Ensure parent directory exists but write fails
        temp_history_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(Path, "open", side_effect=OSError("Read-only filesystem")),
            pytest.raises(OSError, match="Read-only filesystem"),
        ):
            await history.append_final_result(result)
