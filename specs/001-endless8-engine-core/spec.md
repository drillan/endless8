# Feature Specification: endless8 エンジンコア機能

**Feature Branch**: `001-endless8-engine-core`
**Created**: 2026-01-23
**Status**: Draft
**Input**: User description: "docs/architecture.md, README.md をもとに仕様を定義"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 基本タスク実行 (Priority: P1)

開発者として、タスクと完了条件を指定してエンジンを実行し、完了条件が満たされるまで自動的に処理を繰り返してほしい。

**Why this priority**: これがエンジンの最も基本的な機能であり、他のすべての機能の基盤となる

**Independent Test**: タスク「テストカバレッジを90%以上にする」と完了条件「pytest --cov で90%以上」を指定して実行し、カバレッジ目標が達成されることを確認

**Acceptance Scenarios**:

1. **Given** エンジンが初期化されている, **When** ユーザーがタスクと完了条件を指定して実行する, **Then** 完了条件を満たすまでループ処理が行われ、結果が返される
2. **Given** タスクが実行中, **When** 完了条件が満たされた, **Then** ループが終了し成功結果が返される
3. **Given** タスクが実行中, **When** 最大イテレーション数に到達した, **Then** ループが終了し未完了の理由とともに結果が返される

---

### User Story 2 - 曖昧な完了条件の明確化 (Priority: P2)

開発者として、曖昧な完了条件を指定した場合に、エンジンが質問を生成してくれることで、適切な条件を設定したい。

**Why this priority**: 曖昧な条件では正確な判定ができないため、明確化の仕組みが重要

**Independent Test**: 曖昧な完了条件「十分に高速になったら完了」を指定し、受付エージェントが明確化の質問を生成することを確認

**Acceptance Scenarios**:

1. **Given** 曖昧な完了条件が指定された, **When** 受付エージェントが条件を分析する, **Then** 明確化のための質問が生成される
2. **Given** 質問に対してユーザーが回答した, **When** 回答が処理される, **Then** 明確化された完了条件でタスクが実行される

---

### User Story 3 - 履歴参照によるコンテキスト効率化 (Priority: P2)

開発者として、長時間のタスク実行でもコンテキスト枯渇を起こさずに、過去の実行履歴を効率的に参照して処理を継続したい。

**Why this priority**: Ralph Wiggum からの主要な改良点であり、長時間タスクの安定性に直結

**Independent Test**: 10イテレーション以上のタスクを実行し、履歴がサマリ化されて効率的に参照されることを確認

**Acceptance Scenarios**:

1. **Given** 複数のイテレーションが完了している, **When** 次のイテレーションが開始される, **Then** サマリ化された履歴がコンテキストとして注入される
2. **Given** 実行エージェントが履歴を参照している, **When** 過去に失敗したアプローチがある, **Then** 同じアプローチを繰り返さずに改善された方法を試みる

---

### User Story 4 - 履歴の永続化と再開 (Priority: P3)

開発者として、タスク実行を中断しても、後から履歴を読み込んで続きから再開したい。

**Why this priority**: 長時間タスクや不測の中断に対応するために必要

**Independent Test**: タスクを途中で中断し、履歴ファイルから再開して最終的に完了することを確認

**Acceptance Scenarios**:

1. **Given** persist_history オプションが指定されている, **When** 各イテレーションが完了する, **Then** 履歴がファイルに保存される
2. **Given** 履歴ファイルが存在する, **When** 同じ設定でエンジンを再実行する, **Then** 履歴が読み込まれて途中から再開される

---

### User Story 5 - CLI からの実行 (Priority: P3)

開発者として、コマンドラインからタスクを実行し、進捗を確認したい。

**Why this priority**: Python APIだけでなく、CLIからの利用もサポートすることで利便性が向上

**Independent Test**: `e8 run "タスク" --criteria "条件"` コマンドを実行し、結果が表示されることを確認

**Acceptance Scenarios**:

