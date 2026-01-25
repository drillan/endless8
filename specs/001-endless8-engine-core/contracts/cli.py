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
#   e8 run --resume [TASK_ID]
#   e8 list
#   e8 status [--project PATH]
#
# run Options:
#   --criteria, -c TEXT        完了条件（複数指定可）
#   --config PATH              YAML 設定ファイル
#   --project PATH             プロジェクトディレクトリ（デフォルト: カレント）
#   --max-iterations INTEGER   最大イテレーション数（YAML設定より優先）
#   --resume [TASK_ID]         タスクを再開（IDなしで最新タスク）
#   --help                     ヘルプを表示
#
# Examples:
#   e8 run "テストカバレッジを90%以上にする" --criteria "pytest --cov で90%以上"
#   e8 run "認証機能を実装" -c "ログインできる" -c "ログアウトできる"
#   e8 run --config task.yaml
#   e8 run "タスク" --project /path/to/project --criteria "条件"
#   e8 run "タスク" --max-iterations 20 --criteria "条件"
#   e8 run --resume                    # 最新タスクを再開
#   e8 run --resume 2026-01-23T13-30-00  # 特定タスクを再開
#   e8 list                            # タスク一覧を表示

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
    max_iterations: Annotated[int | None, "最大イテレーション数"] = None,
    resume: Annotated[str | bool | None, "再開するタスクID、またはTrue（最新タスク）"] = None,
) -> None:
    """タスクを実行する

    Args:
        task: タスクの説明（config または resume 指定時は省略可）
        criteria: 完了条件のリスト（config または resume 指定時は省略可）
        config: YAML 設定ファイルのパス
        project: プロジェクトディレクトリ
        max_iterations: 最大イテレーション数（YAML設定より優先）
        resume: 再開するタスクID（str）、または True で最新タスクを再開。
                CLI では `--resume` のみで True、`--resume <task-id>` で特定タスク指定。

    Behavior:
        1. project ディレクトリの存在確認
           - 存在しない場合: エラーを表示して終了
        2. .e8/ ディレクトリの確認
           - 存在しない場合: 自動作成
        3. resume 指定時:
           - IDなし: .e8/tasks/ から最新タスクを取得
           - ID指定: 指定タスクの設定を読み込み
        4. 新規タスク時:
           - タスクIDを生成（タイムスタンプ形式）
           - .e8/tasks/<task-id>/ ディレクトリを作成
        5. 設定の読み込み
           - config 指定時: YAML から読み込み
           - config 未指定時: コマンドライン引数から構築
           - max_iterations は CLI 引数が YAML 設定より優先
        6. Engine インスタンス作成
        7. タスク実行（進捗コールバック付き）
        8. 結果表示（ステータス + 判定理由 + 成果物）

    Exit Codes:
        0: 完了条件達成
        1: 最大イテレーション到達（未完了）
        2: エラー終了
        3: キャンセル
    """
    ...


def list_tasks(
    project: Annotated[Path, "プロジェクトディレクトリ"] = Path.cwd(),
) -> None:
    """タスク一覧を表示する

    Args:
        project: プロジェクトディレクトリ

    Behavior:
        1. .e8/tasks/ ディレクトリを走査
        2. 各タスクの情報を表示:
           - タスクID（タイムスタンプ）
           - ステータス（completed/in_progress/failed）
           - イテレーション数
           - 最終更新日時

    Output Format:
        TASK_ID              STATUS      ITERATIONS  LAST_UPDATED
        2026-01-23T13-30-00  completed   3           2026-01-23 13:45:00
        2026-01-23T10-00-00  in_progress 5           2026-01-23 10:30:00

    Exit Codes:
        0: 成功
        1: .e8/ ディレクトリが存在しない
    """
    ...


def status(
    project: Annotated[Path, "プロジェクトディレクトリ"] = Path.cwd(),
) -> None:
    """現在の実行状態を表示する

    Args:
        project: プロジェクトディレクトリ

    Behavior:
        1. .e8/ ディレクトリの存在確認
        2. タスク数、ナレッジエントリ数を表示
        3. 最新タスクの情報を表示

    Exit Codes:
        0: 成功
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
# history_context_size: 5
# knowledge_context_size: 10
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
# Task Directory Structure
# =====================
#
# .e8/
# └── tasks/
#     └── <task-id>/
#         ├── history.jsonl        # タスクの履歴
#         ├── knowledge.jsonl      # タスクのナレッジ
#         └── logs/                # オプション: 生ログ


# =====================
# Output Format
# =====================
#
# 実行中（進捗コールバックによる表示）:
#   タスク開始: 2026-01-23T13-30-00
#
#   [Iteration 1] 開始...
#   [Iteration 1] 受付完了: タスク受理
#   [Iteration 1] 実行完了: テストを追加
#   [Iteration 1] 判定完了: 未完了
#
#   [Iteration 2] 開始...
#   ...
#
# 完了時（ステータス + 判定理由 + 成果物）:
#   ✓ タスク完了（3 イテレーション）
#   タスクID: 2026-01-23T13-30-00
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
#   タスクID: 2026-01-23T13-30-00
#
#   === 判定結果 ===
#   条件1: ✗ pytest --cov で90%以上
#     根拠: 現在のカバレッジは85%
#
#   === 次のアクション ===
#   edge case のテストを追加してカバレッジを向上させる
#
#   再開するには: e8 run --resume 2026-01-23T13-30-00
#
# エラー時:
#   ✗ エラーが発生しました
#   タスクID: 2026-01-23T13-30-00
#   エラー: [エラーメッセージ]
#
#   再開するには: e8 run --resume 2026-01-23T13-30-00
#
# タスク一覧 (e8 list):
#   endless8 タスク一覧
#
#   TASK_ID              STATUS      ITERATIONS  LAST_UPDATED
#   2026-01-23T13-30-00  completed   3           2026-01-23 13:45:00
#   2026-01-23T10-00-00  in_progress 5           2026-01-23 10:30:00
#
#   合計: 2 タスク
