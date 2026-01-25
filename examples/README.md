# endless8 設定ファイル例

このディレクトリには、endless8 で使用できる YAML 設定ファイルのサンプルが含まれています。

## 使用方法

```bash
e8 run --config examples/api-implementation.yaml
```

CLI オプションで設定値を上書きすることもできます：

```bash
e8 run --config examples/api-implementation.yaml --max-iterations 20
```

## サンプルファイル

| ファイル | 説明 |
|---------|------|
| `api-implementation.yaml` | API 実装タスク |
| `research.yaml` | リサーチ・調査タスク |
| `refactoring.yaml` | リファクタリングタスク |
| `advanced.yaml` | 全オプションを含む詳細設定 |
| `haiku-creation.yaml` | 俳句作成タスク（緩いcriteria + 厳しいjudgment パターン） |
| `tanka-chain.yaml` | 連作短歌作成タスク |
| `logic-puzzle.yaml` | 論理パズル解答タスク |
| `test-cov.yaml` | テストカバレッジ改善タスク |

## CLI オプション一覧

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--task` | `-t` | タスクの説明 |
| `--criteria` | `-c` | 完了条件（複数指定可） |
| `--max-iterations` | `-m` | 最大イテレーション数 |
| `--config` | | YAML設定ファイル |
| `--project` | `-p` | プロジェクトディレクトリ |
| `--resume` | `-r` | タスクIDを指定して再開 |
| `--verbose` | `-V` | 詳細な実行ログを表示 |

## 設定オプション一覧

### 必須

- `task`: タスクの説明
- `criteria`: 完了条件（リスト）

### オプション

- `max_iterations`: 最大イテレーション数（デフォルト: 10）
- `agent_model`: エージェントが使用するモデル（デフォルト: `anthropic:claude-sonnet-4-5`）
- `persist`: 履歴ファイルパス（文字列）
  - 省略時も `.e8/tasks/<task_id>/history.jsonl` に自動保存される
- `knowledge`: ナレッジファイルパス（デフォルト: `.e8/knowledge.jsonl`）
- `history_context_size`: 参照する履歴件数（デフォルト: 5）
- `knowledge_context_size`: 参照するナレッジ件数（デフォルト: 10）

### ロギング（`logging`）

- `raw_log`: 生ログを保存するか（デフォルト: false）
- `raw_log_dir`: 生ログ保存先（デフォルト: `.e8/logs`）

### Claude CLI オプション（`claude_options`）

- `allowed_tools`: 許可するツール（デフォルト: `["Read", "Edit", "Write", "Bash"]`）
- `model`: 使用するモデル（デフォルト: `sonnet`）
- `output_format`: 出力形式（デフォルト: `stream-json`）
- `verbose`: 詳細出力（デフォルト: true）
- `timeout`: SDKクエリのタイムアウト秒数（デフォルト: 300.0、範囲: 30〜3600）

### プロンプト（`prompts`）

- `judgment`: 判定エージェントのカスタムプロンプト
- `append_system_prompt`: 実行エージェントに追加するプロンプト
