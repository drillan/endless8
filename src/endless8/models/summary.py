"""Summary models for endless8."""

from typing import Literal

from pydantic import BaseModel, Field

from endless8.models.results import ExecutionStatus


class KnowledgeEntry(BaseModel):
    """LLMが抽出するナレッジエントリ。"""

    type: Literal["discovery", "lesson", "pattern", "constraint", "codebase"] = Field(
        ...,
        description="ナレッジタイプ: discovery | lesson | pattern | constraint | codebase",
    )
    category: str = Field(..., description="カテゴリ（例: error_handling, testing）")
    content: str = Field(..., description="ナレッジの内容")
    confidence: Literal["high", "medium", "low"] = Field(
        default="medium", description="信頼度: high | medium | low"
    )


class SummaryLLMOutput(BaseModel):
    """LLMによるサマリ出力の構造化モデル。"""

    approach: str = Field(..., description="採用したアプローチ（1行）")
    reason: str = Field(
        ..., max_length=4000, description="結果の理由（簡潔に、最大4000文字）"
    )
    artifacts: list[str] = Field(
        default_factory=list, description="生成・変更したファイルのリスト"
    )
    next_action: str | None = Field(
        None, description="次のアクション情報（未完了の場合）"
    )
    knowledge_entries: list[KnowledgeEntry] = Field(
        default_factory=list, description="抽出されたナレッジ"
    )


class SummaryMetadata(BaseModel):
    """機械的に抽出されるメタデータ。"""

    tools_used: list[str] = Field(default_factory=list, description="使用したツール")
    files_modified: list[str] = Field(
        default_factory=list, description="変更したファイル"
    )
    error_type: str | None = Field(None, description="エラータイプ（該当時）")
    tokens_used: int = Field(default=0, ge=0, description="使用トークン数")
    strategy_tags: list[str] = Field(default_factory=list, description="戦略タグ")


class NextAction(BaseModel):
    """次のアクションに関する情報。"""

    suggested_action: str = Field(..., description="推奨アクション")
    blockers: list[str] = Field(default_factory=list, description="ブロッカー")
    partial_progress: str | None = Field(None, description="部分的な進捗")
    pending_items: list[str] = Field(default_factory=list, description="未完了項目")


class ExecutionSummary(BaseModel):
    """サマリエージェントの出力（履歴に保存）。"""

    type: str = Field(default="summary", description="レコードタイプ")
    iteration: int = Field(..., ge=1, description="イテレーション番号")
    approach: str = Field(..., description="採用したアプローチ")
    result: ExecutionStatus
    reason: str = Field(..., description="結果の理由")
    artifacts: list[str] = Field(default_factory=list, description="成果物")
    metadata: SummaryMetadata = Field(default_factory=SummaryMetadata)
    next: NextAction | None = Field(None, description="次のアクション情報")
    timestamp: str = Field(..., description="ISO 8601形式のタイムスタンプ")
