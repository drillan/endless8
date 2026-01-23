# Data Model: endless8 エンジンコア機能

**Date**: 2026-01-23
**Status**: Complete

## Overview

本ドキュメントは endless8 エンジンコア機能のデータモデルを定義する。すべてのモデルは pydantic BaseModel を継承し、型安全性を保証する。

---

## Core Entities

### 1. TaskInput

タスク実行の入力を表す。

```python
from pydantic import BaseModel, Field

class TaskInput(BaseModel):
    """タスク実行の入力"""
    task: str = Field(..., description="タスクの説明（自然言語）")
    criteria: list[str] = Field(..., min_length=1, description="完了条件のリスト")
    max_iterations: int = Field(default=10, ge=1, le=100, description="最大イテレーション数")
    history_context_size: int = Field(default=5, ge=1, le=20, description="参照する履歴の件数")
```

**Validation Rules**:
- `task`: 空文字列不可
- `criteria`: 最低1つの条件が必要
- `max_iterations`: 1-100 の範囲
- `history_context_size`: 1-20 の範囲

---

### 2. IntakeResult

受付エージェントの出力を表す。

```python
from enum import Enum

class IntakeStatus(str, Enum):
    """受付ステータス"""
    ACCEPTED = "accepted"           # タスク受理
    NEEDS_CLARIFICATION = "needs_clarification"  # 明確化が必要

class ClarificationQuestion(BaseModel):
    """明確化のための質問"""
    question: str = Field(..., description="質問内容")
    context: str = Field(..., description="質問の背景・理由")
    suggested_answers: list[str] = Field(default_factory=list, description="回答の候補")

class IntakeResult(BaseModel):
    """受付エージェントの出力"""
    status: IntakeStatus
    task: str = Field(..., description="構造化されたタスク")
    criteria: list[str] = Field(..., description="構造化された完了条件")
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="明確化のための質問（NEEDS_CLARIFICATION時のみ）"
    )
    validation_notes: str | None = Field(None, description="検証時の注記")
```

**State Transitions**:
- `NEEDS_CLARIFICATION` → ユーザー回答後 → 再度受付エージェント実行
- `ACCEPTED` → 実行エージェントへ

---

### 3. ExecutionResult

実行エージェントの出力を表す。

```python
class ExecutionStatus(str, Enum):
    """実行ステータス"""
    SUCCESS = "success"     # 正常完了
    FAILURE = "failure"     # 失敗
    ERROR = "error"         # エラー発生

class SemanticMetadata(BaseModel):
    """実行エージェントが報告するセマンティックメタデータ"""
    approach: str = Field(..., description="採用したアプローチ")
    strategy_tags: list[str] = Field(default_factory=list, description="戦略タグ")
    discoveries: list[str] = Field(default_factory=list, description="発見事項")

class ExecutionResult(BaseModel):
    """実行エージェントの出力"""
    status: ExecutionStatus
    output: str = Field(..., description="実行結果の説明")
    artifacts: list[str] = Field(default_factory=list, description="生成・変更したファイル")
    semantic_metadata: SemanticMetadata | None = Field(None, description="セマンティックメタデータ")
    raw_log_path: str | None = Field(None, description="生ログファイルのパス")
```

---

### 4. ExecutionSummary

サマリエージェントの出力を表す。履歴に保存される。

```python
class SummaryMetadata(BaseModel):
    """機械的に抽出されるメタデータ"""
    tools_used: list[str] = Field(default_factory=list, description="使用したツール")
    files_modified: list[str] = Field(default_factory=list, description="変更したファイル")
    error_type: str | None = Field(None, description="エラータイプ（該当時）")
    tokens_used: int = Field(default=0, ge=0, description="使用トークン数")
    strategy_tags: list[str] = Field(default_factory=list, description="戦略タグ")

class NextAction(BaseModel):
    """次のアクションに関する情報"""
    suggested_action: str = Field(..., description="推奨アクション")
    blockers: list[str] = Field(default_factory=list, description="ブロッカー")
    partial_progress: str | None = Field(None, description="部分的な進捗")
    pending_items: list[str] = Field(default_factory=list, description="未完了項目")

class ExecutionSummary(BaseModel):
    """サマリエージェントの出力（履歴に保存）"""
    type: str = Field(default="summary", const=True)
    iteration: int = Field(..., ge=1, description="イテレーション番号")
    approach: str = Field(..., description="採用したアプローチ")
    result: ExecutionStatus
    reason: str = Field(..., description="結果の理由")
    artifacts: list[str] = Field(default_factory=list, description="成果物")
    metadata: SummaryMetadata = Field(default_factory=SummaryMetadata)
    next: NextAction | None = Field(None, description="次のアクション情報")
    timestamp: str = Field(..., description="ISO 8601形式のタイムスタンプ")
```

