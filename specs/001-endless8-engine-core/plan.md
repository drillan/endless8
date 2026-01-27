# Implementation Plan: endless8 エンジンコア機能

**Branch**: `001-endless8-engine-core` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-endless8-engine-core/spec.md`

## Summary

endless8 は pydantic-ai と claudecode-model を使用したコンテキスト効率の良いタスク実行ループエンジンである。4エージェント構成（受付、実行、サマリ、判定）によりタスクを自動実行し、完了条件が満たされるまでループ処理を行う。履歴とナレッジをJSONL形式で永続化し、DuckDBでクエリする。

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: pydantic-ai, claudecode-model, DuckDB, typer (CLI), pyyaml
**Storage**: JSONL形式ファイル（.e8/tasks/<task-id>/history.jsonl, .e8/tasks/<task-id>/knowledge.jsonl, .e8/tasks/<task-id>/logs/）
**Testing**: pytest
**Target Platform**: Linux/macOS/Windows (cross-platform CLI)
**Project Type**: Single project
**Performance Goals**: 100,000 tokens以下/イテレーション
**Constraints**: コンテキスト枯渇なしで50+イテレーション
**Scale/Scope**: 単一プロジェクト、単一ユーザー

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Requirement | Status | Notes |
|---------|-------------|--------|-------|
| Article 1: Test-First | TDDを厳守 | ✅ PASS | テスト → 承認 → 実装 の順 |
| Article 2: Documentation Integrity | 仕様との整合性 | ✅ PASS | spec.md に基づいて実装 |
| Article 3: Agent Architecture | 4エージェント構成 | ✅ PASS | 受付/実行/サマリ/判定 |
| Article 4: Simplicity | 最大3プロジェクト | ✅ PASS | 単一プロジェクト |
| Article 5: Code Quality | ruff/mypy必須 | ✅ PASS | コミット前にチェック |
| Article 6: Data Accuracy | ハードコード禁止 | ✅ PASS | 設定ファイル/環境変数 |
| Article 7: DRY Principle | 重複禁止 | ✅ PASS | 既存コード検索必須 |
| Article 9: Type Safety | 型注釈必須 | ✅ PASS | mypy strict モード |
| Article 11: Naming Convention | 命名規則準拠 | ✅ PASS | git-conventions.md 参照 |

## Project Structure

### Documentation (this feature)

```text
specs/001-endless8-engine-core/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── agents.py        # エージェントインターフェース
│   ├── cli.py           # CLIインターフェース
│   ├── engine.py        # エンジンインターフェース
│   └── history.py       # 履歴・ナレッジインターフェース
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/endless8/
├── __init__.py          # パッケージエクスポート
├── engine.py            # メインエンジン（ループ制御、進捗コールバック）
├── agents/
│   ├── __init__.py
│   ├── intake.py        # 受付エージェント
│   ├── execution.py     # 実行エージェント
│   ├── summary.py       # サマリエージェント
│   └── judgment.py      # 判定エージェント
├── cli/
│   ├── __init__.py
│   └── main.py          # CLIエントリポイント（run, list, status, resume）
├── config/
│   ├── __init__.py
│   └── loader.py        # YAML設定読み込み
├── history/
│   ├── __init__.py
│   ├── history.py       # 履歴管理（タスクディレクトリ対応）
│   └── knowledge.py     # ナレッジ管理
└── models/
    ├── __init__.py
    ├── task.py          # TaskInput, IntakeResult
    ├── execution.py     # ExecutionResult, ExecutionSummary
    ├── judgment.py      # JudgmentResult
    ├── knowledge.py     # Knowledge
    └── loop.py          # LoopResult, LoopStatus

tests/
├── conftest.py          # 共通フィクスチャ
├── unit/
│   ├── test_engine.py
│   ├── test_intake_agent.py
│   ├── test_execution_agent.py
│   ├── test_summary_agent.py
│   ├── test_judgment_agent.py
│   ├── test_history.py
│   ├── test_knowledge.py
│   └── test_config.py
├── integration/
│   ├── test_loop_execution.py
│   ├── test_persistence.py
│   └── test_cli.py
└── contract/
    └── test_models.py
```

**Structure Decision**: Single project structure を採用。CLI、エンジン、エージェント、履歴管理を src/endless8/ 配下に配置。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

該当なし（すべてのチェックに合格）

## Phase 0: Research Status

**Status**: Complete

research.md に以下の調査結果を記載済み:

1. pydantic-ai エージェントパターン → Agent クラス + output_type
2. claudecode-model アダプタ → stream-json 出力解析
3. DuckDB JSONL クエリ → read_ndjson_auto
4. CLI フレームワーク → typer
5. 設定管理 → YAML + pydantic

## Phase 1: Design Status

**Status**: Complete

新仕様を反映してすべてのアーティファクトを更新済み:

1. **タスクディレクトリ構造**: `.e8/tasks/<task-id>/`
   - task-id: タイムスタンプ形式（例: `2026-01-23T13-30-00`）
   - 各タスクに history.jsonl と logs/ を配置
   - → data-model.md, quickstart.md, contracts/cli.py, contracts/history.py 更新済み

2. **進捗通知コールバック**: `Engine.run()` に `on_progress` コールバックを渡す
   - ProgressEvent, ProgressEventType モデル定義
   - イテレーション開始/終了時に呼び出し
   - → data-model.md, contracts/engine.py 更新済み

3. **CLI 新コマンド**:
   - `e8 list`: タスク一覧表示
   - `e8 run --resume`: 最新タスク再開
   - `e8 run --resume <task-id>`: 特定タスク再開
   - → contracts/cli.py, quickstart.md 更新済み

4. **CLI 表示改善**: 完了時にステータス + 判定理由 + 成果物リスト
   - → contracts/cli.py 更新済み

## Generated Artifacts

- [research.md](./research.md) - 技術リサーチ結果
- [data-model.md](./data-model.md) - データモデル定義
- [quickstart.md](./quickstart.md) - クイックスタートガイド
- [contracts/](./contracts/) - API コントラクト
