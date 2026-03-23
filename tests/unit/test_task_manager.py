"""Tests for TaskManager class."""

from pathlib import Path

import pytest

from endless8.config import EngineConfig
from endless8.models.state import TaskPhase
from endless8.task_manager import TaskManager, TaskStatus


class TestTaskManagerCreate:
    """Tests for TaskManager.create()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    async def test_create_returns_task_id(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    async def test_create_makes_task_directory(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        task_dir = project_dir / ".e8" / "tasks" / task_id
        assert task_dir.exists()

    async def test_create_initializes_state(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        status = await tm.status(task_id)
        assert status.phase == TaskPhase.CREATED
        assert status.current_iteration == 0
        assert status.is_complete is False


class TestTaskManagerStatus:
    """Tests for TaskManager.status()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    async def test_status_returns_task_status(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        status = await tm.status(task_id)
        assert isinstance(status, TaskStatus)
        assert status.task_id == task_id
        assert status.phase == TaskPhase.CREATED
        assert status.max_iterations == 5

    async def test_status_unknown_task_raises(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        with pytest.raises(FileNotFoundError):
            await tm.status("nonexistent-task")
