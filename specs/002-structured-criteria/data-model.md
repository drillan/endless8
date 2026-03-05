# Data Model: 構造化された完了条件

## Entities

### Criterion（完了条件）

仕様 FR-001 に基づく 2 種類の完了条件。

**判別化ユニオン型**:

```
CriterionInput = str | CommandCriterion
```

- `str` → 意味的条件として扱う（FR-004）
- `CommandCriterion` → コマンド条件として扱う

#### CommandCriterion

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | `Literal["command"]` | Yes | 判別子（固定値） |
| command | `str` | Yes | 実行するシェルコマンド（空文字不可） |
| description | `str \| None` | No | 人間向けの説明（FR-012） |
| timeout | `float \| None` | No | コマンド固有のタイムアウト（秒）。未指定時はグローバル設定を使用 |

**バリデーション**:
- `command` は `min_length=1`（Edge Case: 空文字は入力バリデーションで拒否）
- `type` は `Literal["command"]` で固定

#### 型判別ロジック

```python
def criterion_discriminator(v: Any) -> str:
    if isinstance(v, str):
        return "str"
    if isinstance(v, dict) and v.get("type") == "command":
        return "command"
    if isinstance(v, CommandCriterion):
        return "command"
    # 判別不可能 → ValidationError
```

---

### CriterionType（判定方式）

| Value | Description |
|-------|-------------|
| `semantic` | LLM による意味的判定 |
| `command` | コマンド終了コードによる判定 |

---

### CommandResult（コマンド実行結果）

仕様 Key Entities「コマンド実行結果」に対応。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| exit_code | `int` | Yes | 終了コード（0 = met, 非ゼロ = not met） |
| stdout | `str` | Yes | 標準出力（最大 10KB） |
| stderr | `str` | Yes | 標準エラー出力（最大 10KB） |
| execution_time_sec | `float` | Yes | 実行時間（秒） |

---

### CriteriaEvaluation（条件判定結果）拡張

既存モデル `results.py:CriteriaEvaluation` を拡張。

| Field | Type | Required | Description | New? |
|-------|------|----------|-------------|------|
| criterion | `str` | Yes | 完了条件のテキスト表現 | No |
| is_met | `bool` | Yes | 条件を満たしているか | No |
| evidence | `str` | Yes | 判定の根拠 | No |
| confidence | `float` | Yes | 確信度（0.0-1.0）。コマンド条件は常に 1.0 | No |
| evaluation_method | `CriterionType` | Yes | 判定方式（FR-013） | **Yes** |
| command_result | `CommandResult \| None` | No | コマンド実行結果（コマンド条件のみ） | **Yes** |

**バリデーション**:
- `evaluation_method == "command"` の場合、`confidence` は 1.0 でなければならない（FR-011）
- `evaluation_method == "command"` の場合、`command_result` は必須
- `evaluation_method == "semantic"` の場合、`command_result` は None

---

### CommandCriterionResult（コマンド条件の判定結果）

Engine 内部で使用。コマンド実行の結果を保持し、JudgmentContext に渡す。

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| criterion_index | `int` | Yes | criteria リスト内のインデックス |
| description | `str` | Yes | 条件の表示名（CommandCriterion.description or command） |
| command | `str` | Yes | 実行したコマンド |
| is_met | `bool` | Yes | 終了コード 0 = True |
| result | `CommandResult` | Yes | 実行結果 |

---

### TaskInput 拡張

| Field | Type | Change |
|-------|------|--------|
| criteria | `list[CriterionInput]` | `list[str]` → `list[CriterionInput]` |

その他のフィールド（`task`, `max_iterations`, `history_context_size`）は変更なし。

---

### JudgmentContext 拡張

| Field | Type | Change |
|-------|------|--------|
| criteria | `list[str]` | 変更なし（意味的条件のテキストのみ渡す） |
| command_results | `list[CommandCriterionResult] \| None` | **新規追加** |

---

### EngineConfig 拡張

| Field | Type | Change |
|-------|------|--------|
| criteria | `list[CriterionInput]` | `list[str]` → `list[CriterionInput]` |
| command_timeout | `float` | **新規追加**（デフォルト値は名前付き定数で定義） |

---

## Relationships

```
TaskInput
  └── criteria: list[CriterionInput]
        ├── str (意味的条件)
        └── CommandCriterion (コマンド条件)

Engine (判定フェーズ)
  ├── CommandExecutor.execute(CommandCriterion) → CommandResult
  │     └── CommandCriterionResult (内部表現)
  ├── CriteriaEvaluation (コマンド条件分: evaluation_method=command)
  └── JudgmentAgent.run(JudgmentContext) → JudgmentResult
        └── CriteriaEvaluation (意味的条件分: evaluation_method=semantic)

JudgmentResult
  └── evaluations: list[CriteriaEvaluation]
        ├── evaluation_method: semantic | command
        └── command_result: CommandResult | None
```

## State Transitions

```
コマンド条件の判定フロー:

  [コマンド実行開始]
       │
       ├── OSError (shell 起動失敗)
       │     └── [実行エラー] → ループ停止
       │
       ├── TimeoutError
       │     └── [実行エラー] → ループ停止
       │
       └── プロセス正常終了
             ├── exit_code == 0 → [met]
             └── exit_code != 0 → [not met]
```

## 履歴ログへの記録（FR-015）

CriteriaEvaluation に `evaluation_method` と `command_result` が追加されるため、
JudgmentResult の JSONL シリアライズ時に自動的にこれらのフィールドが含まれる。
既存の `history.append_judgment()` の変更は不要（JudgmentResult を丸ごとシリアライズしているため）。
