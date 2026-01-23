# Implementation Plan: endless8 エンジンコア機能

**Branch**: `001-endless8-engine-core` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-endless8-engine-core/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

pydantic-ai と claudecode-model を使用したコンテキスト効率の良いタスク実行ループエンジンの実装。4エージェント構成（受付・実行・サマリ・判定）で責務を分離し、履歴のサマリ化とDuckDBによるクエリで長時間タスクでもコンテキスト枯渇を防ぐ。

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: pydantic-ai, claudecode-model, DuckDB, typer (CLI), pyyaml
**Storage**: JSONL形式ファイル（.e8/history.jsonl, .e8/knowledge.jsonl, .e8/logs/）
**Testing**: pytest + pytest-cov + pytest-asyncio
**Target Platform**: Linux/macOS（claude CLI がインストールされた開発環境）
**Project Type**: Single CLI application
**Performance Goals**: コンテキストサイズ < 100,000 tokens/イテレーション
**Constraints**: 最大50+イテレーションでもコンテキスト枯渇なし、履歴ファイルのクラッシュ耐性
**Scale/Scope**: 単一ユーザー、単一プロジェクト単位での実行

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Check

| Article | Requirement | Status | Notes |
|---------|-------------|--------|-------|
| Art.1 Test-First | TDDワークフロー計画 | PASS | 1機能=1テストファイルで構成、実装前にテスト作成 |
| Art.2 Doc Integrity | 仕様書との整合性 | PASS | spec.md に基づいて設計 |
| Art.3 Agent Architecture | 4エージェント構成 | PASS | 受付・実行・サマリ・判定の責務分離を遵守 |
| Art.4 Simplicity | 最小プロジェクト構造 | PASS | 単一プロジェクト構造 |
| Art.5 Code Quality | ruff + mypy 必須 | PASS | CI/CD設定に含める |
| Art.6 Data Accuracy | ハードコード禁止 | PASS | 環境変数・設定ファイルで管理 |
| Art.7 DRY | 重複検出時停止 | PASS | 実装前に既存コード検索 |
| Art.9 Type Safety | 型注釈必須 | PASS | pydantic BaseModel + 全関数に型注釈 |
| Art.11 Naming | 命名規則準拠 | PASS | git-conventions.md に従う |

**Gate Result**: PASS - Phase 0 に進行可能

### Post-Phase 1 Check

| Article | Requirement | Status | Notes |
|---------|-------------|--------|-------|
| Art.1 Test-First | テストファイル計画 | PASS | 1機能=1テストファイルで設計済み（test_engine.py等） |
| Art.2 Doc Integrity | データモデル整合性 | PASS | data-model.md と contracts/ が spec.md と整合 |
| Art.3 Agent Architecture | 4エージェント設計 | PASS | contracts/agents.py で責務分離を明確化 |
| Art.4 Simplicity | 構造のシンプルさ | PASS | 単一プロジェクト、最小限のモジュール分割 |
| Art.5 Code Quality | 品質チェック計画 | PASS | ruff + mypy をCI/CDに組み込み予定 |
| Art.6 Data Accuracy | 設定管理 | PASS | EngineConfig で環境変数/YAML管理 |
| Art.7 DRY | 重複回避 | PASS | pydantic-ai の機能を直接使用、ラッパー不要 |
| Art.9 Type Safety | 型定義 | PASS | 全モデルに型注釈、BaseModel継承 |
| Art.11 Naming | 命名規則 | PASS | specs/001-endless8-engine-core、ブランチ名準拠 |

**Gate Result**: PASS - Phase 2 (tasks.md生成) に進行可能

## Project Structure

### Documentation (this feature)

```text
specs/001-endless8-engine-core/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/endless8/
├── __init__.py
├── models/              # pydantic データモデル
│   ├── __init__.py
│   ├── task.py          # TaskInput
│   ├── results.py       # IntakeResult, ExecutionResult, JudgmentResult, LoopResult
│   ├── summary.py       # ExecutionSummary, SummaryMetadata, NextAction
│   └── knowledge.py     # Knowledge, KnowledgeType
├── agents/              # 4エージェント実装
│   ├── __init__.py
│   ├── intake.py        # 受付エージェント
│   ├── execution.py     # 実行エージェント
│   ├── summary.py       # サマリエージェント
│   └── judgment.py      # 判定エージェント
├── history/             # 履歴・ナレッジ管理
│   ├── __init__.py
│   ├── history.py       # History クラス
│   ├── knowledge_base.py # KnowledgeBase クラス
│   └── queries.py       # DuckDB クエリ
├── cli/                 # CLI実装
│   ├── __init__.py
│   └── main.py          # typer CLI (e8 コマンド)
├── config/              # 設定管理
│   ├── __init__.py
│   └── settings.py      # YAML設定読み込み
└── engine.py            # Engine メインクラス

tests/
├── __init__.py
├── conftest.py          # pytest fixtures
├── unit/
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_intake_agent.py
│   ├── test_execution_agent.py
│   ├── test_summary_agent.py
│   ├── test_judgment_agent.py
│   ├── test_history.py
│   ├── test_knowledge_base.py
│   └── test_models.py
└── integration/
    ├── __init__.py
    ├── test_loop_execution.py
    └── test_cli.py
```

**Structure Decision**: 単一プロジェクト構造を採用。Constitution Article 4 (Simplicity) に準拠し、過剰な抽象化を避ける。モジュール分割は責務に基づき、各エージェントとデータモデルを独立したファイルで管理。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |

**Note**: 現時点でConstitution違反なし。
