# CLAUDE.md

このファイルは AI 開発支援のランタイムガイダンスです。
詳細な原則は `.specify/memory/constitution.md` を参照してください。

## プロジェクト概要

endless8 は pydantic-ai と claudecode-model を使用したコンテキスト効率の良いタスク実行ループエンジンです。

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

## 命名規則

- specs/ ディレクトリ: `<issue-number>-<name>`（例: `001-engine-core`）
- Git ブランチ: `.claude/git-conventions.md` 参照

## Active Technologies
- Python 3.13+ + pydantic-ai >= 1.46.0, claudecode-model, duckdb >= 1.4.3, typer >= 0.21.1, pyyaml >= 6.0.0
- JSONL形式ファイル（.e8/tasks/<task-id>/history.jsonl, .e8/tasks/<task-id>/knowledge.jsonl, .e8/tasks/<task-id>/logs/）

## Recent Changes
- 001-endless8-engine-core: Added Python 3.13+ + pydantic-ai, claudecode-model, DuckDB, typer (CLI), pyyaml
