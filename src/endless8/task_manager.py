"""Task manager for endless8 task lifecycle management."""

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from endless8.agents import CommandCriterionResult, ExecutionContext, JudgmentContext
from endless8.command.executor import CommandExecutor
from endless8.config import EngineConfig
from endless8.engine import (
    ExecutionAgentProtocol,
    IntakeAgentProtocol,
    JudgmentAgentProtocol,
    SummaryAgentProtocol,
)
from endless8.history import History, KnowledgeBase
from endless8.models import (
    CommandCriterion,
    CriteriaEvaluation,
    CriterionType,
    ExecutionSummary,
    IntakeStatus,
    JudgmentResult,
    criteria_to_str_list,
    filter_semantic_criteria,
)
from endless8.models.state import TaskPhase
from endless8.state import InvalidTransitionError, TaskStateMachine

logger = logging.getLogger(__name__)


class TaskStatus(BaseModel):
    """タスクの現在のステータス。"""

    task_id: str
    phase: TaskPhase
    current_iteration: int = Field(..., ge=0)
    max_iterations: int
    is_complete: bool
    task_description: str
    transitions_count: int = Field(..., ge=0)


class AdvanceResult(BaseModel):
    """advance() の戻り値。"""

    phase: TaskPhase
    iteration: int = Field(..., ge=0)
    judgment: JudgmentResult | None = None