1. **Given** CLIがインストールされている, **When** ユーザーがrunコマンドを実行する, **Then** タスクが実行され結果が表示される
2. **Given** --config オプションが指定されている, **When** 設定ファイルが読み込まれる, **Then** ファイルの設定に基づいてタスクが実行される

---

### User Story 6 - 非プログラミングタスク（リサーチ） (Priority: P2)

研究者・開発者として、プログラミング以外のタスク（論文検索、調査、ドキュメント作成など）もエンジンで実行し、完了条件に基づいて自動的に処理を繰り返してほしい。

**Why this priority**: エンジンの汎用性を示し、プログラミング以外のユースケースもサポートする

**Independent Test**: タスク「プロンプト最適化に関する論文を検索」と完了条件「3件以上の関連論文を発見し、概要をまとめる」を指定して実行し、条件を満たす結果が得られることを確認

**Acceptance Scenarios**:

1. **Given** エンジンが初期化されている, **When** ユーザーがリサーチタスクと完了条件を指定して実行する, **Then** 完了条件を満たすまでループ処理が行われ、結果が返される
2. **Given** リサーチタスクが実行中, **When** 指定された件数・条件を満たす情報が収集された, **Then** ループが終了し成功結果が返される
3. **Given** リサーチタスクが実行中, **When** 判定エージェントが結果を評価する, **Then** 収集した情報が条件を満たしているかどうかが判定される
4. **Given** リサーチタスクが実行完了した, **When** テキスト成果物が生成された, **Then** 成果物が`.e8/tasks/<task-id>/output.md`にファイルとして保存され、artifactsにパスが記録される

---

### Edge Cases

