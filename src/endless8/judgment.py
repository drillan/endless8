"""Shared judgment logic for endless8.

Provides standalone functions for command criteria evaluation,
semantic judgment, and result merging. Used by both Engine and TaskManager.
"""

import logging
from collections.abc import Callable, Coroutine, Sequence

from endless8.agents import CommandCriterionResult, JudgmentContext
from endless8.command.executor import CommandExecutor
from endless8.models import (
    CommandCriterion,
    CriteriaEvaluation,
    CriterionInput,
    CriterionType,
    ExecutionSummary,
    JudgmentResult,
)

logger = logging.getLogger(__name__)

JudgmentAgentRun = Callable[
    [JudgmentContext], Coroutine[object, object, JudgmentResult]
]


async def run_command_criteria(
    criteria: Sequence[CriterionInput],
    cwd: str,
    default_timeout: float,
) -> tuple[list[CriteriaEvaluation], list[CommandCriterionResult]]:
    """コマンド条件を実行し評価結果を返す。

    Args:
        criteria: 全条件リスト（semantic + command）。
        cwd: コマンド実行の作業ディレクトリ。
        default_timeout: デフォルトタイムアウト（秒）。

    Returns:
        (command_evaluations, command_criterion_results) のタプル。

    Raises:
        CommandExecutionError: 実行エラー時（FR-009）。
    """
    executor = CommandExecutor()
    command_evaluations: list[CriteriaEvaluation] = []
    command_criterion_results: list[CommandCriterionResult] = []

    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, CommandCriterion):
            continue

        timeout = criterion.timeout or default_timeout
        result = await executor.execute(criterion.command, cwd, timeout)

        is_met = result.exit_code == 0
        description = criterion.description or criterion.command

        evidence_parts = [f"exit_code={result.exit_code}"]
        if result.stdout:
            evidence_parts.append(f"stdout: {result.stdout[:200]}")
        if result.stderr:
            evidence_parts.append(f"stderr: {result.stderr[:200]}")

        command_evaluations.append(
            CriteriaEvaluation(
                criterion=description,
                is_met=is_met,
                evidence=", ".join(evidence_parts),
                confidence=1.0,
                evaluation_method=CriterionType.COMMAND,
                command_result=result,
            )
        )

        command_criterion_results.append(
            CommandCriterionResult(
                criterion_index=index,
                description=description,
                command=criterion.command,
                is_met=is_met,
                result=result,
            )
        )

    return command_evaluations, command_criterion_results


def build_judgment_result_from_commands(
    command_evaluations: list[CriteriaEvaluation],
) -> JudgmentResult:
    """コマンド評価のみから JudgmentResult を構築する（FR-010）。

    Args:
        command_evaluations: コマンド条件の評価結果。

    Returns:
        コマンド結果のみの JudgmentResult。
    """
    all_met = all(e.is_met for e in command_evaluations)
    if all_met:
        overall_reason = "すべてのコマンド条件が満たされました"
    else:
        not_met = [e.criterion for e in command_evaluations if not e.is_met]
        overall_reason = f"未達成のコマンド条件: {', '.join(not_met)}"

    return JudgmentResult(
        is_complete=all_met,
        evaluations=command_evaluations,
        overall_reason=overall_reason,
        suggested_next_action=None
        if all_met
        else "未達成のコマンド条件を確認してください",
    )


def has_semantic_criteria(criteria: Sequence[CriterionInput]) -> bool:
    """条件リストにセマンティック条件が含まれるか判定する。"""
    return any(isinstance(c, str) for c in criteria)


async def run_judgment_phase(
    *,
    criteria: Sequence[CriterionInput],
    task: str,
    summary: ExecutionSummary,
    cwd: str,
    default_timeout: float,
    judgment_agent_run: JudgmentAgentRun | None = None,
    custom_prompt: str | None = None,
) -> JudgmentResult:
    """判定フェーズを実行する。

    コマンド条件の実行、セマンティック条件のLLM判定、結果マージを行う。

    Args:
        criteria: 全条件リスト。
        task: タスクの説明。
        summary: 実行サマリ。
        cwd: コマンド実行の作業ディレクトリ。
        default_timeout: デフォルトタイムアウト（秒）。
        judgment_agent_run: 判定エージェントの run メソッド（JudgmentContext -> JudgmentResult）。
        custom_prompt: 判定エージェントのカスタムプロンプト。

    Returns:
        全評価をマージした JudgmentResult。
    """
    # Step 1: コマンド条件の実行
    command_evaluations, command_criterion_results = await run_command_criteria(
        criteria, cwd=cwd, default_timeout=default_timeout
    )

    # Step 2a: コマンドのみ → LLM スキップ
    if not has_semantic_criteria(criteria):
        return build_judgment_result_from_commands(command_evaluations)

    # Step 2b: セマンティック条件あり → LLM 判定
    if judgment_agent_run is None:
        raise RuntimeError("Judgment agent not configured")

    semantic_criteria = [c for c in criteria if isinstance(c, str)]
    judgment_context = JudgmentContext(
        task=task,
        criteria=semantic_criteria,
        execution_summary=summary,
        command_results=command_criterion_results
        if command_criterion_results
        else None,
        custom_prompt=custom_prompt,
    )

    semantic_judgment: JudgmentResult = await judgment_agent_run(judgment_context)

    # Step 3: マージ
    if not command_evaluations:
        return semantic_judgment

    merged_evaluations = command_evaluations + semantic_judgment.evaluations
    all_met = all(e.is_met for e in merged_evaluations)

    # suggested_next_action の決定 (#53)
    suggested_next_action: str | None = None
    if not all_met:
        suggested_next_action = semantic_judgment.suggested_next_action
        if not suggested_next_action:
            failed_commands = [e for e in command_evaluations if not e.is_met]
            if failed_commands:
                descriptions = [f"- {e.criterion}" for e in failed_commands]
                suggested_next_action = (
                    "以下のコマンド条件が未達成です。根本的に異なるアプローチを検討してください:\n"
                    + "\n".join(descriptions)
                )

    return JudgmentResult(
        is_complete=all_met,
        evaluations=merged_evaluations,
        overall_reason=semantic_judgment.overall_reason,
        suggested_next_action=suggested_next_action,
    )


__all__ = [
    "build_judgment_result_from_commands",
    "has_semantic_criteria",
    "run_command_criteria",
    "run_judgment_phase",
]
