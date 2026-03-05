"""Contract: Engine judgment phase flow for structured criteria.

This contract defines the judgment phase flow extension in the Engine.
It serves as a reference for implementation - not executable code.

NOTE: Type annotations use string literals because this contract file
cannot import from the actual source modules (specs/ is outside the
package). The actual types are documented in module-level comments below.

Types referenced (from other modules):
- CriterionInput: str | CommandCriterion (models/criteria.py)
- CriteriaEvaluation: (models/results.py)
- CommandCriterionResult: (agents/__init__.py)
- JudgmentResult: (models/results.py)
- TaskInput: (models/task.py)
- ExecutionSummary: (models/summary.py)
"""

from __future__ import annotations


class Engine:
    """Engine の判定フェーズ拡張の擬似コード。"""

    async def _run_command_criteria(
        self,
        criteria: list[str | CommandCriterion],
        cwd: str,
        default_timeout: float,
    ) -> tuple[list[CriteriaEvaluation], list[CommandCriterionResult]]:
        """コマンド条件を順次実行し、評価結果を返す。

        Args:
            criteria: 全条件リスト（意味的 + コマンド）
            cwd: 作業ディレクトリ（FR-014）
            default_timeout: デフォルトタイムアウト（秒）

        Returns:
            tuple:
                - command_evaluations: コマンド条件の CriteriaEvaluation リスト
                - command_criterion_results: JudgmentContext に渡す結果リスト

        Raises:
            CommandExecutionError: 実行エラー時（FR-009: ループ停止）

        Flow:
            1. criteria を走査
            2. CommandCriterion のみ抽出
            3. 定義順に順次実行（FR-005, 並列実行なし）
            4. 最初の実行エラーで停止（FR-009）
            5. 各コマンドの結果を CriteriaEvaluation に変換
        """
        ...

    async def _build_judgment_result_from_commands(
        self,
        command_evaluations: list[CriteriaEvaluation],
    ) -> JudgmentResult:
        """コマンド条件のみの場合に JudgmentResult を構築。

        FR-010: コマンド条件のみのタスクでは LLM 判定を省略。

        Returns:
            JudgmentResult: コマンド結果のみで構築された判定結果
        """
        ...

    async def _judgment_phase(
        self,
        task_input: TaskInput,
        summary: ExecutionSummary,
        iteration: int,
    ) -> JudgmentResult:
        """判定フェーズ（拡張版）。

        Flow:
            1. コマンド条件を実行 (_run_command_criteria)
            2. 意味的条件の有無を判定
               a. 意味的条件なし → _build_judgment_result_from_commands
               b. 意味的条件あり → JudgmentAgent.run() with command_results
            3. コマンド評価 + 意味的評価を統合して JudgmentResult を返す
        """
        ...
