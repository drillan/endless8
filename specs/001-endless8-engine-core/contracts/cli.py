"""CLI Contract - e8 コマンドのインターフェース

このファイルは CLI コマンドの公開 API を定義する。
実装時にはこのインターフェースに準拠すること。
"""

# =====================
# CLI Commands
# =====================
#
# コマンド名: e8
#
# Usage:
#   e8 run <task> [OPTIONS]
#   e8 run --config <config.yaml>
#
# Options:
#   --criteria, -c TEXT        完了条件（複数指定可）
#   --config PATH              YAML 設定ファイル
#   --project PATH             プロジェクトディレクトリ（デフォルト: カレント）
#   --persist PATH             履歴ファイルパス
#   --max-iterations INTEGER   最大イテレーション数（YAML設定より優先）
#   --help                     ヘルプを表示
#
# Examples:
#   e8 run "テストカバレッジを90%以上にする" --criteria "pytest --cov で90%以上"
#   e8 run "認証機能を実装" -c "ログインできる" -c "ログアウトできる"
#   e8 run --config task.yaml
#   e8 run "タスク" --project /path/to/project --criteria "条件"
#   e8 run "タスク" --max-iterations 20 --criteria "条件"
#   e8 run "タスク" --persist .e8/history.jsonl --criteria "条件"

from pathlib import Path
from typing import Annotated

# Note: 実装時に typer を使用
# import typer
# from endless8.engine import Engine
# from endless8.config import EngineConfig, load_config


def run(
    task: Annotated[str, "タスクの説明"] = "",
    criteria: Annotated[list[str], "完了条件（複数指定可）"] = [],
    config: Annotated[Path | None, "YAML 設定ファイル"] = None,
    project: Annotated[Path, "プロジェクトディレクトリ"] = Path.cwd(),
    persist: Annotated[Path | None, "履歴ファイルパス"] = None,
    max_iterations: Annotated[int | None, "最大イテレーション数"] = None,
) -> None:
    """タスクを実行する

    Args:
        task: タスクの説明（config 指定時は省略可）
        criteria: 完了条件のリスト（config 指定時は省略可）
        config: YAML 設定ファイルのパス
        project: プロジェクトディレクトリ
        persist: 履歴ファイルのパス
        max_iterations: 最大イテレーション数（YAML設定より優先）

    Behavior:
        1. project ディレクトリの存在確認
           - 存在しない場合: エラーを表示して終了
        2. .e8/ ディレクトリの確認
           - 存在しない場合: 自動作成
        3. 設定の読み込み
           - config 指定時: YAML から読み込み
           - config 未指定時: コマンドライン引数から構築
           - max_iterations は CLI 引数が YAML 設定より優先
        4. Engine インスタンス作成
        5. タスク実行
        6. 結果表示

    Exit Codes:
        0: 完了条件達成
        1: 最大イテレーション到達（未完了）
        2: エラー終了
        3: キャンセル
    """
    ...


# =====================
# YAML Config Schema
# =====================
#
# task.yaml:
#
# task: "タスクの説明"
# criteria:
#   - "完了条件1"
#   - "完了条件2"
#
# # オプション
# max_iterations: 10
# persist: ".e8/history.jsonl"
# knowledge: ".e8/knowledge.jsonl"
# history_context_size: 5
#
# # ログオプション
# logging:
#   raw_log: false
#   raw_log_dir: ".e8/logs"
#
# # claude コマンドオプション
# claude_options:
#   allowed_tools:
#     - "Read"
#     - "Edit"
#     - "Write"
#     - "Bash(git:*)"
#   model: "sonnet"
#   output_format: "stream-json"
#   verbose: true
#
# # プロンプトカスタマイズ
# prompts:
#   judgment: |
#     以下の基準で完了条件を評価してください...
#   append_system_prompt: |
#     各作業の最後に、以下のJSON形式で報告してください...


# =====================
# Output Format
# =====================
#
# 実行中:
#   [Iteration 1] 開始...
#   [Iteration 1] アプローチ: テストを追加
#   [Iteration 1] 結果: success
#   [Iteration 1] 理由: テストファイル作成完了
#
#   [Iteration 2] 開始...
#   ...
#
# 完了時:
#   ✓ タスク完了（3 イテレーション）
#
#   === 判定結果 ===
#   条件1: ✓ pytest --cov で90%以上
#     根拠: カバレッジレポートで92%を確認
#
#   === 成果物 ===
#   - tests/test_main.py
#   - src/main.py
#
# 未完了時（最大イテレーション到達）:
#   ✗ 最大イテレーション数に到達（10回）
#
#   === 判定結果 ===
#   条件1: ✗ pytest --cov で90%以上
#     根拠: 現在のカバレッジは85%
#
#   === 次のアクション ===
#   edge case のテストを追加してカバレッジを向上させる
#
# エラー時:
#   ✗ エラーが発生しました
#   エラー: [エラーメッセージ]
