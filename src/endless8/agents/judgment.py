"""Judgment Agent implementation for endless8.

The Judgment Agent is responsible for:
- Evaluating each completion criterion individually
- Explaining the reasoning for each evaluation
- Suggesting next actions when not complete
"""

import asyncio
import logging

from pydantic_ai import Agent

from endless8.agents import JudgmentContext
from endless8.agents.model_factory import create_agent_model
from endless8.models import JudgmentResult

logger = logging.getLogger(__name__)

# Retry configuration for CLI errors
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0  # seconds

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

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-5",
        timeout: float = 300.0,
        max_turns: int = 10,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        """Initialize the judgment agent.

        Args:
            model_name: Name of the model to use for the agent.
            timeout: Timeout in seconds for SDK queries.
            max_turns: Maximum number of turns for the agent.
            max_retries: Maximum number of retries on CLI errors.
            retry_delay: Delay in seconds between retries.
        """
        if max_turns < 1:
            raise ValueError(f"max_turns must be >= 1, got {max_turns}")
        self._model_name = model_name
        self._timeout = timeout
        self._max_turns = max_turns
        self._max_retries = max_retries
        self._retry_delay = retry_delay
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

        Raises:
            Exception: If all retries fail.
        """
        # Use custom prompt if provided
        system_prompt = context.custom_prompt or DEFAULT_JUDGMENT_PROMPT
        prompt = self._build_prompt(context)

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                # Create fresh model instance for each attempt
                model = create_agent_model(
                    self._model_name,
                    max_turns=self._max_turns,
                    allowed_tools=[],  # No tools - pure text/JSON output only
                    timeout=self._timeout,
                )

                agent: Agent[None, JudgmentResult] = Agent(
                    model,
                    output_type=JudgmentResult,
                    system_prompt=system_prompt,
                )

                result = await agent.run(prompt)
                return result.output

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Check if this is a retriable CLI error
                if (
                    "Command failed with exit code" in error_msg
                    or "message reader" in error_msg.lower()
                ):
                    remaining = self._max_retries - attempt - 1
                    if remaining > 0:
                        logger.warning(
                            "JudgmentAgent CLI error (attempt %d/%d), retrying in %.1fs: %s",
                            attempt + 1,
                            self._max_retries,
                            self._retry_delay,
                            error_msg[:200],
                        )
                        await asyncio.sleep(self._retry_delay)
                        continue
                    else:
                        logger.error(
                            "JudgmentAgent CLI error (attempt %d/%d), no more retries: %s",
                            attempt + 1,
                            self._max_retries,
                            error_msg[:200],
                        )
                else:
                    # Non-retriable error, raise immediately
                    raise

        # All retries exhausted
        if last_error is not None:
            raise last_error
        raise RuntimeError("JudgmentAgent failed with no error captured")


__all__ = ["JudgmentAgent"]
