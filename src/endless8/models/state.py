"""Task state models for endless8 task lifecycle management."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class TaskPhase(StrEnum):
    """タスクのフェーズ。"""

    CREATED = "created"
    INTAKE = "intake"
    EXECUTING = "executing"
    SUMMARIZING = "summarizing"
    JUDGING = "judging"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """終端フェーズかどうか。"""
        return self in _TERMINAL_PHASES

    @property
    def valid_next_phases(self) -> frozenset["TaskPhase"]:
        """このフェーズから遷移可能なフェーズ。"""
        return _TRANSITIONS.get(self, frozenset())


_TERMINAL_PHASES: frozenset[TaskPhase] = frozenset(
    {
        TaskPhase.COMPLETED,
        TaskPhase.FAILED,
        TaskPhase.ERROR,
        TaskPhase.CANCELLED,
    }
)

_TRANSITIONS: dict[TaskPhase, frozenset[TaskPhase]] = {
    TaskPhase.CREATED: frozenset(
        {TaskPhase.INTAKE, TaskPhase.EXECUTING, TaskPhase.ERROR, TaskPhase.CANCELLED}
    ),
    TaskPhase.INTAKE: frozenset(
        {TaskPhase.EXECUTING, TaskPhase.ERROR, TaskPhase.CANCELLED}
    ),
    TaskPhase.EXECUTING: frozenset(
        {TaskPhase.SUMMARIZING, TaskPhase.ERROR, TaskPhase.CANCELLED}
    ),
    TaskPhase.SUMMARIZING: frozenset(
        {TaskPhase.JUDGING, TaskPhase.ERROR, TaskPhase.CANCELLED}
    ),
    TaskPhase.JUDGING: frozenset(
        {
            TaskPhase.COMPLETED,
            TaskPhase.FAILED,
            TaskPhase.EXECUTING,
            TaskPhase.ERROR,
            TaskPhase.CANCELLED,
        }
    ),
}


class StateTransition(BaseModel):
    """状態遷移レコード。"""

    type: Literal["state_transition"] = "state_transition"
    from_phase: TaskPhase
    to_phase: TaskPhase
    iteration: int = Field(..., ge=0)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    metadata: dict[str, str] = Field(default_factory=dict)
