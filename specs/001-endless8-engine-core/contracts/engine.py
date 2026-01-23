"""Engine Contract - endless8 エンジンの公開インターフェース

このファイルは Engine クラスの公開 API を定義する。
実装時にはこのインターフェースに準拠すること。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# Note: 実装時に models/ から import する
# from endless8.models.task import TaskInput
# from endless8.models.results import LoopResult, JudgmentResult
# from endless8.models.summary import ExecutionSummary


class TaskInput(BaseModel):
    """タスク実行の入力"""

    task: str
    criteria: list[str]
    max_iterations: int = 10
    history_context_size: int = 5


class LoopResult(BaseModel):
    """ループ全体の最終結果"""

    status: str  # "completed" | "max_iterations" | "error" | "cancelled"
    iterations_used: int
    task_id: str | None = None  # タスクID（タイムスタンプ形式）
    task_dir: str | None = None  # タスクディレクトリパス
    final_summary: ExecutionSummary | None = None  # 最終イテレーションのサマリ
    error_message: str | None = None


class ExecutionSummary(BaseModel):
    """サマリエージェントの出力（履歴に保存）"""

    iteration: int
    approach: str
    result: str  # "success" | "failure" | "error"
    reason: str


# Progress Callback Types
class ProgressEventType(str, Enum):
    """進捗イベントタイプ"""

    TASK_START = "task_start"  # タスク開始
    TASK_END = "task_end"  # タスク終了
    ITERATION_START = "iteration_start"  # イテレーション開始
    ITERATION_END = "iteration_end"  # イテレーション終了
    INTAKE_COMPLETE = "intake_complete"  # 受付完了
    EXECUTION_COMPLETE = "execution_complete"  # 実行完了
    JUDGMENT_COMPLETE = "judgment_complete"  # 判定完了


class ProgressEvent(BaseModel):
    """進捗イベント"""

    event_type: ProgressEventType
    iteration: int | None = Field(None, description="イテレーション番号")
    message: str = Field(..., description="進捗メッセージ")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict | None = Field(None, description="追加データ")


# コールバック型定義
ProgressCallback = Callable[[ProgressEvent], None]
AsyncProgressCallback = Callable[[ProgressEvent], Awaitable[None]]


class EngineProtocol(ABC):
    """Engine の公開インターフェース

    Usage:
        engine = Engine(config)
        result = await engine.run(task_input)

        # 進捗コールバック付きで実行
        def on_progress(event: ProgressEvent) -> None:
            print(f"[{event.event_type}] {event.message}")

        result = await engine.run(task_input, on_progress=on_progress)

        # または進捗を監視しながら実行
        async for summary in engine.run_iter(task_input):
            print(f"Iteration {summary.iteration}: {summary.result}")
    """

    @abstractmethod
    async def run(
        self,
        task_input: TaskInput,
        on_progress: ProgressCallback | AsyncProgressCallback | None = None,
        task_id: str | None = None,
    ) -> LoopResult:
        """タスクを実行し、完了まで待機する

        Args:
            task_input: タスク実行の入力
            on_progress: 進捗通知コールバック（オプション）
            task_id: タスクID（指定しない場合はタイムスタンプで生成）
                     既存タスクの再開時に指定する

        Returns:
            LoopResult: ループ全体の最終結果

        Raises:
            ValueError: 入力が不正な場合
            RuntimeError: 実行中にエラーが発生した場合
        """
        ...

    @abstractmethod
    def run_iter(self, task_input: TaskInput) -> AsyncIterator[ExecutionSummary]:
        """タスクを実行し、各イテレーションの結果を yield する

        Args:
            task_input: タスク実行の入力

        Yields:
            ExecutionSummary: 各イテレーションのサマリ

        Raises:
            ValueError: 入力が不正な場合
            RuntimeError: 実行中にエラーが発生した場合
        """
        ...

    @abstractmethod
    async def cancel(self) -> None:
        """実行中のタスクをキャンセルする

        Note:
            キャンセル後、run() は LoopResult(status="cancelled") を返す
        """
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """タスクが実行中かどうか"""
        ...

    @property
    @abstractmethod
    def current_iteration(self) -> int:
        """現在のイテレーション番号（0 = 未開始）"""
        ...
