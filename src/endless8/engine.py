"""Engine - Main task execution loop for endless8.

The Engine coordinates the 4 agents:
1. Intake Agent: Validates task and criteria
2. Execution Agent: Executes the task
3. Summary Agent: Compresses results
4. Judgment Agent: Evaluates completion
"""

import asyncio
import logging
import traceback
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol

from endless8.agents import ExecutionContext, JudgmentContext
from endless8.config import EngineConfig
from endless8.history import History, KnowledgeBase
from endless8.models import (
    ExecutionResult,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    Knowledge,
    LoopResult,
    LoopStatus,
    ProgressEvent,
    ProgressEventType,
    TaskInput,
)

# Progress callback type
ProgressCallback = (
    Callable[[ProgressEvent], None] | Callable[[ProgressEvent], Awaitable[None]]
)

logger = logging.getLogger(__name__)


class IntakeAgentProtocol(Protocol):
    """Protocol for intake agent."""

    async def run(self, task: str, criteria: list[str]) -> IntakeResult: ...


class ExecutionAgentProtocol(Protocol):
    """Protocol for execution agent."""

    async def run(self, context: ExecutionContext) -> ExecutionResult: ...


class SummaryAgentProtocol(Protocol):
    """Protocol for summary agent."""

    async def run(
        self,
        execution_result: ExecutionResult,
        iteration: int,
        criteria: list[str],
        raw_log_content: str | None = None,
    ) -> tuple[ExecutionSummary, list[Knowledge]]: ...


class JudgmentAgentProtocol(Protocol):
    """Protocol for judgment agent."""

    async def run(self, context: JudgmentContext) -> JudgmentResult: ...


