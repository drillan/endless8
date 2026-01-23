# endless8

**endless8** は、pydantic-ai と claudecode-model を使用した、コンテキスト効率の良いタスク実行ループエンジンです。

## 概要

Ralph Wiggum（Claude Code のループプラグイン）にインスパイアされていますが、以下の点で改良されています：

- **コンテキスト枯渇を回避**: 実行エージェントは毎回フレッシュな状態で開始
- **履歴管理**: サマリ化された履歴を効率的に参照
- **柔軟な完了条件**: 自然言語で条件を指定、AIが判定
- **責務分離**: 4つの専門エージェントによるパイプライン

## アーキテクチャ

```
[ユーザー] タスク + 完了条件
     ↓
[受付エージェント] → 不明確なら質問を返す
     ↓
┌─── ループ ───────────────────────┐
│ [実行エージェント] ← 履歴を注入   │
│      ↓                          │
│ [サマリエージェント] → 履歴に保存 │
│      ↓                          │
│ [判定エージェント]               │
│      ├→ 完了 → 結果を返す        │
│      └→ 未完了 → ループ継続      │
└─────────────────────────────────┘
```

## インストール

```bash
uv add endless8
```

## 使用例

### 基本的な使用

```python
from endless8 import Engine

engine = Engine()

result = await engine.run(
    task="認証機能を実装してください",
    completion_criteria=[
        "すべてのテストが通る",
        "カバレッジが80%以上",
    ],
    max_iterations=10,
)

print(f"完了: {result.success}")
print(f"イテレーション: {result.iterations}")
```

### 曖昧な条件の明確化

```python
def ask_user(question: str) -> str:
    return input(f"質問: {question}\n回答: ")

result = await engine.run(
    task="APIを最適化してください",
    completion_criteria="十分に高速になったら完了",  # 曖昧
    on_clarification=ask_user,  # 受付エージェントが質問を生成
)
```

### 履歴の永続化（中断・再開）

```python
from pathlib import Path

result = await engine.run(
    task="大規模リファクタリング",
    completion_criteria=["全テスト通過", "型エラーなし"],
    persist_history=Path(".e8/history.jsonl"),
)
```

## CLI

```bash
# 基本実行
e8 run "タスクの説明" --criteria "条件1" --criteria "条件2"

# 設定ファイルから
e8 run --config task.yaml

# 履歴を永続化
e8 run "タスク" --persist .e8/history.jsonl
```

## 特徴

### Ralph Wiggum との比較

| 観点 | Ralph Wiggum | endless8 |
|------|--------------|----------|
| コンテキスト | 蓄積（枯渇リスク） | 毎回リフレッシュ |
| 履歴参照 | 会話履歴全体 | サマリ化して効率的に |
| 完了条件 | `<promise>` タグ | 自然言語 + AI判定 |
| 長時間実行 | トークン上限 | 安定継続 |

### 4エージェント構成

1. **受付エージェント**: 完了条件の妥当性チェック、曖昧な場合は質問
2. **実行エージェント**: タスク実行に専念
3. **サマリエージェント**: 実行結果を圧縮して履歴に保存
4. **判定エージェント**: 完了条件の評価

## 依存関係

- Python 3.13+
- [claudecode-model](https://github.com/your-org/claudecode-model) - pydantic-ai アダプタ
- pydantic >= 2.12
- pydantic-ai >= 1.46
- typer >= 0.21
- duckdb >= 1.4.3

## ライセンス

MIT
