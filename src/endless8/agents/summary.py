"""Summary Agent implementation for endless8.

The Summary Agent is responsible for:
- Compressing execution results into summaries via LLM
- Extracting metadata from stream-json logs (mechanical)
- Integrating semantic metadata
- Extracting knowledge from executions via LLM
"""

import json
import logging
from datetime import UTC, datetime

from pydantic_ai import Agent

from endless8.agents.model_factory import create_agent_model
from endless8.models import (
    ExecutionResult,
    ExecutionSummary,
    Knowledge,
    KnowledgeConfidence,
    KnowledgeType,
    NextAction,
    SummaryMetadata,
)
from endless8.models.summary import SummaryLLMOutput

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """あなたはサマリエージェントです。

実行エージェントの結果を、完了条件に照らして分析し、以下を行ってください：
1. 実行結果を完了条件の観点から簡潔にサマリ化
2. 次のイテレーションに役立つ情報を抽出
3. プロジェクトに永続化すべきナレッジを特定

## 重要な制約
- reason フィールドは **最大1000トークン** に収めてください。簡潔かつ情報量の多い要約を心がけてください。
- 注意: result はシステムが自動設定するため、出力に含める必要はありません。

## 出力形式
構造化された JSON で以下のフィールドを返してください：

- approach: 採用したアプローチ（1行）
- reason: 結果の理由（最大1000トークン。完了条件に対する進捗を含めること）
- artifacts: 生成・変更したファイルのリスト
- next_action: 次のアクション情報（未完了の場合、null可）
- knowledge_entries: 抽出されたナレッジのリスト（該当する場合のみ）
  - type: "discovery" | "lesson" | "pattern" | "constraint" | "codebase"
  - category: カテゴリ（例: error_handling, testing）
  - content: ナレッジの内容
  - confidence: "high" | "medium" | "low"
"""

# Mapping from LLM string confidence to KnowledgeConfidence enum
_CONFIDENCE_MAP: dict[str, KnowledgeConfidence] = {
    "high": KnowledgeConfidence.HIGH,
    "medium": KnowledgeConfidence.MEDIUM,
    "low": KnowledgeConfidence.LOW,
}

# Mapping from LLM string type to KnowledgeType enum
_KNOWLEDGE_TYPE_MAP: dict[str, KnowledgeType] = {
    "discovery": KnowledgeType.DISCOVERY,
    "lesson": KnowledgeType.LESSON,
    "pattern": KnowledgeType.PATTERN,
    "constraint": KnowledgeType.CONSTRAINT,
    "codebase": KnowledgeType.CODEBASE,
}


def _parse_tools_from_log(raw_log: str) -> list[str]:
    """Extract tool names from raw log.

    Args:
        raw_log: Raw stream-json log content.

    Returns:
        List of unique tool names used.
    """
    tools: set[str] = set()
    for line in raw_log.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "tool_use":
                tool_name = data.get("name", "")
                if tool_name:
                    tools.add(tool_name)
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON in log line (skipped): %s - Error: %s",
                line[:100],
                e,
            )
            continue
    return sorted(tools)


def _parse_files_from_log(raw_log: str) -> list[str]:
    """Extract modified files from raw log.

    Args:
        raw_log: Raw stream-json log content.

    Returns:
        List of unique file paths modified.
    """
    files: set[str] = set()
    for line in raw_log.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "tool_use":
                tool_name = data.get("name", "")
                if tool_name in ("Edit", "Write"):
                    tool_input = data.get("input", {})
                    path = tool_input.get("path", "") or tool_input.get("file_path", "")
                    if path:
                        files.add(path)
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON in log line (skipped): %s - Error: %s",
                line[:100],
                e,
            )
            continue
    return sorted(files)


def _parse_tokens_from_log(raw_log: str) -> int:
    """Extract token usage from raw log.

    Args:
        raw_log: Raw stream-json log content.

    Returns:
        Total tokens used.
    """
    total_tokens = 0
    for line in raw_log.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if "usage" in data:
                usage = data["usage"]
                total_tokens += usage.get("input_tokens", 0)
                total_tokens += usage.get("output_tokens", 0)
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON in log line (skipped): %s - Error: %s",
                line[:100],
                e,
            )
            continue
    return total_tokens


