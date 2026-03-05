# Research: 構造化された完了条件

## R-001: Pydantic 判別化ユニオンによる criteria 型の拡張

**Decision**: `Annotated[str | CommandCriterion, Discriminator(fn)]` を使用

**Rationale**:
- Pydantic v2 の `Discriminator` + カスタム関数パターンにより、プリミティブ型（str）と構造化モデル（CommandCriterion）の混在リストを型安全に処理できる
- 判別関数が `isinstance(v, str)` で文字列を自動的に意味的条件と判定するため、既存の `list[str]` 指定が後方互換で動作する
- 判別不可能な値（数値など）に対しては Pydantic が自動的に `ValidationError` を発生させる（エラー隠蔽なし）

**Alternatives considered**:
1. **`Union[str, SemanticCriterion, CommandCriterion]`（Discriminator なし）**: Pydantic が left-to-right で試行するため非決定的。却下
2. **SemanticCriterion モデルを独立定義**: 文字列をラップするだけの意味のないモデルになる。str を直接使用し、CommandCriterion のみモデル化する方がシンプル。却下
3. **`criteria: list[str]` を維持し、コマンド条件を別フィールドで定義**: FR-004（文字列のみ = 意味的条件）と矛盾せず実装可能だが、条件の順序関係が失われる。却下

## R-002: コマンド実行の実装方式

**Decision**: `asyncio.create_subprocess_shell` + `asyncio.wait_for` によるタイムアウト制御

**Rationale**:
- ユーザー指定のシェルコマンドはパイプやリダイレクトを含む可能性があるため、shell=True が必要
- `asyncio.wait_for` で `communicate()` をラップすることでタイムアウトを実装
- タイムアウト時は `proc.kill()` + `proc.wait()` で確実にプロセスを回収

**Alternatives considered**:
1. **`asyncio.create_subprocess_exec`**: shell 機能（パイプ等）が使えない。ユーザーが指定するコマンドには不適。却下
2. **`subprocess.run`（同期）**: asyncio イベントループをブロックする。却下
3. **`start_new_session=True` でプロセスグループ管理**: 初期実装では過剰。将来の拡張として検討

## R-003: コマンド実行エラーの分類（FR-009）

**Decision**: 「実行エラー」と「コマンド失敗」を明確に区別

**Rationale**:
- 仕様 FR-009 により、実行エラー（プロセス起動失敗、タイムアウト）はループを即座に停止
- コマンドが正常に起動し終了コードを返した場合は実行エラーではない（終了コード != 0 でも not met として正常処理）
- `create_subprocess_shell` では「コマンド未検出」は shell が返す終了コード 127 として表現されるため、shell 起動自体の OSError のみを実行エラーとして扱う

**区分**:
| シナリオ | 分類 | 対応 |
|---------|------|------|
| shell 起動失敗（OSError） | 実行エラー | ループ停止 |
| タイムアウト | 実行エラー | ループ停止 |
| 終了コード 0 | met | 正常処理 |
| 終了コード != 0（127 含む） | not met | 正常処理 |

**Alternatives considered**:
1. **終了コード 127 を実行エラーとして扱う**: shell が返す 127 は「コマンド未検出」を示すが、仕様は「コマンドプロセスが正常に起動し終了コードを返した場合は実行エラーとはみなさない」と明記。却下

## R-004: 判定フェーズへのコマンド実行の組み込み位置

**Decision**: Engine の判定フェーズ内で、サマリ完了後・LLM 判定前にコマンドを実行

**Rationale**:
- 仕様 FR-005: コマンドは「各イテレーションの判定フェーズで実行」
- 仕様 Assumptions: 「実行エージェント → サマリ → コマンド検証 → LLM 判定の順」
- コマンド結果は ExecutionSummary には含めない（仕様 Assumptions）
- コマンド結果は JudgmentContext に新フィールドとして追加し、LLM 判定のコンテキストとして提供

**フロー**:
```
実行エージェント → サマリエージェント → [コマンド実行] → 判定エージェント（LLM）
                                         ↓
                                    CommandResult[]
                                         ↓
                                  JudgmentContext に追加
```

**Alternatives considered**:
1. **コマンド結果を ExecutionSummary に含める**: 仕様が明示的に否定（「ExecutionSummary は実行エージェントの作業記録であり、判定フェーズの結果は別管理」）。却下
2. **コマンド実行を独立エージェントとして実装**: Art.3（4 エージェント構成）に違反。コマンド実行は判定的（LLM 不要）であり、エージェントとして実装する理由がない。却下

## R-005: コマンド条件のみのタスクにおける LLM 判定スキップ（FR-010）

**Decision**: criteria に意味的条件が 1 つもない場合、JudgmentAgent の呼び出しを省略

**Rationale**:
- FR-010: 「コマンド条件のみのタスクでは、LLM 判定エージェントの呼び出しを省略できなければならない」
- コマンド条件の判定は確定的（確信度 1.0）であり、LLM を呼ぶ必要がない
- LLM 呼び出しのコスト削減にもなる

**実装方針**:
- Engine 内で criteria を走査し、意味的条件の有無を判定
- 意味的条件がない場合、コマンド結果のみで JudgmentResult を構築して返す
- 意味的条件がある場合、従来通り JudgmentAgent を呼び出す

## R-006: 親仕様 FR-008 との整合性（JudgmentContext の拡張）

**Decision**: JudgmentContext に `command_results` フィールドを追加（オプショナル）

**Rationale**:
- 親仕様 FR-008: 「判定エージェントは ExecutionSummary のみを情報源として受け取る」
- 002 仕様 FR-007: 「コマンド条件の判定結果は、意味的条件の LLM 判定時にコンテキストとして提供」
- ExecutionSummary を変更せず、JudgmentContext に新フィールドを追加することで、親仕様の意図を尊重しつつ拡張

**変更**:
```python
class JudgmentContext(BaseModel):
    task: str
    criteria: list[str]  # 意味的条件のテキストのみ（コマンド条件は除外）
    execution_summary: ExecutionSummary
    command_results: list[CommandCriterionResult] | None = None  # NEW
    custom_prompt: str | None = None
```

## R-007: コマンド出力の記録とサイズ制限

**Decision**: stdout, stderr それぞれ 10KB に制限。超過分は末尾に `[... truncated ...]` を付加して切り捨て

**Rationale**:
- 仕様 Edge Cases: 「根拠として記録する出力は 10KB に制限する」
- `communicate()` で全出力を取得後、バイト数で切り捨て
- UTF-8 境界でのバイト切り捨ての安全性は `errors='replace'` で対応

**定数定義**:
- `COMMAND_OUTPUT_MAX_BYTES = 10 * 1024`（設定ファイルで管理）
