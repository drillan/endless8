"""Agent protocols and base classes for endless8.

This module defines the protocols (interfaces) for the 4 agents:
- IntakeAgent: Validates task and criteria, generates clarification questions
- ExecutionAgent: Executes the task with fresh context each iteration
- SummaryAgent: Compresses execution results and extracts knowledge
- JudgmentAgent: Evaluates completion criteria
"""

from typing import Protocol

from pydantic import BaseModel, Field

from endless8.models import (
    ExecutionResult,
    ExecutionSummary,
    IntakeResult,
    JudgmentResult,
    Knowledge,
)


class ExecutionContext(BaseModel):
    """実行エージェントに渡すコンテキスト。"""

    task: str = Field(..., description="タスクの説明")
    criteria: list[str] = Field(..., description="完了条件のリスト")
    iteration: int = Field(..., ge=1, description="イテレーション番号")
    history_context: str = Field(..., description="サマリ化された履歴")
    knowledge_context: str = Field(..., description="関連するナレッジ")


class JudgmentContext(BaseModel):
    """判定エージェントに渡すコンテキスト。"""

    task: str = Field(..., description="タスクの説明")
    criteria: list[str] = Field(..., description="完了条件のリスト")
    execution_summary: ExecutionSummary = Field(..., description="実行サマリ")
    custom_prompt: str | None = Field(None, description="prompts.judgment からの上書き")


class IntakeAgentProtocol(Protocol):
    """受付エージェントのインターフェース。

    責務:
    - 完了条件の妥当性チェック
    - 曖昧な条件に対する質問生成
    - タスクと条件の構造化
    """

    async def run(self, task: str, criteria: list[str]) -> IntakeResult:
        """タスクと完了条件を検証する。

        Args:
            task: タスクの説明
            criteria: 完了条件のリスト

        Returns:
            IntakeResult: 検証結果
        """
        ...


class ExecutionAgentProtocol(Protocol):
    """実行エージェントのインターフェース。

    責務:
    - タスクの実行（毎回フレッシュなコンテキストで開始）
    - 履歴を参照して過去の失敗を回避
    - セマンティックメタデータの報告
    """

    async def run(self, context: ExecutionContext) -> ExecutionResult:
        """タスクを実行する。

        Args:
            context: 実行コンテキスト

        Returns:
            ExecutionResult: 実行結果
        """
        ...


class SummaryAgentProtocol(Protocol):
    """サマリエージェントのインターフェース。

    責務:
    - 実行結果の圧縮・サマリ化
    - 機械的メタデータの抽出（stream-json から）
    - セマンティックメタデータとの統合
    - ナレッジの抽出
    """

    async def run(
        self,
        execution_result: ExecutionResult,
        iteration: int,
        criteria: list[str],
        raw_log_content: str | None = None,
    ) -> tuple[ExecutionSummary, list[Knowledge]]:
        """実行結果をサマリ化し、ナレッジを抽出する。

        Args:
            execution_result: 実行エージェントの出力
            iteration: イテレーション番号
            criteria: 完了条件のリスト
            raw_log_content: stream-json の生ログ（オプション）

        Returns:
            tuple: (サマリ, 抽出されたナレッジのリスト)
        """
        ...


class JudgmentAgentProtocol(Protocol):
    """判定エージェントのインターフェース。

    責務:
    - 各完了条件の個別評価
    - 判定理由の説明
    - 未完了時の次のアクション提案
    """

    async def run(self, context: JudgmentContext) -> JudgmentResult:
        """完了条件を評価する。

        Args:
            context: 判定コンテキスト

        Returns:
            JudgmentResult: 判定結果
        """
        ...


__all__ = [
    "ExecutionContext",
    "JudgmentContext",
    "IntakeAgentProtocol",
    "ExecutionAgentProtocol",
    "SummaryAgentProtocol",
    "JudgmentAgentProtocol",
]
