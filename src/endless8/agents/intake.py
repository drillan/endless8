"""Intake Agent implementation for endless8.

The Intake Agent is responsible for:
- Validating task and criteria clarity
- Generating clarification questions for ambiguous criteria
- Refining criteria based on user answers
"""

from pydantic_ai import Agent

from endless8.agents.model_factory import create_agent_model
from endless8.models import IntakeResult

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

## ツール提案ガイドライン

**基本的に最小限のツールのみ提案してください。**

タスク実行に不可欠なツールだけを suggested_tools に含めてください。
以下の場合はツールを提案しないでください：

- 文章作成・創作タスク（俳句、翻訳、要約など）→ ツール不要または Write のみ
- タスクの判定基準に参照情報の確認が含まれていても、実行エージェントの知識で対応できる範囲は許容

実行エージェントが判断できる範囲は許容してください。
「あると便利」程度のツールは提案しないでください。

利用可能なツール:
- Read: ファイル読み取り
- Edit: ファイル編集
- Write: ファイル作成
- Bash: コマンド実行
- WebSearch: Web検索
- WebFetch: URL取得
- Glob: ファイルパターン検索
- Grep: 内容検索

提案の目安:
- コード変更タスク → ["Read", "Edit", "Write", "Bash"]
- Web調査タスク → ["WebSearch", "WebFetch", "Read", "Write"]
- コード分析タスク → ["Read", "Glob", "Grep"]
- テスト実行タスク → ["Read", "Edit", "Bash"]

## 出力形式

status: "accepted" | "needs_clarification" | "rejected"
task: 受け付けたタスク
criteria: 完了条件リスト（明確化された場合は更新）
clarification_questions: 明確化が必要な場合の質問リスト
rejection_reason: 却下理由（却下の場合のみ）
suggested_tools: タスク実行に推奨されるツールのリスト
"""


class IntakeAgent:
    """Intake Agent for validating task and criteria."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-5",
        timeout: float = 300.0,
        max_turns: int = 10,
    ) -> None:
        """Initialize the intake agent.

        Args:
            model_name: Name of the model to use for the agent.
            timeout: Timeout in seconds for SDK queries.
            max_turns: Maximum number of turns for the agent.
        """
        if max_turns < 1:
            raise ValueError(f"max_turns must be >= 1, got {max_turns}")
        self._model_name = model_name
        self._timeout = timeout
        self._max_turns = max_turns

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
        model = create_agent_model(
            self._model_name,
            max_turns=self._max_turns,
            allowed_tools=[],  # No tools - pure text/JSON output only
            timeout=self._timeout,
        )

        agent: Agent[None, IntakeResult] = Agent(
            model,
            output_type=IntakeResult,
            system_prompt=DEFAULT_INTAKE_PROMPT,
        )

        prompt = self._build_prompt(task, criteria, clarification_answers)
        result = await agent.run(prompt)

        return result.output


__all__ = ["IntakeAgent"]
