"""Engine - Main task execution loop for endless8.

The Engine coordinates the 4 agents:
1. Intake Agent: Validates task and criteria
2. Execution Agent: Executes the task
3. Summary Agent: Compresses results
4. Judgment Agent: Evaluates completion
"""

from collections.abc import AsyncIterator
from typing import Protocol

from endless8.agents import ExecutionContext, JudgmentContext
from endless8.config import EngineConfig
from endless8.models import (
    ExecutionResult,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    Knowledge,
    LoopResult,
    LoopStatus,
    TaskInput,
)


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
    ) -> None:
        """Initialize the engine.

        Args:
            config: Engine configuration.
            intake_agent: Intake agent instance (optional, created if not provided).
            execution_agent: Execution agent instance (optional, created if not provided).
            summary_agent: Summary agent instance (optional, created if not provided).
            judgment_agent: Judgment agent instance (optional, created if not provided).
        """
        self._config = config
        self._intake_agent = intake_agent
        self._execution_agent = execution_agent
        self._summary_agent = summary_agent
        self._judgment_agent = judgment_agent

        self._current_iteration = 0
        self._is_running = False
        self._cancelled = False
        self._history: list[ExecutionSummary] = []
        self._knowledge: list[Knowledge] = []

    @property
    def is_running(self) -> bool:
        """Whether the engine is currently running."""
        return self._is_running

    @property
    def current_iteration(self) -> int:
        """Current iteration number (0 = not started)."""
        return self._current_iteration

    def _get_history_context(self) -> str:
        """Get formatted history context for execution agent.

        Returns:
            Formatted string of recent execution summaries.
        """
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

    def _get_knowledge_context(self) -> str:
        """Get formatted knowledge context for execution agent.

        Returns:
            Formatted string of relevant knowledge.
        """
        if not self._knowledge:
            return "ナレッジなし"

        lines = []
        for k in self._knowledge[-10:]:  # Last 10 knowledge items
            lines.append(f"[{k.type.value}] {k.content}")
        return "\n".join(lines)

    async def run(self, task_input: TaskInput) -> LoopResult:
        """Run the task execution loop.

        Args:
            task_input: Task input with task description, criteria, etc.

        Returns:
            LoopResult with final status and judgment.
        """
        self._is_running = True
        self._cancelled = False
        self._current_iteration = 0
        final_judgment: JudgmentResult | None = None

        try:
            # Run intake validation
            if self._intake_agent:
                intake_result = await self._intake_agent.run(
                    task_input.task, task_input.criteria
                )
                if intake_result.status == IntakeStatus.NEEDS_CLARIFICATION:
                    self._is_running = False
                    questions = ", ".join(intake_result.clarification_questions)
                    return LoopResult(
                        status=LoopStatus.ERROR,
                        iterations_used=0,
                        intake_result=intake_result,
                        error_message=f"Task requires clarification: {questions}",
                    )
                if intake_result.status == IntakeStatus.REJECTED:
                    self._is_running = False
                    reason = intake_result.rejection_reason or "Unknown reason"
                    return LoopResult(
                        status=LoopStatus.ERROR,
                        iterations_used=0,
                        intake_result=intake_result,
                        error_message=f"Task rejected: {reason}",
                    )

            # Main execution loop
            max_iter = task_input.max_iterations
            for iteration in range(1, max_iter + 1):
                if self._cancelled:
                    self._is_running = False
                    return LoopResult(
                        status=LoopStatus.CANCELLED,
                        iterations_used=self._current_iteration,
                        final_judgment=final_judgment,
                    )

                self._current_iteration = iteration

                # Build execution context
                context = ExecutionContext(
                    task=task_input.task,
                    criteria=task_input.criteria,
                    iteration=iteration,
                    history_context=self._get_history_context(),
                    knowledge_context=self._get_knowledge_context(),
                )

                # Execute
                if self._execution_agent:
                    execution_result = await self._execution_agent.run(context)
                else:
                    raise RuntimeError("Execution agent not configured")

                # Summarize
                if self._summary_agent:
                    summary, knowledge_list = await self._summary_agent.run(
                        execution_result, iteration
                    )
                    self._history.append(summary)
                    self._knowledge.extend(knowledge_list)
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

                    if final_judgment.is_complete:
                        self._is_running = False
                        return LoopResult(
                            status=LoopStatus.COMPLETED,
                            iterations_used=iteration,
                            final_judgment=final_judgment,
                            history_path=self._config.persist,
                        )
                else:
                    raise RuntimeError("Judgment agent not configured")

            # Max iterations reached
            self._is_running = False
            return LoopResult(
                status=LoopStatus.MAX_ITERATIONS,
                iterations_used=max_iter,
                final_judgment=final_judgment,
                history_path=self._config.persist,
            )

        except Exception as e:
            self._is_running = False
            return LoopResult(
                status=LoopStatus.ERROR,
                iterations_used=self._current_iteration,
                error_message=str(e),
            )

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
                    history_context=self._get_history_context(),
                    knowledge_context=self._get_knowledge_context(),
                )

                # Execute
                if self._execution_agent:
                    execution_result = await self._execution_agent.run(context)
                else:
                    raise RuntimeError("Execution agent not configured")

                # Summarize
                if self._summary_agent:
                    summary, knowledge_list = await self._summary_agent.run(
                        execution_result, iteration
                    )
                    self._history.append(summary)
                    self._knowledge.extend(knowledge_list)
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
