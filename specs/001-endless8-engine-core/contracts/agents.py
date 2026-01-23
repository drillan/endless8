"""Agents Contract - 4エージェントの公開インターフェース

このファイルは各エージェントの公開 API を定義する。
実装時にはこのインターフェースに準拠すること。
"""

from typing import Protocol

from pydantic import BaseModel

# =====================
# Intake Agent
# =====================


class ClarificationQuestion(BaseModel):
    """明確化のための質問"""

    question: str
    context: str
    suggested_answers: list[str] = []


class IntakeResult(BaseModel):
    """受付エージェントの出力"""

    status: str  # "accepted" | "needs_clarification"
    task: str
    criteria: list[str]
    clarification_questions: list[ClarificationQuestion] = []
    validation_notes: str | None = None


class IntakeAgentProtocol(Protocol):
    """受付エージェントのインターフェース

    責務:
    - 完了条件の妥当性チェック
    - 曖昧な条件に対する質問生成
    - タスクと条件の構造化
    """

    async def run(self, task: str, criteria: list[str]) -> IntakeResult:
        """タスクと完了条件を検証する

        Args:
            task: タスクの説明
            criteria: 完了条件のリスト

        Returns:
            IntakeResult: 検証結果
        """
        ...


# =====================
# Execution Agent
# =====================


class SemanticMetadata(BaseModel):
    """実行エージェントが報告するセマンティックメタデータ"""

    approach: str
    strategy_tags: list[str] = []
    discoveries: list[str] = []


class ExecutionResult(BaseModel):
    """実行エージェントの出力"""

    status: str  # "success" | "failure" | "error"
    output: str
    artifacts: list[str] = []
    semantic_metadata: SemanticMetadata | None = None
    raw_log_path: str | None = None


class ExecutionContext(BaseModel):
    """実行エージェントに渡すコンテキスト"""

    task: str
    criteria: list[str]
    iteration: int
    history_context: str  # サマリ化された履歴
    knowledge_context: str  # 関連するナレッジ


class ExecutionAgentProtocol(Protocol):
    """実行エージェントのインターフェース

    責務:
    - タスクの実行（毎回フレッシュなコンテキストで開始）
    - 履歴を参照して過去の失敗を回避
    - セマンティックメタデータの報告
    """

    async def run(self, context: ExecutionContext) -> ExecutionResult:
        """タスクを実行する

        Args:
            context: 実行コンテキスト

        Returns:
            ExecutionResult: 実行結果
        """
        ...


# =====================
# Summary Agent
# =====================


class SummaryMetadata(BaseModel):
    """機械的に抽出されるメタデータ"""

    tools_used: list[str] = []
    files_modified: list[str] = []
    error_type: str | None = None
    tokens_used: int = 0
    strategy_tags: list[str] = []


class NextAction(BaseModel):
    """次のアクションに関する情報"""

    suggested_action: str
    blockers: list[str] = []
    partial_progress: str | None = None
    pending_items: list[str] = []


class ExecutionSummary(BaseModel):
    """サマリエージェントの出力（履歴に保存）"""

    type: str = "summary"
    iteration: int
    approach: str
    result: str  # "success" | "failure" | "error"
    reason: str
    artifacts: list[str] = []
    metadata: SummaryMetadata = SummaryMetadata()
    next: NextAction | None = None
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


class SummaryAgentProtocol(Protocol):
    """サマリエージェントのインターフェース

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
        raw_log_content: str | None = None,
    ) -> tuple[ExecutionSummary, list[Knowledge]]:
        """実行結果をサマリ化し、ナレッジを抽出する

        Args:
            execution_result: 実行エージェントの出力
            iteration: イテレーション番号
            raw_log_content: stream-json の生ログ（オプション）

        Returns:
            tuple: (サマリ, 抽出されたナレッジのリスト)
        """
        ...


# =====================
# Judgment Agent
# =====================


class CriteriaEvaluation(BaseModel):
    """各完了条件の評価"""

    criterion: str
    is_met: bool
    evidence: str
    confidence: float  # 0.0 - 1.0


class JudgmentResult(BaseModel):
    """判定エージェントの出力"""

    is_complete: bool
    evaluations: list[CriteriaEvaluation]
    overall_reason: str
    suggested_next_action: str | None = None


class JudgmentContext(BaseModel):
    """判定エージェントに渡すコンテキスト"""

    task: str
    criteria: list[str]
    execution_summary: ExecutionSummary
    custom_prompt: str | None = None  # prompts.judgment からの上書き


class JudgmentAgentProtocol(Protocol):
    """判定エージェントのインターフェース

    責務:
    - 各完了条件の個別評価
    - 判定理由の説明
    - 未完了時の次のアクション提案
    """

    async def run(self, context: JudgmentContext) -> JudgmentResult:
        """完了条件を評価する

        Args:
            context: 判定コンテキスト

        Returns:
            JudgmentResult: 判定結果
        """
        ...
