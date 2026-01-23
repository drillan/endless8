# CLAUDE.md

このファイルは AI 開発支援のランタイムガイダンスです。
詳細な原則は `.specify/memory/constitution.md` を参照してください。

## プロジェクト概要

endless8 は pydantic-ai と claudecode-model を使用したコンテキスト効率の良いタスク実行ループエンジンです。

## 非交渉的ルール（MUST）

### 1. テストファースト

```
実装前に: テスト作成 → ユーザー承認 → テスト失敗確認 → 実装
```

- 1機能 = 1テストファイル（例: `test_engine.py` ← `engine.py`）

### 2. コード品質チェック

コミット前に必ず実行:

```bash
ruff check --fix . && ruff format . && mypy .
```

### 3. 型安全性

- すべての関数・メソッドに型注釈必須
- `Any` 型の使用禁止
- `| None` 構文を優先（`Optional` より）

### 4. データ正確性

- ハードコード禁止 → 環境変数または設定ファイルで管理
- 暗黙的フォールバック禁止 → 明示的エラー処理

### 5. DRY原則

- 実装前に既存コードを検索（Glob, Grep）
- 重複検出時は作業停止 → リファクタリング計画

## エージェントアーキテクチャ

4エージェント構成を遵守:

| エージェント | 責務 |
|-------------|------|
| 受付 | 完了条件の妥当性チェック、曖昧な場合は質問生成 |
| 実行 | タスク実行（毎回フレッシュなコンテキストで開始） |
| サマリ | 実行結果を圧縮して履歴に保存 |
| 判定 | 完了条件の評価 |

**コンテキスト管理**:
- 実行エージェントは毎イテレーションでリフレッシュ
- 履歴はサマリ化して効率的に参照

## フレームワーク使用

- pydantic-ai の機能を直接使用（不要なラッパー禁止）
- claudecode-model アダプタを標準的に活用
- pydantic の BaseModel で型安全なデータ定義

## Python 実行

システムの `python3` を直接使用せず、以下を使用:

```bash
uv run python ...
# または
.venv/bin/python ...
```

## 命名規則

- specs/ ディレクトリ: `<issue-number>-<name>`（例: `001-engine-core`）
- Git ブランチ: `.claude/git-conventions.md` 参照

## Active Technologies
- Python 3.13+ + pydantic-ai, claudecode-model, DuckDB, typer (CLI), pyyaml (001-endless8-engine-core)
- JSONL形式ファイル（.e8/tasks/<task-id>/history.jsonl, .e8/tasks/<task-id>/knowledge.jsonl, .e8/tasks/<task-id>/logs/） (001-endless8-engine-core)

## Recent Changes
- 001-endless8-engine-core: Added Python 3.13+ + pydantic-ai, claudecode-model, DuckDB, typer (CLI), pyyaml