class TaskManager:
    """タスクのライフサイクルを管理する。"""

    def __init__(self, project_dir: Path, config: EngineConfig) -> None:
        self._project_dir = project_dir
        self._config = config
        self._intake_agent: IntakeAgentProtocol | None = None
        self._execution_agent: ExecutionAgentProtocol | None = None
        self._summary_agent: SummaryAgentProtocol | None = None
        self._judgment_agent: JudgmentAgentProtocol | None = None
        self._previous_suggested_next_action: str | None = None

    def _task_dir(self, task_id: str) -> Path:
        return self._project_dir / ".e8" / "tasks" / task_id

    def _state_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "state.jsonl"

    async def create(self) -> str:
        """新しいタスクを作成し、task_id を返す。"""
        task_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        task_dir = self._task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        # 状態マシンを初期化（CREATED 状態のファイルを作成）
        TaskStateMachine(self._state_path(task_id))

        return task_id

    async def status(self, task_id: str) -> TaskStatus:
        """タスクの現在のステータスを返す。"""
        task_dir = self._task_dir(task_id)

        if not task_dir.exists():
            raise FileNotFoundError(f"Task not found: {task_id}")

        sm = TaskStateMachine(self._state_path(task_id))

        return TaskStatus(
            task_id=task_id,
            phase=sm.current_phase,
            current_iteration=sm.current_iteration,
            max_iterations=self._config.max_iterations,
            is_complete=sm.current_phase == TaskPhase.COMPLETED,
            task_description=self._config.task,
            transitions_count=len(sm.get_transitions()),
        )

    def set_agents(
        self,
        intake_agent: IntakeAgentProtocol | None = None,
        execution_agent: ExecutionAgentProtocol | None = None,
        summary_agent: SummaryAgentProtocol | None = None,
        judgment_agent: JudgmentAgentProtocol | None = None,
    ) -> None:
        """エージェントを設定する。"""
        if intake_agent is not None:
            self._intake_agent = intake_agent
        if execution_agent is not None:
            self._execution_agent = execution_agent
        if summary_agent is not None:
            self._summary_agent = summary_agent
        if judgment_agent is not None:
            self._judgment_agent = judgment_agent

    async def advance(self, task_id: str) -> AdvanceResult:
        """次のフェーズを実行する。"""
        sm = TaskStateMachine(self._state_path(task_id))
        task_dir = self._task_dir(task_id)
        phase = sm.current_phase

        if phase.is_terminal:
            raise InvalidTransitionError(phase, TaskPhase.EXECUTING)

        if phase == TaskPhase.CREATED:
            return await self._advance_intake(sm, task_dir)
        if phase == TaskPhase.EXECUTING:
            return await self._advance_execute(sm, task_dir)

        raise RuntimeError(f"Cannot advance from phase: {phase.value}")

    async def _advance_intake(
        self,
        sm: TaskStateMachine,
        task_dir: Path,  # noqa: ARG002
    ) -> AdvanceResult:
        """CREATED -> INTAKE -> EXECUTING。"""
        sm.transition(TaskPhase.INTAKE)

        if self._intake_agent:
            criteria_str = criteria_to_str_list(self._config.criteria)
            intake_result = await self._intake_agent.run(
                self._config.task, criteria_str
            )
            if intake_result.status != IntakeStatus.ACCEPTED:
                sm.transition(TaskPhase.ERROR, metadata={"reason": "intake_rejected"})
                return AdvanceResult(phase=TaskPhase.ERROR, iteration=0)

        sm.transition(TaskPhase.EXECUTING, iteration=sm.current_iteration + 1)
        return AdvanceResult(phase=TaskPhase.EXECUTING, iteration=sm.current_iteration)

    async def _advance_execute(
        self, sm: TaskStateMachine, task_dir: Path
    ) -> AdvanceResult:
        """EXECUTING -> SUMMARIZING -> JUDGING -> (COMPLETED | EXECUTING | FAILED)。"""
        iteration = sm.current_iteration

        # 1. Execute
        if not self._execution_agent:
            raise RuntimeError("Execution agent not configured")

        history_store = History(task_dir / "history.jsonl")
        knowledge_base = KnowledgeBase(task_dir / "knowledge.jsonl")

        history_context = await history_store.get_context_string(
            self._config.history_context_size
        )
        knowledge_context = await knowledge_base.get_context_string(
            self._config.knowledge_context_size
        )

        context = ExecutionContext(
            task=self._config.task,
            criteria=filter_semantic_criteria(self._config.criteria),
            iteration=iteration,
            history_context=history_context,
            knowledge_context=knowledge_context,
            working_directory=self._config.working_directory,
            suggested_next_action=self._previous_suggested_next_action,
        )
        execution_result = await self._execution_agent.run(context)

        # 2. Summary
        sm.transition(TaskPhase.SUMMARIZING)

        if not self._summary_agent:
            raise RuntimeError("Summary agent not configured")

        criteria_str = criteria_to_str_list(self._config.criteria)
        summary, knowledge_list = await self._summary_agent.run(
            execution_result, iteration, criteria_str
        )
        await history_store.append(summary)
        if knowledge_list:
            await knowledge_base.add_many(knowledge_list)

        # 3. Judgment
        sm.transition(TaskPhase.JUDGING)
        judgment = await self._run_judgment(summary)
        await history_store.append_judgment(judgment, iteration)

        self._previous_suggested_next_action = judgment.suggested_next_action

        # 4. Transition
        if judgment.is_complete:
            sm.transition(TaskPhase.COMPLETED)
            return AdvanceResult(
                phase=TaskPhase.COMPLETED, iteration=iteration, judgment=judgment
            )

        if iteration >= self._config.max_iterations:
            sm.transition(TaskPhase.FAILED, metadata={"reason": "max_iterations"})
            return AdvanceResult(
                phase=TaskPhase.FAILED, iteration=iteration, judgment=judgment
            )

        sm.transition(TaskPhase.EXECUTING, iteration=iteration + 1)
        return AdvanceResult(
            phase=TaskPhase.EXECUTING, iteration=iteration + 1, judgment=judgment
        )

    async def _run_judgment(self, summary: ExecutionSummary) -> JudgmentResult:
        """判定フェーズ。"""
        criteria = self._config.criteria
        cwd = self._config.working_directory

        # コマンド条件の実行
        executor = CommandExecutor()
        command_evaluations: list[CriteriaEvaluation] = []
        command_results: list[CommandCriterionResult] = []

        for index, criterion in enumerate(criteria):
            if not isinstance(criterion, CommandCriterion):
                continue
            timeout = criterion.timeout or self._config.command_timeout
            result = await executor.execute(criterion.command, cwd, timeout)
            is_met = result.exit_code == 0
            description = criterion.description or criterion.command
            evidence_parts = [f"exit_code={result.exit_code}"]
            if result.stdout:
                evidence_parts.append(f"stdout: {result.stdout[:200]}")

            command_evaluations.append(
                CriteriaEvaluation(
                    criterion=description,
                    is_met=is_met,
                    evidence=", ".join(evidence_parts),
                    confidence=1.0,
                    evaluation_method=CriterionType.COMMAND,
                    command_result=result,
                )
            )
            command_results.append(
                CommandCriterionResult(
                    criterion_index=index,
                    description=description,
                    command=criterion.command,
                    is_met=is_met,
                    result=result,
                )
            )

        has_semantic = any(isinstance(c, str) for c in criteria)

        if not has_semantic:
            all_met = all(e.is_met for e in command_evaluations)
            return JudgmentResult(
                is_complete=all_met,
                evaluations=command_evaluations,
                overall_reason="すべてのコマンド条件が満たされました"
                if all_met
                else "未達成のコマンド条件あり",
                suggested_next_action=None if all_met else "コマンド条件を確認",
            )

        if not self._judgment_agent:
            raise RuntimeError("Judgment agent not configured")

        semantic_criteria = [c for c in criteria if isinstance(c, str)]
        judgment_context = JudgmentContext(
            task=self._config.task,
            criteria=semantic_criteria,
            execution_summary=summary,
            command_results=command_results if command_results else None,
            custom_prompt=self._config.prompts.judgment,
        )
        semantic_judgment = await self._judgment_agent.run(judgment_context)

        if not command_evaluations:
            return semantic_judgment

        merged = command_evaluations + semantic_judgment.evaluations
        all_met = all(e.is_met for e in merged)
        return JudgmentResult(
            is_complete=all_met,
            evaluations=merged,
            overall_reason=semantic_judgment.overall_reason,
            suggested_next_action=semantic_judgment.suggested_next_action
            if not all_met
            else None,
        )


__all__ = ["AdvanceResult", "TaskManager", "TaskStatus"]
