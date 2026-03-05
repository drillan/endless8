"""Result models for endless8."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from endless8.models.criteria import CriterionType


class IntakeStatus(StrEnum):
    """受付ステータス。"""

    ACCEPTED = "accepted"
    NEEDS_CLARIFICATION = "needs_clarification"
    REJECTED = "rejected"


class ExecutionStatus(StrEnum):
    """実行ステータス。"""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class LoopStatus(StrEnum):
    """ループ終了ステータス。"""

    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    ERROR = "error"
    CANCELLED = "cancelled"


class IntakeResult(BaseModel):
    """受付エージェントの出力。"""

    status: IntakeStatus
    task: str = Field(..., description="構造化されたタスク")
    criteria: list[str] = Field(..., description="構造化された完了条件")
    clarification_questions: list[str] = Field(
        default_factory=list,
        description="明確化のための質問（NEEDS_CLARIFICATION時のみ）",
    )
    rejection_reason: str | None = Field(None, description="却下理由（REJECTED時のみ）")
    validation_notes: str | None = Field(None, description="検証時の注記")
    suggested_tools: list[str] = Field(
        default_factory=list,
        description="タスク実行に推奨されるツール",
    )


class SemanticMetadata(BaseModel):
    """実行エージェントが報告するセマンティックメタデータ。"""

    approach: str = Field(..., description="採用したアプローチ")
    strategy_tags: list[str] = Field(default_factory=list, description="戦略タグ")
    discoveries: list[str] = Field(default_factory=list, description="発見事項")


class ExecutionResult(BaseModel):
    """実行エージェントの出力。"""

    status: ExecutionStatus
    output: str = Field(..., description="実行結果の説明")
    artifacts: list[str] = Field(
        default_factory=list, description="生成・変更したファイル"
    )
    semantic_metadata: SemanticMetadata | None = Field(
        None, description="セマンティックメタデータ"
    )
    raw_log_path: str | None = Field(None, description="生ログファイルのパス")


class CommandResult(BaseModel):
    """コマンド条件の実行結果。"""

    exit_code: int = Field(..., description="終了コード")
    stdout: str = Field(default="", description="標準出力（最大 10KB）")
    stderr: str = Field(default="", description="標準エラー出力（最大 10KB）")
    execution_time_sec: float = Field(..., ge=0.0, description="実行時間（秒）")


class CriteriaEvaluation(BaseModel):
    """各完了条件の評価。"""

    criterion: str = Field(..., description="完了条件")
    is_met: bool = Field(..., description="条件を満たしているか")
    evidence: str = Field(..., description="判定の根拠")
    confidence: float = Field(..., ge=0.0, le=1.0, description="判定の確信度")
    evaluation_method: CriterionType = Field(
        default=CriterionType.SEMANTIC, description="判定方式（FR-013）"
    )
    command_result: CommandResult | None = Field(
        None, description="コマンド実行結果（command 型のみ）"
    )

    @model_validator(mode="after")
    def validate_evaluation_consistency(self) -> Self:
        """Validate cross-field invariants.

        - evaluation_method == 'command' -> confidence == 1.0 (FR-011)
        - evaluation_method == 'command' -> command_result is not None
        - evaluation_method == 'semantic' -> command_result is None
        """
        if self.evaluation_method == CriterionType.COMMAND:
            if self.confidence != 1.0:
                raise ValueError("Command evaluation confidence must be 1.0 (FR-011)")
            if self.command_result is None:
                raise ValueError("command_result is required for command evaluation")
        elif self.evaluation_method == CriterionType.SEMANTIC:
            if self.command_result is not None:
                raise ValueError("command_result must be None for semantic evaluation")
        return self


class JudgmentResult(BaseModel):
    """判定エージェントの出力。"""

    is_complete: bool = Field(..., description="すべての条件を満たしているか")
    evaluations: list[CriteriaEvaluation] = Field(..., description="各条件の評価")
    overall_reason: str = Field(..., description="総合的な判定理由")
    suggested_next_action: str | None = Field(
        None, description="未完了時の次のアクション提案"
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        """Validate consistency between is_complete and evaluations."""
        if self.is_complete and not all(e.is_met for e in self.evaluations):
            raise ValueError("is_complete=True but not all criteria are met")
        return self


class LoopResult(BaseModel):
    """ループ全体の最終結果。"""

    status: LoopStatus
    iterations_used: int = Field(..., ge=0, description="実行したイテレーション数")
    final_judgment: JudgmentResult | None = Field(None, description="最終判定結果")
    intake_result: "IntakeResult | None" = Field(
        None, description="受付結果（明確化が必要な場合に参照）"
    )
    history_path: str | None = Field(None, description="履歴ファイルのパス")
    error_message: str | None = Field(None, description="エラーメッセージ（ERROR時）")

    @model_validator(mode="after")
    def validate_status_fields(self) -> Self:
        """Validate status-dependent required fields."""
        if self.status == LoopStatus.ERROR and not self.error_message:
            raise ValueError("error_message required when status is ERROR")
        if self.status == LoopStatus.COMPLETED and not self.final_judgment:
            raise ValueError("final_judgment required when status is COMPLETED")
        return self