- 完了条件が一つも満たされないままイテレーションが継続する場合、最大イテレーション数に到達してループが終了する
- 実行エージェントでエラーが発生した場合、即座のリトライは行わず、エラーを履歴に記録して次のイテレーションで別のアプローチを試みる
- 複数の完了条件が指定されている場合、すべての条件が満たされるまでループが継続する
- ユーザーが明確化の質問に回答しない場合、タスクは実行されない
- `--project` で存在しないディレクトリを指定した場合、エラーを表示して終了する
- プロジェクトディレクトリに `.e8/` が存在しない場合、自動的に作成して処理を続行する

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: システムはタスク（自然言語）と完了条件（自然言語、単一または複数）を受け取って処理を開始できなければならない
- **FR-002**: 受付エージェントは完了条件の妥当性をチェックし、測定可能かどうかを評価しなければならない
- **FR-003**: 受付エージェントは曖昧な完了条件に対して明確化のための質問を生成しなければならない
- **FR-004**: 実行エージェントはタスク実行に専念し、完了判定は行わない（責務分離）
- **FR-005**: 実行エージェントは履歴を参照して過去の失敗を回避しなければならない。参照範囲は直近N件（`history_context_size`で設定、デフォルト: 5件）+ 過去の失敗履歴（DuckDBでフィルタリング）とする
- **FR-006**: サマリエージェントはpydantic-aiのAgentを使用し、LLMによる知的要約で実行結果を圧縮しなければならない。入力として完了条件（criteria）を受け取り、各条件に関連する情報を優先的に要約に含める。判定エージェントが各完了条件を評価するために十分な情報（具体的な成果内容、数値、根拠）を保持しつつ、冗長な記述を削減する。`reason`フィールドの目標サイズは最大1000トークンとし、LLMのコンテキスト消費量で制御する
- **FR-007**: サマリエージェントは各イテレーションの結果を履歴に保存しなければならない
- **FR-008**: 判定エージェントはExecutionSummaryのみを情報ソースとして各完了条件を個別に評価し、判定理由を説明しなければならない。サマリエージェントが判定に十分な情報を含む要約を生成する責務を負う
- **FR-009**: 判定エージェントは未完了の場合に次のアクションを提案しなければならない
- **FR-010**: システムは最大イテレーション数（デフォルト: 10回）に到達した場合にループを終了しなければならない
- **FR-011**: システムは履歴をJSONL形式で永続化できなければならない
- **FR-012**: システムは永続化された履歴から実行を再開できなければならない
- **FR-013**: システムはCLIからタスクを実行できなければならない
- **FR-014**: システムはYAML形式の設定ファイルをサポートしなければならない
- **FR-015**: 実行エージェントはMCPサーバーと連携できなければならない
- **FR-016**: 実行エージェントはAgent Skillsを活用できなければならない
- **FR-017**: 設定ファイルでclaudeコマンドに渡すallowed_toolsを定義できなければならない
- **FR-018**: システムはオプションで実行エージェントの生ログ（stream-json出力）を保存できなければならない
- **FR-019**: 設定ファイルで判定エージェントのプロンプト（判定基準）をカスタマイズできなければならない
- **FR-020**: サマリエージェントは実行結果からナレッジ（発見、教訓、パターン）を抽出し、各イテレーション終了時に即座にknowledge.jsonlへ追記しなければならない
- **FR-021**: 実行エージェントは各イテレーション開始時にナレッジベース（knowledge.jsonl）を参照して、過去の学習を活用しなければならない
- **FR-022**: CLIはカレントディレクトリをデフォルトのプロジェクトディレクトリとし、`--project` オプションで明示的に上書きできなければならない
- **FR-023**: システムは `.e8/` ディレクトリが存在しない場合、自動的に作成しなければならない
- **FR-024**: パッケージは `uv tool install git+https://github.com/drillan/endless8.git` でインストール可能でなければならない
- **FR-025**: 実行エージェントは各イテレーション終了時にセマンティックメタデータ（approach, strategy_tags, discoveries）をJSON形式で報告しなければならない（append_system_prompt経由で指示）
- **FR-026**: サマリエージェントは各イテレーション終了後、即座にstream-jsonから機械的メタデータを抽出し、実行エージェントの報告と統合してExecutionSummaryを生成しなければならない
- **FR-027**: CLIは `--max-iterations <N>` オプションで最大イテレーション数を指定できなければならない（YAML設定より優先）
- **FR-028**: CLIはタスク完了時にステータス、判定理由、成果物リストを表示しなければならない
- **FR-029**: CLIは `--resume` オプションで最新タスクを再開、`--resume <task-id>` で特定タスクを再開できなければならない
- **FR-030**: システムはタスクごとにディレクトリを作成し、履歴と生ログをタスク単位で分離しなければならない（`.e8/tasks/<task-id>/`）
- **FR-031**: CLIは `e8 list` コマンドでタスク一覧を表示できなければならない
- **FR-032**: システムは各イテレーション終了時に判定結果（JudgmentResult）を history.jsonl に `type: "judgment"` として即座に保存しなければならない
- **FR-033**: システムはタスク終了時（completed, max_iterations, error, cancelled のいずれの場合も）に最終結果（LoopResult）を history.jsonl に `type: "final_result"` として保存しなければならない
- **FR-034**: CLIは `--verbose` オプションで、実行中のツールコールとテキスト応答をリアルタイム表示できなければならない
  - ツールコール: `→ ツール名` 形式
  - テキスト応答: `📝 テキスト...` 形式（先頭80文字）

### Key Entities

