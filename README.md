# endless8

**endless8** は、pydantic-ai と claudecode-model を使用した、コンテキスト効率の良いタスク実行ループエンジンです。

## 概要

Ralph Wiggum（Claude Code のループプラグイン）にインスパイアされていますが、以下の点で改良されています：

- **コンテキスト枯渇を回避**: 実行エージェントは毎回フレッシュな状態で開始
- **履歴管理**: サマリ化された履歴を効率的に参照
- **柔軟な完了条件**: 自然言語で条件を指定、AIが判定
- **責務分離**: 4つの専門エージェントによるパイプライン

## アーキテクチャ

```
[ユーザー] タスク + 完了条件
     ↓
[受付エージェント] → 不明確なら質問を返す
     ↓
┌─── ループ ───────────────────────┐
│ [実行エージェント] ← 履歴を注入   │
│      ↓                          │
│ [サマリエージェント] → 履歴に保存 │
│      ↓                          │
│ [判定エージェント]               │
│      ├→ 完了 → 結果を返す        │
│      └→ 未完了 → ループ継続      │
└─────────────────────────────────┘
```

## インストール

```bash
uv tool install git+https://github.com/drillan/endless8.git
```

## 使用例

### Python API

```python
from endless8.engine import Engine
from endless8.models import TaskInput
from endless8.config import EngineConfig

config = EngineConfig(persist=".e8/history.jsonl")
engine = Engine(config)

result = await engine.run(TaskInput(
    task="認証機能を実装してください",
    criteria=["すべてのテストが通る", "カバレッジが80%以上"],
    max_iterations=10,
))

print(f"状態: {result.status}")
print(f"イテレーション: {result.iterations_used}")
```

### ストリーミング実行

各イテレーションのサマリをストリーミングで取得できます：

```python
async for summary in engine.run_iter(task_input):
    print(f"[Iteration {summary.iteration}] {summary.result}")
```

## CLI

```bash
# 基本実行
e8 run --task "タスクの説明" --criteria "条件1" --criteria "条件2"

# プロジェクトディレクトリを指定
e8 run -t "タスク" -c "条件" --project /path/to/project

# イテレーション数を指定
e8 run -t "タスク" -c "条件" --max-iterations 5
```

### CLI オプション一覧

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--task` | `-t` | タスクの説明 |
| `--criteria` | `-c` | 完了条件（複数指定可） |
| `--project` | `-p` | プロジェクトディレクトリ |
| `--max-iterations` | `-m` | 最大イテレーション数（デフォルト: 10） |
| `--config` | | YAML設定ファイル |
| `--resume` | `-r` | タスクIDを指定して再開 |
| `--verbose` | `-V` | 詳細な実行ログを表示（ツールコール・テキスト応答） |

## データストレージ

endless8 はプロジェクトディレクトリに `.e8/` ディレクトリを作成して履歴とナレッジを保存します：

```
project/
├── .e8/
│   ├── history.jsonl      # タスク単位の履歴
│   ├── knowledge.jsonl    # プロジェクト単位のナレッジ
│   └── logs/              # オプション: 生ログ
```

## 特徴

### Ralph Wiggum との比較

| 観点 | Ralph Wiggum | endless8 |
|------|--------------|----------|
| コンテキスト | 蓄積（枯渇リスク） | 毎回リフレッシュ |
| 履歴参照 | 会話履歴全体 | サマリ化して効率的に |
| 完了条件 | `<promise>` タグ | 自然言語 + AI判定 |
| 長時間実行 | トークン上限 | 安定継続 |

### 4エージェント構成

1. **受付エージェント**: 完了条件の妥当性チェック、曖昧な場合は質問
2. **実行エージェント**: タスク実行に専念
3. **サマリエージェント**: 実行結果を圧縮して履歴に保存
4. **判定エージェント**: 完了条件の評価

## 依存関係

- Python 3.13+
- pydantic-ai >= 1.46.0
- [claudecode-model](https://github.com/drillan/claudecode-model) - pydantic-ai 用 Claude Code アダプタ
- typer >= 0.21.1
- duckdb >= 1.4.3
- pyyaml >= 6.0.0

## ライセンス

MIT