class Engine:
    """Main task execution engine.

    Coordinates the execution loop with 4 agents:
    - Intake: Validates task and criteria
    - Execution: Runs the task
    - Summary: Compresses results for history
    - Judgment: Evaluates completion criteria
    """

    def __init__(
        self,
        config: EngineConfig,
        intake_agent: IntakeAgentProtocol | None = None,
        execution_agent: ExecutionAgentProtocol | None = None,
        summary_agent: SummaryAgentProtocol | None = None,
        judgment_agent: JudgmentAgentProtocol | None = None,
        history: History | None = None,
        knowledge_base: KnowledgeBase | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            config: Engine configuration.
            intake_agent: Intake agent instance (optional, created if not provided).
            execution_agent: Execution agent instance (optional, created if not provided).
            summary_agent: Summary agent instance (optional, created if not provided).
            judgment_agent: Judgment agent instance (optional, created if not provided).
            history: History instance for persisting summaries (optional).
            knowledge_base: KnowledgeBase instance for persisting knowledge (optional).
        """
        self._config = config
        self._intake_agent = intake_agent
        self._execution_agent = execution_agent
        self._summary_agent = summary_agent
        self._judgment_agent = judgment_agent
        self._history_store = history
        self._knowledge_base = knowledge_base

        self._current_iteration = 0
        self._is_running = False
        self._cancelled = False
        self._history: list[ExecutionSummary] = []
        self._knowledge: list[Knowledge] = []
        self._start_iteration = 1  # For resume support

    async def _initialize_from_history(self) -> None:
        """Initialize iteration counter from history for resume support."""
        if self._history_store:
            last_iter = await self._history_store.get_last_iteration()
            if last_iter > 0:
                self._start_iteration = last_iter + 1
                logger.info("Resuming from iteration %d", self._start_iteration)

    @property
    def is_running(self) -> bool:
        """Whether the engine is currently running."""
        return self._is_running

    @property
    def current_iteration(self) -> int:
        """Current iteration number (0 = not started)."""
        return self._current_iteration

    async def _get_history_context(self) -> str:
        """Get formatted history context for execution agent.

        Returns:
            Formatted string of recent execution summaries.
        """
        # Use persisted history if available
        if self._history_store:
            return await self._history_store.get_context_string(
                self._config.history_context_size
            )

        # Fall back to in-memory history
        if not self._history:
            return "履歴なし"

        # Get recent summaries
        recent = self._history[-self._config.history_context_size :]
        lines = []
        for summary in recent:
            lines.append(
                f"[Iteration {summary.iteration}] {summary.approach} -> {summary.result.value}: {summary.reason}"
            )
        return "\n".join(lines)

    async def _get_knowledge_context(self) -> str:
        """Get formatted knowledge context for execution agent.

        Returns:
            Formatted string of relevant knowledge.
        """
        limit = self._config.knowledge_context_size

        # Use persisted knowledge base if available
        if self._knowledge_base:
            return await self._knowledge_base.get_context_string(limit)

        # Fall back to in-memory knowledge with debug log
        logger.debug("Knowledge base not configured, using in-memory storage")
        if not self._knowledge:
            return "ナレッジなし"

        lines = []
        for k in self._knowledge[-limit:]:
            lines.append(f"[{k.type.value}] {k.content}")
        return "\n".join(lines)

    async def _emit_progress(
        self,
        on_progress: ProgressCallback | None,
        event_type: ProgressEventType,
        message: str,
        iteration: int | None = None,
        data: dict[str, object] | None = None,
    ) -> None:
        """Emit a progress event.

        Args:
            on_progress: Progress callback function.
            event_type: Type of progress event.
            message: Progress message.
            iteration: Current iteration number.
            data: Additional data to include in the event.
        """
        if on_progress is None:
            return

        event = ProgressEvent(
            event_type=event_type,
            iteration=iteration,
            message=message,
            data=data,
        )

        # Call the callback - handle both sync and async
        result = on_progress(event)
        if asyncio.iscoroutine(result):
            await result

    async def run(
        self,
        task_input: TaskInput,
        on_progress: ProgressCallback | None = None,
        resume: bool = False,
    ) -> LoopResult:
        """Run the task execution loop.

        Args:
            task_input: Task input with task description, criteria, etc.
            on_progress: Optional callback for progress events.
            resume: If True, resume from last iteration in history.

        Returns:
            LoopResult with final status and judgment.
        """
        self._is_running = True
        self._cancelled = False
        self._current_iteration = 0
        final_judgment: JudgmentResult | None = None

        try:
            # Initialize from history if resuming
            if resume:
                await self._initialize_from_history()

            # Emit task start event
            start_msg = (
                "タスク再開" if resume and self._start_iteration > 1 else "タスク開始"
            )
            await self._emit_progress(
                on_progress,
                ProgressEventType.TASK_START,
                f"{start_msg}: {task_input.task[:50]}...",
                data={
                    "task": task_input.task,
                    "criteria": task_input.criteria,
                    "resume": resume,
                },
            )

            # Run intake validation
            if self._intake_agent:
                intake_result = await self._intake_agent.run(
                    task_input.task, task_input.criteria
                )

                await self._emit_progress(
                    on_progress,
                    ProgressEventType.INTAKE_COMPLETE,
                    f"受付完了: {intake_result.status.value}",
                    data={"status": intake_result.status.value},
                )

                if intake_result.status == IntakeStatus.NEEDS_CLARIFICATION:
                    self._is_running = False
                    questions = ", ".join(intake_result.clarification_questions)
                    await self._emit_progress(
                        on_progress,
                        ProgressEventType.TASK_END,
                        "タスク終了: 明確化が必要",
                        data={"status": "needs_clarification"},
                    )
                    return LoopResult(
                        status=LoopStatus.ERROR,
                        iterations_used=0,
                        intake_result=intake_result,
                        error_message=f"Task requires clarification: {questions}",
                    )

                # Check tool mismatch
                if intake_result.suggested_tools:
                    allowed_tools = set(self._config.claude_options.allowed_tools)
                    suggested_tools = set(intake_result.suggested_tools)
                    missing_tools = suggested_tools - allowed_tools
                    if missing_tools:
                        self._is_running = False
                        missing_list = ", ".join(sorted(missing_tools))
                        allowed_list = ", ".join(sorted(allowed_tools))
                        await self._emit_progress(
                            on_progress,
                            ProgressEventType.TASK_END,
                            "タスク終了: ツール設定エラー",
                            data={
                                "status": "tool_mismatch",
                                "missing_tools": list(missing_tools),
                            },
                        )
                        return LoopResult(
                            status=LoopStatus.ERROR,
                            iterations_used=0,
                            intake_result=intake_result,
                            error_message=(
                                f"Tool mismatch: required tools [{missing_list}] "
                                f"are not in allowed_tools [{allowed_list}]"
                            ),
                        )

                if intake_result.status == IntakeStatus.REJECTED:
                    self._is_running = False
                    reason = intake_result.rejection_reason or "Unknown reason"
                    await self._emit_progress(
                        on_progress,
                        ProgressEventType.TASK_END,
                        "タスク終了: 却下",
                        data={"status": "rejected", "reason": reason},
                    )
                    return LoopResult(
                        status=LoopStatus.ERROR,
                        iterations_used=0,
                        intake_result=intake_result,
                        error_message=f"Task rejected: {reason}",
                    )

            # Main execution loop
            max_iter = task_input.max_iterations
            start = self._start_iteration if resume else 1
            for iteration in range(start, max_iter + 1):
                if self._cancelled:
                    self._is_running = False
                    await self._emit_progress(
                        on_progress,
                        ProgressEventType.TASK_END,
                        "タスクキャンセル",
                        iteration=iteration,
                        data={"status": "cancelled"},
                    )
                    result = LoopResult(
                        status=LoopStatus.CANCELLED,
                        iterations_used=self._current_iteration,
                        final_judgment=final_judgment,
                    )
                    # Save final result to history
                    if self._history_store:
                        await self._history_store.append_final_result(result)
                    return result

                self._current_iteration = iteration

                # Emit iteration start
                await self._emit_progress(
                    on_progress,
                    ProgressEventType.ITERATION_START,
                    f"イテレーション {iteration} 開始",
                    iteration=iteration,
                )

                # Build execution context
                context = ExecutionContext(
                    task=task_input.task,
                    criteria=task_input.criteria,
                    iteration=iteration,
                    history_context=await self._get_history_context(),
                    knowledge_context=await self._get_knowledge_context(),
                )

                # Execute
                if self._execution_agent:
                    execution_result = await self._execution_agent.run(context)
                    await self._emit_progress(
                        on_progress,
                        ProgressEventType.EXECUTION_COMPLETE,
                        f"実行完了: {execution_result.status.value}",
                        iteration=iteration,
                        data={"status": execution_result.status.value},
                    )

                    # Save execution output to output.md
                    if self._history_store:
                        output_path = self._history_store.path.parent / "output.md"
                        output_path.write_text(
                            execution_result.output, encoding="utf-8"
                        )
                else:
                    raise RuntimeError("Execution agent not configured")

                # Summarize
                if self._summary_agent:
                    summary, knowledge_list = await self._summary_agent.run(
                        execution_result, iteration, task_input.criteria
                    )
                    self._history.append(summary)
                    self._knowledge.extend(knowledge_list)

                    # Persist summary to history store
                    if self._history_store:
                        await self._history_store.append(summary)

                    # Persist knowledge to knowledge base
                    if self._knowledge_base and knowledge_list:
                        await self._knowledge_base.add_many(knowledge_list)
                else:
                    raise RuntimeError("Summary agent not configured")

                # Judge
                if self._judgment_agent:
                    judgment_context = JudgmentContext(
                        task=task_input.task,
                        criteria=task_input.criteria,
                        execution_summary=summary,
                        custom_prompt=self._config.prompts.judgment,
                    )
                    final_judgment = await self._judgment_agent.run(judgment_context)

                    await self._emit_progress(
                        on_progress,
                        ProgressEventType.JUDGMENT_COMPLETE,
                        f"判定完了: {'完了' if final_judgment.is_complete else '未完了'}",
                        iteration=iteration,
                        data={"is_complete": final_judgment.is_complete},
                    )

                    # Emit iteration end
                    await self._emit_progress(
                        on_progress,
                        ProgressEventType.ITERATION_END,
                        f"イテレーション {iteration} 終了",
                        iteration=iteration,
                        data={"result": summary.result.value},
                    )

                    # Save judgment to history
                    if self._history_store:
                        await self._history_store.append_judgment(
                            final_judgment, iteration
                        )

                    if final_judgment.is_complete:
                        self._is_running = False
                        await self._emit_progress(
                            on_progress,
                            ProgressEventType.TASK_END,
                            f"タスク完了 ({iteration} イテレーション)",
                            iteration=iteration,
                            data={"status": "completed"},
                        )
                        result = LoopResult(
                            status=LoopStatus.COMPLETED,
                            iterations_used=iteration,
                            final_judgment=final_judgment,
                            history_path=self._config.persist,
                        )
                        # Save final result to history
                        if self._history_store:
                            await self._history_store.append_final_result(result)
                        return result
                else:
                    raise RuntimeError("Judgment agent not configured")

            # Max iterations reached
            self._is_running = False
            await self._emit_progress(
                on_progress,
                ProgressEventType.TASK_END,
                f"最大イテレーション数に到達 ({max_iter})",
                iteration=max_iter,
                data={"status": "max_iterations"},
            )
            result = LoopResult(
                status=LoopStatus.MAX_ITERATIONS,
                iterations_used=max_iter,
                final_judgment=final_judgment,
                history_path=self._config.persist,
            )
            # Save final result to history
            if self._history_store:
                await self._history_store.append_final_result(result)
            return result

        except Exception as e:
            self._is_running = False
            stack_trace = traceback.format_exc()
            logger.exception(
                "Engine execution failed at iteration %d: %s",
                self._current_iteration,
                e,
            )
            await self._emit_progress(
                on_progress,
                ProgressEventType.TASK_END,
                f"エラー: {e}",
                iteration=self._current_iteration
                if self._current_iteration > 0
                else None,
                data={"status": "error", "error": str(e)},
            )
            result = LoopResult(
                status=LoopStatus.ERROR,
                iterations_used=self._current_iteration,
                error_message=f"{e}\n\nStack trace:\n{stack_trace}",
            )
            # Save final result to history (if history is available)
            if self._history_store:
                await self._history_store.append_final_result(result)
            return result

    async def run_iter(self, task_input: TaskInput) -> AsyncIterator[ExecutionSummary]:
        """Run the task execution loop, yielding summaries.

        Args:
            task_input: Task input with task description, criteria, etc.

        Yields:
            ExecutionSummary for each iteration.
        """
        self._is_running = True
        self._cancelled = False
        self._current_iteration = 0

        try:
            # Run intake validation
            if self._intake_agent:
                intake_result = await self._intake_agent.run(
                    task_input.task, task_input.criteria
                )
                if intake_result.status == IntakeStatus.NEEDS_CLARIFICATION:
                    self._is_running = False
                    return

            # Main execution loop
            max_iter = task_input.max_iterations
            for iteration in range(1, max_iter + 1):
                if self._cancelled:
                    self._is_running = False
                    return

                self._current_iteration = iteration

                # Build execution context
                context = ExecutionContext(
                    task=task_input.task,
                    criteria=task_input.criteria,
                    iteration=iteration,
                    history_context=await self._get_history_context(),
                    knowledge_context=await self._get_knowledge_context(),
                )

                # Execute
                if self._execution_agent:
                    execution_result = await self._execution_agent.run(context)

                    # Save execution output to output.md
                    if self._history_store:
                        output_path = self._history_store.path.parent / "output.md"
                        output_path.write_text(
                            execution_result.output, encoding="utf-8"
                        )
                else:
                    raise RuntimeError("Execution agent not configured")

                # Summarize
                if self._summary_agent:
                    summary, knowledge_list = await self._summary_agent.run(
                        execution_result, iteration, task_input.criteria
                    )
                    self._history.append(summary)
                    self._knowledge.extend(knowledge_list)

                    # Persist summary to history store
                    if self._history_store:
                        await self._history_store.append(summary)

                    # Persist knowledge to knowledge base
                    if self._knowledge_base and knowledge_list:
                        await self._knowledge_base.add_many(knowledge_list)

                    yield summary
                else:
                    raise RuntimeError("Summary agent not configured")

                # Judge
                if self._judgment_agent:
                    judgment_context = JudgmentContext(
                        task=task_input.task,
                        criteria=task_input.criteria,
                        execution_summary=summary,
                        custom_prompt=self._config.prompts.judgment,
                    )
                    judgment = await self._judgment_agent.run(judgment_context)

                    # Save judgment to history
                    if self._history_store:
                        await self._history_store.append_judgment(judgment, iteration)

                    if judgment.is_complete:
                        self._is_running = False
                        return
                else:
                    raise RuntimeError("Judgment agent not configured")

            self._is_running = False

        except Exception:
            self._is_running = False
            raise

    async def cancel(self) -> None:
        """Cancel the running execution."""
        self._cancelled = True
        self._is_running = False


__all__ = ["Engine"]
