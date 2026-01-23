"""Integration tests for context management (User Story 3)."""

from datetime import datetime
from pathlib import Path

import pytest

from endless8.history import History, KnowledgeBase
from endless8.models import (
    ExecutionStatus,
    ExecutionSummary,
    Knowledge,
    KnowledgeConfidence,
    KnowledgeType,
    SummaryMetadata,
)


def _make_summary(
    iteration: int,
    approach: str,
    result: ExecutionStatus,
    reason: str,
    artifacts: list[str] | None = None,
) -> ExecutionSummary:
    """Helper to create ExecutionSummary with timestamp."""
    return ExecutionSummary(
        iteration=iteration,
        approach=approach,
        result=result,
        reason=reason,
        artifacts=artifacts or [],
        metadata=SummaryMetadata(),
        timestamp=datetime.now().isoformat(),
    )


def _make_knowledge(
    knowledge_type: KnowledgeType,
    content: str,
    confidence: KnowledgeConfidence = KnowledgeConfidence.HIGH,
) -> Knowledge:
    """Helper to create Knowledge with required fields."""
    return Knowledge(
        type=knowledge_type,
        category="test",
        content=content,
        source_task="test_task",
        confidence=confidence,
    )


class TestHistoryContextGeneration:
    """Tests for history context generation."""

    @pytest.fixture
    def temp_history_path(self, tmp_path: Path) -> Path:
        """Create temporary history file path."""
        return tmp_path / "history.jsonl"

    @pytest.mark.asyncio
    async def test_empty_history_context(self, temp_history_path: Path) -> None:
        """Test context generation with empty history."""
        history = History(temp_history_path)
        context = await history.get_context_string()

        assert context == "履歴なし"

    @pytest.mark.asyncio
    async def test_single_entry_context(self, temp_history_path: Path) -> None:
        """Test context generation with single entry."""
        history = History(temp_history_path)

        summary = _make_summary(
            iteration=1,
            approach="最初のアプローチ",
            result=ExecutionStatus.SUCCESS,
            reason="成功した",
        )
        await history.append(summary)

        context = await history.get_context_string()
        assert "Iteration 1" in context
        assert "最初のアプローチ" in context
        assert "success" in context

    @pytest.mark.asyncio
    async def test_multiple_entries_context(self, temp_history_path: Path) -> None:
        """Test context generation with multiple entries."""
        history = History(temp_history_path)

        for i in range(1, 6):
            summary = _make_summary(
                iteration=i,
                approach=f"アプローチ{i}",
                result=ExecutionStatus.SUCCESS
                if i % 2 == 0
                else ExecutionStatus.FAILURE,
                reason=f"理由{i}",
            )
            await history.append(summary)

        context = await history.get_context_string(limit=3)
        # Should include last 3 entries
        assert "Iteration 3" in context
        assert "Iteration 4" in context
        assert "Iteration 5" in context
        # Should not include earlier entries
        assert "Iteration 1" not in context
        assert "Iteration 2" not in context

    @pytest.mark.asyncio
    async def test_history_persists_across_instances(
        self, temp_history_path: Path
    ) -> None:
        """Test that history persists across instances."""
        # First instance writes
        history1 = History(temp_history_path)
        summary = _make_summary(
            iteration=1,
            approach="テストアプローチ",
            result=ExecutionStatus.SUCCESS,
            reason="テスト成功",
        )
        await history1.append(summary)

        # Second instance reads
        history2 = History(temp_history_path)
        count = await history2.count()
        assert count == 1

        context = await history2.get_context_string()
        assert "テストアプローチ" in context


