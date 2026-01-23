"""History Contract - 履歴・ナレッジ管理のインターフェース

このファイルは History と KnowledgeBase クラスの公開 API を定義する。
実装時にはこのインターフェースに準拠すること。
"""

from typing import Protocol

from pydantic import BaseModel


class ExecutionSummary(BaseModel):
    """サマリエージェントの出力（履歴に保存）"""

    type: str = "summary"
    iteration: int
    approach: str
    result: str  # "success" | "failure" | "error"
    reason: str
    artifacts: list[str] = []
    timestamp: str


class Knowledge(BaseModel):
    """ナレッジエントリ"""

    type: str  # "discovery" | "lesson" | "pattern" | "constraint" | "codebase"
    category: str
    content: str
    example_file: str | None = None
    source_task: str
    confidence: str = "medium"  # "high" | "medium" | "low"
    applied_count: int = 0
    created_at: str


class HistoryProtocol(Protocol):
    """履歴管理クラスのインターフェース

    責務:
    - 履歴の保存・読み込み
    - コンテキスト生成（直近N件 + 失敗履歴）
    - JSONL ファイルへの永続化

    Storage: .e8/tasks/<task-id>/history.jsonl
    """

    def add_summary(self, summary: ExecutionSummary) -> None:
        """サマリを履歴に追加

        Args:
            summary: 追加するサマリ

        Note:
            persist が設定されている場合、即座にファイルに追記
        """
        ...

    def get_context(self, limit: int = 5) -> list[ExecutionSummary]:
        """コンテキスト用の履歴を取得

        Args:
            limit: 直近の履歴件数

        Returns:
            直近N件 + 過去の失敗履歴

        Note:
            DuckDB を使用してクエリ
        """
        ...

    def get_context_text(self, limit: int = 5) -> str:
        """コンテキスト用の履歴をテキスト形式で取得

        Args:
            limit: 直近の履歴件数

        Returns:
            実行エージェントに注入するためのテキスト形式
        """
        ...

    def load(self) -> None:
        """ファイルから履歴を読み込み

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: ファイル形式が不正な場合
        """
        ...

    def clear(self) -> None:
        """履歴をクリア（メモリのみ、ファイルは削除しない）"""
        ...

    @property
    def path(self) -> str | None:
        """履歴ファイルのパス（None = メモリのみ）"""
        ...

    @property
    def count(self) -> int:
        """履歴の件数"""
        ...


class KnowledgeBaseProtocol(Protocol):
    """ナレッジ管理クラスのインターフェース

    責務:
    - ナレッジの保存・読み込み
    - 条件に基づくナレッジ検索
    - タスクに関連するナレッジの取得

    Storage: .e8/knowledge.jsonl
    """

    def add_knowledge(self, knowledge: Knowledge) -> None:
        """ナレッジを追加

        Args:
            knowledge: 追加するナレッジ

        Note:
            即座にファイルに追記（クラッシュ耐性）
        """
        ...

    def query(
        self,
        knowledge_type: str | None = None,
        category: str | None = None,
        min_confidence: str = "low",
    ) -> list[Knowledge]:
        """条件に合うナレッジを検索

        Args:
            knowledge_type: フィルタするタイプ（None = すべて）
            category: フィルタするカテゴリ（None = すべて）
            min_confidence: 最低信頼度 ("low", "medium", "high")

        Returns:
            条件に合うナレッジのリスト

        Note:
            DuckDB を使用してクエリ
        """
        ...

    def get_relevant_knowledge(self, task: str, limit: int = 10) -> list[Knowledge]:
        """タスクに関連するナレッジを取得

        Args:
            task: タスクの説明
            limit: 取得する最大件数

        Returns:
            関連度の高いナレッジのリスト
        """
        ...

    def get_context_text(self, task: str, limit: int = 10) -> str:
        """タスクに関連するナレッジをテキスト形式で取得

        Args:
            task: タスクの説明
            limit: 取得する最大件数

        Returns:
            実行エージェントに注入するためのテキスト形式
        """
        ...

    def increment_applied_count(self, knowledge: Knowledge) -> None:
        """ナレッジの適用カウントを増加

        Args:
            knowledge: 適用されたナレッジ
        """
        ...

    @property
    def path(self) -> str:
        """ナレッジファイルのパス"""
        ...

    @property
    def count(self) -> int:
        """ナレッジの件数"""
        ...
