"""Tests for TaskManager class."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from endless8.config import EngineConfig
from endless8.models.state import TaskPhase
from endless8.task_manager import TaskManager, TaskStatus


class TestTaskManagerCreate:
    """Tests for TaskManager.create()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    async def test_create_returns_task_id(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    async def test_create_makes_task_directory(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        task_dir = project_dir / ".e8" / "tasks" / task_id
        assert task_dir.exists()

    async def test_create_initializes_state(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        status = await tm.status(task_id)
        assert status.phase == TaskPhase.CREATED
        assert status.current_iteration == 0
        assert status.is_complete is False


class TestTaskManagerStatus:
    """Tests for TaskManager.status()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    async def test_status_returns_task_status(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        task_id = await tm.create()
        status = await tm.status(task_id)
        assert isinstance(status, TaskStatus)
        assert status.task_id == task_id
        assert status.phase == TaskPhase.CREATED
        assert status.max_iterations == 5

    async def test_status_unknown_task_raises(
        self, project_dir: Path, config: EngineConfig
    ) -> None:
        tm = TaskManager(project_dir, config)
        with pytest.raises(FileNotFoundError):
            await tm.status("nonexistent-task")


class TestTaskManagerAdvance:
    """Tests for TaskManager.advance()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        from endless8.models import IntakeResult, IntakeStatus

        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストを書く",
            criteria=["テストが全パス"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        from endless8.models import ExecutionResult, ExecutionStatus

        agent = AsyncMock()
        agent.raw_log_collector = None
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テスト追加完了",
            artifacts=["tests/test_main.py"],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        from endless8.models import ExecutionStatus, ExecutionSummary, SummaryMetadata

        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="テスト追加",
                result=ExecutionStatus.SUCCESS,
                reason="完了",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-03-23T10:00:00Z",
            ),
            [],
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        from endless8.models import CriteriaEvaluation, JudgmentResult

        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="テストが全パス",
                    is_met=True,
                    evidence="全テスト通過",
                    confidence=0.95,
                )
            ],
            overall_reason="完了",
        )
        return agent

    async def test_advance_from_created_to_intake(
        self,
        project_dir: Path,
        config: EngineConfig,
        mock_intake_agent: AsyncMock,
    ) -> None:
        tm = TaskManager(project_dir, config)
        tm.set_agents(intake_agent=mock_intake_agent)
        task_id = await tm.create()
        result = await tm.advance(task_id)
        assert result.phase == TaskPhase.EXECUTING
        mock_intake_agent.run.assert_called_once()

    async def test_advance_through_full_cycle(
        self,
        project_dir: Path,
        config: EngineConfig,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        tm = TaskManager(project_dir, config)
        tm.set_agents(
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )
        task_id = await tm.create()

        # CREATED -> INTAKE -> EXECUTING
        await tm.advance(task_id)
        # EXECUTING -> SUMMARIZING -> JUDGING -> COMPLETED
        await tm.advance(task_id)

        status = await tm.status(task_id)
        assert status.phase == TaskPhase.COMPLETED
        assert status.is_complete

    async def test_advance_on_terminal_raises(
        self,
        project_dir: Path,
        config: EngineConfig,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        from endless8.state import InvalidTransitionError

        tm = TaskManager(project_dir, config)
        tm.set_agents(
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )
        task_id = await tm.create()
        await tm.advance(task_id)  # intake
        await tm.advance(task_id)  # execute -> complete

        with pytest.raises(InvalidTransitionError):
            await tm.advance(task_id)


class TestTaskManagerRun:
    """Tests for TaskManager.run()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        from endless8.models import IntakeResult, IntakeStatus

        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テストを書く",
            criteria=["テストが全パス"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        from endless8.models import ExecutionResult, ExecutionStatus

        agent = AsyncMock()
        agent.raw_log_collector = None
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テスト追加完了",
            artifacts=[],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        from endless8.models import ExecutionStatus, ExecutionSummary, SummaryMetadata

        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="テスト追加",
                result=ExecutionStatus.SUCCESS,
                reason="完了",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-03-23T10:00:00Z",
            ),
            [],
        )
        return agent

    @pytest.fixture
    def mock_judgment_agent(self) -> AsyncMock:
        from endless8.models import CriteriaEvaluation, JudgmentResult

        agent = AsyncMock()
        agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="テストが全パス",
                    is_met=True,
                    evidence="全テスト通過",
                    confidence=0.95,
                )
            ],
            overall_reason="完了",
        )
        return agent

    async def test_run_loops_until_complete(
        self,
        project_dir: Path,
        config: EngineConfig,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        mock_judgment_agent: AsyncMock,
    ) -> None:
        from endless8.models import LoopStatus

        tm = TaskManager(project_dir, config)
        tm.set_agents(
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )
        task_id = await tm.create()
        result = await tm.run(task_id)
        assert result.status == LoopStatus.COMPLETED

    async def test_run_stops_at_max_iterations(
        self,
        project_dir: Path,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        from endless8.models import CriteriaEvaluation, JudgmentResult, LoopStatus

        config = EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=2,
        )
        mock_judgment_not_complete = AsyncMock()
        mock_judgment_not_complete.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="テストが全パス",
                    is_met=False,
                    evidence="まだ不足",
                    confidence=0.8,
                )
            ],
            overall_reason="未完了",
            suggested_next_action="テスト追加",
        )

        tm = TaskManager(project_dir, config)
        tm.set_agents(
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_not_complete,
        )
        task_id = await tm.create()
        result = await tm.run(task_id)
        assert result.status == LoopStatus.MAX_ITERATIONS


class TestTaskManagerInjectResult:
    """Tests for TaskManager.inject_result()."""

    @pytest.fixture
    def project_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "project"

    @pytest.fixture
    def config(self) -> EngineConfig:
        return EngineConfig(
            task="テストを書く",
            criteria=["テストが全パス"],
            max_iterations=5,
        )

    async def test_inject_result_writes_file(
        self, project_dir: Path, config: EngineConfig, tmp_path: Path
    ) -> None:
        import json

        tm = TaskManager(project_dir, config)
        task_id = await tm.create()

        result_file = tmp_path / "result.json"
        result_data = {
            "criteria_results": [
                {
                    "criterion_index": 0,
                    "command": "pytest",
                    "is_met": True,
                    "exit_code": 0,
                    "stdout": "all passed",
                    "stderr": "",
                }
            ]
        }
        result_file.write_text(json.dumps(result_data))

        await tm.inject_result(task_id, result_file)

        injected = project_dir / ".e8" / "tasks" / task_id / "injected_result.json"
        assert injected.exists()
        loaded = json.loads(injected.read_text())
        assert loaded["criteria_results"][0]["is_met"] is True

    async def test_inject_result_nonexistent_task_raises(
        self, project_dir: Path, config: EngineConfig, tmp_path: Path
    ) -> None:
        tm = TaskManager(project_dir, config)
        result_file = tmp_path / "result.json"
        result_file.write_text("{}")
        with pytest.raises(FileNotFoundError):
            await tm.inject_result("nonexistent", result_file)