class TestKnowledgeContextGeneration:
    """Tests for knowledge context generation."""

    @pytest.fixture
    def temp_knowledge_path(self, tmp_path: Path) -> Path:
        """Create temporary knowledge file path."""
        return tmp_path / "knowledge.jsonl"

    @pytest.mark.asyncio
    async def test_empty_knowledge_context(self, temp_knowledge_path: Path) -> None:
        """Test context generation with empty knowledge base."""
        kb = KnowledgeBase(temp_knowledge_path)
        context = await kb.get_context_string()

        assert context == "ナレッジなし"

    @pytest.mark.asyncio
    async def test_single_knowledge_entry(self, temp_knowledge_path: Path) -> None:
        """Test context generation with single knowledge entry."""
        kb = KnowledgeBase(temp_knowledge_path)

        knowledge = _make_knowledge(
            knowledge_type=KnowledgeType.DISCOVERY,
            content="テストは重要です",
        )
        await kb.add(knowledge)

        context = await kb.get_context_string()
        assert "discovery" in context.lower()
        assert "テストは重要です" in context

    @pytest.mark.asyncio
    async def test_multiple_knowledge_types(self, temp_knowledge_path: Path) -> None:
        """Test context with different knowledge types."""
        kb = KnowledgeBase(temp_knowledge_path)

        knowledge_items = [
            _make_knowledge(
                knowledge_type=KnowledgeType.DISCOVERY,
                content="発見情報",
            ),
            _make_knowledge(
                knowledge_type=KnowledgeType.CONSTRAINT,
                content="制約情報",
                confidence=KnowledgeConfidence.MEDIUM,
            ),
            _make_knowledge(
                knowledge_type=KnowledgeType.LESSON,
                content="教訓情報",
                confidence=KnowledgeConfidence.LOW,
            ),
        ]
        await kb.add_many(knowledge_items)

        context = await kb.get_context_string()
        assert "発見情報" in context
        assert "制約情報" in context
        assert "教訓情報" in context

    @pytest.mark.asyncio
    async def test_knowledge_persists_across_instances(
        self, temp_knowledge_path: Path
    ) -> None:
        """Test that knowledge persists across instances."""
        # First instance writes
        kb1 = KnowledgeBase(temp_knowledge_path)
        knowledge = _make_knowledge(
            knowledge_type=KnowledgeType.DISCOVERY,
            content="永続化テスト",
        )
        await kb1.add(knowledge)

        # Second instance reads
        kb2 = KnowledgeBase(temp_knowledge_path)
        context = await kb2.get_context_string()
        # Knowledge should be persisted and available
        assert "永続化テスト" in context


class TestContextEfficiency:
    """Tests for context efficiency over multiple iterations."""

    @pytest.fixture
    def temp_history_path(self, tmp_path: Path) -> Path:
        """Create temporary history file path."""
        return tmp_path / "history.jsonl"

    @pytest.mark.asyncio
    async def test_context_size_limited(self, temp_history_path: Path) -> None:
        """Test that context size is limited to avoid token overflow."""
        history = History(temp_history_path)

        # Add many iterations
        for i in range(1, 21):
            summary = _make_summary(
                iteration=i,
                approach=f"長いアプローチの説明 {i}" * 10,  # Make it long
                result=ExecutionStatus.SUCCESS,
                reason=f"詳細な理由の説明 {i}" * 10,
                artifacts=[f"file{i}.py"],
            )
            await history.append(summary)

        # Get context with limit
        context = await history.get_context_string(limit=5)

        # Should only include last 5 iterations
        assert "Iteration 20" in context
        assert "Iteration 16" in context
        assert "Iteration 15" not in context

    @pytest.mark.asyncio
    async def test_failure_history_retrieval(self, temp_history_path: Path) -> None:
        """Test retrieval of failure history for learning."""
        history = History(temp_history_path)

        # Add mix of successes and failures
        for i in range(1, 11):
            status = ExecutionStatus.FAILURE if i % 3 == 0 else ExecutionStatus.SUCCESS
            summary = _make_summary(
                iteration=i,
                approach=f"アプローチ {i}",
                result=status,
                reason=f"理由 {i}",
            )
            await history.append(summary)

        # Get failures
        failures = await history.get_failures(limit=3)

        # Should return failure iterations (3, 6, 9)
        assert len(failures) == 3
        assert all(f.result == ExecutionStatus.FAILURE for f in failures)
