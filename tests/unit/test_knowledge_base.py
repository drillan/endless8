"""Unit tests for the KnowledgeBase class."""

from pathlib import Path

import pytest

from endless8.models import Knowledge, KnowledgeConfidence, KnowledgeType


class TestKnowledgeBase:
    """Tests for KnowledgeBase class."""

    @pytest.fixture
    def temp_knowledge_path(self, tmp_path: Path) -> Path:
        """Create temporary knowledge file path."""
        return tmp_path / ".e8" / "knowledge.jsonl"

    @pytest.fixture
    def sample_knowledge(self) -> Knowledge:
        """Create sample knowledge item."""
        return Knowledge(
            type=KnowledgeType.DISCOVERY,
            category="testing",
            content="新しいパターンを発見: テストファーストが効果的",
            source_task="iteration:1",
            confidence=KnowledgeConfidence.HIGH,
        )

    async def test_knowledge_base_add_and_retrieve(
        self,
        temp_knowledge_path: Path,
        sample_knowledge: Knowledge,
    ) -> None:
        """Test that knowledge base can add and retrieve items."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)
        await kb.add(sample_knowledge)

        items = await kb.get_all()
        assert len(items) == 1
        assert items[0].content == "新しいパターンを発見: テストファーストが効果的"

    async def test_knowledge_base_query_by_type(
        self,
        temp_knowledge_path: Path,
    ) -> None:
        """Test that knowledge base can query by type."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)

        # Add different types
        await kb.add(
            Knowledge(
                type=KnowledgeType.DISCOVERY,
                category="general",
                content="発見1",
                source_task="test",
                confidence=KnowledgeConfidence.HIGH,
            )
        )
        await kb.add(
            Knowledge(
                type=KnowledgeType.LESSON,
                category="general",
                content="レッスン1",
                source_task="test",
                confidence=KnowledgeConfidence.MEDIUM,
            )
        )
        await kb.add(
            Knowledge(
                type=KnowledgeType.DISCOVERY,
                category="general",
                content="発見2",
                source_task="test",
                confidence=KnowledgeConfidence.HIGH,
            )
        )

        discoveries = await kb.query(type_filter=KnowledgeType.DISCOVERY)
        assert len(discoveries) == 2
        assert all(k.type == KnowledgeType.DISCOVERY for k in discoveries)

        lessons = await kb.query(type_filter=KnowledgeType.LESSON)
        assert len(lessons) == 1

    async def test_knowledge_base_query_by_tags(
        self,
        temp_knowledge_path: Path,
    ) -> None:
        """Test that knowledge base can query by tags."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)

        await kb.add(
            Knowledge(
                type=KnowledgeType.DISCOVERY,
                category="testing",
                content="テスト関連",
                source_task="test",
                confidence=KnowledgeConfidence.HIGH,
            )
        )
        await kb.add(
            Knowledge(
                type=KnowledgeType.DISCOVERY,
                category="build",
                content="ビルド関連",
                source_task="test",
                confidence=KnowledgeConfidence.HIGH,
            )
        )

        test_items = await kb.query(category_filter="testing")
        assert len(test_items) == 1
        assert "テスト関連" in test_items[0].content

    async def test_knowledge_base_generates_context_string(
        self,
        temp_knowledge_path: Path,
    ) -> None:
        """Test that knowledge base generates context string."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)

        await kb.add(
            Knowledge(
                type=KnowledgeType.DISCOVERY,
                category="general",
                content="発見: パターンA",
                source_task="test",
                confidence=KnowledgeConfidence.HIGH,
            )
        )
        await kb.add(
            Knowledge(
                type=KnowledgeType.LESSON,
                category="general",
                content="レッスン: 手法B",
                source_task="test",
                confidence=KnowledgeConfidence.MEDIUM,
            )
        )

        context = await kb.get_context_string(limit=10)
        assert "発見" in context
        assert "レッスン" in context

    async def test_knowledge_base_respects_limit(
        self,
        temp_knowledge_path: Path,
    ) -> None:
        """Test that knowledge base respects limit parameter."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)

        for i in range(1, 11):
            await kb.add(
                Knowledge(
                    type=KnowledgeType.DISCOVERY,
                    category="general",
                    content=f"知識 {i}",
                    source_task="test",
                    confidence=KnowledgeConfidence.HIGH,
                )
            )

        items = await kb.get_all(limit=5)
        assert len(items) == 5

    async def test_knowledge_base_persists_to_file(
        self,
        temp_knowledge_path: Path,
        sample_knowledge: Knowledge,
    ) -> None:
        """Test that knowledge base persists to JSONL file."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)
        await kb.add(sample_knowledge)

        # File should exist and contain data
        assert temp_knowledge_path.exists()
        content = temp_knowledge_path.read_text()
        assert "テストファーストが効果的" in content

        # New instance should load existing data
        kb2 = KnowledgeBase(knowledge_path=temp_knowledge_path)
        items = await kb2.get_all()
        assert len(items) == 1

    async def test_knowledge_base_add_multiple(
        self,
        temp_knowledge_path: Path,
    ) -> None:
        """Test that knowledge base can add multiple items at once."""
        from endless8.history import KnowledgeBase

        kb = KnowledgeBase(knowledge_path=temp_knowledge_path)

        items = [
            Knowledge(
                type=KnowledgeType.DISCOVERY,
                category="general",
                content=f"発見 {i}",
                source_task="test",
                confidence=KnowledgeConfidence.HIGH,
            )
            for i in range(1, 4)
        ]

        await kb.add_many(items)

        all_items = await kb.get_all()
        assert len(all_items) == 3
