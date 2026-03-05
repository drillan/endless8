# Implementation Plan: 構造化された完了条件（Structured Criteria）

**Branch**: `002-structured-criteria` | **Date**: 2026-03-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-structured-criteria/spec.md`

## Summary

既存の `criteria: list[str]` を「意味的条件（LLM 判定）」と「コマンド条件（終了コード判定）」の判別化ユニオンに拡張する。判定フェーズにコマンド実行ステップを挿入し、コマンド結果を LLM 判定のコンテキストとして提供する。文字列のみの指定は意味的条件として後方互換に処理する。

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: pydantic-ai >= 1.46.0, claudecode-model, duckdb >= 1.4.3, typer >= 0.21.1, pyyaml >= 6.0.0
**Storage**: JSONL ファイル（`.e8/tasks/<task-id>/history.jsonl`, `knowledge.jsonl`）
**Testing**: pytest + pytest-asyncio（`tests/unit/`, `tests/integration/`）
**Target Platform**: Linux（CLI ツール）
**Project Type**: single
**Performance Goals**: コマンド実行のタイムアウトをユーザーが設定可能（デフォルト: 30.0 秒、名前付き定数 `DEFAULT_COMMAND_TIMEOUT_SEC` で定義）
**Constraints**: コマンド出力は 10KB に制限、コマンドは定義順に順次実行（並列実行なし）
**Scale/Scope**: 既存の 4 エージェント構成を維持しつつ、判定フェーズを拡張

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Article | Status | Notes |
|---------|--------|-------|
| Art.1 テストファースト | PASS | 新しいモデル・コマンド実行・判定ロジックに対してテストを先行作成 |
| Art.2 ドキュメント整合性 | PASS | spec.md 策定済み、plan.md（本ファイル）で設計を文書化 |
| Art.3 エージェントアーキテクチャ準拠 | PASS | 4 エージェント構成を維持。コマンド実行は判定フェーズ内のステップとして追加（新エージェントは作成しない） |
| Art.4 シンプルさ | PASS | 既存プロジェクト構造を維持、不要なラッパーなし |
| Art.5 コード品質基準 | PASS | ruff + mypy チェック必須 |
| Art.6 データ正確性 | PASS | タイムアウト値は設定で管理、エラー時は明示的例外（暗黙的処理なし） |
| Art.7 DRY 原則 | PASS | 既存の CriteriaEvaluation を拡張（新規バージョン作成しない） |
| Art.8 リファクタリングポリシー | PASS | 既存モデルを直接修正（V2 クラス作成しない） |
| Art.9 Python 型安全性 | PASS | 全関数に型注釈、Discriminator による型安全なユニオン。既存の `(str, Enum)` パターンを `StrEnum` に移行（ruff UP042 準拠） |
| Art.10 Docstring 標準 | PASS | Google-style docstring を適用 |
| Art.11 命名規則 | PASS | ブランチ名 `002-structured-criteria` は規則準拠 |

**親仕様（001）との整合性**: FR-007 により親仕様 FR-008 を拡張。判定エージェントの情報源に「コマンド実行結果」を追加。ExecutionSummary には含めず、JudgmentContext に新フィールドとして追加する設計。これは親仕様の意図（判定エージェントは ExecutionSummary を情報源とする）の精神を維持しつつ、コマンド結果という新しい情報源を明示的に追加する。

## Project Structure

### Documentation (this feature)

```text
specs/002-structured-criteria/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/endless8/
├── models/
│   ├── task.py          # [MODIFY] TaskInput.criteria を判別化ユニオンに拡張
│   ├── results.py       # [MODIFY] CriteriaEvaluation に evaluation_method, command_result を追加
│   └── criteria.py      # [NEW] Criterion 型定義（CommandCriterion, CriterionInput, CriterionType）
├── agents/
│   ├── __init__.py      # [MODIFY] JudgmentContext に command_results 追加、CommandCriterionResult モデル追加（既存エージェント Protocol は list[str] を維持、Engine 側で変換）
│   └── judgment.py      # [MODIFY] コマンド結果をプロンプトに含める
├── engine.py            # [MODIFY] 判定フェーズにコマンド実行ステップを挿入、criteria を list[str] に変換して各エージェントに渡すロジック追加
├── command/
│   ├── __init__.py      # [NEW]
│   └── executor.py      # [NEW] CommandExecutor（asyncio subprocess）
└── config/
    └── settings.py      # [MODIFY] コマンドタイムアウト設定を追加

tests/
├── unit/
│   ├── test_criteria_models.py  # [NEW] Criterion 型のバリデーションテスト
│   ├── test_command_executor.py # [NEW] CommandExecutor のテスト
│   ├── test_judgment_agent.py   # [MODIFY] コマンド結果コンテキストのテスト追加
│   └── test_models.py           # [MODIFY] 拡張された CriteriaEvaluation のテスト
└── integration/
    └── test_command_criteria.py  # [NEW] コマンド条件を含むループ実行テスト
```

**Structure Decision**: 既存の single project 構造を維持。新規ファイルは `src/endless8/models/criteria.py`（型定義）と `src/endless8/command/executor.py`（コマンド実行）の 2 ファイルのみ。

**Criteria 変換方針**: `TaskInput.criteria` は `list[CriterionInput]`（str | CommandCriterion の混在リスト）だが、既存エージェント（受付・実行・サマリ）のインターフェースは `list[str]` のまま維持する。Engine が各エージェント呼び出し前に `list[CriterionInput]` → `list[str]` への変換を行う:
- `str` → そのまま
- `CommandCriterion` → `description or command`（表示名またはコマンド文字列）

これにより、受付・実行・サマリエージェントの Protocol 変更を最小限に抑える。`IntakeResult.criteria` も `list[str]` のまま維持する。

## Complexity Tracking

> Constitution Check に違反なし。追加の正当化は不要。
