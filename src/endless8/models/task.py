"""Task input models for endless8."""

from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    """タスク実行の入力。

    Attributes:
        task: タスクの説明（自然言語）
        criteria: 完了条件のリスト
        max_iterations: 最大イテレーション数
        history_context_size: 参照する履歴の件数
    """

    task: str = Field(..., description="タスクの説明（自然言語）", min_length=1)
    criteria: list[str] = Field(..., description="完了条件のリスト", min_length=1)
    max_iterations: int = Field(
        default=10, ge=1, le=100, description="最大イテレーション数"
    )
    history_context_size: int = Field(
        default=5, ge=1, le=20, description="参照する履歴の件数"
    )
