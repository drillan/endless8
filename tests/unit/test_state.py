"""Tests for task state models."""

from endless8.models.state import StateTransition, TaskPhase


class TestTaskPhase:
    """Tests for TaskPhase enum."""

    def test_all_phases_exist(self) -> None:
        assert TaskPhase.CREATED == "created"
        assert TaskPhase.INTAKE == "intake"
        assert TaskPhase.EXECUTING == "executing"
        assert TaskPhase.SUMMARIZING == "summarizing"
        assert TaskPhase.JUDGING == "judging"
        assert TaskPhase.COMPLETED == "completed"
        assert TaskPhase.FAILED == "failed"
        assert TaskPhase.ERROR == "error"
        assert TaskPhase.CANCELLED == "cancelled"

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
