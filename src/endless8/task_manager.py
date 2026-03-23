"""Task manager for endless8 task lifecycle management."""

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from endless8.config import EngineConfig
from endless8.models.state import TaskPhase
from endless8.state import TaskStateMachine

logger = logging.getLogger(__name__)


class TaskStatus(BaseModel):
    """タスクの現在のステータス。"""

    task_id: str
    phase: TaskPhase
    current_iteration: int = Field(..., ge=0)
    max_iterations: int
    is_complete: bool
    task_description: str
    transitions_count: int = Field(..., ge=0)


class TaskManager:
    """タスクのライフサイクルを管理する。"""

    def __init__(self, project_dir: Path, config: EngineConfig) -> None:
        self._project_dir = project_dir
        self._config = config

    def _task_dir(self, task_id: str) -> Path:
        return self._project_dir / ".e8" / "tasks" / task_id

    def _state_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "state.jsonl"

    async def create(self) -> str:
        """新しいタスクを作成し、task_id を返す。"""
        task_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        task_dir = self._task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        # 状態マシンを初期化（CREATED 状態のファイルを作成）
        TaskStateMachine(self._state_path(task_id))

        return task_id

    async def status(self, task_id: str) -> TaskStatus:
        """タスクの現在のステータスを返す。"""
        task_dir = self._task_dir(task_id)

        if not task_dir.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")

        sm = TaskStateMachine(self._state_path(task_id))

        return TaskStatus(
            task_id=task_id,
            phase=sm.current_phase,
            current_iteration=sm.current_iteration,
            max_iterations=self._config.max_iterations,
            is_complete=sm.current_phase == TaskPhase.COMPLETED,
            task_description=self._config.task,
            transitions_count=len(sm.get_transitions()),
        )


__all__ = ["TaskManager", "TaskStatus"]