- **Engine**: メインのエンジンクラス。タスク実行の全体を制御し、4つのエージェントを調整する
- **IntakeResult**: 受付エージェントの出力。タスクと完了条件の構造化、明確化質問を含む
- **ExecutionResult**: 実行エージェントの出力。実行状況、結果、生成物を含む
- **ExecutionSummary**: サマリエージェントの出力。基本フィールド（iteration, approach, result, reason, artifacts）に加え、metadata（ツール使用、変更ファイル等）、next（次のタスク用情報）を含む
- **Knowledge**: 永続的なナレッジエントリ。タイプ: discovery（発見）, lesson（教訓）, pattern（共通パターン）, constraint（制約）, codebase（構造知見）
- **JudgmentResult**: 判定エージェントの出力。完了判定、各条件の評価、次のアクション提案を含む
- **History**: 履歴を管理するクラス。サマリのリストを保持し、コンテキスト生成と永続化を担当
- **KnowledgeBase**: ナレッジを管理するクラス。タスク単位で永続化
- **LoopResult**: ループ全体の最終結果。成功/失敗、理由、履歴を含む

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 明確な完了条件を持つ単純なタスクは、3イテレーション以内に完了する
  - 測定方法: `tests/integration/test_loop_execution.py` で「ファイル作成」などの単純タスクを実行し、イテレーション数を検証
- **SC-002**: 50イテレーション以上の長時間タスクでもコンテキスト枯渇が発生しない
  - 測定方法: 手動テストまたは専用の長時間テストスクリプトで検証（CI では除外）
- **SC-003**: 履歴のサマリ化により、各イテレーションのコンテキストサイズが100,000 tokens以下に収まる
  - 測定方法: ExecutionSummary.metadata.tokens_used を監視し、上限超過時にログ警告を出力
- **SC-004**: 曖昧な完了条件の90%以上に対して、適切な明確化質問が生成される
- **SC-005**: 中断されたタスクの100%が、履歴から正常に再開できる
- **SC-006**: CLIからの実行結果がPython APIからの実行結果と同等である
- **SC-007**: 各エージェントの責務が明確に分離され、単体テストが可能である

## Technical Context

本システムは以下の技術スタックを使用する：

- **claudecode-model**: pydantic-ai 用の Claude Code アダプタ。claude コマンド（Claude Code CLI）を介して Claude を呼び出す
- **pydantic-ai**: 各エージェント（受付、実行、サマリ、判定）の実装に使用する AI エージェントフレームワーク
- **claude コマンド**: Claude Code CLI。実行エージェントはこのコマンドを通じて MCP サーバーや Agent Skills にアクセスする
- **DuckDB**: JSONL形式の履歴・ナレッジファイルを効率的にクエリするためのインプロセスSQL OLAPデータベース

### データの3層構造

| 層 | ファイル | スコープ | 内容 | 用途 |
|----|---------|---------|------|------|
| 履歴 | `.e8/tasks/<task-id>/history.jsonl` | タスク単位 | ExecutionSummary | 次イテレーションへのコンテキスト注入 |
| ナレッジ | `.e8/tasks/<task-id>/knowledge.jsonl` | タスク単位 | 発見、教訓、パターン | 各イテレーション開始時に参照 |
| 生ログ | `.e8/tasks/<task-id>/logs/iteration-NNN.jsonl` | イテレーション単位 | stream-json全出力 | デバッグ・監査（オプション） |

**タスク ID**: タイムスタンプ形式（例: `2026-01-23T13-30-00`）で生成。各タスク実行時に新しいディレクトリが作成される。

実行エージェントは `--output-format stream-json --verbose` でclaude CLIを呼び出し、サマリエージェントがその出力を解析してExecutionSummaryとKnowledgeを生成する。サマリエージェントはpydantic-aiのAgentを使用し、LLMによる知的要約で`reason`フィールドを生成する（機械的切詰は行わない）。機械的メタデータ（tools_used, files_modified, tokens_used）はstream-jsonから直接抽出し、LLM要約と統合する。

### ExecutionSummary構造

```json
{
  "type": "summary",
  "iteration": 3,
  "approach": "テストを修正",
  "result": "success",
  "reason": "全テストパス",
  "artifacts": ["tests/test_main.py"],
  "metadata": {
    "tools_used": ["Read", "Edit", "Bash(pytest)"],
    "files_modified": ["src/main.py"],
    "error_type": null,
    "tokens_used": 15000,
    "strategy_tags": ["test-fix"]
  },
  "next": {
    "suggested_action": "カバレッジを確認",
    "blockers": [],
    "partial_progress": "認証機能の実装完了",
    "pending_items": ["カバレッジ確認"]
  }
}
```

