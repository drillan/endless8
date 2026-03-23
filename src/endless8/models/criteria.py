"""Criterion type models for structured completion criteria.

Defines the discriminated union type for completion criteria:
- str: semantic criterion (LLM evaluation)
- CommandCriterion: command criterion (exit code evaluation)
"""

from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, Field, Tag


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

str -> 意味的条件（LLM 判定）
CommandCriterion -> コマンド条件（終了コード判定）
"""


def criteria_to_str_list(criteria: list[CriterionInput]) -> list[str]:
    """Convert CriterionInput list to str list for display/agent interfaces.

    Args:
        criteria: list of CriterionInput (str | CommandCriterion)

    Returns:
        list of str representations for each criterion
    """
    return [c if isinstance(c, str) else (c.description or c.command) for c in criteria]


def filter_semantic_criteria(criteria: Sequence[CriterionInput]) -> list[str]:
    """セマンティック条件のみをフィルタリングして返す。

    コマンド条件は実行エージェントのコンテキストから除外し、
    判定フェーズでのみ CommandExecutor が評価する。

    Args:
        criteria: CriterionInput のリスト（str | CommandCriterion）

    Returns:
        セマンティック条件（str）のみのリスト
    """
    return [c for c in criteria if isinstance(c, str)]
