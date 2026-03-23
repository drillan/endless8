# endless8

**endless8** は、pydantic-ai と claudecode-model を使用した、コンテキスト効率の良いタスク実行ループエンジンです。

## 概要

Ralph Wiggum（Claude Code のループプラグイン）にインスパイアされていますが、以下の点で改良されています：

- **コンテキスト枯渇を回避**: 実行エージェントは毎回フレッシュな状態で開始
- **履歴管理**: サマリ化された履歴を効率的に参照
- **柔軟な完了条件**: 自然言語条件（AI判定）とコマンド条件（終了コード判定）を混在可能
- **責務分離**: 4つの専門エージェントによるパイプライン

## アーキテクチャ

```
[ユーザー] タスク + 完了条件
     ↓
[受付エージェント] → 不明確なら質問を返す
     ↓
┌─── ループ ──────────────────────────────┐
│ [実行エージェント] ← 履歴 + 判定FB注入   │
│      ↓                                 │
│ [サマリエージェント] → 履歴に保存        │
│      ↓                                 │
│ [コマンド条件実行] ← 終了コード判定      │
│      ↓                                 │
│ [判定エージェント]                      │
│      ├→ 完了 → 結果を返す               │
│      └→ 未完了 → suggested_next_action  │
│                  を次の実行に注入        │
└─────────────────────────────────────────┘
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
    criteria=[
        "すべてのテストが通る",
        {"type": "command", "command": "pytest --tb=short", "description": "テストスイート"},
        {"type": "command", "command": "pytest --cov=src --cov-fail-under=80"},
    ],
    max_iterations=10,
))

print(f"状態: {result.status}")
print(f"イテレーション: {result.iterations_used}")
```

### TaskManager API

タスクのライフサイクルをステップ実行で管理できます：

```python
from pathlib import Path
from endless8.config import EngineConfig
from endless8.task_manager import TaskManager

config = EngineConfig(
    task="認証機能を実装する",
    criteria=["テストが全パス"],
    max_iterations=10,
)
tm = TaskManager(Path("."), config)
tm.set_agents(intake_agent=..., execution_agent=..., summary_agent=..., judgment_agent=...)

# タスク作成
task_id = await tm.create()

# 1フェーズずつ進める
result = await tm.advance(task_id)  # CREATED -> INTAKE -> EXECUTING
result = await tm.advance(task_id)  # EXECUTING -> SUMMARIZING -> JUDGING -> ...

# ステータス確認
status = await tm.status(task_id)
print(f"フェーズ: {status.phase}, 完了: {status.is_complete}")

# 外部評価結果を注入（hachimoku 等の外部ツールとの連携）
await tm.inject_result(task_id, Path("review_result.json"))

# 自動ループ実行（advance を完了まで繰り返す）
result = await tm.run(task_id)
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

### CLI オプション一覧（`e8 run`）

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--task` | `-t` | タスクの説明 |
| `--criteria` | `-c` | 完了条件（複数指定可） |
| `--project` | `-p` | プロジェクトディレクトリ |
| `--max-iterations` | `-m` | 最大イテレーション数（デフォルト: 10） |
| `--config` | | YAML設定ファイル（詳細は [examples/README.md](examples/README.md) を参照） |
| `--resume` | `-r` | タスクIDを指定して再開 |
| `--verbose` | `-V` | 詳細な実行ログを表示（ツールコール・テキスト応答） |
| `--command-timeout` | | コマンド条件のデフォルトタイムアウト秒（デフォルト: 30） |

### ステップ実行と外部ツール連携

タスクを1フェーズずつ実行し、外部ツールの評価結果を注入できます：

```bash
# タスクのステータスを確認（フェーズ・イテレーション）
e8 status --task-id <TASK_ID> --project /path/to/project

# JSON 形式で出力（スクリプトからの参照用）
e8 status --task-id <TASK_ID> --json

# 1フェーズ進める
e8 advance <TASK_ID> --config config.yaml --project /path/to/project

# 外部評価結果を注入
e8 inject-result <TASK_ID> result.json --project /path/to/project
```

**外部ツール連携の例**（hachimoku 等のコードレビューツールとの併用）：

```bash
TASK_ID="20260323-143000"  # e8 run で生成されたタスクID

for i in $(seq 1 10); do
  # 外部ツールで評価
  hachimoku --no-confirm docs/strategies/*.md || true

  # 評価結果を注入
  e8 inject-result "$TASK_ID" .hachimoku/reviews/files.jsonl

  # 1イテレーション実行（execute → summary → judgment）
  e8 advance "$TASK_ID" --config strategy-evaluation.yaml

  # 完了チェック
  if e8 status --task-id "$TASK_ID" --json | jq -e '.is_complete'; then
    echo "Complete!"
    exit 0
  fi
done
```

