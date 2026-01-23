"""History class for managing execution summaries.

Provides JSONL-based storage and retrieval of execution summaries,
with DuckDB-powered queries for efficient context generation.
"""

import json
from pathlib import Path

from endless8.models import ExecutionStatus, ExecutionSummary, SummaryMetadata


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
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
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

        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

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


__all__ = ["History"]
