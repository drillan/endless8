"""Pytest fixtures for endless8 tests."""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def e8_dir(tmp_path: Path) -> Path:
    """Provide a temporary .e8 directory for tests."""
    e8_path = tmp_path / ".e8"
    e8_path.mkdir(parents=True, exist_ok=True)
    return e8_path


@pytest.fixture
def history_path(e8_dir: Path) -> Path:
    """Provide a path for history.jsonl."""
    return e8_dir / "history.jsonl"


@pytest.fixture
def knowledge_path(e8_dir: Path) -> Path:
    """Provide a path for knowledge.jsonl."""
    return e8_dir / "knowledge.jsonl"


@pytest.fixture
def sample_task() -> dict[str, Any]:
    """Provide a sample task input."""
    return {
        "task": "テストカバレッジを90%以上にする",
        "criteria": ["pytest --cov で90%以上"],
        "max_iterations": 10,
        "history_context_size": 5,
    }


@pytest.fixture
def sample_execution_summary() -> dict[str, Any]:
    """Provide a sample execution summary."""
    return {
        "type": "summary",
        "iteration": 1,
        "approach": "テストを追加",
        "result": "success",
        "reason": "テストファイル作成完了",
        "artifacts": ["tests/test_main.py"],
        "metadata": {
            "tools_used": ["Read", "Edit", "Bash(pytest)"],
            "files_modified": ["src/main.py"],
            "error_type": None,
            "tokens_used": 15000,
            "strategy_tags": ["test-fix"],
        },
        "next": {
            "suggested_action": "カバレッジを確認",
            "blockers": [],
            "partial_progress": "認証機能の実装完了",
            "pending_items": ["カバレッジ確認"],
        },
        "timestamp": "2026-01-23T10:00:00Z",
    }


@pytest.fixture
def sample_knowledge() -> dict[str, Any]:
    """Provide a sample knowledge entry."""
    return {
        "type": "pattern",
        "category": "testing",
        "content": "テストは tests/ ディレクトリに配置",
        "example_file": "tests/test_main.py",
        "source_task": "テストカバレッジ向上",
        "confidence": "high",
        "applied_count": 0,
        "created_at": "2026-01-23T10:00:00Z",
    }
