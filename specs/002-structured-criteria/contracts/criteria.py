"""Contract: Criterion types for structured completion criteria.

This contract defines the public interfaces for the 002-structured-criteria feature.
It serves as a reference for implementation - not executable code.
"""

# --- models/criteria.py ---

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Discriminator, Field, Tag, model_validator


class CriterionType(StrEnum):
    """判定方式。"""

    SEMANTIC = "semantic"
    COMMAND = "command"


class CommandCriterion(BaseModel):
    """コマンド条件。

    シェルコマンドの終了コードで条件の met/not met を判定する。
    """

    type: Literal["command"]
    command: str = Field(..., min_length=1, description="実行するシェルコマンド")
    description: str | None = Field(None, description="人間向けの説明（FR-012）")
    timeout: float | None = Field(
        None, gt=0, description="コマンド固有のタイムアウト（秒）"
    )


def _criterion_discriminator(v: object) -> str:
    """Criterion 型の判別関数。

    Args:
        v: バリデーション対象の入力値

    Returns:
        判別タグ（"str" or "command"）

    Raises:
        ValueError: 判別不可能な入力値の場合
    """
    if isinstance(v, str):
        return "str"
    if isinstance(v, dict):
        if v.get("type") == "command":
            return "command"
        raise ValueError(
            f"Dict criterion must have type='command', got type={v.get('type')!r}"
        )
    if isinstance(v, CommandCriterion):
        return "command"
    raise ValueError(f"Cannot discriminate criterion from {type(v).__name__}")


CriterionInput = Annotated[
    Annotated[str, Tag("str")] | Annotated[CommandCriterion, Tag("command")],
    Discriminator(_criterion_discriminator),
]
"""完了条件の入力型。

str → 意味的条件（LLM 判定）
CommandCriterion → コマンド条件（終了コード判定）
"""


# --- models/results.py (extensions) ---


class CommandResult(BaseModel):
    """コマンド条件の実行結果。"""

    exit_code: int = Field(..., description="終了コード")
    stdout: str = Field(default="", description="標準出力（最大 10KB）")
    stderr: str = Field(default="", description="標準エラー出力（最大 10KB）")
    execution_time_sec: float = Field(..., ge=0.0, description="実行時間（秒）")


class CriteriaEvaluation(BaseModel):
    """各完了条件の評価（拡張版）。

    既存フィールドに evaluation_method と command_result を追加。
    """

    criterion: str = Field(..., description="完了条件")
    is_met: bool = Field(..., description="条件を満たしているか")
    evidence: str = Field(..., description="判定の根拠")
    confidence: float = Field(..., ge=0.0, le=1.0, description="判定の確信度")
    evaluation_method: CriterionType = Field(..., description="判定方式（FR-013）")
    command_result: CommandResult | None = Field(
        None, description="コマンド実行結果（command 型のみ）"
    )

    @model_validator(mode="after")
    def validate_evaluation_consistency(self) -> Self:
        """Validate cross-field invariants.

        - evaluation_method == 'command' → confidence == 1.0 (FR-011)
        - evaluation_method == 'command' → command_result is not None
        - evaluation_method == 'semantic' → command_result is None
        """
        if self.evaluation_method == CriterionType.COMMAND:
            if self.confidence != 1.0:
                raise ValueError(
                    "Command evaluation confidence must be 1.0 (FR-011)"
                )
            if self.command_result is None:
                raise ValueError(
                    "command_result is required for command evaluation"
                )
        elif self.evaluation_method == CriterionType.SEMANTIC:
            if self.command_result is not None:
                raise ValueError(
                    "command_result must be None for semantic evaluation"
                )
        return self


# --- command/executor.py ---


class CommandExecutionError(Exception):
    """コマンドの実行エラー（FR-009）。

    プロセス起動失敗またはタイムアウト時に送出される。
    コマンドが正常に起動し終了コードを返した場合は送出されない。
    """

    ...


class CommandExecutor:
    """コマンド条件の実行器。

    asyncio.create_subprocess_shell を使用してシェルコマンドを実行する。
    """

    async def execute(
        self,
        command: str,
        cwd: str,
        timeout: float,
    ) -> CommandResult:
        """コマンドを実行し結果を返す。

        Args:
            command: 実行するシェルコマンド
            cwd: 作業ディレクトリ（FR-014）
            timeout: タイムアウト（秒）（FR-008）

        Returns:
            CommandResult: 実行結果

        Raises:
            CommandExecutionError: プロセス起動失敗またはタイムアウト時（FR-009）
        """
        ...


# --- agents/__init__.py (extensions) ---


class CommandCriterionResult(BaseModel):
    """コマンド条件の判定結果（Engine 内部用）。

    JudgmentContext に渡してLLM判定のコンテキストとして使用。
    """

    criterion_index: int = Field(..., ge=0, description="criteria リスト内のインデックス")
    description: str = Field(..., description="条件の表示名")
    command: str = Field(..., description="実行したコマンド")
    is_met: bool = Field(..., description="終了コード 0 = True")
    result: CommandResult = Field(..., description="実行結果")


class JudgmentContext(BaseModel):
    """判定エージェントに渡すコンテキスト（拡張版）。"""

    task: str = Field(..., description="タスクの説明")
    criteria: list[str] = Field(..., description="意味的完了条件のテキストのみ")
    execution_summary: "ExecutionSummary" = Field(..., description="実行サマリ")
    command_results: list[CommandCriterionResult] | None = Field(
        None, description="コマンド条件の判定結果（FR-007）"
    )
    custom_prompt: str | None = Field(None, description="prompts.judgment からの上書き")
