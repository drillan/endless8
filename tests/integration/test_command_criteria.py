"""Integration tests for command criteria loop execution (T021).

Tests command-only, mixed (semantic + command), and error scenarios
using real CommandExecutor with mock LLM agents.
"""

from unittest.mock import AsyncMock

import pytest

from endless8.agents import JudgmentContext
from endless8.config import EngineConfig
from endless8.engine import Engine
from endless8.models import (
    CommandCriterion,
    CriteriaEvaluation,
    CriterionType,
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


@pytest.fixture
def mock_intake_agent() -> AsyncMock:
    """Create mock intake agent that always accepts."""
    agent = AsyncMock()
    agent.run.return_value = IntakeResult(
        status=IntakeStatus.ACCEPTED,
        task="テストタスク",
        criteria=["条件"],
    )
    return agent


@pytest.fixture
def mock_execution_agent() -> AsyncMock:
    """Create mock execution agent."""
    agent = AsyncMock()
    agent.run.return_value = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        output="実行完了",
        artifacts=[],
    )
    return agent


@pytest.fixture
def mock_summary_agent() -> AsyncMock:
    """Create mock summary agent."""
    agent = AsyncMock()
    agent.run.return_value = (
        ExecutionSummary(
            iteration=1,
            approach="テスト実行",
            result=ExecutionStatus.SUCCESS,
            reason="完了",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-03-05T10:00:00Z",
        ),
        [],
    )
    return agent


