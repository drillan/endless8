"""KnowledgeBase class for managing project knowledge.

Provides JSONL-based storage and retrieval of knowledge items,
with filtering by type and tags.
"""

import json
from pathlib import Path

from endless8.models import Knowledge, KnowledgeConfidence, KnowledgeType


class KnowledgeBase:
    """Manages project knowledge stored in JSONL format.

    Provides:
    - Append-only storage of knowledge items
    - Query by type and tags
    - Context string generation for execution agent
    """

    def __init__(self, knowledge_path: str | Path) -> None:
        """Initialize knowledge base.

        Args:
            knowledge_path: Path to knowledge.jsonl file.
        """
        self._path = Path(knowledge_path)
        self._items: list[Knowledge] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing knowledge from file."""
        if not self._path.exists():
            return

        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                knowledge = Knowledge(
                    type=KnowledgeType(data["type"]),
                    category=data["category"],
                    content=data["content"],
                    source_task=data["source_task"],
                    confidence=KnowledgeConfidence(data["confidence"]),
                    example_file=data.get("example_file"),
                )
                self._items.append(knowledge)

    def _ensure_directory(self) -> None:
        """Ensure the parent directory exists."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _write_item(self, item: Knowledge) -> None:
        """Write a single item to file.

        Args:
            item: Knowledge item to write.
        """
        record = {
            "type": item.type.value,
            "category": item.category,
            "content": item.content,
            "source_task": item.source_task,
            "confidence": item.confidence.value,
            "example_file": item.example_file,
        }

        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def add(self, knowledge: Knowledge) -> None:
        """Add a knowledge item.

        Args:
            knowledge: Knowledge item to add.
        """
        self._items.append(knowledge)
        self._ensure_directory()
        self._write_item(knowledge)

    async def add_many(self, items: list[Knowledge]) -> None:
        """Add multiple knowledge items.

        Args:
            items: List of knowledge items to add.
        """
        for item in items:
            await self.add(item)

    async def get_all(self, limit: int | None = None) -> list[Knowledge]:
        """Get all knowledge items.

        Args:
            limit: Optional maximum number of items to return.

        Returns:
            List of knowledge items.
        """
        if limit is None:
            return list(self._items)
        return self._items[-limit:]

    async def query(
        self,
        type_filter: KnowledgeType | None = None,
        category_filter: str | None = None,
        limit: int = 10,
    ) -> list[Knowledge]:
        """Query knowledge items.

        Args:
            type_filter: Filter by knowledge type.
            category_filter: Filter by category.
            limit: Maximum number of items to return.

        Returns:
            List of matching knowledge items.
        """
        results = self._items

        if type_filter is not None:
            results = [k for k in results if k.type == type_filter]

        if category_filter is not None:
            results = [k for k in results if k.category == category_filter]

        return results[-limit:]

    async def get_context_string(self, limit: int = 10) -> str:
        """Generate context string for execution agent.

        Args:
            limit: Maximum number of items to include.

        Returns:
            Formatted context string.
        """
        items = await self.get_all(limit)
        if not items:
            return "ナレッジなし"

        lines = []
        for k in items:
            lines.append(f"[{k.type.value}] {k.content}")
        return "\n".join(lines)


__all__ = ["KnowledgeBase"]
