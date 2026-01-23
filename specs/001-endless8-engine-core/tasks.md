# Tasks: endless8 エンジンコア機能

**Input**: Design documents from `/specs/001-endless8-engine-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: テストタスクは TDD ワークフローに従い、各実装の前に作成します。

**Organization**: タスクはユーザーストーリーごとにグループ化され、各ストーリーの独立した実装とテストを可能にします。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: タスクが属するユーザーストーリー（例: US1, US2, US3）
- 説明には正確なファイルパスを含める

## Path Conventions

- **Single project**: `src/endless8/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: プロジェクト初期化と基本構造

- [X] T001 Create project structure with pyproject.toml and uv configuration
- [X] T002 [P] Configure ruff and mypy in pyproject.toml
- [X] T003 [P] Create src/endless8/__init__.py with package exports
- [X] T004 [P] Create tests/conftest.py with common fixtures
- [X] T005 [P] Setup pytest configuration in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: すべてのユーザーストーリーの前に完了必須のコアインフラ

**⚠️ CRITICAL**: このフェーズが完了するまでユーザーストーリーの作業は開始不可

### データモデル（全ストーリー共通）

- [X] T006 [P] Create TaskInput model in src/endless8/models/task.py
- [X] T007 [P] Create IntakeResult, IntakeStatus, ClarificationQuestion models in src/endless8/models/intake.py
- [X] T008 [P] Create ExecutionResult, ExecutionStatus, SemanticMetadata models in src/endless8/models/execution.py
- [X] T009 [P] Create ExecutionSummary, SummaryMetadata, NextAction models in src/endless8/models/summary.py
- [X] T010 [P] Create JudgmentResult, CriteriaEvaluation models in src/endless8/models/judgment.py
- [X] T011 [P] Create LoopResult (with final_summary: ExecutionSummary | None), LoopStatus models in src/endless8/models/loop.py
- [X] T012 [P] Create Knowledge, KnowledgeType, KnowledgeConfidence models in src/endless8/models/knowledge.py
- [X] T013 [P] Create ProgressEvent, ProgressEventType models in src/endless8/models/progress.py
- [X] T014 Create src/endless8/models/__init__.py with all model exports

### 設定管理

- [X] T015 [P] Create EngineConfig, ClaudeOptions, LoggingOptions, PromptsConfig in src/endless8/config/settings.py
- [X] T016 Create YAML config loader in src/endless8/config/__init__.py
- [X] T017 Create src/endless8/config/__init__.py with exports

**Checkpoint**: Foundation ready - ユーザーストーリー実装開始可能

---

## Phase 3: User Story 1 - 基本タスク実行 (Priority: P1) 🎯 MVP

**Goal**: タスクと完了条件を指定してエンジンを実行し、完了条件が満たされるまで自動的に処理を繰り返す

**Independent Test**: タスク「テストカバレッジを90%以上にする」と完了条件「pytest --cov で90%以上」を指定して実行し、カバレッジ目標が達成されることを確認

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T018 [P] [US1] Unit test for IntakeAgent in tests/unit/test_intake_agent.py
- [X] T019 [P] [US1] Unit test for ExecutionAgent in tests/unit/test_execution_agent.py
- [X] T020 [P] [US1] Unit test for SummaryAgent in tests/unit/test_summary_agent.py
- [X] T021 [P] [US1] Unit test for JudgmentAgent in tests/unit/test_judgment_agent.py
- [X] T022 [P] [US1] Unit test for Engine in tests/unit/test_engine.py
- [X] T023 [US1] Integration test for basic loop execution in tests/integration/test_loop_execution.py

### Implementation for User Story 1

- [X] T024 [P] [US1] Implement IntakeAgent in src/endless8/agents/intake.py
- [X] T025 [P] [US1] Implement ExecutionAgent in src/endless8/agents/execution.py (claudecode-model integration)
- [X] T026 [US1] Implement SummaryAgent in src/endless8/agents/summary.py (stream-json parsing)
- [X] T027 [US1] Implement JudgmentAgent in src/endless8/agents/judgment.py
- [X] T028 [US1] Create src/endless8/agents/__init__.py with exports
- [X] T029 [US1] Implement Engine class with run() and run_iter() in src/endless8/engine.py
- [X] T030 [US1] Add progress callback support to Engine.run() in src/endless8/engine.py

