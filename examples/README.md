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
| `ci-pipeline.yaml` | CI パイプラインタスク（コマンド条件のみ） |
| `code-quality.yaml` | コード品質改善タスク（意味的 + コマンド混在条件） |
| `database-migration.yaml` | DB マイグレーションタスク（混在条件の実践例） |

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
| `--command-timeout` | | コマンド条件のデフォルトタイムアウト秒（デフォルト: 30） |

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
- `command_timeout`: コマンド条件のデフォルトタイムアウト秒（デフォルト: 30）

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

## 構造化された完了条件（Structured Criteria）

完了条件には「意味的条件」と「コマンド条件」の2種類を指定できます。

### 意味的条件（従来と同じ）

文字列で指定した条件は LLM が判定します：

```yaml
criteria:
  - "コードが読みやすい"
  - "テストカバレッジが十分である"
```

### コマンド条件

シェルコマンドの終了コードで条件を判定します（0 = met, 非ゼロ = not met）：

```yaml
criteria:
  - type: command
    command: "uv run pytest"
    description: "全テストがパス"     # 任意: 人間向けの説明
    timeout: 120                      # 任意: コマンド固有のタイムアウト（秒）
```

### 混在

1つのタスクに両方の条件を混在できます。コマンド条件が先に実行され、
その結果は意味的条件の LLM 判定時にコンテキストとして提供されます：

```yaml
criteria:
  - "コードが読みやすい"                        # LLM 判定
  - type: command
    command: "uv run pytest --tb=short"         # 終了コード判定
    description: "テスト全パス"
```

### コマンド条件のみ（LLM 判定省略）

すべての条件がコマンド型の場合、LLM 判定は完全に省略されます（`ci-pipeline.yaml` 参照）：

```yaml
criteria:
  - type: command
    command: "uv run ruff check ."
    description: "リンターパス"
  - type: command
    command: "uv run pytest"
    description: "テストパス"
```

### タイムアウト設定

| 設定 | 説明 |
|------|------|
| `command_timeout` | コマンド条件のデフォルトタイムアウト（秒、デフォルト: 30） |
| `--command-timeout` | CLI からの指定（config の `command_timeout` を上書き） |
| 各条件の `timeout` | 個別コマンドのタイムアウト（`command_timeout` より優先） |

### エラー処理

- プロセス起動失敗（OSError）: ループ停止、エラー報告
- タイムアウト: ループ停止、エラー報告
- 終了コード 127（コマンド未検出）: not met として処理（warning ログ出力）
- stdout/stderr は各最大 10KB 記録

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
