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
- `history_context_size`: 参照する履歴件数（デフォルト: 5）
- `knowledge_context_size`: 参照するナレッジ件数（デフォルト: 10）
- `raw_output_context`: 直前イテレーションの生出力参照の有効化（デフォルト: 0）
  - `0`: 生出力を参照しない（デフォルト）
  - `1`: 直前イテレーションの生出力を実行エージェントに渡す

### ロギング（`logging`）

- `raw_log`: 生ログを保存するか（デフォルト: false）
- `raw_log_dir`: 生ログ保存先（省略時はタスクディレクトリ内）

### Claude CLI オプション（`claude_options`）

- `allowed_tools`: 許可するツール（デフォルト: `["Read", "Edit", "Write", "Bash"]`）
- `model`: 使用するモデル（デフォルト: `sonnet`）
- `output_format`: 出力形式（デフォルト: `stream-json`）
- `verbose`: 詳細出力（デフォルト: true）
- `timeout`: SDKクエリのタイムアウト秒数（デフォルト: 300.0、範囲: 30〜3600）

### プロンプト（`prompts`）

- `judgment`: 判定エージェントのカスタムプロンプト
- `append_system_prompt`: 実行エージェントに追加するプロンプト

## 詳細: raw_output_context（生出力参照）

### 背景

endless8 はイテレーション間の情報をサマリエージェントが圧縮して履歴に保存します。
この圧縮により、テスト出力の詳細やエラーメッセージの全文など、次のイテレーションで
有用な情報が失われることがあります。

`raw_output_context` を有効にすると、直前イテレーションの生出力（圧縮前）を
次の実行エージェントに渡すことで、この情報損失を補います。

### 設定値

| 値 | 動作 |
|----|------|
| `0`（デフォルト） | 生出力を参照しない。履歴サマリのみで動作 |
| `1` | 直前イテレーションの生出力を実行エージェントのプロンプトに含める |

### 動作の仕組み

1. 各イテレーション完了後、出力を `.e8/tasks/<task-id>/output.md` に保存
2. 次のイテレーション開始時、このファイルを読み込んでプロンプトに注入
3. `--resume` でタスクを再開した場合も、保存済みの `output.md` から自動復元

### 使用例

```yaml
task: "テストカバレッジを90%以上にする"
criteria:
  - "pytest --cov で90%以上"
  - "すべてのテストがパスする"
max_iterations: 10
raw_output_context: 1  # 前回のテスト出力を参照して効率的に改善
```

### 推奨ユースケース

- テストカバレッジ改善（テスト実行結果の詳細が必要）
- デバッグ・エラー修正（エラーメッセージの全文が必要）
- 段階的なコード生成（前回出力の構造を正確に把握したい）

### 注意事項

- 初回イテレーションでは前回出力が存在しないため、生出力セクションは省略されます
- 生出力はサマリと異なり圧縮されないため、コンテキストの消費量が増加します
