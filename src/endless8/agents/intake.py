"""Intake Agent implementation for endless8.

The Intake Agent is responsible for:
- Validating task and criteria clarity
- Generating clarification questions for ambiguous criteria
- Refining criteria based on user answers
"""

from pydantic_ai import Agent

from endless8.models import IntakeResult

# Import claudecode-model adapter
try:
    from claudecode_model import ClaudeCodeModel
except ImportError:
    ClaudeCodeModel = None  # type: ignore[assignment, misc]

DEFAULT_INTAKE_PROMPT = """あなたは受付エージェントです。

タスクと完了条件の妥当性を評価してください。

## 最重要原則

**基本的に「accepted」を返してください。**

明確化が必要なのは、完了条件が本当に検証不可能な場合のみです。
以下の場合は必ず「accepted」を返してください：

- 数値や具体的な基準がある（例: 90%以上、5,7,5）
- Yes/No で判定できる（例: ○○が含まれているか）
- コマンドで検証できる（例: pytest がパス、ruff エラーなし）
- 形式が明確（例: JSON形式、俳句形式）

**追加の詳細や品質基準を求めないでください。**
実行エージェントが判断できる範囲は許容してください。

## 明確化が必要な例（稀なケース）

- 「良いものを作る」→ 基準が完全に不明
- 「適切に処理する」→ 何をもって適切か不明

## 出力形式

status: "accepted" | "needs_clarification" | "rejected"
task: 受け付けたタスク
criteria: 完了条件リスト（明確化された場合は更新）
clarification_questions: 明確化が必要な場合の質問リスト
rejection_reason: 却下理由（却下の場合のみ）
"""


class IntakeAgent:
    """Intake Agent for validating task and criteria."""

    def __init__(self) -> None:
        """Initialize the intake agent."""
        pass

    def _build_prompt(
        self,
        task: str,
        criteria: list[str],
        clarification_answers: dict[str, str] | None = None,
    ) -> str:
        """Build the intake prompt.

        Args:
            task: Task description.
            criteria: List of completion criteria.
            clarification_answers: Optional dict of question -> answer for refinement.

        Returns:
            Formatted prompt string.
        """
        criteria_text = "\n".join(f"- {c}" for c in criteria)

        prompt = f"""## タスク
{task}

## 完了条件
{criteria_text}
"""

        if clarification_answers:
            answers_text = "\n".join(
                f"Q: {q}\nA: {a}" for q, a in clarification_answers.items()
            )
            prompt += f"""

## 明確化の回答
{answers_text}

上記の回答を踏まえて、完了条件を具体化してください。
"""

        return prompt

    async def run(
        self,
        task: str,
        criteria: list[str],
        clarification_answers: dict[str, str] | None = None,
    ) -> IntakeResult:
        """Validate task and criteria.

        Args:
            task: Task description.
            criteria: List of completion criteria.
            clarification_answers: Optional answers to clarification questions.

        Returns:
            IntakeResult with validation status and any clarification questions.
        """
        # Use ClaudeCodeModel if available, otherwise use default anthropic model
        if ClaudeCodeModel is not None:
            model = ClaudeCodeModel(max_turns=10)
        else:
            model = "anthropic:claude-sonnet-4-5"

        agent: Agent[None, IntakeResult] = Agent(
            model,
            output_type=IntakeResult,
            system_prompt=DEFAULT_INTAKE_PROMPT,
        )

        prompt = self._build_prompt(task, criteria, clarification_answers)
        result = await agent.run(prompt)

        return result.output


__all__ = ["IntakeAgent"]
