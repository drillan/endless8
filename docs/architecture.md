# endless8 アーキテクチャ設計

## 設計思想

### Ralph Wiggum からの改良点

**Ralph Wiggum の仕組み**:
- Claude Code CLI 内で stop-hook がセッション終了を捕捉
- 同じプロンプトを繰り返し注入
- 会話履歴が蓄積 → コンテキスト枯渇のリスク

**endless8 の改良**:
- claudecode-model 経由で外部から Claude を呼び出し
- 実行エージェントは毎回フレッシュ（コンテキストリセット）
- 履歴はサマリ化して効率的に参照
- 完了条件は自然言語で指定、AI が判定

## システム構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         endless8 Engine                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [ユーザー入力]                                                  │
│       ↓ タスク + 完了条件                                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 受付エージェント (IntakeAgent)                            │  │
│  │ - 完了条件の妥当性チェック                                 │  │
│  │ - 曖昧な条件 → ユーザーに質問                              │  │
│  │ - タスクと条件を構造化                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│       ↓ IntakeResult                                            │
│                                                                 │
│  ┌──────────────── メインループ ────────────────────────────┐  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ 実行エージェント (ExecutorAgent)                    │ │  │
│  │  │ - タスク実行に専念                                  │ │  │
│  │  │ - 履歴サマリをコンテキストとして受け取る             │ │  │
│  │  │ - MCP / Agent Skills を活用                        │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │       ↓ ExecutionResult                                  │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ サマリエージェント (SummarizerAgent)                │ │  │
│  │  │ - 実行結果を圧縮                                    │ │  │
│  │  │ - 重要な情報のみ抽出                                │ │  │
│  │  │ - 履歴ストアに保存                                  │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │       ↓ ExecutionSummary → History                       │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ 判定エージェント (JudgeAgent)                       │ │  │
│  │  │ - 完了条件を評価                                    │ │  │
│  │  │ - 各条件を個別に判定                                │ │  │
│  │  │ - 未完了時は次のアクションを提案                     │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │       ↓ JudgmentResult                                   │  │
│  │       ├→ is_complete=True → ループ終了                   │  │
│  │       └→ is_complete=False → ループ継続                  │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [LoopResult] ← 最終結果                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## データフロー

### 1. 受付フェーズ

```
入力:
  - task: str              # 自然言語のタスク記述
  - completion_criteria:   # 完了条件（自然言語）
      str | list[str]

処理:
  IntakeAgent が条件を分析
  ├→ 明確 → IntakeResult を生成
  └→ 曖昧 → clarification_needed を設定 → ユーザーに質問

出力:
  IntakeResult:
    is_valid: bool
    task: str                      # 明確化されたタスク
    completion_criteria: list[str] # 明確化された条件リスト
    clarification_needed: str?     # 質問（曖昧な場合）
```

### 2. 実行フェーズ

```
入力:
  - task: str              # 明確化されたタスク
  - criteria: list[str]    # 完了条件
  - history_context: str   # サマリ化された履歴

処理:
  ExecutorAgent がタスクを実行
  - 履歴を参照して過去の失敗を回避
  - MCP / Agent Skills を活用

出力:
  ExecutionResult:
    status: str                    # 実行状況
    output: dict[str, Any]         # 実行結果
    artifacts: list[str]           # 生成物
    notes: str?                    # 補足
```

### 3. サマリフェーズ

```
入力:
  - execution_result: ExecutionResult
  - judgment: JudgmentResult

処理:
  SummarizerAgent が結果を圧縮
  - 重要な情報のみ抽出
  - トークン効率を最適化

出力:
  ExecutionSummary:
    iteration: int
    task_performed: str            # 実行内容（簡潔）
    outcome: str                   # 結果
    artifacts_created: list[str]   # 作成したファイル
    key_decisions: list[str]       # 重要な判断
    issues_found: list[str]        # 発見した問題
```

### 4. 判定フェーズ

```
入力:
  - criteria: list[str]            # 完了条件
  - execution_result: ExecutionResult
  - history: History               # 全履歴

処理:
  JudgeAgent が条件を評価
  - 各条件を個別に判定
  - 理由を説明

出力:
  JudgmentResult:
    is_complete: bool
    criteria_met: dict[str, bool]  # 各条件の判定
    reason: str                    # 判定理由
    suggestion: str?               # 次のアクション提案
```

## 履歴管理

### コンテキスト効率

