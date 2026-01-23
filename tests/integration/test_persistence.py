"""Integration tests for task persistence and resume (User Story 4)."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from endless8.agents import JudgmentContext
from endless8.config import EngineConfig
from endless8.engine import Engine
from endless8.history import History, KnowledgeBase
from endless8.models import (
    CriteriaEvaluation,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    Knowledge,
    KnowledgeConfidence,
    KnowledgeType,
    LoopResult,
    SummaryMetadata,
    TaskInput,
)


def _make_summary(
    iteration: int,
    approach: str,
    result: ExecutionStatus,
    reason: str,
    artifacts: list[str] | None = None,
) -> ExecutionSummary:
    """Helper to create ExecutionSummary with timestamp."""
    return ExecutionSummary(
        iteration=iteration,
        approach=approach,
        result=result,
        reason=reason,
        artifacts=artifacts or [],
        metadata=SummaryMetadata(),
        timestamp=datetime.now().isoformat(),
    )


def _make_knowledge(
    knowledge_type: KnowledgeType,
    content: str,
    confidence: KnowledgeConfidence = KnowledgeConfidence.HIGH,
) -> Knowledge:
    """Helper to create Knowledge with required fields."""
    return Knowledge(
        type=knowledge_type,
        category="test",
        content=content,
        source_task="test_task",
        confidence=confidence,
    )


class TestTaskPersistence:
    """Tests for task persistence."""

    @pytest.fixture
    def temp_task_dir(self, tmp_path: Path) -> Path:
        """Create temporary task directory."""
        task_dir = tmp_path / ".e8" / "tasks" / "test-task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    @pytest.fixture
    def engine_config(self) -> EngineConfig:
        """Create engine configuration."""
        return EngineConfig(
            task="テストタスク",
            criteria=["条件1", "条件2"],
            max_iterations=10,
        )

    @pytest.mark.asyncio
    async def test_history_saved_per_iteration(self, temp_task_dir: Path) -> None:
        """Test that history is saved after each iteration."""
        history_path = temp_task_dir / "history.jsonl"
        history = History(history_path)

        # Simulate iteration 1
        summary1 = _make_summary(
            iteration=1,
            approach="アプローチ1",
            result=ExecutionStatus.SUCCESS,
            reason="成功1",
        )
        await history.append(summary1)

        # File should exist and have content
        assert history_path.exists()
        content = history_path.read_text()
        assert "アプローチ1" in content

        # Simulate iteration 2
        summary2 = _make_summary(
            iteration=2,
            approach="アプローチ2",
            result=ExecutionStatus.FAILURE,
            reason="失敗2",
        )
        await history.append(summary2)

        # Both should be in file
        content = history_path.read_text()
        assert "アプローチ1" in content
        assert "アプローチ2" in content

    @pytest.mark.asyncio
    async def test_knowledge_saved_per_iteration(self, temp_task_dir: Path) -> None:
        """Test that knowledge is saved after each iteration."""
        knowledge_path = temp_task_dir / "knowledge.jsonl"
        kb = KnowledgeBase(knowledge_path)

        knowledge = _make_knowledge(
            knowledge_type=KnowledgeType.DISCOVERY,
            content="重要な発見",
        )
        await kb.add(knowledge)

        # File should exist and have content
        assert knowledge_path.exists()
        content = knowledge_path.read_text()
        assert "重要な発見" in content


class TestTaskResume:
    """Tests for task resume functionality."""

    @pytest.fixture
    def temp_task_dir(self, tmp_path: Path) -> Path:
        """Create temporary task directory."""
        task_dir = tmp_path / ".e8" / "tasks" / "resume-task-001"
        task_dir.mkdir(parents=True)
        return task_dir

    @pytest.fixture
    def engine_config(self) -> EngineConfig:
        """Create engine configuration."""
        return EngineConfig(
            task="再開テストタスク",
            criteria=["条件1"],
            max_iterations=10,
        )

    @pytest.mark.asyncio
    async def test_resume_from_existing_history(self, temp_task_dir: Path) -> None:
        """Test that engine can resume from existing history."""
        history_path = temp_task_dir / "history.jsonl"

        # Pre-populate history with 3 iterations
        history = History(history_path)
        for i in range(1, 4):
            summary = _make_summary(
                iteration=i,
                approach=f"既存アプローチ{i}",
                result=ExecutionStatus.FAILURE,
                reason=f"未完了{i}",
            )
            await history.append(summary)

        # Verify last iteration
        last_iter = await history.get_last_iteration()
        assert last_iter == 3

        # Create new history instance (simulating resume)
        history2 = History(history_path)
        last_iter2 = await history2.get_last_iteration()
        assert last_iter2 == 3

    @pytest.mark.asyncio
    async def test_engine_start_iteration_from_history(
        self, temp_task_dir: Path, engine_config: EngineConfig
    ) -> None:
        """Test that engine initializes start iteration from history."""
        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        # Pre-populate history with 5 iterations
        history = History(history_path)
        for i in range(1, 6):
            summary = _make_summary(
                iteration=i,
                approach=f"既存アプローチ{i}",
                result=ExecutionStatus.FAILURE,
                reason=f"未完了{i}",
            )
            await history.append(summary)

        # Create engine with history
        kb = KnowledgeBase(knowledge_path)
        engine = Engine(
            config=engine_config,
            history=history,
            knowledge_base=kb,
        )

        # Initialize from history
        await engine._initialize_from_history()

        # Engine should start from iteration 6
        assert engine._start_iteration == 6


class TestEngineWithPersistence:
    """Tests for engine with persistence integration."""

    @pytest.fixture
    def temp_task_dir(self, tmp_path: Path) -> Path:
        """Create temporary task directory."""
        task_dir = tmp_path / ".e8" / "tasks" / "engine-persist-test"
        task_dir.mkdir(parents=True)
        return task_dir

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストタスク",
            criteria=["条件1"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="実行完了",
            artifacts=["test.py"],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()
        summary = _make_summary(
            iteration=1,
            approach="テストアプローチ",
            result=ExecutionStatus.SUCCESS,
            reason="成功",
            artifacts=["test.py"],
        )
        knowledge = [
            _make_knowledge(
                knowledge_type=KnowledgeType.DISCOVERY,
                content="テストナレッジ",
            )
        ]
        agent.run.return_value = (summary, knowledge)
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        """Create mock judgment agent that completes on first try."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=True,
                    evidence="条件を満たしている",
                    confidence=1.0,
                )
            ],
            overall_reason="タスク完了",
        )
        return agent

    @pytest.mark.asyncio
    async def test_engine_saves_to_history(
        self,
        temp_task_dir: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        """Test that engine saves summaries to history store."""
        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        history = History(history_path)
        kb = KnowledgeBase(knowledge_path)

        config = EngineConfig(
            task="永続化テスト",
            criteria=["条件1"],
            max_iterations=5,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            history=history,
            knowledge_base=kb,
        )

        task_input = TaskInput(
            task="永続化テスト",
            criteria=["条件1"],
            max_iterations=5,
        )

        await engine.run(task_input)

        # History file should have been written
        assert history_path.exists()
        content = history_path.read_text()
        assert "テストアプローチ" in content

    @pytest.mark.asyncio
    async def test_engine_saves_to_knowledge_base(
        self,
        temp_task_dir: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        """Test that engine saves knowledge to knowledge base."""
        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        history = History(history_path)
        kb = KnowledgeBase(knowledge_path)

        config = EngineConfig(
            task="ナレッジテスト",
            criteria=["条件1"],
            max_iterations=5,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            history=history,
            knowledge_base=kb,
        )

        task_input = TaskInput(
            task="ナレッジテスト",
            criteria=["条件1"],
            max_iterations=5,
        )

        await engine.run(task_input)

        # Knowledge file should have been written
        assert knowledge_path.exists()
        content = knowledge_path.read_text()
        assert "テストナレッジ" in content


class TestJudgmentAndFinalResultPersistence:
    """Tests for judgment and final result persistence (FR-032, FR-033)."""

    @pytest.fixture
    def temp_task_dir(self, tmp_path: Path) -> Path:
        """Create temporary task directory."""
        task_dir = tmp_path / ".e8" / "tasks" / "judgment-persist-test"
        task_dir.mkdir(parents=True)
        return task_dir

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        """Create mock intake agent."""
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="判定永続化テスト",
            criteria=["条件1"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        """Create mock execution agent."""
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="実行完了",
            artifacts=["test.py"],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        """Create mock summary agent."""
        agent = AsyncMock()

        def create_summary(
            _result: ExecutionResult, iteration: int
        ) -> tuple[ExecutionSummary, list[Knowledge]]:
            summary = _make_summary(
                iteration=iteration,
                approach=f"アプローチ{iteration}",
                result=ExecutionStatus.SUCCESS,
                reason=f"成功{iteration}",
                artifacts=["test.py"],
            )
            return (summary, [])

        agent.run.side_effect = create_summary
        return agent

    @pytest.fixture
    def mock_judgment_agent_incomplete(self) -> AsyncMock:
        """Create mock judgment agent that never completes."""
        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=False,
                    evidence="まだ未達成",
                    confidence=0.8,
                )
            ],
            overall_reason="タスク未完了",
            suggested_next_action="続行",
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent_complete_on_third(self) -> AsyncMock:
        """Create mock judgment agent that completes on third iteration."""
        agent = AsyncMock()

        call_count = 0

        def judgment_side_effect(_context: JudgmentContext) -> JudgmentResult:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件1",
                            is_met=True,
                            evidence="達成済み",
                            confidence=1.0,
                        )
                    ],
                    overall_reason="タスク完了",
                )
            return JudgmentResult(
                is_complete=False,
                evaluations=[
                    CriteriaEvaluation(
                        criterion="条件1",
                        is_met=False,
                        evidence=f"未達成 (試行{call_count})",
                        confidence=0.7,
                    )
                ],
                overall_reason=f"タスク未完了 (試行{call_count})",
                suggested_next_action="続行",
            )

        agent.run.side_effect = judgment_side_effect
        return agent

    @pytest.mark.asyncio
    async def test_engine_saves_judgment_per_iteration(
        self,
        temp_task_dir: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent_complete_on_third: AsyncMock,
    ) -> None:
        """Test that engine saves JudgmentResult after each iteration."""
        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        history = History(history_path)
        kb = KnowledgeBase(knowledge_path)

        config = EngineConfig(
            task="判定永続化テスト",
            criteria=["条件1"],
            max_iterations=10,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent_complete_on_third,
            history=history,
            knowledge_base=kb,
        )

        task_input = TaskInput(
            task="判定永続化テスト",
            criteria=["条件1"],
            max_iterations=10,
        )

        result = await engine.run(task_input)

        # Should have completed after 3 iterations
        assert result.status.value == "completed"
        assert result.iterations_used == 3

        # History file should contain judgment records
        assert history_path.exists()
        content = history_path.read_text()

        # Should have 3 judgments (one per iteration)
        assert content.count('"type": "judgment"') == 3
        assert "タスク未完了 (試行1)" in content
        assert "タスク未完了 (試行2)" in content
        assert "タスク完了" in content

    @pytest.mark.asyncio
    async def test_engine_saves_final_result_completed(
        self,
        temp_task_dir: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent_complete_on_third: AsyncMock,
    ) -> None:
        """Test that engine saves LoopResult on completion."""
        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        history = History(history_path)
        kb = KnowledgeBase(knowledge_path)

        config = EngineConfig(
            task="最終結果永続化テスト",
            criteria=["条件1"],
            max_iterations=10,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent_complete_on_third,
            history=history,
            knowledge_base=kb,
        )

        task_input = TaskInput(
            task="最終結果永続化テスト",
            criteria=["条件1"],
            max_iterations=10,
        )

        result = await engine.run(task_input)

        assert result.status.value == "completed"

        # History file should contain final_result record
        content = history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "completed"' in content
        assert '"iterations_used": 3' in content

    @pytest.mark.asyncio
    async def test_engine_saves_final_result_max_iterations(
        self,
        temp_task_dir: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent_incomplete: AsyncMock,
    ) -> None:
        """Test that engine saves LoopResult when max iterations reached."""
        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        history = History(history_path)
        kb = KnowledgeBase(knowledge_path)

        config = EngineConfig(
            task="最大イテレーションテスト",
            criteria=["条件1"],
            max_iterations=3,
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent_incomplete,
            history=history,
            knowledge_base=kb,
        )

        task_input = TaskInput(
            task="最大イテレーションテスト",
            criteria=["条件1"],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status.value == "max_iterations"
        assert result.iterations_used == 3

        # History file should contain final_result record
        content = history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "max_iterations"' in content
        assert '"iterations_used": 3' in content

        # Should also have 3 judgment records
        assert content.count('"type": "judgment"') == 3

    @pytest.mark.asyncio
    async def test_engine_saves_final_result_cancelled(
        self,
        temp_task_dir: Path,
        mock_intake_agent: AsyncMock,
    ) -> None:
        """Test that engine saves LoopResult when cancelled."""
        import asyncio

        history_path = temp_task_dir / "history.jsonl"
        knowledge_path = temp_task_dir / "knowledge.jsonl"

        history = History(history_path)
        kb = KnowledgeBase(knowledge_path)

        config = EngineConfig(
            task="キャンセルテスト",
            criteria=["条件1"],
            max_iterations=10,
        )

        # Create slow execution agent to ensure cancel happens during execution
        slow_execution_agent = AsyncMock()

        async def slow_execution(_context: object) -> ExecutionResult:
            await asyncio.sleep(0.1)  # Slow enough for cancel to trigger
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output="実行完了",
                artifacts=["test.py"],
            )

        slow_execution_agent.run.side_effect = slow_execution

        mock_summary_agent = AsyncMock()
        mock_summary_agent.run.return_value = (
            _make_summary(
                iteration=1,
                approach="アプローチ1",
                result=ExecutionStatus.SUCCESS,
                reason="成功1",
            ),
            [],
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=False,
                    evidence="未達成",
                    confidence=0.8,
                )
            ],
            overall_reason="タスク未完了",
            suggested_next_action="続行",
        )

        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=slow_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
            history=history,
            knowledge_base=kb,
        )

        task_input = TaskInput(
            task="キャンセルテスト",
            criteria=["条件1"],
            max_iterations=10,
        )

        # Start the engine in a task and cancel after execution starts
        async def run_and_cancel() -> LoopResult:
            async def cancel_after_delay() -> None:
                # Wait long enough for first iteration to complete,
                # but cancel before second iteration starts execution
                await asyncio.sleep(0.15)
                await engine.cancel()

            cancel_task = asyncio.create_task(cancel_after_delay())
            result = await engine.run(task_input)
            await cancel_task
            return result

        result = await run_and_cancel()

        assert result.status.value == "cancelled"

        # History file should contain final_result record
        content = history_path.read_text()
        assert '"type": "final_result"' in content
        assert '"status": "cancelled"' in content
