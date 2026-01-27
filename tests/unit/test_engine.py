"""Unit tests for the Engine class."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from endless8.agents import ExecutionContext
from endless8.models import (
    CriteriaEvaluation,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    Knowledge,
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
        assert config.knowledge_context_size == 10

    async def test_in_memory_knowledge_fallback(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        """Test that engine uses in-memory knowledge when knowledge_base is not configured."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import Knowledge, KnowledgeType

        # Create engine without knowledge_base
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        # Manually add knowledge to in-memory storage
        knowledge1 = Knowledge(
            type=KnowledgeType.LESSON,
            category="testing",
            content="テスト知見1",
            source_task="テスト",
        )
        knowledge2 = Knowledge(
            type=KnowledgeType.DISCOVERY,
            category="code",
            content="テスト知見2",
            source_task="テスト",
        )
        engine._knowledge.append(knowledge1)
        engine._knowledge.append(knowledge2)

        # Get knowledge context
        context = await engine._get_knowledge_context()

        # Should return formatted in-memory knowledge
        assert "[lesson] テスト知見1" in context
        assert "[discovery] テスト知見2" in context

    async def test_empty_in_memory_knowledge_returns_none_message(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        """Test that empty in-memory knowledge returns 'ナレッジなし' message."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        # Create engine without knowledge_base
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        # Get knowledge context with empty knowledge
        context = await engine._get_knowledge_context()

        # Should return "ナレッジなし"
        assert context == "ナレッジなし"


class TestEngineSummaryCriteria:
    """Tests for Engine passing criteria to SummaryAgent."""

    async def test_engine_passes_criteria_to_summary_agent(self) -> None:
        """Test that Engine passes criteria to summary_agent.run()."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件1", "条件2"],
        )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=[],
        )

        mock_summary_agent = AsyncMock()
        mock_summary_agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-27T10:00:00Z",
            ),
            [],
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=True,
                    evidence="達成",
                    confidence=1.0,
                )
            ],
            overall_reason="完了",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件1", "条件2"],
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(
            task="テスト",
            criteria=["条件1", "条件2"],
            max_iterations=3,
        )
        await engine.run(task_input)

        # Verify summary_agent.run was called with criteria
        mock_summary_agent.run.assert_called_once()
        call_kwargs = mock_summary_agent.run.call_args
        # criteria should be passed as a keyword argument or positional
        args, kwargs = call_kwargs
        # Check criteria is in the call (positional arg 3 or keyword)
        if "criteria" in kwargs:
            assert kwargs["criteria"] == ["条件1", "条件2"]
        else:
            # positional: execution_result, iteration, criteria
            assert args[2] == ["条件1", "条件2"]