### JudgmentResult構造（履歴保存用）

```json
{
  "type": "judgment",
  "iteration": 3,
  "is_complete": false,
  "evaluations": [
    {
      "criterion": "pytest --cov で90%以上",
      "is_met": false,
      "evidence": "現在のカバレッジは85%",
      "confidence": 0.95
    }
  ],
  "overall_reason": "カバレッジが目標に達していない",
  "suggested_next_action": "未カバーの関数にテストを追加",
  "timestamp": "2026-01-23T10:05:00Z"
}
```

### LoopResult構造（最終結果）

```json
{
  "type": "final_result",
  "status": "completed",
  "iterations_used": 3,
  "final_judgment": {
    "is_complete": true,
    "overall_reason": "すべての完了条件を満たした"
  },
  "timestamp": "2026-01-23T10:10:00Z"
}
```

### Knowledge構造

```json
{
  "type": "pattern",
  "category": "error_handling",
  "content": "例外はAppErrorを継承したカスタム例外を使用",
  "example_file": "src/errors.py:15-30",
  "source_task": "認証機能実装",
  "confidence": "high",
  "applied_count": 3,
  "created_at": "2026-01-23T10:00:00Z"
}
```

**ナレッジタイプ:**
- `discovery`: コードベースの事実（「認証はsrc/auth/で処理」）
- `lesson`: 失敗から学んだ教訓（「型エラーは依存関係更新で解決」）
- `pattern`: コーディング規約・慣習（「エラーはAppErrorを継承」）
- `constraint`: 技術的制約（「Python 3.13以上が必要」）
- `codebase`: 構造的な知見（「tests/unit/とintegration/に分離」）

### メタデータ取得のハイブリッドアプローチ

| メタデータ | 取得元 | 理由 |
|-----------|--------|------|
| `tools_used` | stream-json | 機械的に確実に取得 |
| `files_modified` | stream-json | 機械的に確実に取得 |
| `tokens_used` | stream-json | 機械的に確実に取得 |
| `error_type` | stream-json | エラーイベントから抽出 |
| `strategy_tags` | append_system_prompt | 実行者の意図 |
| `approach` | append_system_prompt | 実行者の意図 |
| `discoveries` | append_system_prompt | 実行者が発見を報告 |

### DuckDBによるクエリ

履歴・ナレッジファイル（JSONL）をDuckDBで直接クエリし、効率的にコンテキストを生成する。

```sql
-- 失敗したアプローチを抽出（同じ失敗を繰り返さない）
SELECT approach, reason FROM read_json_auto('.e8/history.jsonl')
WHERE type = 'summary' AND result = 'failure'

-- 高信頼度のパターンを取得
SELECT content, example_file FROM read_json_auto('.e8/tasks/<task-id>/knowledge.jsonl')
WHERE type = 'pattern' AND confidence = 'high'

-- 特定ファイルに関連する履歴を検索
SELECT * FROM read_json_auto('.e8/history.jsonl')
WHERE list_contains(metadata.files_modified, 'src/main.py')

-- イテレーション開始時のコンテキスト生成（直近N件 + 失敗履歴）
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (ORDER BY iteration DESC) as rn
  FROM read_json_auto('.e8/history.jsonl')
  WHERE type = 'summary'
)
SELECT * FROM ranked WHERE rn <= 5  -- 直近5件
UNION ALL
SELECT *, 0 as rn FROM read_json_auto('.e8/history.jsonl')
WHERE type = 'summary' AND result = 'failure' AND iteration NOT IN (
  SELECT iteration FROM ranked WHERE rn <= 5
)
```

### インストール

```bash
uv tool install git+https://github.com/drillan/endless8.git
```

インストール後、`e8` コマンドがパスに追加される。

### CLI コマンド

