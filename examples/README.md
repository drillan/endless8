# endless8 設定ファイル例

このディレクトリには、endless8 で使用できる YAML 設定ファイルのサンプルが含まれています。

## 使用方法

```bash
e8 run --config examples/basic.yaml
```

CLI オプションで設定値を上書きすることもできます：

```bash
e8 run --config examples/basic.yaml --max-iterations 20
```

## サンプルファイル

| ファイル | 説明 |
|---------|------|
| `basic.yaml` | 最小限の基本設定 |
| `api-implementation.yaml` | API 実装タスク |
| `research.yaml` | リサーチ・調査タスク |
| `refactoring.yaml` | リファクタリングタスク |
| `advanced.yaml` | 全オプションを含む詳細設定 |

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
- `persist`: 履歴ファイルパス（文字列、省略時は永続化なし）
  - 例: `.e8/history.jsonl`
- `knowledge`: ナレッジファイルパス（デフォルト: `.e8/knowledge.jsonl`）
- `history_context_size`: 参照する履歴件数（デフォルト: 5）

### ロギング（`logging`）

- `raw_log`: 生ログを保存するか（デフォルト: false）
- `raw_log_dir`: 生ログ保存先（省略時はタスクディレクトリ内）

### Claude CLI オプション（`claude_options`）

- `allowed_tools`: 許可するツール
- `model`: 使用するモデル（デフォルト: `sonnet`）
- `output_format`: 出力形式（デフォルト: `stream-json`）
- `verbose`: 詳細出力（デフォルト: true）

### プロンプト（`prompts`）

- `judgment`: 判定エージェントのカスタムプロンプト
- `append_system_prompt`: 実行エージェントに追加するプロンプト