**JSONL Format Example**:
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
  },
  "timestamp": "2026-01-23T10:00:00Z"
}
```

---

### 5. Knowledge

ナレッジエントリを表す。プロジェクト単位で永続化される。

```python
from datetime import datetime

class KnowledgeType(str, Enum):
    """ナレッジタイプ"""
    DISCOVERY = "discovery"     # コードベースの事実
    LESSON = "lesson"           # 失敗から学んだ教訓
    PATTERN = "pattern"         # コーディング規約・慣習
    CONSTRAINT = "constraint"   # 技術的制約
    CODEBASE = "codebase"       # 構造的な知見

class KnowledgeConfidence(str, Enum):
    """信頼度"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Knowledge(BaseModel):
    """ナレッジエントリ"""
    type: KnowledgeType
    category: str = Field(..., description="カテゴリ（例: error_handling, testing）")
    content: str = Field(..., description="ナレッジの内容")
    example_file: str | None = Field(None, description="例となるファイルと行番号")
    source_task: str = Field(..., description="発見元のタスク")
    confidence: KnowledgeConfidence = Field(default=KnowledgeConfidence.MEDIUM)
    applied_count: int = Field(default=0, ge=0, description="適用された回数")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**JSONL Format Example**:
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

---

### 6. JudgmentResult

判定エージェントの出力を表す。

```python
class CriteriaEvaluation(BaseModel):
    """各完了条件の評価"""
    criterion: str = Field(..., description="完了条件")
    is_met: bool = Field(..., description="条件を満たしているか")
    evidence: str = Field(..., description="判定の根拠")
    confidence: float = Field(..., ge=0.0, le=1.0, description="判定の確信度")

class JudgmentResult(BaseModel):
    """判定エージェントの出力"""
    is_complete: bool = Field(..., description="すべての条件を満たしているか")
    evaluations: list[CriteriaEvaluation] = Field(..., description="各条件の評価")
    overall_reason: str = Field(..., description="総合的な判定理由")
    suggested_next_action: str | None = Field(
        None,
        description="未完了時の次のアクション提案"
    )
```

---

### 7. LoopResult

ループ全体の最終結果を表す。

```python
class LoopStatus(str, Enum):
    """ループ終了ステータス"""
    COMPLETED = "completed"           # 完了条件達成
    MAX_ITERATIONS = "max_iterations" # 最大イテレーション到達
    ERROR = "error"                   # エラー終了
    CANCELLED = "cancelled"           # キャンセル

class LoopResult(BaseModel):
    """ループ全体の最終結果"""
    status: LoopStatus
    iterations_used: int = Field(..., ge=0, description="実行したイテレーション数")
    final_judgment: JudgmentResult | None = Field(None, description="最終判定結果")
    history_path: str | None = Field(None, description="履歴ファイルのパス")
    error_message: str | None = Field(None, description="エラーメッセージ（ERROR時）")
```

---

## Service Entities

### 8. History

履歴を管理するクラス。

```python
class History:
    """履歴管理クラス"""

    def __init__(self, path: str | None = None):
        """
        Args:
            path: 履歴ファイルのパス（None の場合はメモリのみ）
        """
        ...

    def add_summary(self, summary: ExecutionSummary) -> None:
        """サマリを履歴に追加"""
        ...

    def get_context(self, limit: int = 5) -> list[ExecutionSummary]:
        """コンテキスト用の履歴を取得（直近N件 + 失敗履歴）"""
        ...

    def load(self) -> None:
        """ファイルから履歴を読み込み"""
        ...

    def persist(self) -> None:
        """履歴をファイルに永続化"""
        ...
```

**Storage**: `.e8/history.jsonl`

---

### 9. KnowledgeBase

ナレッジを管理するクラス。

```python
class KnowledgeBase:
    """ナレッジ管理クラス"""

    def __init__(self, path: str = ".e8/knowledge.jsonl"):
        """
        Args:
            path: ナレッジファイルのパス
        """
        ...

    def add_knowledge(self, knowledge: Knowledge) -> None:
        """ナレッジを追加（即座にファイルに追記）"""
        ...

    def query(
        self,
        knowledge_type: KnowledgeType | None = None,
        category: str | None = None,
        min_confidence: KnowledgeConfidence = KnowledgeConfidence.LOW
    ) -> list[Knowledge]:
        """条件に合うナレッジを検索"""
        ...

    def get_relevant_knowledge(self, task: str) -> list[Knowledge]:
        """タスクに関連するナレッジを取得"""
        ...
```

**Storage**: `.e8/knowledge.jsonl`

---

## Configuration Entities

### 10. EngineConfig

エンジン設定を表す。

```python
class ClaudeOptions(BaseModel):
    """claude CLI オプション"""
    allowed_tools: list[str] = Field(
        default=["Read", "Edit", "Write", "Bash"],
        description="許可するツール"
    )
    model: str = Field(default="sonnet", description="使用するモデル")
    output_format: str = Field(default="stream-json", description="出力形式")
    verbose: bool = Field(default=True, description="詳細出力")

class LoggingOptions(BaseModel):
    """ロギングオプション"""
    raw_log: bool = Field(default=False, description="生ログを保存するか")
    raw_log_dir: str = Field(default=".e8/logs", description="生ログ保存先")

class PromptsConfig(BaseModel):
    """プロンプト設定"""
    judgment: str | None = Field(None, description="判定エージェントのプロンプト")
    append_system_prompt: str | None = Field(
        None,
        description="実行エージェントに追加するシステムプロンプト"
    )

class EngineConfig(BaseModel):
    """エンジン設定"""
    task: str = Field(..., description="タスクの説明")
    criteria: list[str] = Field(..., min_length=1, description="完了条件")
    max_iterations: int = Field(default=10, ge=1, le=100, description="最大イテレーション数")
    persist: str | None = Field(None, description="履歴ファイルパス")
    knowledge: str = Field(default=".e8/knowledge.jsonl", description="ナレッジファイルパス")
    history_context_size: int = Field(default=5, ge=1, le=20, description="履歴参照件数")
    logging: LoggingOptions = Field(default_factory=LoggingOptions)
    claude_options: ClaudeOptions = Field(default_factory=ClaudeOptions)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
```

---

## Entity Relationships

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  TaskInput  │────▶│ IntakeResult │────▶│ ExecutionResult │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                                  ▼
┌─────────────┐     ┌────────────────┐     ┌──────────────────┐
│  LoopResult │◀────│ JudgmentResult │◀────│ ExecutionSummary │
└─────────────┘     └────────────────┘     └────────┬─────────┘
                                                    │
                                                    ▼
                           ┌─────────┐        ┌───────────┐
                           │ History │◀───────│ Knowledge │
                           └─────────┘        └───────────┘
                                                    │
                                                    ▼
                                           ┌──────────────┐
                                           │ KnowledgeBase│
                                           └──────────────┘
```

---

## Data Flow

1. **入力**: `TaskInput` → 受付エージェント
2. **検証**: 受付エージェント → `IntakeResult`
3. **実行**: 実行エージェント → `ExecutionResult`
4. **サマリ**: サマリエージェント → `ExecutionSummary` → `History`
5. **ナレッジ抽出**: サマリエージェント → `Knowledge` → `KnowledgeBase`
6. **判定**: 判定エージェント → `JudgmentResult`
7. **ループ制御**: ループ終了時 → `LoopResult`

---

## Storage Format

| データ | ファイル | 形式 | スコープ |
|--------|----------|------|----------|
| 履歴 | `.e8/history.jsonl` | JSONL | タスク単位 |
| ナレッジ | `.e8/knowledge.jsonl` | JSONL | プロジェクト単位 |
| 生ログ | `.e8/logs/iteration-NNN.jsonl` | JSONL | イテレーション単位 |
| 設定 | `task.yaml` | YAML | タスク単位 |
