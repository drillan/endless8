"""Tests for task state models."""

from pathlib import Path

import pytest

from endless8.models.state import StateTransition, TaskPhase
from endless8.state import InvalidTransitionError, TaskStateMachine


class TestTaskPhase:
    """Tests for TaskPhase enum."""

    def test_all_phases_exist(self) -> None:
        assert TaskPhase.CREATED.value == "created"
        assert TaskPhase.INTAKE.value == "intake"
        assert TaskPhase.EXECUTING.value == "executing"
        assert TaskPhase.SUMMARIZING.value == "summarizing"
        assert TaskPhase.JUDGING.value == "judging"
        assert TaskPhase.COMPLETED.value == "completed"
        assert TaskPhase.FAILED.value == "failed"
        assert TaskPhase.ERROR.value == "error"
        assert TaskPhase.CANCELLED.value == "cancelled"

    def test_terminal_phases(self) -> None:
        assert TaskPhase.COMPLETED.is_terminal
        assert TaskPhase.FAILED.is_terminal
        assert TaskPhase.ERROR.is_terminal
        assert TaskPhase.CANCELLED.is_terminal
        assert not TaskPhase.EXECUTING.is_terminal

    def test_valid_transitions(self) -> None:
        assert TaskPhase.EXECUTING in TaskPhase.CREATED.valid_next_phases
        assert TaskPhase.COMPLETED not in TaskPhase.CREATED.valid_next_phases


class TestStateTransition:
    """Tests for StateTransition model."""

    def test_create_transition(self) -> None:
        t = StateTransition(
            from_phase=TaskPhase.CREATED,
            to_phase=TaskPhase.INTAKE,
            iteration=0,
        )
        assert t.from_phase == TaskPhase.CREATED
        assert t.to_phase == TaskPhase.INTAKE
        assert t.type == "state_transition"

    def test_serialization_roundtrip(self) -> None:
        t = StateTransition(
            from_phase=TaskPhase.EXECUTING,
            to_phase=TaskPhase.SUMMARIZING,
            iteration=1,
            metadata={"execution_status": "success"},
        )
        data = t.model_dump()
        restored = StateTransition(**data)
        assert restored == t


class TestTaskStateMachine:
    """Tests for TaskStateMachine class."""

    @pytest.fixture
    def state_file(self, tmp_path: Path) -> Path:
        return tmp_path / "state.jsonl"

    def test_initial_phase_is_created(self, state_file: Path) -> None:
        sm = TaskStateMachine(state_file)
        assert sm.current_phase == TaskPhase.CREATED
        assert sm.current_iteration == 0

    def test_valid_transition(self, state_file: Path) -> None:
        sm = TaskStateMachine(state_file)
        t = sm.transition(TaskPhase.INTAKE)
        assert t.from_phase == TaskPhase.CREATED
        assert t.to_phase == TaskPhase.INTAKE
        assert sm.current_phase == TaskPhase.INTAKE

    def test_invalid_transition_raises(self, state_file: Path) -> None:
        sm = TaskStateMachine(state_file)
        with pytest.raises(InvalidTransitionError):
            sm.transition(TaskPhase.COMPLETED)

    def test_terminal_phase_blocks_transition(self, state_file: Path) -> None:
        sm = TaskStateMachine(state_file)
        sm.transition(TaskPhase.INTAKE)
        sm.transition(TaskPhase.EXECUTING, iteration=1)
        sm.transition(TaskPhase.SUMMARIZING)
        sm.transition(TaskPhase.JUDGING)
        sm.transition(TaskPhase.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            sm.transition(TaskPhase.EXECUTING, iteration=2)

    def test_persistence_and_reload(self, state_file: Path) -> None:
        sm1 = TaskStateMachine(state_file)
        sm1.transition(TaskPhase.INTAKE)
        sm1.transition(TaskPhase.EXECUTING, iteration=1)

        sm2 = TaskStateMachine(state_file)
        assert sm2.current_phase == TaskPhase.EXECUTING
        assert sm2.current_iteration == 1

    def test_get_transitions(self, state_file: Path) -> None:
        sm = TaskStateMachine(state_file)
        sm.transition(TaskPhase.INTAKE)
        sm.transition(TaskPhase.EXECUTING, iteration=1)
        transitions = sm.get_transitions()
        assert len(transitions) == 2
        assert transitions[0].to_phase == TaskPhase.INTAKE
        assert transitions[1].to_phase == TaskPhase.EXECUTING

    def test_iteration_updates_on_executing(self, state_file: Path) -> None:
        sm = TaskStateMachine(state_file)
        sm.transition(TaskPhase.INTAKE)
        sm.transition(TaskPhase.EXECUTING, iteration=1)
        sm.transition(TaskPhase.SUMMARIZING)
        sm.transition(TaskPhase.JUDGING)
        sm.transition(TaskPhase.EXECUTING, iteration=2)
        assert sm.current_iteration == 2
