# Tasks: endless8 エンジンコア機能

**Input**: Design documents from `/specs/001-endless8-engine-core/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included based on the test-first requirement in the project constitution (CLAUDE.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Source: `src/endless8/`
- Tests: `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan (`src/endless8/`, `tests/`)
- [x] T002 Initialize Python project with uv and pyproject.toml (pydantic-ai, claudecode-model, duckdb, typer, pyyaml, pytest, pytest-asyncio, pytest-cov)
- [x] T003 [P] Configure ruff and mypy settings in pyproject.toml
- [x] T004 [P] Create `src/endless8/__init__.py` with package exports
- [x] T005 [P] Create pytest fixtures in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create data models in `src/endless8/models/task.py` (TaskInput)
- [x] T007 [P] Create result models in `src/endless8/models/results.py` (IntakeResult, ExecutionResult, JudgmentResult, LoopResult, status enums)
- [x] T008 [P] Create summary models in `src/endless8/models/summary.py` (ExecutionSummary, SummaryMetadata, NextAction)
- [x] T009 [P] Create knowledge models in `src/endless8/models/knowledge.py` (Knowledge, KnowledgeType, KnowledgeConfidence)
- [x] T010 Create `src/endless8/models/__init__.py` to export all models
- [x] T011 Create configuration models in `src/endless8/config/settings.py` (EngineConfig, ClaudeOptions, LoggingOptions, PromptsConfig)
- [x] T012 [P] Create YAML config loader in `src/endless8/config/__init__.py`
- [x] T013 Create base agent protocols in `src/endless8/agents/__init__.py` (Protocol definitions from contracts/agents.py)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 基本タスク実行 (Priority: P1) 🎯 MVP

**Goal**: タスクと完了条件を指定してエンジンを実行し、完了条件が満たされるまで自動的に処理を繰り返す

**Independent Test**: タスク「テストカバレッジを90%以上にする」と完了条件「pytest --cov で90%以上」を指定して実行し、カバレッジ目標が達成されることを確認

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T014 [P] [US1] Unit test for Engine class in `tests/unit/test_engine.py`
- [x] T015 [P] [US1] Unit test for execution agent in `tests/unit/test_execution_agent.py`
- [x] T016 [P] [US1] Unit test for judgment agent in `tests/unit/test_judgment_agent.py`
- [x] T017 [P] [US1] Unit test for summary agent in `tests/unit/test_summary_agent.py`
- [x] T018 [P] [US1] Integration test for basic loop execution in `tests/integration/test_loop_execution.py`

### Implementation for User Story 1

- [x] T019 [US1] Implement execution agent in `src/endless8/agents/execution.py` (claudecode-model integration, stream-json parsing, MCP server connection, Agent Skills support via claude CLI)
- [x] T020 [US1] Implement summary agent in `src/endless8/agents/summary.py` (result compression, metadata extraction from stream-json)
- [x] T021 [US1] Implement judgment agent in `src/endless8/agents/judgment.py` (criteria evaluation, next action suggestion)
- [x] T022 [US1] Implement Engine class in `src/endless8/engine.py` (main loop, agent coordination, max iteration handling)
- [x] T023 [US1] Create DuckDB query utilities in `src/endless8/history/queries.py` (JSONL queries)

**Checkpoint**: Basic task execution loop should work with in-memory history

---

## Phase 4: User Story 2 - 曖昧な完了条件の明確化 (Priority: P2)

**Goal**: 曖昧な完了条件を指定した場合に、エンジンが質問を生成してくれることで、適切な条件を設定する

**Independent Test**: 曖昧な完了条件「十分に高速になったら完了」を指定し、受付エージェントが明確化の質問を生成することを確認

### Tests for User Story 2

- [x] T024 [P] [US2] Unit test for intake agent in `tests/unit/test_intake_agent.py`

### Implementation for User Story 2

- [x] T025 [US2] Implement intake agent in `src/endless8/agents/intake.py` (criteria validation, clarification question generation)
- [x] T026 [US2] Integrate intake agent into Engine loop in `src/endless8/engine.py` (pre-execution validation)

