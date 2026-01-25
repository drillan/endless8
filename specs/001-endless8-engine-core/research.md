# Research: endless8 エンジンコア機能

**Date**: 2026-01-23
**Status**: Complete

## Overview

本ドキュメントは endless8 エンジンコア機能の実装に必要な技術リサーチ結果をまとめたものである。

---

## 1. pydantic-ai エージェントパターン

### Decision: pydantic-ai の標準パターンを採用

**Rationale**:
- pydantic-ai は Agent クラスを中心とした型安全なエージェント定義を提供
- 構造化出力（Pydantic モデル）による厳密な型チェックが可能
- 依存性注入パターンにより、テスト容易性が向上
- Constitution Article 4 (Simplicity) に準拠し、不要なラッパーを避ける

**Alternatives Considered**:
- LangChain: 過剰な抽象化、Constitution Article 4 違反
- 独自フレームワーク: 車輪の再発明、Constitution Article 4 違反

### Key Patterns

#### Agent Definition
```python
from pydantic_ai import Agent
from pydantic import BaseModel

class AgentOutput(BaseModel):
    result: str
    metadata: dict

agent = Agent(
    'anthropic:claude-sonnet-4-5',
    deps_type=EngineDependencies,
    output_type=AgentOutput,
    system_prompt="エージェントの指示"
)
```

#### 依存性注入
```python
from dataclasses import dataclass

@dataclass
class EngineDependencies:
    history: History
    knowledge_base: KnowledgeBase
    config: EngineConfig

# ランタイムで注入
result = await agent.run('task', deps=deps)
```

#### Tool Definition
```python
@agent.tool
async def execute_command(ctx: RunContext[EngineDependencies], command: str) -> str:
    """コマンドを実行する"""
    # ctx.deps で依存関係にアクセス
    return result
```

### Best Practices

1. **すべてのエージェントに output_type を定義**: 構造化出力を保証
2. **RunContext を使用**: ツール内で依存関係にアクセス
3. **ctx.usage を伝播**: マルチエージェントでトークン使用量を追跡
4. **ModelRetry を活用**: 明示的なリトライ要求

---

## 2. claudecode-model アダプタ

### Decision: claudecode-model 経由で claude CLI を呼び出す

**Rationale**:
- pydantic-ai と Claude Code CLI を統合するアダプタ
- MCP サーバーや Agent Skills へのアクセスが可能
- stream-json 出力形式でリアルタイム処理が可能

**Alternatives Considered**:
- Anthropic API 直接呼び出し: MCP/Agent Skills 非対応
- subprocess 直接呼び出し: pydantic-ai の構造化出力が使えない

### Integration Pattern

```python
# claude CLI 呼び出しオプション
claude_options = {
    "output_format": "stream-json",
    "verbose": True,
    "allowed_tools": ["Read", "Edit", "Bash(git:*)"],
    "model": "sonnet"
}
```

### Stream-JSON 出力形式

```json
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"token"}}}
```

各行が独立した JSON オブジェクトで、リアルタイム処理が可能。

### Metadata Extraction

| メタデータ | 取得元 | 方法 |
|-----------|--------|------|
| tools_used | stream-json | tool_use イベントから抽出 |
| files_modified | stream-json | Edit/Write ツール呼び出しから抽出 |
| tokens_used | stream-json | usage イベントから抽出 |
| error_type | stream-json | error イベントから抽出 |
| approach | append_system_prompt | 実行エージェントの報告 |
| strategy_tags | append_system_prompt | 実行エージェントの報告 |
| discoveries | append_system_prompt | 実行エージェントの報告 |

---

## 3. DuckDB JSONL クエリ

### Decision: DuckDB で履歴・ナレッジファイルをクエリ

**Rationale**:
- JSONL ファイルを直接 SQL でクエリ可能
- ネスト構造の JSON フィールドに効率的にアクセス
- インプロセス実行で外部依存なし
- フィルタープッシュダウンによる高速クエリ

**Alternatives Considered**:
- SQLite + JSON1: JSON クエリ機能が限定的
- pandas: 大規模ファイルでメモリ効率が悪い
- 独自パーサー: 再発明、Constitution Article 4 違反

### Query Patterns

#### JSONL ファイル読み込み
```sql
-- read_ndjson_auto を使用（自動スキーマ検出）
SELECT * FROM read_ndjson_auto('.e8/history.jsonl');
```

#### ネストフィールドのクエリ
```sql
-- JSONPath 構文
SELECT json_extract_string(metadata, '$.tools_used[0]') AS first_tool
FROM read_ndjson_auto('.e8/history.jsonl');

-- 演算子構文
SELECT metadata->'files_modified' AS files
FROM read_ndjson_auto('.e8/history.jsonl');
```