**問題**: 長時間実行でコンテキストが枯渇

**解決策**:
1. 実行エージェントは毎回フレッシュ
2. 履歴はサマリ化して圧縮
3. 最新 N 件のみをコンテキストとして注入

```python
class History:
    summaries: list[ExecutionSummary]

    def get_context(self, max_entries: int = 5) -> str:
        """最新 N 件の履歴をテキスト化"""
        recent = self.summaries[-max_entries:]
        # フォーマットして返す
```

### 永続化

```python
# 保存
history.model_dump_json() → history.json

# 復元
History.model_validate_json(json_text)
```

## エージェント詳細

### IntakeAgent（受付）

**責務**:
- 完了条件の妥当性チェック
- 曖昧な条件の検出
- ユーザーへの質問生成

**システムプロンプト**:
```
ユーザーからタスクと完了条件を受け取り、以下を行います：
1. 完了条件が測定可能か評価
2. 曖昧な場合は明確化の質問を生成
3. 明確な場合はタスクと条件を構造化
```

**出力型**: `IntakeResult`

### ExecutorAgent（実行）

**責務**:
- タスクの実行に専念
- 完了判定は行わない（責務分離）
- 履歴を参照して改善

**システムプロンプト**:
```
与えられたタスクを実行し、結果を報告してください。
履歴を参照し、過去に試したことを繰り返さないでください。
完了条件の判定は別のエージェントが行います。
```

**出力型**: `ExecutionResult`

### SummarizerAgent（サマリ）

**責務**:
- 実行結果の圧縮
- 重要情報の抽出
- トークン効率の最適化

**システムプロンプト**:
```
実行結果を分析し、重要な情報のみを抽出してサマリを作成してください。
次のイテレーションで参照できるよう、以下を含めてください：
- 何を実行したか（簡潔に）
- 結果と成果物
- 重要な判断や発見
- 未解決の問題
```

**出力型**: `ExecutionSummary`

### JudgeAgent（判定）

**責務**:
- 完了条件の評価
- 各条件の個別判定
- 判定理由の説明

**システムプロンプト**:
```
実行結果が完了条件を満たすか判定してください。
各条件について個別に評価し、理由を説明してください。
未完了の場合は、次に何をすべきか提案してください。
```

**出力型**: `JudgmentResult`

## 統合

### MCP 統合

```python
class Engine:
    def __init__(
        self,
        mcp_servers: list[McpServerConfig] | None = None,
    ):
        # MCP サーバーを実行エージェントに渡す
```

### Agent Skills 統合

```python
class Engine:
    def __init__(
        self,
        skills_dir: Path | None = None,  # .claude/skills/
    ):
        # スキルを発見して実行エージェントに渡す
```

## エラーハンドリング

### 実行エラー

```python
# 実行エージェントでエラー発生時
try:
    exec_result = await executor.execute(...)
except ExecutionError as e:
    # サマリにエラーを記録
    # 次のイテレーションで回避を試みる
```

### 最大イテレーション到達

```python
if iterations >= max_iterations:
    return LoopResult(
        success=False,
        reason="max_iterations_reached",
        history=history,
    )
```

## 設定

### 環境変数

```bash
ENDLESS8_LOG_LEVEL=DEBUG       # ログレベル
ENDLESS8_DEFAULT_MODEL=sonnet  # デフォルトモデル
ENDLESS8_MAX_ITERATIONS=50     # デフォルト最大イテレーション
```

### YAML 設定

```yaml
# endless8.yaml
engine:
  max_iterations: 30
  history_context_size: 5

integrations:
  mcp:
    - filesystem
    - github
  skills_dir: .claude/skills/
```

## テスト戦略

### ユニットテスト

```python
# 各エージェントを個別にテスト
async def test_intake_agent_detects_ambiguous_criteria():
    agent = IntakeAgent(mock_model)
    result = await agent.process("タスク", "良い感じになったら完了")
    assert result.clarification_needed is not None
```

### 統合テスト

```python
# エンジン全体をテスト
async def test_engine_completes_simple_task():
    engine = Engine(model=mock_model)
    result = await engine.run(
        task="1+1を計算",
        completion_criteria="答えが2",
    )
    assert result.success
```

### E2E テスト

```python
# 実際の API を使用（CI では skip）
@pytest.mark.e2e
async def test_real_coding_task():
    engine = Engine()
    result = await engine.run(...)
```
