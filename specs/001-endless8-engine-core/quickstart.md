# Quickstart: endless8 エンジンコア機能

**Date**: 2026-01-23

## Prerequisites

- Python 3.13+
- claude CLI（Claude Code CLI）がインストール・認証済み
- uv（Python パッケージマネージャ）

## Installation

```bash
uv tool install git+https://github.com/drillan/endless8.git
```

インストール後、`e8` コマンドが使用可能になります。

## Quick Start

### 1. 基本的な使い方

```bash
# タスクと完了条件を指定して実行
e8 run "テストカバレッジを90%以上にする" --criteria "pytest --cov で90%以上"

# 複数の完了条件を指定
e8 run "認証機能を実装" \
  --criteria "ログインできる" \
  --criteria "ログアウトできる" \
  --criteria "不正なパスワードでエラーになる"
```

### 2. 設定ファイルを使用

```yaml
# task.yaml
task: "APIエンドポイントを実装"
criteria:
  - "GET /users が200を返す"
  - "POST /users でユーザー作成できる"
  - "テストがすべてパスする"

max_iterations: 15
persist: ".e8/history.jsonl"
```

```bash
e8 run --config task.yaml
```

### 3. プロジェクトディレクトリを指定

```bash
e8 run "バグを修正" --project /path/to/project --criteria "テストがパスする"
```

### 4. 履歴を永続化して再開可能に

```bash
# 履歴を保存
e8 run "大規模なリファクタリング" \
  --persist .e8/history.jsonl \
  --criteria "すべてのテストがパスする"

# 中断後、同じ設定で再実行すると履歴から再開
e8 run "大規模なリファクタリング" \
  --persist .e8/history.jsonl \
  --criteria "すべてのテストがパスする"
```

## Python API

```python
import asyncio
from endless8 import Engine, TaskInput, EngineConfig

async def main():
    # 設定を作成
    config = EngineConfig(
        task="テストカバレッジを90%以上にする",
        criteria=["pytest --cov で90%以上"],
        max_iterations=10,
        persist=".e8/history.jsonl"
    )

    # エンジンを作成して実行
    engine = Engine(config)
    result = await engine.run(TaskInput(
        task=config.task,
        criteria=config.criteria,
        max_iterations=config.max_iterations
    ))

    if result.status == "completed":
        print(f"✓ タスク完了（{result.iterations_used} イテレーション）")
    else:
        print(f"✗ {result.status}（{result.iterations_used} イテレーション）")

asyncio.run(main())
```

### 進捗を監視しながら実行

```python
async def main_with_progress():
    engine = Engine(config)
    task_input = TaskInput(task=config.task, criteria=config.criteria)

    async for summary in engine.run_iter(task_input):
        print(f"[Iteration {summary.iteration}]")
        print(f"  アプローチ: {summary.approach}")
        print(f"  結果: {summary.result}")
        print(f"  理由: {summary.reason}")

asyncio.run(main_with_progress())
```

## Configuration Reference

### YAML 設定ファイル

```yaml
# 必須
task: "タスクの説明"
criteria:
  - "完了条件1"
  - "完了条件2"

# オプション
max_iterations: 10          # 最大イテレーション数（デフォルト: 10）
persist: ".e8/history.jsonl" # 履歴ファイルパス
knowledge: ".e8/knowledge.jsonl"  # ナレッジファイルパス
history_context_size: 5     # 参照する履歴件数（デフォルト: 5）

# ログオプション
logging:
  raw_log: false            # 生ログを保存（デフォルト: false）
  raw_log_dir: ".e8/logs"   # 生ログ保存先

# claude CLI オプション
claude_options:
  allowed_tools:
    - "Read"
    - "Edit"
    - "Write"
    - "Bash(git:*)"
  model: "sonnet"
  output_format: "stream-json"
  verbose: true

# プロンプトカスタマイズ
prompts:
  judgment: |
    以下の基準で完了条件を評価してください：
    - テストが実際に実行され、すべてパスしていること
    - エラーログや警告がないこと
  append_system_prompt: |
    各作業の最後に、以下のJSON形式で報告してください：
    {"strategy_tags": ["タグ"], "approach": "アプローチ", "discoveries": ["発見"]}
```

### CLI オプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--criteria` | `-c` | 完了条件（複数指定可） |
| `--config` | | YAML 設定ファイル |
| `--project` | | プロジェクトディレクトリ |
| `--persist` | | 履歴ファイルパス |
| `--max-iterations` | | 最大イテレーション数 |

## Data Storage

### ディレクトリ構造

```
project/
├── .e8/
│   ├── history.jsonl      # タスク単位の履歴
│   ├── knowledge.jsonl    # プロジェクト単位のナレッジ
│   └── logs/              # オプション: 生ログ
│       ├── iteration-001.jsonl
│       ├── iteration-002.jsonl
│       └── ...
└── task.yaml              # 設定ファイル（オプション）
```

### 履歴形式（JSONL）

```json
{"type":"summary","iteration":1,"approach":"テスト追加","result":"success","reason":"テストファイル作成完了","artifacts":["tests/test_main.py"],"timestamp":"2026-01-23T10:00:00Z"}
{"type":"summary","iteration":2,"approach":"実装修正","result":"success","reason":"テストパス","artifacts":["src/main.py"],"timestamp":"2026-01-23T10:05:00Z"}
```

### ナレッジ形式（JSONL）

```json
{"type":"pattern","category":"testing","content":"テストは tests/ ディレクトリに配置","example_file":"tests/test_main.py","source_task":"テストカバレッジ向上","confidence":"high","created_at":"2026-01-23T10:00:00Z"}
```

## Troubleshooting

### `.e8/` ディレクトリがない

自動的に作成されます。

### `--project` で存在しないディレクトリを指定

エラーが表示されて終了します。

### 最大イテレーション到達

```bash
# イテレーション数を増やして再実行
e8 run --config task.yaml --max-iterations 20
```

### 履歴から再開されない

`--persist` オプションで同じファイルパスを指定してください。

## Next Steps

- [データモデル詳細](./data-model.md)
- [API コントラクト](./contracts/)
- [リサーチノート](./research.md)