**Checkpoint**: User Story 1 完了 - 基本的なループ実行が動作

---

## Phase 4: User Story 2 - 曖昧な完了条件の明確化 (Priority: P2)

**Goal**: 曖昧な完了条件を指定した場合に、エンジンが質問を生成する

**Independent Test**: 曖昧な完了条件「十分に高速になったら完了」を指定し、受付エージェントが明確化の質問を生成することを確認

### Tests for User Story 2 ⚠️

- [X] T031 [P] [US2] Unit test for clarification question generation in tests/unit/test_intake_agent.py (extend)
- [X] T032 [US2] Integration test for clarification flow in tests/integration/test_clarification.py

### Implementation for User Story 2

- [X] T033 [US2] Enhance IntakeAgent with ambiguity detection in src/endless8/agents/intake.py
- [X] T034 [US2] Add clarification question generation to IntakeAgent in src/endless8/agents/intake.py
- [X] T035 [US2] Update Engine to handle clarification flow in src/endless8/engine.py

**Checkpoint**: User Story 2 完了 - 曖昧な条件に対する質問生成が動作

---

## Phase 5: User Story 6 - 非プログラミングタスク（リサーチ） (Priority: P2)

**Goal**: プログラミング以外のタスク（論文検索、調査など）もエンジンで実行

**Independent Test**: タスク「プロンプト最適化に関する論文を検索」と完了条件「3件以上の関連論文を発見し、概要をまとめる」を指定して実行

### Tests for User Story 6 ⚠️

- [X] T036 [P] [US6] Unit test for research task execution in tests/unit/test_execution_agent.py (extend)
- [X] T037 [US6] Integration test for research task in tests/integration/test_research_task.py

### Implementation for User Story 6

- [X] T038 [US6] Add research task handling to ExecutionAgent in src/endless8/agents/execution.py
- [X] T039 [US6] Update JudgmentAgent for non-programming criteria in src/endless8/agents/judgment.py

**Checkpoint**: User Story 6 完了 - 非プログラミングタスクが実行可能

---

## Phase 6: User Story 3 - 履歴参照によるコンテキスト効率化 (Priority: P2)

**Goal**: 長時間のタスク実行でもコンテキスト枯渇を起こさず、過去の実行履歴を効率的に参照

**Independent Test**: 10イテレーション以上のタスクを実行し、履歴がサマリ化されて効率的に参照されることを確認

### Tests for User Story 3 ⚠️

- [X] T040 [P] [US3] Unit test for History class in tests/unit/test_history.py
- [X] T041 [P] [US3] Unit test for KnowledgeBase class in tests/unit/test_knowledge_base.py
- [X] T042 [US3] Integration test for context management in tests/integration/test_context.py

### Implementation for User Story 3

- [X] T043 [P] [US3] Implement History class with DuckDB queries in src/endless8/history/history.py
- [X] T044 [P] [US3] Implement KnowledgeBase class with DuckDB queries in src/endless8/history/knowledge_base.py
- [X] T045 [US3] Create src/endless8/history/__init__.py with exports
- [X] T046 [US3] Integrate History and KnowledgeBase with Engine (save summary after each iteration via History.add_summary()) in src/endless8/engine.py
- [X] T047 [US3] Add context injection to ExecutionAgent in src/endless8/agents/execution.py

**Checkpoint**: User Story 3 完了 - 履歴とナレッジの効率的な参照が動作

---

## Phase 7: User Story 4 - 履歴の永続化と再開 (Priority: P3)

**Goal**: タスク実行を中断しても、後から履歴を読み込んで続きから再開

**Independent Test**: タスクを途中で中断し、履歴ファイルから再開して最終的に完了することを確認

### Tests for User Story 4 ⚠️

- [X] T048 [P] [US4] Unit test for JSONL persistence in tests/unit/test_history.py (extend)
- [X] T049 [US4] Integration test for task resume in tests/integration/test_persistence.py

