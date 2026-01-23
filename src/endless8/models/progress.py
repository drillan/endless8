"""Progress event models for endless8."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

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


class ProgressEvent(BaseModel):
    """進捗イベント。"""

    event_type: ProgressEventType
    iteration: int | None = Field(None, description="イテレーション番号")
    message: str = Field(..., description="進捗メッセージ")
    timestamp: datetime = Field(default_factory=_utc_now)
    data: dict[str, Any] | None = Field(None, description="追加データ")


__all__ = ["ProgressEventType", "ProgressEvent"]