#### 履歴コンテキスト生成（直近N件 + 失敗履歴）
```sql
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (ORDER BY iteration DESC) as rn
  FROM read_ndjson_auto('.e8/history.jsonl')
  WHERE type = 'summary'
)
SELECT * FROM ranked WHERE rn <= 5  -- 直近5件
UNION ALL
SELECT *, 0 as rn FROM read_ndjson_auto('.e8/history.jsonl')
WHERE type = 'summary' AND result = 'failure' AND iteration NOT IN (
  SELECT iteration FROM ranked WHERE rn <= 5
)
```

#### ナレッジベースクエリ
```sql
-- 高信頼度パターンの取得
SELECT content, example_file
FROM read_ndjson_auto('.e8/tasks/<task-id>/knowledge.jsonl')
WHERE type = 'pattern' AND confidence = 'high';

-- 特定カテゴリのナレッジ検索
SELECT * FROM read_ndjson_auto('.e8/tasks/<task-id>/knowledge.jsonl')
WHERE type = 'lesson' AND category = 'error_handling';
```

### Python Integration

```python
import duckdb

def query_history(history_path: str, limit: int = 5) -> list[dict]:
    """履歴からコンテキストを生成"""
    query = """
    WITH ranked AS (
      SELECT *, ROW_NUMBER() OVER (ORDER BY iteration DESC) as rn
      FROM read_ndjson_auto(?)
      WHERE type = 'summary'
    )
    SELECT * FROM ranked WHERE rn <= ?
    UNION ALL
    SELECT *, 0 as rn FROM read_ndjson_auto(?)
    WHERE type = 'summary' AND result = 'failure'
    AND iteration NOT IN (SELECT iteration FROM ranked WHERE rn <= ?)
    """
    return duckdb.execute(query, [history_path, limit, history_path, limit]).fetchall()
```

### Performance Tips

1. **WHERE 句を必ず含める**: フィルタープッシュダウンを活用
2. **LIMIT を活用**: DuckDB の TopN 最適化が効く
3. **頻繁にクエリするフィールドは抽出**: JSON からカラムに変換
4. **prepared statements**: 繰り返しクエリの効率化

---

## 4. CLI フレームワーク

### Decision: typer を採用

**Rationale**:
- 型ヒントベースの CLI 定義
- pydantic との親和性が高い
- 自動ヘルプ生成
- async サポート

**Alternatives Considered**:
- click: typer のベース、typer の方が型安全
- argparse: 標準ライブラリだが冗長

### CLI Structure

```python
import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def run(
    task: str = typer.Argument(..., help="タスクの説明"),
    criteria: list[str] = typer.Option([], "--criteria", "-c", help="完了条件"),
    config: Path | None = typer.Option(None, "--config", help="設定ファイル"),
    project: Path = typer.Option(Path.cwd(), "--project", help="プロジェクトディレクトリ"),
    persist: Path | None = typer.Option(None, "--persist", help="履歴ファイル"),
    max_iterations: int | None = typer.Option(None, "--max-iterations", help="最大イテレーション数"),
):
    """タスクを実行する"""
    ...

if __name__ == "__main__":
    app()
```

---

## 5. 設定ファイル

### Decision: YAML 形式 + pydantic-settings

**Rationale**:
- 人間が読み書きしやすい
- pydantic-settings で型安全な設定読み込み
- 環境変数との統合が容易

### Configuration Schema

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class ClaudeOptions(BaseModel):
    allowed_tools: list[str] = ["Read", "Edit", "Write", "Bash"]
    model: str = "sonnet"
    output_format: str = "stream-json"
    verbose: bool = True

class LoggingOptions(BaseModel):
    raw_log: bool = False
    raw_log_dir: str = ".e8/logs"

class PromptsConfig(BaseModel):
    judgment: str | None = None
    append_system_prompt: str | None = None

class EngineConfig(BaseSettings):
    task: str
    criteria: list[str]
    max_iterations: int = 10
    persist: str | None = None
    history_context_size: int = 5
    knowledge_context_size: int = 10
    logging: LoggingOptions = LoggingOptions()
    claude_options: ClaudeOptions = ClaudeOptions()
    prompts: PromptsConfig = PromptsConfig()
```

---

## 6. 解決済みの不明点

| 項目 | 解決策 |
|------|--------|
| pydantic-ai エージェント定義 | Agent クラス + output_type で構造化出力 |
| claudecode-model 統合 | stream-json 出力を解析してメタデータ抽出 |
| 履歴クエリ | DuckDB で JSONL を直接クエリ |
| CLI フレームワーク | typer を採用 |
| 設定管理 | YAML + pydantic-settings |

---

## References

- [pydantic-ai Documentation](https://ai.pydantic.dev/)
- [DuckDB JSON Documentation](https://duckdb.org/docs/stable/data/json/loading_json)
- [typer Documentation](https://typer.tiangolo.com/)
- [pydantic-settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
