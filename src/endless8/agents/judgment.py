"""Judgment Agent implementation for endless8.

The Judgment Agent is responsible for:
- Evaluating each completion criterion individually
- Explaining the reasoning for each evaluation
- Suggesting next actions when not complete
"""

from pydantic_ai import Agent

from endless8.agents import JudgmentContext
from endless8.agents.model_factory import create_agent_model
from endless8.models import JudgmentResult

DEFAULT_JUDGMENT_PROMPT = """あなたは判定エージェントです。

タスクの完了条件が満たされているかを評価してください。

## 評価のガイドライン
1. 各完了条件を個別に評価する
2. 判定の根拠を具体的に説明する
3. 確信度（0.0-1.0）を設定する
4. 未完了の場合は次のアクションを提案する

## 重要
- 曖昧な場合は厳しく判定する
- 部分的な達成は完了とみなさない
- 明確な証拠がある場合のみ完了とする

## 出力形式
各条件について以下を報告：
- criterion: 評価対象の条件
- is_met: true/false
- evidence: 判定の根拠（具体的に）
- confidence: 確信度（0.0-1.0）

全体の判定：
- is_complete: すべての条件が満たされているか
- overall_reason: 総合的な判定理由
- suggested_next_action: 未完了時の次のアクション
"""


class JudgmentAgent:
    """Judgment Agent for evaluating completion criteria."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-5") -> None:
        """Initialize the judgment agent.

        Args:
            model_name: Name of the model to use for the agent.
        """
        self._model_name = model_name
        self._agent: Agent[None, JudgmentResult] | None = None

    def _build_prompt(self, context: JudgmentContext) -> str:
        """Build the judgment prompt from context.

        Args:
            context: Judgment context.

        Returns:
            Formatted prompt string.
        """
        criteria_text = "\n".join(f"- {c}" for c in context.criteria)
        summary = context.execution_summary

        prompt = f"""## タスク
{context.task}

## 完了条件
{criteria_text}

## 実行結果
- イテレーション: {summary.iteration}
- アプローチ: {summary.approach}
- 結果: {summary.result.value}
- 理由: {summary.reason}
- 成果物: {", ".join(summary.artifacts) if summary.artifacts else "なし"}

## 使用ツール
{", ".join(summary.metadata.tools_used) if summary.metadata.tools_used else "なし"}

## 変更ファイル
{", ".join(summary.metadata.files_modified) if summary.metadata.files_modified else "なし"}
"""
        return prompt

    async def run(self, context: JudgmentContext) -> JudgmentResult:
        """Evaluate completion criteria.

        Args:
            context: Judgment context with task, criteria, and execution summary.

        Returns:
            JudgmentResult with evaluations and overall judgment.
        """
        # Use custom prompt if provided
        system_prompt = context.custom_prompt or DEFAULT_JUDGMENT_PROMPT

        model = create_agent_model(self._model_name, max_turns=10)

        agent: Agent[None, JudgmentResult] = Agent(
            model,
            output_type=JudgmentResult,
            system_prompt=system_prompt,
        )

        prompt = self._build_prompt(context)
        result = await agent.run(prompt)
        return result.output


__all__ = ["JudgmentAgent"]