- **コマンド名**: `e8`（endless8 の短縮形）
- **プロジェクトディレクトリ**: カレントディレクトリをデフォルトとし、`--project <path>` オプションで上書き可能
- **タスク再開**: `--resume` で最新タスクを再開、`--resume <task-id>` で特定タスクを再開
- **使用例**:
  - `e8 run "タスクの説明" --criteria "条件1" --criteria "条件2"`
  - `e8 run --config task.yaml`
  - `e8 run "タスク" --project /path/to/project --criteria "条件"`
  - `e8 run "タスク" --max-iterations 20 --criteria "条件"`
  - `e8 run --resume` （最新タスクを再開）
  - `e8 run --resume 2026-01-23T13-30-00` （特定タスクを再開）
  - `e8 list` （タスク一覧を表示）

### YAML 設定ファイル構造

```yaml
# task.yaml
task: "タスクの説明"
criteria:
  - "完了条件1"
  - "完了条件2"

# オプション
max_iterations: 10
persist: ".e8/history.jsonl"
knowledge_context_size: 10        # 参照するナレッジの件数（デフォルト: 10）
history_context_size: 5           # 直近N件の履歴を参照（デフォルト: 5）

# ログオプション（3層構造）
logging:
  raw_log: false             # 生ログを保存（デフォルト: false）
  raw_log_dir: ".e8/logs"    # 生ログ保存先

# claude コマンドオプション
claude_options:
  allowed_tools:
    - "Read"
    - "Edit"
    - "Write"
    - "Bash(git:*)"
    - "Bash(uv:*)"
    - "mcp__context7__*"
  model: "sonnet"
  output_format: "stream-json"  # サマリエージェントが解析するため
  verbose: true

# エージェントプロンプトのカスタマイズ
prompts:
  judgment: |
    以下の基準で完了条件を厳密に評価してください：
    - テストが実際に実行され、すべてパスしていること
    - エラーログや警告がないこと
    - 指定された条件が明確に満たされていること

  # 実行エージェントに意図・発見の報告を指示（セマンティックメタデータ取得用）
  append_system_prompt: |
    各作業の最後に、以下のJSON形式で報告してください：
    ```json
    {"strategy_tags": ["タグ1"], "approach": "アプローチの説明", "discoveries": ["発見1"]}
    ```
```

## Assumptions

- pydantic-ai と claudecode-model が利用可能である
- claude コマンド（Claude Code CLI）がインストールされ、認証済みである
- Python 3.13+ 環境で実行される
- ファイルシステムへの読み書きアクセスが可能である
- MCP サーバーおよび Agent Skills の設定はユーザーの Claude Code 設定（~/.claude/）から継承される
- DuckDB が利用可能である（履歴・ナレッジのクエリに使用）

## Clarifications

### Session 2026-01-23

