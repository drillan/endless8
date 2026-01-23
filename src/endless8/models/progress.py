"""Progress event models for endless8."""

from datetime import UTC, datetime
from enum import Enum
from typing import NotRequired, TypedDict

from pydantic import BaseModel, Field


class ProgressEventType(str, Enum):
    """進捗イベントタイプ。"""

    TASK_START = "task_start"  # タスク開始
    TASK_END = "task_end"  # タスク終了
    ITERATION_START = "iteration_start"  # イテレーション開始
    ITERATION_END = "iteration_end"  # イテレーション終了
    INTAKE_COMPLETE = "intake_complete"  # 受付完了
    EXECUTION_COMPLETE = "execution_complete"  # 実行完了
    JUDGMENT_COMPLETE = "judgment_complete"  # 判定完了


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


class TaskStartData(TypedDict):
    """TASK_START イベントのデータ。"""

    task: str
    criteria: list[str]
    resume: NotRequired[bool]


class StatusData(TypedDict):
    """ステータス関連イベント（INTAKE_COMPLETE, TASK_END等）のデータ。"""

    status: str
    reason: NotRequired[str]
    error: NotRequired[str]
    missing_tools: NotRequired[list[str]]


class JudgmentData(TypedDict):
    """JUDGMENT_COMPLETE イベントのデータ。"""

    is_complete: bool


class IterationEndData(TypedDict):
    """ITERATION_END イベントのデータ。"""

    result: str


ProgressData = TaskStartData | StatusData | JudgmentData | IterationEndData


class ProgressEvent(BaseModel):
    """進捗イベント。"""

    event_type: ProgressEventType
    iteration: int | None = Field(None, description="イテレーション番号")
    message: str = Field(..., description="進捗メッセージ")
    timestamp: datetime = Field(default_factory=_utc_now)
    data: ProgressData | None = Field(None, description="追加データ")


__all__ = ["ProgressEventType", "ProgressEvent"]