**Checkpoint**: Ambiguous criteria should trigger clarification questions

---

## Phase 5: User Story 3 - 履歴参照によるコンテキスト効率化 (Priority: P2)

**Goal**: 長時間のタスク実行でもコンテキスト枯渇を起こさずに、過去の実行履歴を効率的に参照して処理を継続する

**Independent Test**: 10イテレーション以上のタスクを実行し、履歴がサマリ化されて効率的に参照されることを確認

### Tests for User Story 3

- [x] T027 [P] [US3] Unit test for History class in `tests/unit/test_history.py`
- [x] T028 [P] [US3] Unit test for KnowledgeBase class in `tests/unit/test_knowledge_base.py`

### Implementation for User Story 3

- [x] T029 [US3] Implement History class in `src/endless8/history/history.py` (summary storage, context generation, DuckDB queries)
- [x] T030 [US3] Implement KnowledgeBase class in `src/endless8/history/knowledge_base.py` (knowledge storage, relevance queries)
- [x] T031 [US3] Create `src/endless8/history/__init__.py` to export History and KnowledgeBase
- [x] T032 [US3] Integrate history context into execution agent in `src/endless8/agents/execution.py` (inject summarized history)
- [x] T033 [US3] Update summary agent to extract knowledge in `src/endless8/agents/summary.py` (knowledge extraction from execution results)

**Checkpoint**: Long-running tasks should maintain efficient context through summarization

---

## Phase 6: User Story 4 - 履歴の永続化と再開 (Priority: P3)

**Goal**: タスク実行を中断しても、後から履歴を読み込んで続きから再開する

**Independent Test**: タスクを途中で中断し、履歴ファイルから再開して最終的に完了することを確認

### Tests for User Story 4

- [x] T034 [US4] Integration test for history persistence and resume in `tests/integration/test_loop_execution.py`

### Implementation for User Story 4

- [x] T035 [US4] Add JSONL persistence to History class in `src/endless8/history/history.py` (load, persist methods)
- [x] T036 [US4] Add JSONL persistence to KnowledgeBase class in `src/endless8/history/knowledge_base.py` (immediate append on add)
- [x] T037 [US4] Update Engine to support history resume in `src/endless8/engine.py` (load existing history on init)

**Checkpoint**: Tasks can be interrupted and resumed from persisted history

---

## Phase 7: User Story 5 - CLI からの実行 (Priority: P3)

**Goal**: コマンドラインからタスクを実行し、進捗を確認する

**Independent Test**: `e8 run "タスク" --criteria "条件"` コマンドを実行し、結果が表示されることを確認

### Tests for User Story 5

- [x] T038 [US5] Integration test for CLI in `tests/integration/test_cli.py`

### Implementation for User Story 5

- [x] T039 [US5] Implement CLI with typer in `src/endless8/cli/main.py` (run command, options parsing)
- [x] T040 [US5] Create `src/endless8/cli/__init__.py`
- [x] T041 [US5] Add CLI entry point in `pyproject.toml` ([project.scripts] e8 = "endless8.cli.main:app")
- [x] T042 [US5] Implement `.e8/` directory auto-creation in CLI
- [x] T043 [US5] Add progress output formatting in CLI (iteration status, results display)

**Checkpoint**: `e8 run` command should work with all options

---

## Phase 8: User Story 6 - 非プログラミングタスク（リサーチ） (Priority: P2)

**Goal**: プログラミング以外のタスク（論文検索、調査、ドキュメント作成など）もエンジンで実行する

**Independent Test**: タスク「プロンプト最適化に関する論文を検索」と完了条件「3件以上の関連論文を発見し、概要をまとめる」を指定して実行し、条件を満たす結果が得られることを確認

### Tests for User Story 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T044 [P] [US6] Unit test for research task criteria evaluation in `tests/unit/test_judgment_agent.py`

### Implementation for User Story 6

- [x] T045 [US6] Update judgment agent prompts for research tasks in `src/endless8/agents/judgment.py` (flexible criteria evaluation for non-coding tasks)
- [x] T046 [US6] Add research-focused knowledge types handling in `src/endless8/history/knowledge_base.py`

