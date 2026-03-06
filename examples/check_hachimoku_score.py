"""hachimoku レビュースコアチェッカー.

hachimoku の JSONL レビューファイルを読み取り、
全体スコアが閾値以上かを判定するスタンドアロンスクリプト。

Usage:
    uv run python examples/check_hachimoku_score.py .hachimoku/reviews/pr-35.jsonl
    uv run python examples/check_hachimoku_score.py .hachimoku/reviews/pr-35.jsonl --threshold 7.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 8.0
PASS_EXIT_CODE = 0
FAIL_EXIT_CODE = 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="hachimoku レビュースコアが閾値以上かを判定する",
    )
    parser.add_argument(
        "file_path",
        type=Path,
        help="hachimoku JSONL レビューファイルのパス",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"合格スコアの閾値 (デフォルト: {DEFAULT_THRESHOLD})",
    )
    return parser.parse_args(argv)


def read_last_review(file_path: Path) -> str:
    """JSONL ファイルの最終行（最新レビュー）を返す."""
    lines = [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError(f"JSONL file contains no valid lines: {file_path}")
    return lines[-1]


def extract_agent_scores(
    results: list[dict[str, object]],
) -> list[tuple[str, float]]:
    """成功したエージェントの (agent_name, overall_score) リストを返す."""
    scores: list[tuple[str, float]] = []
    for result in results:
        if result.get("status") != "success":
            continue
        score = result.get("overall_score")
        if isinstance(score, (int, float)):
            scores.append((str(result.get("agent_name", "unknown")), float(score)))
    return scores


def resolve_overall_score(
    summary: dict[str, object],
    agent_scores: list[tuple[str, float]],
) -> float:
    """全体スコアを決定する.

    summary.overall_score が有効ならそれを使用。
    null の場合はエージェントスコアの平均を算出する。
    """
    overall = summary.get("overall_score")
    if isinstance(overall, (int, float)):
        return float(overall)
    if not agent_scores:
        raise ValueError(
            "No valid agent scores found and summary.overall_score is null"
        )
    return sum(s for _, s in agent_scores) / len(agent_scores)


def format_report(
    pr_number: int | None,
    agent_scores: list[tuple[str, float]],
    overall_score: float,
    threshold: float,
    *,
    passed: bool,
) -> str:
    """人間が読みやすいレポート文字列を生成する."""
    lines: list[str] = ["=== hachimoku Review Score Check ==="]

    if pr_number is not None:
        lines.append(f"PR: #{pr_number}")
    lines.append(f"Threshold: {threshold}")
    lines.append("")

    if agent_scores:
        max_name_len = max(len(name) for name, _ in agent_scores)
        lines.append("Agent Scores:")
        for name, score in agent_scores:
            status = "PASS" if score >= threshold else "FAIL"
            lines.append(f"  {name:<{max_name_len}}  {score:.1f}  {status}")
        lines.append("")

    lines.append(f"Overall Score: {overall_score:.1f}")
    if passed:
        lines.append(f"Result: PASS ({overall_score:.1f} >= {threshold})")
    else:
        lines.append(f"Result: FAIL ({overall_score:.1f} < {threshold})")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    file_path: Path = args.file_path
    threshold: float = args.threshold

    raw_line = read_last_review(file_path)
    data: dict[str, object] = json.loads(raw_line)

    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(f"'results' field is missing or not a list in {file_path}")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"'summary' field is missing or not a dict in {file_path}")

    agent_scores = extract_agent_scores(results)
    overall_score = resolve_overall_score(summary, agent_scores)
    passed = overall_score >= threshold

    pr_number_raw = data.get("pr_number")
    pr_number = int(pr_number_raw) if isinstance(pr_number_raw, (int, float)) else None

    report = format_report(
        pr_number=pr_number,
        agent_scores=agent_scores,
        overall_score=overall_score,
        threshold=threshold,
        passed=passed,
    )
    print(report)

    return PASS_EXIT_CODE if passed else FAIL_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
