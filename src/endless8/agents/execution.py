"""Execution Agent implementation for endless8.

The Execution Agent is responsible for:
- Executing tasks with fresh context each iteration
- Using history to avoid past failures
- Reporting semantic metadata
"""

from pydantic_ai import Agent

from endless8.agents import ExecutionContext
from endless8.agents.model_factory import create_agent_model
from endless8.models import ExecutionResult

EXECUTION_SYSTEM_PROMPT = """あなたはタスク実行エージェントです。

与えられたタスクを完了条件を満たすように実行してください。

## 入力情報
- タスク: 実行すべきタスクの説明
- 完了条件: 満たすべき条件のリスト
- 履歴コンテキスト: 過去のイテレーションの概要
- ナレッジ: 関連するプロジェクトの知見

## 実行のガイドライン
1. 履歴を確認し、過去の失敗を繰り返さない
2. 一度に多くのことをしすぎず、段階的に進める
3. 各ステップで進捗を確認する
4. エラーが発生した場合は、原因を分析してから対処する

## 出力形式
実行結果を以下の形式で報告してください：
- status: "success" | "failure" | "error"
- output: 実行結果の説明
- artifacts: 生成・変更したファイルのリスト
- semantic_metadata (オプション):
  - approach: 採用したアプローチ
  - strategy_tags: 戦略タグのリスト
  - discoveries: 発見事項のリスト
"""


class ExecutionAgent:
    """Execution Agent for running tasks with claudecode-model."""

    def __init__(
        self,
        append_system_prompt: str | None = None,
        model_name: str = "anthropic:claude-sonnet-4-5",
        allowed_tools: list[str] | None = None,
        timeout: float = 300.0,
    ) -> None:
        """Initialize the execution agent.

        Args:
            append_system_prompt: Additional system prompt to append.
            model_name: Name of the model to use for the agent.
            allowed_tools: List of allowed tool names for the agent.
            timeout: Timeout in seconds for SDK queries.
        """
        self._append_system_prompt = append_system_prompt
        self._model_name = model_name
        self._allowed_tools = allowed_tools
        self._timeout = timeout

    def _build_prompt(self, context: ExecutionContext) -> str:
        """Build the execution prompt from context.

        Args:
            context: Execution context.

        Returns:
            Formatted prompt string.
        """
        prompt = f"""## タスク
{context.task}

## 完了条件
{chr(10).join(f"- {c}" for c in context.criteria)}

## イテレーション
{context.iteration}

## 履歴コンテキスト
{context.history_context}

## 関連するナレッジ
{context.knowledge_context}
"""
        return prompt

    async def run(self, context: ExecutionContext) -> ExecutionResult:
        """Execute the task.

        Args:
            context: Execution context with task, criteria, and history.

        Returns:
            ExecutionResult with status, output, and artifacts.
        """
        system_prompt = EXECUTION_SYSTEM_PROMPT
        if self._append_system_prompt:
            system_prompt += f"\n\n{self._append_system_prompt}"

        model = create_agent_model(
            self._model_name,
            max_turns=50,
            allowed_tools=self._allowed_tools,
            timeout=self._timeout,
        )

        agent: Agent[None, ExecutionResult] = Agent(
            model,
            output_type=ExecutionResult,
            system_prompt=system_prompt,
        )

        prompt = self._build_prompt(context)
        result = await agent.run(prompt)

        return result.output


__all__ = ["ExecutionAgent"]
