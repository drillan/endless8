# Quickstart: 構造化された完了条件

## 概要

この機能により、endless8 のタスク完了条件として「意味的条件」と「コマンド条件」を組み合わせて指定できます。

## 基本的な使い方

### 1. 意味的条件のみ（従来と同じ）

```yaml
task: "README.md を更新する"
criteria:
  - "インストール手順が記載されている"
  - "使用例が含まれている"
```

文字列で指定された条件は LLM が判定します。

### 2. コマンド条件のみ

```yaml
task: "テストを修正する"
criteria:
  - type: command
    command: "uv run pytest"
    description: "全テストがパスする"
  - type: command
    command: "uv run pytest --cov=endless8 --cov-fail-under=90"
    description: "カバレッジが90%以上"
```

コマンドの終了コードで判定します（0 = met, 非ゼロ = not met）。
コマンド条件のみの場合、LLM は呼び出されません。

### 3. 混在（意味的 + コマンド）

```yaml
task: "認証機能を実装する"
criteria:
  - "コードが読みやすく、適切なコメントがある"
  - type: command
    command: "uv run pytest tests/test_auth.py"
    description: "認証テストがパスする"
  - type: command
    command: "uv run mypy src/"
    description: "型チェックがパスする"
```

コマンド条件はコマンドで判定され、意味的条件は LLM で判定されます。
LLM はコマンドの結果も参照して判定品質を向上させます。

## コマンド条件の動作

### 実行タイミング

各イテレーションの判定フェーズで実行されます:

```
実行エージェント → サマリエージェント → [コマンド実行] → 判定エージェント（LLM）
```

### エラー処理

- **shell 起動失敗（OSError）**: ループが停止し、エラーが報告されます
- **タイムアウト**: ループが停止し、エラーが報告されます
- **終了コード != 0**: 条件は「not met」として処理されます（エラーではない）。コマンド未検出（終了コード 127）もこのカテゴリに含まれます。コマンド名の typo による意図しない「not met」を早期発見するため、終了コード 127 の場合は warning ログを出力します

### 出力の記録

コマンドの標準出力・標準エラー出力は判定の根拠として記録されます（最大 10KB）。

## 設定

```yaml
# e8.yaml
command_timeout: 30  # コマンドのデフォルトタイムアウト（秒）。デフォルト: 30秒
```

個別のコマンドにタイムアウトを指定することもできます:

```yaml
criteria:
  - type: command
    command: "uv run pytest"
    description: "テスト実行"
    timeout: 120  # このコマンドのみ 120 秒
```