- Q: 実行エージェントの Claude 呼び出し方式は？ → A: claudecode-model 経由で claude コマンド（Claude Code CLI）を呼び出す
- Q: CLI コマンド名は？ → A: `e8`（endless8 の短縮形）
- Q: 履歴の永続化形式は？ → A: JSONL形式（追記効率・クラッシュ耐性のため）
- Q: コンテキストサイズの上限は？ → A: 100,000 tokens以下
- Q: エラー時のリトライ戦略は？ → A: リトライなし（履歴に記録し次イテレーションで別アプローチ）
- Q: 最大イテレーション数のデフォルト値は？ → A: 10回
- Q: ExecutionSummaryの必須フィールドは？ → A: iteration, approach, result, reason, artifacts（5フィールド）
- Q: MCP/Agent Skills設定の取得方法は？ → A: ユーザーのClaude Code設定（~/.claude/）を継承
- Q: YAML設定ファイルでallowed_toolsを定義できるか？ → A: はい、claude_options.allowed_toolsで定義可能
- Q: 実行ログの記録方式は？ → A: 2層構造（履歴: サマリのみ、生ログ: オプションでstream-json全出力を保存）
- Q: 判定エージェントのプロンプトをカスタマイズできるか？ → A: はい、prompts.judgmentで定義可能
- Q: ナレッジの永続化方式は？ → A: 3層構造（履歴: タスク単位、ナレッジ: タスク単位で別ファイル、生ログ: オプション）
- Q: ナレッジのタイプは？ → A: discovery, lesson, pattern, constraint, codebase の5タイプ
- Q: 履歴・ナレッジのクエリ方法は？ → A: DuckDBでJSONLを直接SQLクエリ
- Q: メタデータの取得方法は？ → A: ハイブリッドアプローチ（機械的データはstream-json、セマンティックデータはappend_system_prompt）
- Q: プロジェクトディレクトリの判別方法は？ → A: カレントディレクトリをデフォルトとし、`--project <path>` オプションで上書き可能
- Q: `.e8/` ディレクトリがない場合の動作は？ → A: 自動作成して処理を続行
- Q: `--project` で存在しないディレクトリを指定した場合は？ → A: エラーを表示して終了
- Q: インストール方法は？ → A: `uv tool install git+https://github.com/drillan/endless8.git`
- Q: 実行エージェントのメタデータ報告責務は？ → A: append_system_prompt経由でセマンティックメタデータ（approach, strategy_tags, discoveries）をJSON形式で報告
- Q: メタデータ記録のタイミングは？ → A: 各イテレーション終了後、サマリエージェントが即座に処理（判定エージェントがタイムリーにクエリ可能）
- Q: knowledge.jsonlの記録タイミングは？ → A: 各イテレーション終了時に即座に追記（クラッシュ耐性、次イテレーションで参照可能）
- Q: knowledge.jsonlの参照タイミングは？ → A: 各イテレーション開始時（history.jsonlと同様に毎回参照、DuckDBでフィルタリング）
- Q: history.jsonl肥大化時の参照方法は？ → A: 直近N件（デフォルト5件）+ 過去の失敗履歴をDuckDBでフィルタリング
- Q: 直近N件の設定方法は？ → A: YAML設定の`history_context_size`で定義可能（デフォルト: 5）
- Q: User Story 1 の実用的なテストタスクは？ → A: タスク「テストカバレッジを90%以上にする」、完了条件「pytest --cov で90%以上」
- Q: 非プログラミングタスクの User Story は？ → A: タスク「プロンプト最適化に関する論文を検索」、完了条件「3件以上の関連論文を発見し、概要をまとめる」
- Q: CLIで最大イテレーション数を指定できるか？ → A: `--max-iterations <N>` オプションで指定可能（YAML設定より優先）
- Q: 履歴ディレクトリ構造は？ → A: タスクごとにディレクトリを作成（`.e8/tasks/<task-id>/`）
- Q: タスク ID の生成方法は？ → A: タイムスタンプ（例: `2026-01-23T13-30-00`）
- Q: タスク再開時の ID 指定方法は？ → A: `--resume` で最新を自動選択、`--resume <task-id>` で特定タスクを指定（両方サポート）
- Q: タスク完了時の CLI 表示内容は？ → A: ステータス + 判定理由 + 成果物リスト
- Q: 古いタスクディレクトリのクリーンアップ方法は？ → A: 手動削除のみ（MVP では CLI コマンドなし）
- Q: タスク一覧表示機能は？ → A: `e8 list` コマンドでタスク一覧を表示
- Q: 実行中の進捗通知方式は？ → A: コールバック方式（Engine.run() に on_progress コールバックを渡す）
- Q: history.jsonl に保存するレコードタイプは？ → A: ExecutionSummary + JudgmentResult + LoopResult（最終結果）の3種類
- Q: JudgmentResult の保存タイミングは？ → A: 毎イテレーション終了時（判定完了後に即座に保存）
- Q: LoopResult の保存条件は？ → A: すべての終了ケース（completed, max_iterations, error, cancelled）で保存
