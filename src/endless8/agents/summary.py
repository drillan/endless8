"""Summary Agent implementation for endless8.

The Summary Agent is responsible for:
- Compressing execution results into summaries
- Extracting metadata from stream-json logs
- Integrating semantic metadata
- Extracting knowledge from executions
"""

import json
from datetime import UTC, datetime

from endless8.models import (
    ExecutionResult,
    ExecutionSummary,
    Knowledge,
    KnowledgeConfidence,
    KnowledgeType,
    NextAction,
    SummaryMetadata,
)

SUMMARY_SYSTEM_PROMPT = """あなたはサマリエージェントです。

実行エージェントの結果を分析し、以下を行ってください：
1. 実行結果を簡潔にサマリ化
2. 次のイテレーションに役立つ情報を抽出
3. プロジェクトに永続化すべきナレッジを特定

## 出力形式
サマリとナレッジを以下の形式で報告してください：

### サマリ
- approach: 採用したアプローチ（1行）
- result: "success" | "failure" | "error"
- reason: 結果の理由（1-2文）
- artifacts: 生成・変更したファイルのリスト
- next: 次のアクション情報（未完了の場合）

### ナレッジ（該当する場合のみ）
- type: "discovery" | "lesson" | "pattern" | "constraint" | "codebase"
- category: カテゴリ（例: error_handling, testing）
- content: ナレッジの内容
- confidence: "high" | "medium" | "low"
"""


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
        except json.JSONDecodeError:
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
        except json.JSONDecodeError:
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
        except json.JSONDecodeError:
            continue
    return total_tokens


class SummaryAgent:
    """Summary Agent for compressing execution results."""

    def __init__(self, task_description: str = "") -> None:
        """Initialize the summary agent.

        Args:
            task_description: Description of the current task for knowledge extraction.
        """
        self._task_description = task_description

    async def run(
        self,
        execution_result: ExecutionResult,
        iteration: int,
        raw_log_content: str | None = None,
    ) -> tuple[ExecutionSummary, list[Knowledge]]:
        """Summarize execution result and extract knowledge.

        Args:
            execution_result: Result from execution agent.
            iteration: Current iteration number.
            raw_log_content: Optional raw stream-json log.

        Returns:
            Tuple of (ExecutionSummary, list of extracted Knowledge).
        """
        # Build metadata from execution result and raw log
        metadata = SummaryMetadata()

        if raw_log_content:
            metadata.tools_used = _parse_tools_from_log(raw_log_content)
            metadata.files_modified = _parse_files_from_log(raw_log_content)
            metadata.tokens_used = _parse_tokens_from_log(raw_log_content)

        # Merge with semantic metadata if available
        if execution_result.semantic_metadata:
            metadata.strategy_tags = execution_result.semantic_metadata.strategy_tags

        # If we don't have files from log, use artifacts
        if not metadata.files_modified and execution_result.artifacts:
            metadata.files_modified = execution_result.artifacts

        # Build approach from semantic metadata or generate
        approach = ""
        if execution_result.semantic_metadata:
            approach = execution_result.semantic_metadata.approach
        else:
            # Generate a simple approach based on status
            if execution_result.status.value == "success":
                approach = "タスク実行完了"
            elif execution_result.status.value == "failure":
                approach = "タスク実行失敗"
            else:
                approach = "タスク実行エラー"

        # Build next action for non-complete results
        next_action: NextAction | None = None
        if execution_result.status.value != "success":
            next_action = NextAction(
                suggested_action="前回の失敗を分析して再試行",
                blockers=[],
                partial_progress=None,
                pending_items=[],
            )

        # Create summary
        summary = ExecutionSummary(
            iteration=iteration,
            approach=approach,
            result=execution_result.status,
            reason=execution_result.output[:200] if execution_result.output else "",
            artifacts=execution_result.artifacts,
            metadata=metadata,
            next=next_action,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # Extract knowledge from discoveries
        knowledge_list: list[Knowledge] = []
        if execution_result.semantic_metadata:
            for discovery in execution_result.semantic_metadata.discoveries:
                knowledge = Knowledge(
                    type=KnowledgeType.DISCOVERY,
                    category="execution",
                    content=discovery,
                    source_task=self._task_description or "unknown",
                    confidence=KnowledgeConfidence.MEDIUM,
                )
                knowledge_list.append(knowledge)

        # Extract lessons from failures
        if execution_result.status.value == "failure":
            lesson = Knowledge(
                type=KnowledgeType.LESSON,
                category="error_handling",
                content=f"失敗: {execution_result.output[:100]}",
                source_task=self._task_description or "unknown",
                confidence=KnowledgeConfidence.LOW,
            )
            knowledge_list.append(lesson)

        return summary, knowledge_list


__all__ = ["SummaryAgent"]