### Implementation for User Story 4

- [X] T050 [US4] Add JSONL persistence to History class in src/endless8/history/history.py
- [X] T051 [US4] Add JSONL persistence to KnowledgeBase in src/endless8/history/knowledge_base.py
- [X] T052 [US4] Implement task directory structure (.e8/tasks/<task-id>/) in src/endless8/history/history.py
- [X] T053 [US4] Add task resume support to Engine in src/endless8/engine.py

**Checkpoint**: User Story 4 完了 - 履歴の永続化と再開が動作

---

## Phase 8: User Story 5 - CLI からの実行 (Priority: P3)

**Goal**: コマンドラインからタスクを実行し、進捗を確認

**Independent Test**: `e8 run "タスク" --criteria "条件"` コマンドを実行し、結果が表示されることを確認

### Tests for User Story 5 ⚠️

- [X] T054 [P] [US5] Unit test for CLI commands in tests/unit/test_cli.py
- [X] T055 [US5] Integration test for CLI execution in tests/integration/test_cli.py

### Implementation for User Story 5

- [X] T056 [US5] Implement run command in src/endless8/cli/main.py
- [X] T057 [US5] Implement list command in src/endless8/cli/main.py
- [X] T058 [US5] Implement status command in src/endless8/cli/main.py
- [X] T059 [US5] Add --resume option support in src/endless8/cli/main.py
- [X] T060 [US5] Add progress display callback for CLI in src/endless8/cli/main.py
- [X] T061 [US5] Add completion result display (status, reason, artifacts) in src/endless8/cli/main.py
- [X] T062 [US5] Create src/endless8/cli/__init__.py with exports
- [X] T063 [US5] Configure CLI entry point (e8) in pyproject.toml

**Checkpoint**: User Story 5 完了 - CLIからの実行が動作

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 複数のユーザーストーリーに影響する改善

- [X] T064 [P] Contract tests for all models in tests/unit/test_models.py
- [X] T065 Run ruff check --fix . && ruff format . && mypy .
- [ ] T066 Validate quickstart.md scenarios work correctly
- [X] T067 Update src/endless8/__init__.py with complete public API exports

---

## Phase 10: 履歴への判定結果・最終結果保存 (FR-032, FR-033)

**Purpose**: 各イテレーションの判定結果と最終結果を history.jsonl に保存

**Requirements**: FR-032 (JudgmentResult保存), FR-033 (LoopResult保存)

### Tests for Phase 10 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T068 [P] Unit test for History.append_judgment() in tests/unit/test_history.py (extend)
- [X] T069 [P] Unit test for History.append_final_result() in tests/unit/test_history.py (extend)
- [X] T070 Integration test for judgment/final_result persistence in tests/integration/test_persistence.py (extend)

### Implementation for Phase 10

- [X] T071 Implement History.append_judgment(judgment: JudgmentResult, iteration: int) in src/endless8/history/history.py
- [X] T072 Implement History.append_final_result(result: LoopResult) in src/endless8/history/history.py
- [X] T073 Update Engine to save JudgmentResult after each iteration in src/endless8/engine.py
- [X] T074 Update Engine to save LoopResult on task completion (all exit cases) in src/endless8/engine.py

**Checkpoint**: Phase 10 完了 - 判定結果と最終結果が履歴に保存される

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存関係なし - すぐに開始可能
- **Foundational (Phase 2)**: Setup完了が必要 - すべてのユーザーストーリーをブロック
- **User Stories (Phase 3-8)**: Foundational完了が必要
  - US1 (Phase 3): 他のストーリーに依存なし
  - US2 (Phase 4): US1に依存（IntakeAgent拡張）
  - US6 (Phase 5): US1に依存（ExecutionAgent拡張）
  - US3 (Phase 6): US1に依存（History/Knowledge統合）
  - US4 (Phase 7): US3に依存（永続化拡張）
  - US5 (Phase 8): US1, US4に依存（CLI統合）