class TestCommandOnlyCriteria:
    """Integration tests for command-only criteria (FR-010: LLM skip)."""

    async def test_command_success_completes_without_llm(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Command exit 0 → met → COMPLETED, judgment agent not called."""
        mock_judgment = AsyncMock()

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment,
        )

        task_input = TaskInput(
            task="テストを実行する",
            criteria=[
                CommandCriterion(
                    type="command", command="true", description="常に成功"
                ),
            ],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.iterations_used == 1
        # FR-010: LLM judgment should be skipped for command-only
        mock_judgment.run.assert_not_called()

        # Verify evaluations
        assert result.final_judgment is not None
        evals = result.final_judgment.evaluations
        assert len(evals) == 1
        assert evals[0].is_met is True
        assert evals[0].evaluation_method == CriterionType.COMMAND
        assert evals[0].confidence == 1.0
        assert evals[0].command_result is not None
        assert evals[0].command_result.exit_code == 0

    async def test_command_failure_not_met(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Command exit 1 → not met → MAX_ITERATIONS."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="テストを修正する",
            criteria=[
                CommandCriterion(
                    type="command", command="false", description="常に失敗"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.iterations_used == 1
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False

        evals = result.final_judgment.evaluations
        assert len(evals) == 1
        assert evals[0].is_met is False
        assert evals[0].evaluation_method == CriterionType.COMMAND
        assert evals[0].command_result is not None
        assert evals[0].command_result.exit_code != 0

    async def test_multiple_commands_all_met(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Multiple command criteria all exit 0 → COMPLETED."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="複数条件テスト",
            criteria=[
                CommandCriterion(type="command", command="true", description="条件1"),
                CommandCriterion(
                    type="command",
                    command="echo hello",
                    description="条件2",
                ),
            ],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.final_judgment is not None
        assert len(result.final_judgment.evaluations) == 2
        assert all(e.is_met for e in result.final_judgment.evaluations)

    async def test_command_output_captured(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Command stdout/stderr are captured in result."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="出力確認",
            criteria=[
                CommandCriterion(
                    type="command",
                    command="echo 'test output'",
                    description="出力あり",
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.final_judgment is not None
        cmd_result = result.final_judgment.evaluations[0].command_result
        assert cmd_result is not None
        assert "test output" in cmd_result.stdout


class TestMixedCriteria:
    """Integration tests for mixed semantic + command criteria."""

    async def test_mixed_all_met_completes(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """All command + semantic criteria met → COMPLETED."""
        mock_judgment = AsyncMock()
        mock_judgment.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="コードが読みやすい",
                    is_met=True,
                    evidence="OK",
                    confidence=0.9,
                ),
            ],
            overall_reason="完了",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment,
        )

        task_input = TaskInput(
            task="認証機能を実装する",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="true", description="テスト通過"
                ),
            ],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED

        # Judgment agent SHOULD be called for mixed criteria
        mock_judgment.run.assert_called_once()

        # Verify command_results passed to judgment context (FR-007)
        call_args = mock_judgment.run.call_args
        context: JudgmentContext = call_args[0][0]
        assert context.command_results is not None
        assert len(context.command_results) == 1
        assert context.command_results[0].is_met is True
        assert context.command_results[0].result.exit_code == 0

        # Verify merged evaluations (command + semantic)
        assert result.final_judgment is not None
        evals = result.final_judgment.evaluations
        assert len(evals) == 2
        methods = {e.evaluation_method for e in evals}
        assert CriterionType.COMMAND in methods
        assert CriterionType.SEMANTIC in methods

    async def test_mixed_command_met_semantic_not_met(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Command met + semantic not met → not complete."""
        mock_judgment = AsyncMock()
        mock_judgment.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="コードが読みやすい",
                    is_met=False,
                    evidence="可読性不足",
                    confidence=0.8,
                ),
            ],
            overall_reason="意味的条件未達成",
            suggested_next_action="リファクタリング",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment,
        )

        task_input = TaskInput(
            task="認証機能を実装する",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="true", description="テスト通過"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False

    async def test_mixed_command_not_met_semantic_met(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Command not met + semantic met → not complete."""
        mock_judgment = AsyncMock()
        mock_judgment.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="コードが読みやすい",
                    is_met=True,
                    evidence="OK",
                    confidence=0.9,
                ),
            ],
            overall_reason="意味的条件達成",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment,
        )

        task_input = TaskInput(
            task="認証機能を実装する",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="false", description="テスト失敗"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False

        # Verify command evaluation is not met in merged results
        cmd_evals = [
            e
            for e in result.final_judgment.evaluations
            if e.evaluation_method == CriterionType.COMMAND
        ]
        assert len(cmd_evals) == 1
        assert cmd_evals[0].is_met is False

    async def test_mixed_semantic_only_criteria_passes(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Semantic-only criteria (quickstart scenario 1) → delegates to LLM."""
        mock_judgment = AsyncMock()
        mock_judgment.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="インストール手順が記載されている",
                    is_met=True,
                    evidence="README に記載あり",
                    confidence=0.95,
                ),
                CriteriaEvaluation(
                    criterion="使用例が含まれている",
                    is_met=True,
                    evidence="Examples セクションあり",
                    confidence=0.9,
                ),
            ],
            overall_reason="完了",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment,
        )

        task_input = TaskInput(
            task="README.md を更新する",
            criteria=[
                "インストール手順が記載されている",
                "使用例が含まれている",
            ],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        mock_judgment.run.assert_called_once()

        # No command_results for semantic-only
        context: JudgmentContext = mock_judgment.run.call_args[0][0]
        assert context.command_results is None


class TestErrorScenarios:
    """Integration tests for command execution error handling (US3)."""

    async def test_oserror_stops_loop(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """OSError (non-existent cwd) → CommandExecutionError → ERROR."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            working_directory="/nonexistent_path_xyz_12345",
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="テスト実行",
            criteria=[
                CommandCriterion(
                    type="command", command="echo test", description="テスト"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.error_message is not None
        assert (
            "CommandExecutionError" in result.error_message
            or "Failed to start" in result.error_message
        )

    async def test_timeout_stops_loop(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Command timeout → CommandExecutionError → ERROR."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            command_timeout=0.1,
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="タイムアウトテスト",
            criteria=[
                CommandCriterion(
                    type="command",
                    command="sleep 10",
                    description="タイムアウトするコマンド",
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.error_message is not None
        assert "timed out" in result.error_message

    async def test_exit_code_127_treated_as_error(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Exit code 127 (command not found) → CommandExecutionError → ERROR."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="存在しないコマンドテスト",
            criteria=[
                CommandCriterion(
                    type="command",
                    command="nonexistent_command_xyz_12345",
                    description="存在しないコマンド",
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.error_message is not None
        assert "exit code 127" in result.error_message

    async def test_exit_code_2_stops_loop(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Exit code 2 (e.g. script not found) → CommandExecutionError → ERROR."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="スクリプト不在テスト",
            criteria=[
                CommandCriterion(
                    type="command",
                    command="python nonexistent_script.py",
                    description="存在しないスクリプト",
                ),
            ],
            max_iterations=3,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.error_message is not None
        assert "exit code" in result.error_message
        # Should stop at iteration 1, not repeat 3 times
        assert result.iterations_used == 1

    async def test_first_error_stops_remaining_commands(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """First command error stops execution of remaining commands (FR-009)."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            command_timeout=0.1,
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="複数コマンドエラーテスト",
            criteria=[
                CommandCriterion(
                    type="command",
                    command="sleep 10",
                    description="タイムアウト（最初）",
                ),
                CommandCriterion(
                    type="command",
                    command="echo should-not-run",
                    description="実行されないはず",
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.ERROR
        assert result.error_message is not None
        assert "timed out" in result.error_message

    async def test_per_command_timeout_override(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Per-command timeout overrides default (quickstart scenario)."""
        config = EngineConfig(
            task="テスト",
            criteria=["条件"],
            command_timeout=0.1,
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
        )

        task_input = TaskInput(
            task="タイムアウト上書き",
            criteria=[
                CommandCriterion(
                    type="command",
                    command="true",
                    description="個別タイムアウト",
                    timeout=30.0,
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        # With generous per-command timeout, `true` should succeed
        assert result.status == LoopStatus.COMPLETED