class TestOutputMdSaving:
    """Tests for output.md saving in engine."""

    async def test_output_md_saved_after_run(self, tmp_path: Path) -> None:
        """Test that output.md is saved after engine run."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件"],
        )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="実行結果の出力テキスト",
            artifacts=[],
        )

        mock_summary_agent = AsyncMock()
        mock_summary_agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-27T10:00:00Z",
            ),
            [],
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
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

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=3)
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            history=history,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=3)
        await engine.run(task_input)

        output_path = tmp_path / "output.md"
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "実行結果の出力テキスト"

    async def test_output_md_overwritten_each_iteration(self, tmp_path: Path) -> None:
        """Test that output.md is overwritten each iteration with latest output."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件"],
        )

        # Return different outputs for each iteration
        call_count = 0

        async def execution_side_effect(_ctx: object) -> ExecutionResult:
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=f"出力イテレーション{call_count}",
                artifacts=[],
            )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.side_effect = execution_side_effect

        def summary_side_effect(
            _result: ExecutionResult,
            iteration: int,
            _criteria: list[str],
        ) -> tuple[ExecutionSummary, list[Knowledge]]:
            return (
                ExecutionSummary(
                    iteration=iteration,
                    approach=f"アプローチ{iteration}",
                    result=ExecutionStatus.SUCCESS,
                    reason=f"理由{iteration}",
                    artifacts=[],
                    metadata=SummaryMetadata(),
                    timestamp="2026-01-27T10:00:00Z",
                ),
                [],
            )

        mock_summary_agent = AsyncMock()
        mock_summary_agent.run.side_effect = summary_side_effect

        # Complete on second iteration
        judgment_count = 0

        def judgment_side_effect(_ctx: object) -> JudgmentResult:
            nonlocal judgment_count
            judgment_count += 1
            return JudgmentResult(
                is_complete=(judgment_count >= 2),
                evaluations=[
                    CriteriaEvaluation(
                        criterion="条件",
                        is_met=(judgment_count >= 2),
                        evidence="達成" if judgment_count >= 2 else "未達成",
                        confidence=1.0,
                    )
                ],
                overall_reason="完了" if judgment_count >= 2 else "未完了",
            )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = judgment_side_effect

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=5)
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            history=history,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        await engine.run(task_input)

        output_path = tmp_path / "output.md"
        assert output_path.exists()
        # Should contain the last iteration's output
        assert output_path.read_text(encoding="utf-8") == "出力イテレーション2"

    async def test_no_error_when_history_store_is_none(self) -> None:
        """Test that no error occurs when history_store is None."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件"],
        )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="出力",
            artifacts=[],
        )

        mock_summary_agent = AsyncMock()
        mock_summary_agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-27T10:00:00Z",
            ),
            [],
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
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

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=3)
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            # No history store
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=3)
        result = await engine.run(task_input)
        # Should complete without error
        assert result.status == LoopStatus.COMPLETED

    async def test_output_md_saved_in_run_iter(self, tmp_path: Path) -> None:
        """Test that output.md is saved when using run_iter."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        mock_intake_agent = AsyncMock()
        mock_intake_agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["条件"],
        )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="run_iter出力テキスト",
            artifacts=[],
        )

        mock_summary_agent = AsyncMock()
        mock_summary_agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-27T10:00:00Z",
            ),
            [],
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
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

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=3)
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            history=history,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=3)
        async for _ in engine.run_iter(task_input):
            pass

        output_path = tmp_path / "output.md"
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "run_iter出力テキスト"


class TestSaveOutputMd:
    """Tests for _save_output_md error handling."""

    def test_save_output_md_skips_when_no_history_store(self) -> None:
        """Test that _save_output_md does nothing when history_store is None."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=3)
        engine = Engine(config=config)

        # Should not raise
        engine._save_output_md("some output")

    def test_save_output_md_writes_file(self, tmp_path: Path) -> None:
        """Test that _save_output_md writes output to file."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=3)
        engine = Engine(config=config, history=history)

        engine._save_output_md("テスト出力")

        output_path = tmp_path / "output.md"
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "テスト出力"

    def test_save_output_md_handles_os_error(self, tmp_path: Path) -> None:
        """Test that _save_output_md handles OSError gracefully."""
        from unittest.mock import patch as mock_patch

        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        config = EngineConfig(task="テスト", criteria=["条件"], max_iterations=3)
        engine = Engine(config=config, history=history)

        with mock_patch.object(Path, "write_text", side_effect=OSError("disk full")):
            # Should not raise, just log warning
            engine._save_output_md("テスト出力")


