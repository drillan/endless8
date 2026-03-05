# Tasks: 構造化された完了条件（Structured Criteria）

**Input**: Design documents from `/specs/002-structured-criteria/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

**Tests**: TDD 必須（CLAUDE.md Art.1 準拠）。各フェーズでテストを先行作成し、失敗を確認してから実装する。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: 新規パッケージ構造の作成

- [ ] T001 Create command package structure: src/endless8/command/__init__.py

---

## Phase 2: Foundational (Data Models & Config)

**Purpose**: 全ユーザーストーリーが依存するデータモデルと設定の定義

**CRITICAL**: ここで定義するモデルが US1〜US3 すべての基盤となる

### Tests for Foundational

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T002 [P] Create test for Criterion type models (CriterionType, CommandCriterion, CriterionInput discriminator, validation) in tests/unit/test_criteria_models.py
- [ ] T003 [P] Create test for CommandResult model and CriteriaEvaluation extension (evaluation_method, command_result, cross-field validation) in tests/unit/test_models.py

### Implementation for Foundational

- [ ] T004 [P] Implement CriterionType (StrEnum), CommandCriterion, _criterion_discriminator, CriterionInput in src/endless8/models/criteria.py
- [ ] T005 [P] Add CommandResult model and extend CriteriaEvaluation with evaluation_method (CriterionType) and command_result (CommandResult | None) including model_validator in src/endless8/models/results.py
- [ ] T006 [P] Add DEFAULT_COMMAND_TIMEOUT_SEC (30.0) and COMMAND_OUTPUT_MAX_BYTES (10240) constants, add command_timeout field to config in src/endless8/config/settings.py
- [ ] T007 Add CommandCriterionResult model to src/endless8/agents/__init__.py (depends on T005: imports CommandResult)
- [ ] T008 Update TaskInput.criteria type from list[str] to list[CriterionInput] in src/endless8/models/task.py (depends on T004: imports CriterionInput)

**Checkpoint**: 全データモデルと設定が定義済み。既存テストが引き続きパスすることを確認（str は CriterionInput の有効な値）

---

## Phase 3: User Story 1 - コマンド実行による客観的条件の検証 (Priority: P1) MVP

**Goal**: コマンド型の完了条件が終了コードに基づいて正しく met/not met 判定される

**Independent Test**: コマンド型の条件のみを持つタスクを実行し、コマンドの終了コードに基づいて正しく met/not met が判定されることを確認する

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Create test for CommandExecutor (happy path: exit code 0 → met, non-zero → not met; error path: OSError → CommandExecutionError, timeout → CommandExecutionError; output truncation at COMMAND_OUTPUT_MAX_BYTES) in tests/unit/test_command_executor.py
- [ ] T010 [P] [US1] Create test for Engine._run_command_criteria (sequential execution, CriteriaEvaluation generation) and _build_judgment_result_from_commands (FR-010: LLM skip for command-only tasks) in tests/unit/test_engine.py

### Implementation for User Story 1

- [ ] T011 [US1] Implement CommandExecutionError and CommandExecutor (asyncio.create_subprocess_shell + asyncio.wait_for, output truncation, OSError/TimeoutError handling) in src/endless8/command/executor.py
- [ ] T012 [US1] Implement Engine command judgment methods in src/endless8/engine.py: _run_command_criteria (sequential command execution, CriteriaEvaluation with evaluation_method=command), _build_judgment_result_from_commands (FR-010), criteria conversion helper (CriterionInput → str for agent interfaces), and initial _judgment_phase modification

**Checkpoint**: コマンド条件のみのタスクが正しく判定される。LLM 判定は省略される（FR-010）

---

## Phase 4: User Story 2 - 意味的条件とコマンド条件の混在 (Priority: P1)

**Goal**: 1つのタスクに意味的条件とコマンド条件を混在させ、各条件が適切な方式で判定される

**Independent Test**: 意味的条件とコマンド条件を混在させたタスクで、コマンド条件はコマンドで判定され、意味的条件は LLM で判定されることを確認する

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [US2] Create test for JudgmentContext with command_results, judgment agent prompt including command results, and Engine mixed judgment flow in tests/unit/test_judgment_agent.py

### Implementation for User Story 2

- [ ] T014 [US2] Extend JudgmentContext with command_results (list[CommandCriterionResult] | None) field in src/endless8/agents/__init__.py
- [ ] T015 [US2] Update judgment agent to include command results in LLM prompt (FR-007: command results as additional context for semantic judgment) in src/endless8/agents/judgment.py
- [ ] T016 [US2] Implement mixed judgment flow in Engine._judgment_phase: pass command_results to JudgmentContext, merge command evaluations with semantic evaluations into unified JudgmentResult in src/endless8/engine.py

**Checkpoint**: 意味的条件 + コマンド条件の混在タスクが正しく判定される。コマンド結果が LLM 判定のコンテキストとして提供される

---

## Phase 5: User Story 3 - コマンド実行エラーの明示的な報告 (Priority: P2)

**Goal**: コマンド実行エラー（OSError, タイムアウト）が発生した場合、ループを即座に停止しエラーを明示的に報告する

**Independent Test**: シェル起動失敗（OSError）やタイムアウトするコマンドを条件として指定し、ループが停止しエラーが適切に報告されることを確認する。また、存在しないコマンド名（終了コード 127）では条件が not met として正常処理されることを確認する

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US3] Create test for Engine loop stop on CommandExecutionError (first error stops execution, remaining commands skipped) in tests/unit/test_engine.py
- [ ] T018 [P] [US3] Create test for exit code 127 warning log in tests/unit/test_command_executor.py

### Implementation for User Story 3

- [ ] T019 [US3] Implement Engine error propagation: catch CommandExecutionError in _judgment_phase, stop loop immediately, report error to user with command details and error message in src/endless8/engine.py
- [ ] T020 [US3] Add warning log for exit code 127 (potential command typo) in src/endless8/command/executor.py

**Checkpoint**: コマンド実行エラー時にループが停止し、ユーザーにエラー内容が報告される

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 統合テストとドキュメント検証

- [ ] T021 Create integration test for command criteria loop execution (command-only, mixed, error scenarios) in tests/integration/test_command_criteria.py
- [ ] T022 Run quickstart.md scenarios for end-to-end validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (Phase 3) can start after Foundational
  - US2 (Phase 4) depends on US1 completion (extends Engine judgment phase)
  - US3 (Phase 5) depends on US1 completion (adds error handling to Engine)
  - US2 and US3 are independent of each other and can proceed in parallel
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on US1 (extends Engine._judgment_phase with mixed criteria flow)
- **User Story 3 (P2)**: Depends on US1 (adds error handling to Engine._judgment_phase). Independent of US2

### Within Each Phase

- Tests MUST be written and FAIL before implementation (TDD)
- Models before dependent implementations
- Core logic before integration logic

### Parallel Opportunities

- Foundational tests: T002 || T003
- Foundational implementation: T004 || T005 || T006
- US1 tests: T009 || T010
- US3 tests: T017 || T018
- After US1: US2 and US3 can proceed in parallel

---

## Parallel Example: Foundational Phase

```text
# Launch foundational tests together:
Task: T002 "Test Criterion type models in tests/unit/test_criteria_models.py"
Task: T003 "Test CommandResult and CriteriaEvaluation in tests/unit/test_models.py"