def _build_prompt(
    execution_result: ExecutionResult,
    iteration: int,
    criteria: list[str],
) -> str:
    """Build LLM prompt from execution result and criteria.

    Args:
        execution_result: Result from execution agent.
        iteration: Current iteration number.
        criteria: Completion criteria list.

    Returns:
        Formatted prompt string for the LLM.
    """
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    sections = [
        f"## イテレーション {iteration}",
        "",
        "## 完了条件",
        criteria_text,
        "",
        "## 実行結果",
        f"- ステータス: {execution_result.status.value}",
        f"- 出力: {execution_result.output}",
        f"- 成果物: {', '.join(execution_result.artifacts) if execution_result.artifacts else 'なし'}",
    ]

    if execution_result.semantic_metadata:
        sm = execution_result.semantic_metadata
        sections.extend(
            [
                "",
                "## セマンティックメタデータ",
                f"- アプローチ: {sm.approach}",
                f"- 戦略タグ: {', '.join(sm.strategy_tags)}",
                f"- 発見: {', '.join(sm.discoveries) if sm.discoveries else 'なし'}",
            ]
        )

    return "\n".join(sections)


class SummaryAgent:
    """Summary Agent for compressing execution results via LLM."""

    def __init__(
        self,
        task_description: str = "",
        model_name: str = "anthropic:claude-sonnet-4-5",
        timeout: float = 300.0,
    ) -> None:
        """Initialize the summary agent.

        Args:
            task_description: Description of the current task for knowledge extraction.
            model_name: Model name for the pydantic-ai Agent.
            timeout: Timeout for LLM calls in seconds.
        """
        self._task_description = task_description
        self._model_name = model_name
        self._timeout = timeout

    async def run(
        self,
        execution_result: ExecutionResult,
        iteration: int,
        criteria: list[str],
        raw_log_content: str | None = None,
    ) -> tuple[ExecutionSummary, list[Knowledge]]:
        """Summarize execution result and extract knowledge via LLM.

        Args:
            execution_result: Result from execution agent.
            iteration: Current iteration number.
            criteria: Completion criteria list.
            raw_log_content: Optional raw stream-json log.

        Returns:
            Tuple of (ExecutionSummary, list of extracted Knowledge).
        """
        # 1. Mechanical metadata extraction (preserved from original)
        metadata = SummaryMetadata()

        if raw_log_content:
            metadata.tools_used = _parse_tools_from_log(raw_log_content)
            metadata.files_modified = _parse_files_from_log(raw_log_content)
            metadata.tokens_used = _parse_tokens_from_log(raw_log_content)

        if execution_result.semantic_metadata:
            metadata.strategy_tags = execution_result.semantic_metadata.strategy_tags

        if not metadata.files_modified and execution_result.artifacts:
            metadata.files_modified = execution_result.artifacts

        # 2. LLM summarization
        prompt = _build_prompt(execution_result, iteration, criteria)

        model = create_agent_model(
            self._model_name,
            max_turns=10,
            allowed_tools=[],
            timeout=self._timeout,
        )
        agent: Agent[None, SummaryLLMOutput] = Agent(
            model,
            output_type=SummaryLLMOutput,
            system_prompt=SUMMARY_SYSTEM_PROMPT,
        )

        try:
            llm_result = await agent.run(prompt)
            llm_output: SummaryLLMOutput = llm_result.output
        except Exception:
            logger.exception("LLM summarization failed, using fallback summary")
            summary = ExecutionSummary(
                iteration=iteration,
                approach="LLM summarization failed",
                result=execution_result.status,
                reason=execution_result.output[:500],
                artifacts=execution_result.artifacts,
                metadata=metadata,
                next=None,
                timestamp=datetime.now(UTC).isoformat(),
            )
            return summary, []

        # 3. Build next action from LLM output
        next_action: NextAction | None = None
        if llm_output.next_action:
            next_action = NextAction(
                suggested_action=llm_output.next_action,
                blockers=[],
                partial_progress=None,
                pending_items=[],
            )
        elif execution_result.status.value != "success":
            next_action = NextAction(
                suggested_action="前回の失敗を分析して再試行",
                blockers=[],
                partial_progress=None,
                pending_items=[],
            )

        # 4. Build summary — status from ExecutionResult, not LLM
        summary = ExecutionSummary(
            iteration=iteration,
            approach=llm_output.approach,
            result=execution_result.status,
            reason=llm_output.reason,
            artifacts=execution_result.artifacts,
            metadata=metadata,
            next=next_action,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # 5. Convert LLM knowledge entries to Knowledge objects
        knowledge_list: list[Knowledge] = []
        for entry in llm_output.knowledge_entries:
            knowledge_type = _KNOWLEDGE_TYPE_MAP[entry.type]
            confidence = _CONFIDENCE_MAP[entry.confidence]
            knowledge = Knowledge(
                type=knowledge_type,
                category=entry.category,
                content=entry.content,
                source_task=self._task_description or "unknown",
                confidence=confidence,
            )
            knowledge_list.append(knowledge)

        return summary, knowledge_list


__all__ = ["SummaryAgent"]