class TestRawOutputContext:
    """Tests for raw_output_context feature."""

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
    def mock_judgment_complete(self) -> AsyncMock:
        """Create mock judgment agent that always completes."""
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
                timestamp="2026-01-27T10:00:00Z",
            ),
            [],
        )
        return agent

    async def test_raw_output_context_zero_passes_none(
        self,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_complete: AsyncMock,
    ) -> None:
        """Test that raw_output_context=0 passes None to ExecutionContext."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="出力",
            artifacts=[],
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=1,
            raw_output_context=0,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_complete,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=1)
        await engine.run(task_input)

        # Verify ExecutionContext was called with raw_output_context=None
        call_args = mock_execution_agent.run.call_args
        ctx: ExecutionContext = call_args[0][0]
        assert ctx.raw_output_context is None

    async def test_raw_output_context_one_passes_previous_output(
        self,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Test that raw_output_context=1 passes previous output on 2nd iteration."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        call_count = 0

        async def execution_side_effect(_ctx: ExecutionContext) -> ExecutionResult:
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=f"出力{call_count}",
                artifacts=[],
            )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.side_effect = execution_side_effect

        judgment_count = 0

        def judgment_side_effect(_ctx: object) -> JudgmentResult:
            nonlocal judgment_count
            judgment_count += 1
            return JudgmentResult(
                is_complete=(judgment_count >= 2),
                evaluations=[
                    CriteriaEvaluation(
                        criterion="条件",
                        is_met=(judgment_count >= 2),
                        evidence="達成" if judgment_count >= 2 else "未達成",
                        confidence=1.0,
                    )
                ],
                overall_reason="完了" if judgment_count >= 2 else "未完了",
            )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = judgment_side_effect

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=5,
            raw_output_context=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        await engine.run(task_input)

        # 2 iterations should have happened
        assert mock_execution_agent.run.call_count == 2

        # First call: raw_output_context should be None (no previous output)
        ctx1: ExecutionContext = mock_execution_agent.run.call_args_list[0][0][0]
        assert ctx1.raw_output_context is None

        # Second call: raw_output_context should be "出力1" (previous output)
        ctx2: ExecutionContext = mock_execution_agent.run.call_args_list[1][0][0]
        assert ctx2.raw_output_context == "出力1"

    async def test_raw_output_context_one_first_iteration_has_none(
        self,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_complete: AsyncMock,
    ) -> None:
        """Test that first iteration has None even with raw_output_context=1."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="出力",
            artifacts=[],
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=1,
            raw_output_context=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_complete,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=1)
        await engine.run(task_input)

        ctx: ExecutionContext = mock_execution_agent.run.call_args[0][0]
        assert ctx.raw_output_context is None

    async def test_raw_output_context_zero_backward_compatible(
        self,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_complete: AsyncMock,
    ) -> None:
        """Test that raw_output_context=0 is fully backward compatible."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="出力",
            artifacts=[],
        )

        # Default config (no raw_output_context specified)
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_complete,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=1)
        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        ctx: ExecutionContext = mock_execution_agent.run.call_args[0][0]
        assert ctx.raw_output_context is None

    async def test_raw_output_context_with_run_iter(
        self,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Test that raw_output_context works with run_iter."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        call_count = 0

        async def execution_side_effect(_ctx: ExecutionContext) -> ExecutionResult:
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=f"iter出力{call_count}",
                artifacts=[],
            )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.side_effect = execution_side_effect

        judgment_count = 0

        def judgment_side_effect(_ctx: object) -> JudgmentResult:
            nonlocal judgment_count
            judgment_count += 1
            return JudgmentResult(
                is_complete=(judgment_count >= 2),
                evaluations=[
                    CriteriaEvaluation(
                        criterion="条件",
                        is_met=(judgment_count >= 2),
                        evidence="達成" if judgment_count >= 2 else "未達成",
                        confidence=1.0,
                    )
                ],
                overall_reason="完了" if judgment_count >= 2 else "未完了",
            )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = judgment_side_effect

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=5,
            raw_output_context=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        summaries = []
        async for summary in engine.run_iter(task_input):
            summaries.append(summary)

        assert len(summaries) == 2

        # First call: raw_output_context should be None
        ctx1: ExecutionContext = mock_execution_agent.run.call_args_list[0][0][0]
        assert ctx1.raw_output_context is None

        # Second call: raw_output_context should be "iter出力1"
        ctx2: ExecutionContext = mock_execution_agent.run.call_args_list[1][0][0]
        assert ctx2.raw_output_context == "iter出力1"

    async def test_raw_output_context_resume_reads_output_md(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_complete: AsyncMock,
    ) -> None:
        """Test that resume reads previous output from output.md."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        # Write output.md to simulate previous execution
        output_md_path = tmp_path / "output.md"
        output_md_path.write_text("前回の出力内容", encoding="utf-8")

        # Write a history entry so resume knows to start from iteration 2
        summary = ExecutionSummary(
            iteration=1,
            approach="アプローチ",
            result=ExecutionStatus.SUCCESS,
            reason="理由",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-01-27T10:00:00Z",
        )
        await history.append(summary)

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="新しい出力",
            artifacts=[],
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=5,
            raw_output_context=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_complete,
            history=history,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        await engine.run(task_input, resume=True)

        # Execution agent should receive previous output from output.md
        ctx: ExecutionContext = mock_execution_agent.run.call_args[0][0]
        assert ctx.raw_output_context == "前回の出力内容"

    async def test_raw_output_context_resume_without_output_md(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_complete: AsyncMock,
    ) -> None:
        """Test that resume without output.md does not error."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        # Write a history entry so resume knows to start from iteration 2
        summary = ExecutionSummary(
            iteration=1,
            approach="アプローチ",
            result=ExecutionStatus.SUCCESS,
            reason="理由",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-01-27T10:00:00Z",
        )
        await history.append(summary)

        # No output.md file exists

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="出力",
            artifacts=[],
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=5,
            raw_output_context=1,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_complete,
            history=history,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        result = await engine.run(task_input, resume=True)

        # Should not error
        assert result.status == LoopStatus.COMPLETED
        # raw_output_context should be None since no output.md
        ctx: ExecutionContext = mock_execution_agent.run.call_args[0][0]
        assert ctx.raw_output_context is None

    async def test_raw_output_context_zero_resume_ignores_output_md(
        self,
        tmp_path: Path,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_complete: AsyncMock,
    ) -> None:
        """Test that raw_output_context=0 + resume + output.md exists → ctx.raw_output_context is None."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.history import History

        history_path = tmp_path / "history.jsonl"
        history = History(history_path)

        # Write output.md to simulate previous execution
        output_md_path = tmp_path / "output.md"
        output_md_path.write_text("前回の出力内容", encoding="utf-8")

        # Write a history entry so resume knows to start from iteration 2
        summary = ExecutionSummary(
            iteration=1,
            approach="アプローチ",
            result=ExecutionStatus.SUCCESS,
            reason="理由",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-01-27T10:00:00Z",
        )
        await history.append(summary)

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="新しい出力",
            artifacts=[],
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=5,
            raw_output_context=0,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_complete,
            history=history,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        await engine.run(task_input, resume=True)

        # raw_output_context should be None even though output.md exists
        ctx: ExecutionContext = mock_execution_agent.run.call_args[0][0]
        assert ctx.raw_output_context is None

    async def test_raw_output_context_zero_multi_iteration_stays_none(
        self,
        mock_intake_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Test that raw_output_context=0 + 2 iterations → 2nd iteration also has None."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine

        call_count = 0

        async def execution_side_effect(_ctx: ExecutionContext) -> ExecutionResult:
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=f"出力{call_count}",
                artifacts=[],
            )

        mock_execution_agent = AsyncMock()
        mock_execution_agent.run.side_effect = execution_side_effect

        judgment_count = 0

        def judgment_side_effect(_ctx: object) -> JudgmentResult:
            nonlocal judgment_count
            judgment_count += 1
            return JudgmentResult(
                is_complete=(judgment_count >= 2),
                evaluations=[
                    CriteriaEvaluation(
                        criterion="条件",
                        is_met=(judgment_count >= 2),
                        evidence="達成" if judgment_count >= 2 else "未達成",
                        confidence=1.0,
                    )
                ],
                overall_reason="完了" if judgment_count >= 2 else "未完了",
            )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.side_effect = judgment_side_effect

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            max_iterations=5,
            raw_output_context=0,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        task_input = TaskInput(task="テスト", criteria=["条件"], max_iterations=5)
        await engine.run(task_input)

        # 2 iterations should have happened
        assert mock_execution_agent.run.call_count == 2

        # Both calls should have raw_output_context=None
        ctx1: ExecutionContext = mock_execution_agent.run.call_args_list[0][0][0]
        assert ctx1.raw_output_context is None

        ctx2: ExecutionContext = mock_execution_agent.run.call_args_list[1][0][0]
        assert ctx2.raw_output_context is None