## データストレージ

endless8 はプロジェクトディレクトリに `.e8/` ディレクトリを作成して履歴とナレッジを保存します：

```
project/
├── .e8/
│   └── tasks/
│       └── <task-id>/
│           ├── state.jsonl        # タスクの状態遷移履歴
│           ├── history.jsonl      # タスクの実行履歴
│           ├── knowledge.jsonl    # タスクのナレッジ
│           ├── output.md          # 最新イテレーションの生出力
│           ├── injected_result.json  # 外部評価結果（inject-result 時）
│           └── logs/              # オプション: 生ログ
```

## 特徴

### コマンド条件

完了条件にシェルコマンドを指定し、終了コード（0 = met、非ゼロ = not met）で客観的に判定します。自然言語条件と混在できます。

```yaml
task: "認証機能を実装する"
criteria:
  - "コードが読みやすく保守しやすい"                    # 自然言語条件（AI判定）
  - type: command
    command: "pytest --tb=short"                       # コマンド条件（終了コード判定）
    description: "テストスイートが全パス"
  - type: command
    command: "pytest --cov=src --cov-fail-under=80"
    timeout: 60                                        # コマンド固有タイムアウト（秒）
```

**動作仕様:**

- コマンド条件は実行エージェントには渡されず、判定フェーズでのみ評価される（実行エージェントのコンテキスト枯渇を防止）
- コマンド条件は各イテレーションの判定フェーズで、サマリ完了後・LLM判定前に順次実行される
- コマンドは `working_directory`（デフォルト: プロセスの作業ディレクトリ）で実行される
  - CLI 使用時は `--project` オプションの値（デフォルト: カレントディレクトリ）が `working_directory` として設定される
- `working_directory` は実行エージェントにも伝達され、ファイル操作の基準ディレクトリとして使用される
- コマンド条件のみのタスクでは LLM 判定を省略（コスト・レイテンシ削減）
- コマンド実行エラー（プロセス起動失敗、タイムアウト）が発生した場合、ループを即座に停止しエラーを報告
- 終了コード 127（コマンド未検出）は not met として処理し、warning ログで通知
- stdout/stderr は各 10KB まで記録（根拠記録用）
- デフォルトタイムアウト: 30 秒（`command_timeout` で変更可能）

### 生ログ保存（logging.raw_log）

`logging.raw_log: true` を設定すると、各イテレーションの実行エージェントの stream-json 出力を JSONL ファイルとして保存します。保存された生ログから `SummaryAgent` がメタデータ（使用ツール、変更ファイル、トークン数）を自動抽出します。

```yaml
task: "認証機能を実装する"
criteria:
  - "テストがパスする"
logging:
  raw_log: true
  raw_log_dir: ".e8/logs"  # デフォルト
```

| 設定 | 説明 | デフォルト |
|------|------|-----------|
| `logging.raw_log` | 生ログの保存を有効化 | `false` |
| `logging.raw_log_dir` | 保存先ディレクトリ | `.e8/logs` |

保存されるファイル: `<raw_log_dir>/iteration-<N>.jsonl`

### 生出力参照（raw_output_context）

`raw_output_context: 1` を設定すると、直前イテレーションの実行エージェントの生出力を次のイテレーションに渡します。サマリ化では失われる詳細情報を保持したい場合に有効です。

| 値 | 動作 |
|----|------|
| `0`（デフォルト） | 生出力を参照しない |
| `1` | 直前1イテレーションの生出力を参照 |

```yaml
task: "テストカバレッジを改善する"
criteria:
  - "カバレッジ90%以上"
max_iterations: 10
raw_output_context: 1
```

- 初回イテレーション時は前回出力がないため、生出力セクションはプロンプトに含まれません
- resume 時は `output.md` から前回出力を復元します（ファイルが存在しない場合は初回イテレーションと同様に省略されます）

### 判定フィードバック

判定エージェントが未完了と判定した場合、`suggested_next_action`（次のアクション提案）が次のイテレーションの実行エージェントに自動的に注入されます。これにより、実行エージェントは同じアプローチを繰り返すのではなく、判定エージェントの提案に基づいて根本的に異なる手法を試みることができます。

実行エージェントのプロンプトに以下のセクションが追加されます：

```
## 前回の判定フィードバック
セグメント化篩やビット操作など、根本的に異なるアルゴリズムを検討してください。
```

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
