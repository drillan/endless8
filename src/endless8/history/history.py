"""History class for managing execution summaries.

Provides JSONL-based storage and retrieval of execution summaries,
with DuckDB-powered queries for efficient context generation.
"""

import json
import logging
from pathlib import Path

from endless8.models import (
    ExecutionStatus,
    ExecutionSummary,
    JudgmentResult,
    LoopResult,
    SummaryMetadata,
)

logger = logging.getLogger(__name__)


class History:
    """Manages execution history stored in JSONL format.

    Provides:
    - Append-only storage of execution summaries
    - Efficient retrieval of recent summaries
    - Query for failures
    - Context string generation for execution agent
    """

    def __init__(self, history_path: str | Path) -> None:
        """Initialize history manager.

        Args:
            history_path: Path to history.jsonl file.
        """
        self._path = Path(history_path)
        self._summaries: list[ExecutionSummary] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing summaries from file."""
        if not self._path.exists():
            return

        with self._path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Invalid JSON line skipped at %s:%d: %s",
                        self._path,
                        line_num,
                        e,
                    )
                    continue
                # Only load summary records
                if data.get("type") == "summary":
                    summary = ExecutionSummary(
                        iteration=data["iteration"],
                        approach=data["approach"],
                        result=ExecutionStatus(data["result"]),
                        reason=data["reason"],
                        artifacts=data.get("artifacts", []),
                        metadata=SummaryMetadata(
                            tools_used=data.get("metadata", {}).get("tools_used", []),
                            files_modified=data.get("metadata", {}).get(
                                "files_modified", []
                            ),
                            tokens_used=data.get("metadata", {}).get("tokens_used"),
                            strategy_tags=data.get("metadata", {}).get(
                                "strategy_tags", []
                            ),
                        ),
                        timestamp=data.get("timestamp", ""),
                    )
                    self._summaries.append(summary)

    def _ensure_directory(self) -> None:
        """Ensure the parent directory exists."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def append(self, summary: ExecutionSummary) -> None:
        """Append a summary to history.

        Args:
            summary: Execution summary to append.
        """
        self._summaries.append(summary)
        self._ensure_directory()

        # Write to JSONL file
        record = {
            "type": "summary",
            "iteration": summary.iteration,
            "approach": summary.approach,
            "result": summary.result.value,
            "reason": summary.reason,
            "artifacts": summary.artifacts,
            "metadata": {
                "tools_used": summary.metadata.tools_used,
                "files_modified": summary.metadata.files_modified,
                "tokens_used": summary.metadata.tokens_used,
                "strategy_tags": summary.metadata.strategy_tags,
            },
            "timestamp": summary.timestamp,
        }

        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Failed to write to history file %s: %s", self._path, e)
            raise

    async def get_recent(self, limit: int = 5) -> list[ExecutionSummary]:
        """Get recent execution summaries.

        Args:
            limit: Maximum number of summaries to return.

        Returns:
            List of recent summaries, ordered by iteration ascending.
        """
        if not self._summaries:
            return []

        # Get last N summaries
        start_idx = max(0, len(self._summaries) - limit)
        return self._summaries[start_idx:]

    async def get_failures(
        self, limit: int = 5, exclude_iterations: list[int] | None = None
    ) -> list[ExecutionSummary]:
        """Get failure summaries.

        Args:
            limit: Maximum number of failures to return.
            exclude_iterations: Iterations to exclude.

        Returns:
            List of failed summaries.
        """
        exclude = set(exclude_iterations or [])
        failures = [
            s
            for s in self._summaries
            if s.result == ExecutionStatus.FAILURE and s.iteration not in exclude
        ]
        return failures[-limit:]

    async def get_context_string(self, limit: int = 5) -> str:
        """Generate context string for execution agent.

        Args:
            limit: Maximum number of summaries to include.

        Returns:
            Formatted context string.
        """
        summaries = await self.get_recent(limit)
        if not summaries:
            return "履歴なし"

        lines = []
        for s in summaries:
            lines.append(
                f"[Iteration {s.iteration}] {s.approach} -> {s.result.value}: {s.reason}"
            )
        return "\n".join(lines)

    async def count(self) -> int:
        """Count total iterations.

        Returns:
            Number of summaries.
        """
        return len(self._summaries)

    async def get_last_iteration(self) -> int:
        """Get the last iteration number.

        Returns:
            Last iteration number (0 if empty).
        """
        if not self._summaries:
            return 0
        return self._summaries[-1].iteration

    async def append_judgment(self, judgment: JudgmentResult, iteration: int) -> None:
        """Append a judgment result to history.

        Args:
            judgment: The judgment result to append.
            iteration: The iteration number when this judgment was made.
        """
        self._ensure_directory()

        # Serialize evaluations
        evaluations = [
            {
                "criterion": e.criterion,
                "is_met": e.is_met,
                "evidence": e.evidence,
                "confidence": e.confidence,
            }
            for e in judgment.evaluations
        ]

        record = {
            "type": "judgment",
            "iteration": iteration,
            "is_complete": judgment.is_complete,
            "evaluations": evaluations,
            "overall_reason": judgment.overall_reason,
            "suggested_next_action": judgment.suggested_next_action,
        }

        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error(
                "Failed to write judgment to history file %s: %s", self._path, e
            )
            raise

    async def append_final_result(self, result: LoopResult) -> None:
        """Append a final result to history.

        Args:
            result: The loop result to append.
        """
        self._ensure_directory()

        # Serialize final judgment if present
        final_judgment_data = None
        if result.final_judgment:
            evaluations = [
                {
                    "criterion": e.criterion,
                    "is_met": e.is_met,
                    "evidence": e.evidence,
                    "confidence": e.confidence,
                }
                for e in result.final_judgment.evaluations
            ]
            final_judgment_data = {
                "is_complete": result.final_judgment.is_complete,
                "evaluations": evaluations,
                "overall_reason": result.final_judgment.overall_reason,
                "suggested_next_action": result.final_judgment.suggested_next_action,
            }

        record = {
            "type": "final_result",
            "status": result.status.value,
            "iterations_used": result.iterations_used,
            "final_judgment": final_judgment_data,
            "history_path": result.history_path,
            "error_message": result.error_message,
        }

        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error(
                "Failed to write final result to history file %s: %s", self._path, e
            )
            raise


__all__ = ["History"]
