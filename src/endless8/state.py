"""Task state machine for endless8 task lifecycle management."""

import json
import logging
from pathlib import Path

from endless8.models.state import StateTransition, TaskPhase

logger = logging.getLogger(__name__)


class InvalidTransitionError(Exception):
    """無効な状態遷移。"""

    def __init__(self, from_phase: TaskPhase, to_phase: TaskPhase) -> None:
        self.from_phase = from_phase
        self.to_phase = to_phase
        super().__init__(
            f"Invalid transition: {from_phase.value} -> {to_phase.value}. "
            f"Valid: {', '.join(p.value for p in from_phase.valid_next_phases)}"
        )


class TaskStateMachine:
    """タスクの状態遷移を管理し、JSONL に永続化する。"""

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self._transitions: list[StateTransition] = []
        self._current_phase = TaskPhase.CREATED
        self._current_iteration = 0
        self._load_existing()

    @property
    def current_phase(self) -> TaskPhase:
        return self._current_phase

    @property
    def current_iteration(self) -> int:
        return self._current_iteration

    def _load_existing(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("type") == "state_transition":
                        t = StateTransition(**data)
                        self._transitions.append(t)
                        self._current_phase = t.to_phase
                        if t.iteration > 0:
                            self._current_iteration = t.iteration
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning("Invalid state record skipped: %s", e)

    def transition(
        self,
        to_phase: TaskPhase,
        iteration: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StateTransition:
        """状態を遷移させ、JSONL に永続化する。"""
        if to_phase not in self._current_phase.valid_next_phases:
            raise InvalidTransitionError(self._current_phase, to_phase)

        effective_iteration = (
            iteration if iteration is not None else self._current_iteration
        )

        t = StateTransition(
            from_phase=self._current_phase,
            to_phase=to_phase,
            iteration=effective_iteration,
            metadata=metadata or {},
        )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(t.model_dump_json() + "\n")

        self._transitions.append(t)
        self._current_phase = to_phase
        if iteration is not None and iteration > 0:
            self._current_iteration = iteration

        return t

    def get_transitions(self) -> list[StateTransition]:
        return list(self._transitions)


__all__ = ["InvalidTransitionError", "TaskStateMachine"]