- **Polish (Phase 9)**: すべてのユーザーストーリー完了が必要
- **履歴拡張 (Phase 10)**: US3, US4完了が必要（History/Engine拡張）

### User Story Dependencies Graph

```
        ┌──────────┐
        │  US1     │ ← MVP (基本タスク実行)
        │ (P1)     │
        └────┬─────┘
             │
    ┌────────┼────────┬────────┐
    ▼        ▼        ▼        │
┌──────┐ ┌──────┐ ┌──────┐    │
│ US2  │ │ US6  │ │ US3  │    │
│ (P2) │ │ (P2) │ │ (P2) │    │
│明確化│ │リサーチ│ │履歴参照│    │
└──────┘ └──────┘ └──┬───┘    │
                      │        │
                      ▼        │
                 ┌──────┐     │
                 │ US4  │     │
                 │ (P3) │     │
                 │永続化│     │
                 └──┬───┘     │
                    │         │
                    ▼         ▼
                 ┌──────────────┐
                 │     US5     │
                 │    (P3)     │
                 │     CLI     │
                 └─────────────┘
```

### Within Each User Story

- テストは実装前に作成し、FAILすることを確認
- モデル → サービス → エンドポイント の順
- コア実装 → 統合 の順
- ストーリー完了後に次の優先度に移動

### Parallel Opportunities

**Phase 1 (Setup)**:
- T002, T003, T004, T005 は並列実行可能

**Phase 2 (Foundational)**:
- T006-T013 はすべて並列実行可能（異なるモデルファイル）
- T015 は並列実行可能

**Phase 3 (US1)**:
- T018-T022 はすべて並列実行可能（異なるテストファイル）
- T024, T025 は並列実行可能（異なるエージェントファイル）

**Phase 6 (US3)**:
- T040, T041 は並列実行可能
- T043, T044 は並列実行可能

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all model creation tasks together:
Task: "Create TaskInput model in src/endless8/models/task.py"
Task: "Create IntakeResult models in src/endless8/models/intake.py"
Task: "Create ExecutionResult models in src/endless8/models/execution.py"
Task: "Create ExecutionSummary models in src/endless8/models/summary.py"
Task: "Create JudgmentResult models in src/endless8/models/judgment.py"
Task: "Create LoopResult (with final_summary) models in src/endless8/models/loop.py"
Task: "Create Knowledge models in src/endless8/models/knowledge.py"
Task: "Create ProgressEvent models in src/endless8/models/progress.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2, 6 (parallel) → Test independently
4. Add User Story 3 → Test independently
5. Add User Story 4 → Test independently
6. Add User Story 5 (CLI) → Test independently → Full feature ready
7. Each story adds value without breaking previous stories

### File Summary

| Directory | Files |
|-----------|-------|
| src/endless8/models/ | task.py, intake.py, execution.py, summary.py, judgment.py, loop.py, knowledge.py, progress.py, __init__.py |
| src/endless8/config/ | models.py, loader.py, __init__.py |
| src/endless8/agents/ | intake.py, execution.py, summary.py, judgment.py, __init__.py |
| src/endless8/history/ | history.py, knowledge.py, __init__.py |
| src/endless8/cli/ | main.py, __init__.py |
| src/endless8/ | engine.py, __init__.py |
| tests/unit/ | test_intake_agent.py, test_execution_agent.py, test_summary_agent.py, test_judgment_agent.py, test_engine.py, test_history.py, test_knowledge.py, test_cli.py, test_config.py |
| tests/integration/ | test_loop_execution.py, test_clarification.py, test_research_task.py, test_context.py, test_persistence.py, test_cli.py |
| tests/contract/ | test_models.py |

---

## Notes

- [P] tasks = 異なるファイル、依存関係なし
- [Story] label = 特定のユーザーストーリーへのトレーサビリティ
- 各ユーザーストーリーは独立して完了・テスト可能
- テストは実装前にFAILすることを確認
- タスクまたは論理グループごとにコミット
- 任意のチェックポイントで停止してストーリーを独立して検証可能
- 避けるべき: 曖昧なタスク、同一ファイルの競合、独立性を損なうストーリー間依存