**Checkpoint**: Non-programming research tasks should complete successfully

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T047 [P] Unit test for models in `tests/unit/test_models.py`
- [x] T048 Code cleanup: run `ruff check --fix . && ruff format . && mypy .`
- [x] T049 [P] Add raw log saving option in `src/endless8/agents/execution.py` (logging.raw_log support)
- [x] T050 [P] Add custom judgment prompt support in `src/endless8/agents/judgment.py` (prompts.judgment from config)
- [x] T051 [P] Add append_system_prompt support in `src/endless8/agents/execution.py` (semantic metadata reporting)
- [x] T052 Run quickstart.md validation with installed package

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - Core loop
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) - Can parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 (needs Engine to integrate with)
- **User Story 4 (Phase 6)**: Depends on US3 (needs History to persist)
- **User Story 5 (Phase 7)**: Depends on US1 (needs working Engine) - Can run in parallel with US3/US4
- **User Story 6 (Phase 8)**: Depends on US1 (needs working Engine and Judgment agent) - Can run in parallel with US3/US4
- **Polish (Phase 9)**: Depends on all user stories

### User Story Dependencies

```
                    ┌──────────┐
                    │  Setup   │
                    │ Phase 1  │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │Foundation│
                    │ Phase 2  │
                    └────┬─────┘
                         │
           ┌─────────────┼─────────────┐
           │             │             │
      ┌────▼────┐   ┌────▼────┐        │
      │   US1   │   │   US2   │        │
      │ Phase 3 │   │ Phase 4 │        │
      └────┬────┘   └─────────┘        │
           │                           │
     ┌─────┴─────┬─────────┬───────────┘
     │           │         │
┌────▼────┐ ┌────▼────┐ ┌──▼──────┐
│   US3   │ │   US5   │ │   US6   │
│ Phase 5 │ │ Phase 7 │ │ Phase 8 │
└────┬────┘ └─────────┘ └─────────┘
     │
┌────▼────┐
│   US4   │
│ Phase 6 │
└─────────┘
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services/Agents before Engine integration
- Core implementation before CLI

### Parallel Opportunities

- Phase 1: T003, T004, T005 can run in parallel
- Phase 2: T007, T008, T009 can run in parallel; T011, T012 can run in parallel
- Phase 3: All tests (T014-T018) can run in parallel
- Phase 4: T024 independent
- Phase 5: T027, T028 can run in parallel
- Phase 8: T044 independent
- Phase 9: T047, T049, T050, T051 can run in parallel
- After US1: US3, US5, US6 can run in parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch parallel model creation:
Task: "Create result models in src/endless8/models/results.py"
Task: "Create summary models in src/endless8/models/summary.py"
Task: "Create knowledge models in src/endless8/models/knowledge.py"
```

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for Engine class in tests/unit/test_engine.py"
Task: "Unit test for execution agent in tests/unit/test_execution_agent.py"
Task: "Unit test for judgment agent in tests/unit/test_judgment_agent.py"
Task: "Unit test for summary agent in tests/unit/test_summary_agent.py"
Task: "Integration test for basic loop execution in tests/integration/test_loop_execution.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test basic task execution loop
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test basic loop → **MVP Ready!**
3. Add User Story 2 → Test clarification → Enhanced UX
4. Add User Story 3 → Test context efficiency → Long-running support
5. Add User Story 4 → Test persistence → Resume capability
6. Add User Story 5 → Test CLI → Full CLI experience
7. Add User Story 6 → Test research tasks → Non-coding support

### Recommended Execution Order

For single developer:
1. Phase 1 (Setup)
2. Phase 2 (Foundational)
3. Phase 3 (US1 - MVP)
4. Phase 5 (US3 - History/Context)
5. Phase 6 (US4 - Persistence)
6. Phase 4 (US2 - Clarification)
7. Phase 7 (US5 - CLI)
8. Phase 8 (US6 - Research)
9. Phase 9 (Polish)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution requires: `ruff check --fix . && ruff format . && mypy .` before commit
