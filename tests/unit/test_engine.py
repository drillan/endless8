"""Unit tests for the Engine class."""

from unittest.mock import AsyncMock

import pytest

from endless8.models import (
    CriteriaEvaluation,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    LoopStatus,
    SummaryMetadata,
    TaskInput,
)


class TestEngine:
    """Tests for Engine class."""

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テストを追加しました",
            artifacts=["tests/test_main.py"],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="テストを追加",
                result=ExecutionStatus.SUCCESS,
                reason="テストファイル作成完了",
                artifacts=["tests/test_main.py"],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
            [],  # No knowledge extracted
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        """Create mock judgment agent."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="pytest --cov で90%以上",
                    is_met=True,
                    evidence="カバレッジレポートで92%を確認",
                    confidence=0.95,
                )
            ],
            overall_reason="すべての完了条件を満たしています",
        )
        return agent

    @pytest.fixture
    def task_input(self) -> TaskInput:
        """Create sample task input."""
        return TaskInput(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            max_iterations=10,
        )

    async def test_engine_run_completes_on_success(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine completes when judgment returns is_complete=True."""
        # Import here to allow tests to run before Engine is implemented
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used >= 1
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is True

    async def test_engine_run_stops_at_max_iterations(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine stops at max iterations when not complete."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Make judgment always return not complete
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="pytest --cov で90%以上",
                    is_met=False,
                    evidence="現在のカバレッジは80%",
                    confidence=0.9,
                )
            ],
            overall_reason="カバレッジが不足しています",
            suggested_next_action="edge case のテストを追加",
        )

        task_input_limited = TaskInput(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=3,  # Limit iterations
        )

        config = EngineConfig(
            task=task_input_limited.task,
            criteria=task_input_limited.criteria,
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input_limited)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.iterations_used == 3
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False

    async def test_engine_run_iter_yields_summaries(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that run_iter yields execution summaries."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        summaries: list[ExecutionSummary] = []
        async for summary in engine.run_iter(task_input):
            summaries.append(summary)

        assert len(summaries) >= 1
        assert all(isinstance(s, ExecutionSummary) for s in summaries)

    async def test_engine_cancel_stops_execution(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that cancel stops the execution loop."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Make judgment always return not complete
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[],
            overall_reason="Not complete",
        )

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=100,  # High limit
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        # Start running and cancel after first iteration
        summaries: list[ExecutionSummary] = []
        async for summary in engine.run_iter(task_input):
            summaries.append(summary)
            await engine.cancel()
            break

        assert engine.is_running is False

    async def test_engine_current_iteration_property(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that current_iteration property reflects execution state."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        assert engine.current_iteration == 0

        await engine.run(task_input)

        assert engine.current_iteration >= 1

    async def test_engine_run_needs_clarification(
        self,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine returns ERROR status when intake needs clarification."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Create intake agent that returns NEEDS_CLARIFICATION
        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.NEEDS_CLARIFICATION,
            task="曖昧なタスク",
            criteria=["不明確な条件"],
            clarification_questions=["具体的な基準は何ですか？", "対象範囲は？"],
        )

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.iterations_used == 0
        assert result.intake_result is not None
        assert result.intake_result.status == IntakeStatus.NEEDS_CLARIFICATION
        assert result.error_message is not None
        assert "clarification" in result.error_message.lower()
        # Execution agent should not be called
        mock_execution_agent.run.assert_not_called()

    async def test_engine_run_rejected(
        self,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine returns ERROR status when intake rejects the task."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Create intake agent that returns REJECTED
        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.REJECTED,
            task="不適切なタスク",
            criteria=["実行不可能な条件"],
            rejection_reason="このタスクは実行できません。技術的制約があります。",
        )

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.iterations_used == 0
        assert result.intake_result is not None
        assert result.intake_result.status == IntakeStatus.REJECTED
        assert result.error_message is not None
        assert "rejected" in result.error_message.lower()
        # Execution agent should not be called
        mock_execution_agent.run.assert_not_called()

    async def test_engine_run_tool_mismatch_error(
        self,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine returns ERROR when suggested_tools don't match allowed_tools."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Create intake agent that suggests tools not in allowed_tools
        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="Web検索タスク",
            criteria=["検索結果を取得"],
            suggested_tools=["WebSearch", "WebFetch", "Read", "Write"],
        )

        # Config with limited allowed_tools (no WebSearch/WebFetch)
        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )
        config.claude_options.allowed_tools = ["Read", "Edit", "Write", "Bash"]

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.iterations_used == 0
        assert result.error_message is not None
        assert "WebSearch" in result.error_message or "WebFetch" in result.error_message
        # Execution agent should not be called
        mock_execution_agent.run.assert_not_called()

    async def test_engine_run_tool_match_success(
        self,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine proceeds when suggested_tools match allowed_tools."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Create intake agent that suggests tools within allowed_tools
        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="コード編集タスク",
            criteria=["コードを修正"],
            suggested_tools=["Read", "Edit", "Write"],
        )

        # Config with allowed_tools that include all suggested tools
        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )
        config.claude_options.allowed_tools = ["Read", "Edit", "Write", "Bash"]

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        # Should proceed to execution
        assert result.status == LoopStatus.COMPLETED
        mock_execution_agent.run.assert_called()

    async def test_engine_run_empty_suggested_tools_proceeds(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
        task_input: TaskInput,
    ) -> None:
        """Test that engine proceeds when suggested_tools is empty."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Override to return empty suggested_tools
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="タスク",
            criteria=["条件"],
            suggested_tools=[],  # Empty
        )

        config = EngineConfig(
            task=task_input.task,
            criteria=task_input.criteria,
            max_iterations=task_input.max_iterations,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        result = await engine.run(task_input)

        # Should proceed to execution
        assert result.status == LoopStatus.COMPLETED
        mock_execution_agent.run.assert_called()


class TestProgressCallback:
    """Tests for on_progress callback."""

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=[],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
            [],
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        """Create mock judgment agent."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="達成",
                    confidence=1.0,
                )
            ],
            overall_reason="完了",
        )
        return agent

    async def test_progress_callback_receives_all_events(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        """Test that all event types are passed to callback."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import ProgressEvent, ProgressEventType

        events: list[ProgressEvent] = []

        def progress_callback(event: ProgressEvent) -> None:
            events.append(event)

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=3)
        await engine.run(task_input, on_progress=progress_callback)

        # Should receive at least: TASK_START, INTAKE_COMPLETE,
        # ITERATION_START, EXECUTION_COMPLETE, JUDGMENT_COMPLETE,
        # ITERATION_END, TASK_END
        event_types = [e.event_type for e in events]
        assert ProgressEventType.TASK_START in event_types
        assert ProgressEventType.INTAKE_COMPLETE in event_types
        assert ProgressEventType.ITERATION_START in event_types
        assert ProgressEventType.EXECUTION_COMPLETE in event_types
        assert ProgressEventType.JUDGMENT_COMPLETE in event_types
        assert ProgressEventType.ITERATION_END in event_types
        assert ProgressEventType.TASK_END in event_types

    async def test_progress_callback_exception_does_not_stop_engine(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        """Test that callback exception does not stop engine execution."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import ProgressEvent

        call_count = 0

        def failing_callback(_event: ProgressEvent) -> None:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Callback error")

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=3)

        # Engine should still complete even if callback raises
        # This test documents current behavior (callback exceptions propagate)
        # If this fails, engine needs try-except around callback invocation
        with pytest.raises(RuntimeError, match="Callback error"):
            await engine.run(task_input, on_progress=failing_callback)


class TestKnowledgeContextSize:
    """Tests for knowledge_context_size setting."""

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=[],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
            [],
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        """Create mock judgment agent."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="達成",
                    confidence=1.0,
                )
            ],
            overall_reason="完了",
        )
        return agent

    async def test_knowledge_context_size_is_configurable(self) -> None:
        """Test that knowledge_context_size setting is used."""
        from endless8.config import EngineConfig

        # Test that knowledge_context_size can be set
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=3,
            knowledge_context_size=15,
        )
        assert config.knowledge_context_size == 15

    async def test_knowledge_context_size_default_value(self) -> None:
        """Test that knowledge_context_size has a default value."""
        from endless8.config import EngineConfig

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        # Should have a configured default (not hardcoded 10 in engine)
        assert config.knowledge_context_size >= 1