# Launch independent model implementations together:
Task: T004 "Implement criteria types in src/endless8/models/criteria.py"
Task: T005 "Implement CommandResult + CriteriaEvaluation in src/endless8/models/results.py"
Task: T006 "Add config constants in src/endless8/config/settings.py"
```

## Parallel Example: After US1

```text
# US2 and US3 can proceed in parallel:
Track A (US2): T013 → T014 → T015 → T016
Track B (US3): T017 || T018 → T019 → T020
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: コマンド条件のみのタスクが正しく動作するか確認
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → MVP! (コマンド条件が動作)
3. Add US2 → Test independently → (混在条件が動作)
4. Add US3 → Test independently → (エラー報告が完成)
5. Polish → Integration test + quickstart validation

### File Change Summary

| File | Phase | Action |
|------|-------|--------|
| src/endless8/command/__init__.py | Setup | NEW |
| src/endless8/models/criteria.py | Foundational | NEW |
| src/endless8/models/results.py | Foundational | MODIFY |
| src/endless8/config/settings.py | Foundational | MODIFY |
| src/endless8/agents/__init__.py | Foundational + US2 | MODIFY |
| src/endless8/models/task.py | Foundational | MODIFY |
| src/endless8/command/executor.py | US1 + US3 | NEW |
| src/endless8/engine.py | US1 + US2 + US3 | MODIFY |
| src/endless8/agents/judgment.py | US2 | MODIFY |
| tests/unit/test_criteria_models.py | Foundational | NEW |
| tests/unit/test_models.py | Foundational | MODIFY |
| tests/unit/test_command_executor.py | US1 + US3 | NEW |
| tests/unit/test_engine.py | US1 + US3 | MODIFY |
| tests/unit/test_judgment_agent.py | US2 | MODIFY |
| tests/integration/test_command_criteria.py | Polish | NEW |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD 必須: テスト作成 → Red 確認 → 実装 → Green 確認
- コマンド条件の確信度は常に 1.0（FR-011）
- コマンド出力は 10KB 制限（COMMAND_OUTPUT_MAX_BYTES）
- コマンドは定義順に順次実行（並列実行なし）
- 既存の str 条件は CriterionInput の一部として後方互換で動作する
