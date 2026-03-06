"""Unit tests for the Judgment Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claudecode_model.exceptions import CLIExecutionError

from endless8.agents import CommandCriterionResult, JudgmentContext
from endless8.models import (
    CommandResult,
    CriteriaEvaluation,
    CriterionType,
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    SummaryMetadata,
)


class TestJudgmentAgent:
    """Tests for JudgmentAgent class."""

    @pytest.fixture
    def execution_summary(self) -> ExecutionSummary:
        """Create sample execution summary."""
        return ExecutionSummary(
            iteration=1,
            approach="テストを追加",
            result=ExecutionStatus.SUCCESS,
            reason="テストファイル作成完了",
            artifacts=["tests/test_main.py"],
            metadata=SummaryMetadata(
                tools_used=["Read", "Edit"],
                files_modified=["tests/test_main.py"],
                tokens_used=10000,
            ),
            timestamp="2026-01-23T10:00:00Z",
        )

    @pytest.fixture
    def judgment_context(self, execution_summary: ExecutionSummary) -> JudgmentContext:
        """Create sample judgment context."""
        return JudgmentContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            execution_summary=execution_summary,
        )

    async def test_judgment_agent_returns_result(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that judgment agent returns valid JudgmentResult."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
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
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(judgment_context)

            assert isinstance(result, JudgmentResult)
            assert isinstance(result.is_complete, bool)
            assert len(result.evaluations) == len(judgment_context.criteria)

    async def test_judgment_agent_evaluates_each_criterion(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent evaluates each criterion individually."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="複数の条件を持つタスク",
            criteria=[
                "条件1: テストがパスする",
                "条件2: ドキュメントが更新される",
                "条件3: lintエラーがない",
            ],
            execution_summary=execution_summary,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=False,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件1: テストがパスする",
                            is_met=True,
                            evidence="テストパス",
                            confidence=0.9,
                        ),
                        CriteriaEvaluation(
                            criterion="条件2: ドキュメントが更新される",
                            is_met=False,
                            evidence="ドキュメント未更新",
                            confidence=0.8,
                        ),
                        CriteriaEvaluation(
                            criterion="条件3: lintエラーがない",
                            is_met=True,
                            evidence="lintパス",
                            confidence=0.95,
                        ),
                    ],
                    overall_reason="一部の条件が未達成",
                    suggested_next_action="ドキュメントを更新",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            assert len(result.evaluations) == 3
            assert result.is_complete is False
            assert result.suggested_next_action is not None

    async def test_judgment_agent_includes_confidence(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that each evaluation includes a confidence score."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="pytest --cov で90%以上",
                            is_met=True,
                            evidence="カバレッジ92%",
                            confidence=0.95,
                        )
                    ],
                    overall_reason="完了",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(judgment_context)

            for evaluation in result.evaluations:
                assert 0.0 <= evaluation.confidence <= 1.0

    async def test_judgment_agent_respects_custom_prompt(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent can use custom prompts."""
        from endless8.agents.judgment import JudgmentAgent

        custom_prompt = """
        以下の基準で厳密に評価してください：
        - テスト実行結果を確認
        - カバレッジレポートを検証
        """

        context = JudgmentContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            execution_summary=execution_summary,
            custom_prompt=custom_prompt,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="pytest --cov で90%以上",
                            is_met=True,
                            evidence="カバレッジ92%",
                            confidence=0.98,
                        )
                    ],
                    overall_reason="厳密評価で完了確認",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            # Verify agent was created/called (custom prompt is used internally)
            assert mock_agent.run.called
            assert result.is_complete is True

    async def test_judgment_agent_suggests_next_action_when_incomplete(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent suggests next action when not complete."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="テストカバレッジを90%以上にする",
            criteria=["pytest --cov で90%以上"],
            execution_summary=execution_summary,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=False,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="pytest --cov で90%以上",
                            is_met=False,
                            evidence="現在のカバレッジは85%",
                            confidence=0.9,
                        )
                    ],
                    overall_reason="カバレッジが不足",
                    suggested_next_action="edge case のテストを追加してカバレッジを向上させる",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            assert result.is_complete is False
            assert result.suggested_next_action is not None
            assert len(result.suggested_next_action) > 0

    async def test_judgment_agent_evaluates_research_task(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """Test that judgment agent can evaluate non-coding research tasks."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="プロンプト最適化に関する論文を検索",
            criteria=[
                "3件以上の関連論文を発見",
                "各論文の概要をまとめる",
            ],
            execution_summary=execution_summary,
        )

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="3件以上の関連論文を発見",
                            is_met=True,
                            evidence="5件の論文を発見: Paper1, Paper2, Paper3, Paper4, Paper5",
                            confidence=0.9,
                        ),
                        CriteriaEvaluation(
                            criterion="各論文の概要をまとめる",
                            is_met=True,
                            evidence="全5件の論文について概要を作成",
                            confidence=0.85,
                        ),
                    ],
                    overall_reason="リサーチタスクの完了条件をすべて満たしました",
                )
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent()
            result = await agent.run(context)

            assert result.is_complete is True
            assert len(result.evaluations) == 2
            # Research task should be evaluated correctly
            assert all(e.is_met for e in result.evaluations)


class TestJudgmentAgentMaxTurnsValidation:
    """Tests for JudgmentAgent max_turns validation."""

    def test_max_turns_zero_raises_value_error(self) -> None:
        """Test that max_turns=0 raises ValueError."""
        from endless8.agents.judgment import JudgmentAgent

        with pytest.raises(ValueError, match="max_turns must be >= 1"):
            JudgmentAgent(max_turns=0)

    def test_max_turns_negative_raises_value_error(self) -> None:
        """Test that negative max_turns raises ValueError."""
        from endless8.agents.judgment import JudgmentAgent

        with pytest.raises(ValueError, match="max_turns must be >= 1"):
            JudgmentAgent(max_turns=-5)


class TestJudgmentAgentMaxTurns:
    """Tests for JudgmentAgent max_turns parameter."""

    @pytest.fixture
    def judgment_context(self) -> JudgmentContext:
        """Create sample judgment context."""
        return JudgmentContext(
            task="テスト",
            criteria=["条件"],
            execution_summary=ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
        )

    async def test_max_turns_custom_value(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that custom max_turns is passed to create_agent_model."""
        from endless8.agents.judgment import JudgmentAgent

        with (
            patch("endless8.agents.judgment.Agent") as mock_agent_class,
            patch("endless8.agents.judgment.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件",
                            is_met=True,
                            evidence="証拠",
                            confidence=0.9,
                        )
                    ],
                    overall_reason="完了",
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = JudgmentAgent(max_turns=25)
            await agent.run(judgment_context)

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 25

    async def test_max_turns_default_value(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Test that default max_turns is 10."""
        from endless8.agents.judgment import JudgmentAgent

        with (
            patch("endless8.agents.judgment.Agent") as mock_agent_class,
            patch("endless8.agents.judgment.create_agent_model") as mock_create_model,
        ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = MagicMock(
                output=JudgmentResult(
                    is_complete=True,
                    evaluations=[
                        CriteriaEvaluation(
                            criterion="条件",
                            is_met=True,
                            evidence="証拠",
                            confidence=0.9,
                        )
                    ],
                    overall_reason="完了",
                )
            )
            mock_agent_class.return_value = mock_agent
            mock_create_model.return_value = "mock_model"

            agent = JudgmentAgent()
            await agent.run(judgment_context)

            mock_create_model.assert_called_once()
            call_kwargs = mock_create_model.call_args
            assert call_kwargs.kwargs.get("max_turns") == 10


# --- US2: Mixed semantic and command criteria ---


class TestJudgmentContextCommandResults:
    """Tests for JudgmentContext with command_results field (T014)."""

    @pytest.fixture
    def execution_summary(self) -> ExecutionSummary:
        """Create sample execution summary."""
        return ExecutionSummary(
            iteration=1,
            approach="テスト実行",
            result=ExecutionStatus.SUCCESS,
            reason="完了",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-03-05T10:00:00Z",
        )

    @pytest.fixture
    def sample_command_results(self) -> list[CommandCriterionResult]:
        """Create sample command criterion results."""
        return [
            CommandCriterionResult(
                criterion_index=1,
                description="テストが全パスする",
                command="pytest",
                is_met=True,
                result=CommandResult(
                    exit_code=0,
                    stdout="all tests passed",
                    stderr="",
                    execution_time_sec=2.5,
                ),
            ),
        ]

    def test_judgment_context_accepts_command_results(
        self,
        execution_summary: ExecutionSummary,
        sample_command_results: list[CommandCriterionResult],
    ) -> None:
        """JudgmentContext should accept command_results field."""
        context = JudgmentContext(
            task="テスト",
            criteria=["コードが読みやすい"],
            execution_summary=execution_summary,
            command_results=sample_command_results,
        )
        assert context.command_results is not None
        assert len(context.command_results) == 1
        assert context.command_results[0].is_met is True

    def test_judgment_context_command_results_defaults_to_none(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """JudgmentContext.command_results should default to None."""
        context = JudgmentContext(
            task="テスト",
            criteria=["条件"],
            execution_summary=execution_summary,
        )
        assert context.command_results is None


class TestJudgmentAgentPromptWithCommandResults:
    """Tests for _build_prompt including command results (T015)."""

    @pytest.fixture
    def execution_summary(self) -> ExecutionSummary:
        return ExecutionSummary(
            iteration=1,
            approach="実装",
            result=ExecutionStatus.SUCCESS,
            reason="完了",
            artifacts=[],
            metadata=SummaryMetadata(),
            timestamp="2026-03-05T10:00:00Z",
        )

    @pytest.fixture
    def command_results_met(self) -> list[CommandCriterionResult]:
        return [
            CommandCriterionResult(
                criterion_index=1,
                description="pytest が全パスする",
                command="pytest",
                is_met=True,
                result=CommandResult(
                    exit_code=0,
                    stdout="5 passed",
                    stderr="",
                    execution_time_sec=1.0,
                ),
            ),
        ]

    def test_build_prompt_includes_command_results_section(
        self,
        execution_summary: ExecutionSummary,
        command_results_met: list[CommandCriterionResult],
    ) -> None:
        """_build_prompt should include command results section when command_results is present."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="テスト",
            criteria=["コードが読みやすい"],
            execution_summary=execution_summary,
            command_results=command_results_met,
        )

        agent = JudgmentAgent()
        prompt = agent._build_prompt(context)

        assert "コマンド条件判定結果" in prompt
        assert "pytest" in prompt
        assert "5 passed" in prompt
        assert "met" in prompt.lower() or "合格" in prompt

    def test_build_prompt_excludes_command_results_when_none(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """_build_prompt should not include command results section when None."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="テスト",
            criteria=["コードが読みやすい"],
            execution_summary=execution_summary,
        )

        agent = JudgmentAgent()
        prompt = agent._build_prompt(context)

        assert "コマンド条件判定結果" not in prompt

    def test_build_prompt_excludes_command_results_when_empty(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """_build_prompt should not include command results section when empty list."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="テスト",
            criteria=["コードが読みやすい"],
            execution_summary=execution_summary,
            command_results=[],
        )

        agent = JudgmentAgent()
        prompt = agent._build_prompt(context)

        assert "コマンド条件判定結果" not in prompt

    def test_build_prompt_shows_not_met_command(
        self,
        execution_summary: ExecutionSummary,
    ) -> None:
        """_build_prompt should clearly show not-met command results."""
        from endless8.agents.judgment import JudgmentAgent

        context = JudgmentContext(
            task="テスト",
            criteria=["コードが読みやすい"],
            execution_summary=execution_summary,
            command_results=[
                CommandCriterionResult(
                    criterion_index=0,
                    description="カバレッジ90%以上",
                    command="pytest --cov --cov-fail-under=90",
                    is_met=False,
                    result=CommandResult(
                        exit_code=1,
                        stdout="coverage: 85%",
                        stderr="FAIL Required 90%",
                        execution_time_sec=3.0,
                    ),
                ),
            ],
        )

        agent = JudgmentAgent()
        prompt = agent._build_prompt(context)

        assert "カバレッジ90%以上" in prompt
        assert "coverage: 85%" in prompt or "FAIL Required 90%" in prompt


class TestEngineMixedJudgmentFlow:
    """Tests for Engine mixed judgment flow (T016).

    Tests mock _run_command_criteria to isolate the mixed flow logic.
    """

    @pytest.fixture
    def mock_intake_agent(self) -> AsyncMock:
        agent = AsyncMock()
        agent.run.return_value = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="テスト",
            criteria=["コードが読みやすい"],
        )
        return agent

    @pytest.fixture
    def mock_execution_agent(self) -> AsyncMock:
        agent = AsyncMock()
        agent.run.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="実装完了",
            artifacts=[],
        )
        return agent

    @pytest.fixture
    def mock_summary_agent(self) -> AsyncMock:
        agent = AsyncMock()
        agent.run.return_value = (
            ExecutionSummary(
                iteration=1,
                approach="実装",
                result=ExecutionStatus.SUCCESS,
                reason="完了",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-03-05T10:00:00Z",
            ),
            [],
        )
        return agent

    @pytest.fixture
    def command_eval_met(self) -> CriteriaEvaluation:
        return CriteriaEvaluation(
            criterion="pytest が全パスする",
            is_met=True,
            evidence="exit_code=0, stdout: 5 passed",
            confidence=1.0,
            evaluation_method=CriterionType.COMMAND,
            command_result=CommandResult(
                exit_code=0, stdout="5 passed", stderr="", execution_time_sec=1.0
            ),
        )

    @pytest.fixture
    def command_eval_not_met(self) -> CriteriaEvaluation:
        return CriteriaEvaluation(
            criterion="pytest が全パスする",
            is_met=False,
            evidence="exit_code=1, stderr: 2 failed",
            confidence=1.0,
            evaluation_method=CriterionType.COMMAND,
            command_result=CommandResult(
                exit_code=1, stdout="", stderr="2 failed", execution_time_sec=1.0
            ),
        )

    @pytest.fixture
    def command_criterion_result_met(self) -> CommandCriterionResult:
        return CommandCriterionResult(
            criterion_index=1,
            description="pytest が全パスする",
            command="pytest",
            is_met=True,
            result=CommandResult(
                exit_code=0, stdout="5 passed", stderr="", execution_time_sec=1.0
            ),
        )

    @pytest.fixture
    def command_criterion_result_not_met(self) -> CommandCriterionResult:
        return CommandCriterionResult(
            criterion_index=1,
            description="pytest が全パスする",
            command="pytest",
            is_met=False,
            result=CommandResult(
                exit_code=1, stdout="", stderr="2 failed", execution_time_sec=1.0
            ),
        )

    async def test_mixed_command_met_semantic_not_met_is_incomplete(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        command_eval_met: CriteriaEvaluation,
        command_criterion_result_met: CommandCriterionResult,
    ) -> None:
        """Command met + semantic not met = task incomplete (SC-004)."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import CommandCriterion, LoopStatus, TaskInput

        semantic_eval_not_met = CriteriaEvaluation(
            criterion="コードが読みやすい",
            is_met=False,
            evidence="可読性が不十分",
            confidence=0.8,
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=False,
            evaluations=[semantic_eval_not_met],
            overall_reason="意味的条件が未達成",
            suggested_next_action="コードをリファクタリング",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["コードが読みやすい"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        # Mock _run_command_criteria to return pre-computed results
        engine._run_command_criteria = AsyncMock(  # type: ignore[method-assign]
            return_value=(
                [command_eval_met],
                [command_criterion_result_met],
            )
        )

        task_input = TaskInput(
            task="テスト",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="pytest", description="pytest が全パスする"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False
        # Verify merged evaluations contain both command and semantic
        eval_methods = {e.evaluation_method for e in result.final_judgment.evaluations}
        assert CriterionType.COMMAND in eval_methods
        assert CriterionType.SEMANTIC in eval_methods

    async def test_mixed_semantic_met_command_not_met_is_incomplete(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        command_eval_not_met: CriteriaEvaluation,
        command_criterion_result_not_met: CommandCriterionResult,
    ) -> None:
        """Semantic met + command not met = task incomplete (SC-004)."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import CommandCriterion, LoopStatus, TaskInput

        semantic_eval_met = CriteriaEvaluation(
            criterion="コードが読みやすい",
            is_met=True,
            evidence="コードは読みやすい",
            confidence=0.9,
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[semantic_eval_met],
            overall_reason="意味的条件は達成",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["コードが読みやすい"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        engine._run_command_criteria = AsyncMock(  # type: ignore[method-assign]
            return_value=(
                [command_eval_not_met],
                [command_criterion_result_not_met],
            )
        )

        task_input = TaskInput(
            task="テスト",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="pytest", description="pytest が全パスする"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.MAX_ITERATIONS
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is False

    async def test_mixed_both_met_is_complete(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        command_eval_met: CriteriaEvaluation,
        command_criterion_result_met: CommandCriterionResult,
    ) -> None:
        """Both command and semantic met = task complete."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import CommandCriterion, LoopStatus, TaskInput

        semantic_eval_met = CriteriaEvaluation(
            criterion="コードが読みやすい",
            is_met=True,
            evidence="コードは読みやすい",
            confidence=0.9,
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[semantic_eval_met],
            overall_reason="すべて達成",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["コードが読みやすい"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        engine._run_command_criteria = AsyncMock(  # type: ignore[method-assign]
            return_value=(
                [command_eval_met],
                [command_criterion_result_met],
            )
        )

        task_input = TaskInput(
            task="テスト",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="pytest", description="pytest が全パスする"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.status == LoopStatus.COMPLETED
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is True
        assert len(result.final_judgment.evaluations) == 2

    async def test_command_results_passed_to_judgment_context(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        command_eval_met: CriteriaEvaluation,
        command_criterion_result_met: CommandCriterionResult,
    ) -> None:
        """command_results should be passed to JudgmentContext (FR-007)."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import CommandCriterion, TaskInput

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="コードが読みやすい",
                    is_met=True,
                    evidence="可読性良好",
                    confidence=0.9,
                )
            ],
            overall_reason="完了",
        )

        config = EngineConfig(
            task="テスト",
            criteria=["コードが読みやすい"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        engine._run_command_criteria = AsyncMock(  # type: ignore[method-assign]
            return_value=(
                [command_eval_met],
                [command_criterion_result_met],
            )
        )

        task_input = TaskInput(
            task="テスト",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="pytest", description="pytest が全パスする"
                ),
            ],
            max_iterations=1,
        )

        await engine.run(task_input)

        # Verify JudgmentAgent received command_results in context
        call_args = mock_judgment_agent.run.call_args
        judgment_ctx: JudgmentContext = call_args[0][0]
        assert judgment_ctx.command_results is not None
        assert len(judgment_ctx.command_results) == 1
        assert judgment_ctx.command_results[0].is_met is True

    async def test_command_only_skips_llm_judgment(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
        command_eval_met: CriteriaEvaluation,
        command_criterion_result_met: CommandCriterionResult,
    ) -> None:
        """Command-only criteria should skip LLM judgment (FR-010)."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import CommandCriterion, LoopStatus, TaskInput

        mock_judgment_agent = AsyncMock()

        config = EngineConfig(
            task="テスト",
            criteria=["テスト"],
        )
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )

        engine._run_command_criteria = AsyncMock(  # type: ignore[method-assign]
            return_value=(
                [command_eval_met],
                [command_criterion_result_met],
            )
        )

        task_input = TaskInput(
            task="テスト",
            criteria=[
                CommandCriterion(
                    type="command", command="pytest", description="pytest が全パスする"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        # LLM judgment agent should NOT be called
        mock_judgment_agent.run.assert_not_called()
        assert result.status == LoopStatus.COMPLETED
        assert result.final_judgment is not None
        assert result.final_judgment.is_complete is True

    async def test_merged_evaluations_preserve_order(
        self,
        mock_intake_agent: AsyncMock,
        mock_execution_agent: AsyncMock,
        mock_summary_agent: AsyncMock,
    ) -> None:
        """Merged evaluations should contain both command and semantic evaluations."""
        from endless8.config import EngineConfig
        from endless8.engine import Engine
        from endless8.models import CommandCriterion, TaskInput

        cmd_result = CommandResult(
            exit_code=0, stdout="ok", stderr="", execution_time_sec=0.5
        )
        command_eval = CriteriaEvaluation(
            criterion="pytest パス",
            is_met=True,
            evidence="exit_code=0",
            confidence=1.0,
            evaluation_method=CriterionType.COMMAND,
            command_result=cmd_result,
        )
        command_cr = CommandCriterionResult(
            criterion_index=1,
            description="pytest パス",
            command="pytest",
            is_met=True,
            result=cmd_result,
        )

        semantic_eval = CriteriaEvaluation(
            criterion="コードが読みやすい",
            is_met=True,
            evidence="良好",
            confidence=0.9,
        )

        mock_judgment_agent = AsyncMock()
        mock_judgment_agent.run.return_value = JudgmentResult(
            is_complete=True,
            evaluations=[semantic_eval],
            overall_reason="完了",
        )

        config = EngineConfig(task="テスト", criteria=["テスト"])
        engine = Engine(
            config=config,
            intake_agent=mock_intake_agent,
            execution_agent=mock_execution_agent,
            summary_agent=mock_summary_agent,
            judgment_agent=mock_judgment_agent,
        )
        engine._run_command_criteria = AsyncMock(  # type: ignore[method-assign]
            return_value=([command_eval], [command_cr])
        )

        task_input = TaskInput(
            task="テスト",
            criteria=[
                "コードが読みやすい",
                CommandCriterion(
                    type="command", command="pytest", description="pytest パス"
                ),
            ],
            max_iterations=1,
        )

        result = await engine.run(task_input)

        assert result.final_judgment is not None
        evals = result.final_judgment.evaluations
        assert len(evals) == 2
        methods = [e.evaluation_method for e in evals]
        assert CriterionType.COMMAND in methods
        assert CriterionType.SEMANTIC in methods


class TestJudgmentAgentRetryOnCLIExecutionError:
    """Tests for JudgmentAgent retry logic using CLIExecutionError.recoverable (#36)."""

    @pytest.fixture
    def judgment_context(self) -> JudgmentContext:
        """Create sample judgment context."""
        return JudgmentContext(
            task="テスト",
            criteria=["条件"],
            execution_summary=ExecutionSummary(
                iteration=1,
                approach="アプローチ",
                result=ExecutionStatus.SUCCESS,
                reason="理由",
                artifacts=[],
                metadata=SummaryMetadata(),
                timestamp="2026-01-23T10:00:00Z",
            ),
        )

    @pytest.fixture
    def success_result(self) -> JudgmentResult:
        return JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="証拠",
                    confidence=0.9,
                )
            ],
            overall_reason="完了",
        )

    async def test_retries_on_recoverable_cli_error(
        self,
        judgment_context: JudgmentContext,
        success_result: JudgmentResult,
    ) -> None:
        """CLIExecutionError(recoverable=True) should trigger retry and succeed."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            # First call raises recoverable error, second succeeds
            mock_agent.run.side_effect = [
                CLIExecutionError(
                    "SDK query timed out after 300.0 seconds",
                    error_type="timeout",
                    recoverable=True,
                ),
                MagicMock(output=success_result),
            ]
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent(max_retries=3, retry_delay=0.0)
            result = await agent.run(judgment_context)

            assert result.is_complete is True
            assert mock_agent.run.call_count == 2

    async def test_no_retry_on_non_recoverable_cli_error(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """CLIExecutionError(recoverable=False) should raise immediately without retry."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = CLIExecutionError(
                "Permission denied",
                error_type="permission",
                recoverable=False,
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent(max_retries=3, retry_delay=0.0)

            with pytest.raises(CLIExecutionError, match="Permission denied"):
                await agent.run(judgment_context)

            # Should not retry — only 1 call
            assert mock_agent.run.call_count == 1

    async def test_raises_after_all_retries_exhausted(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """CLIExecutionError(recoverable=True) should raise after max_retries exhausted."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = CLIExecutionError(
                "SDK query timed out after 300.0 seconds",
                error_type="timeout",
                recoverable=True,
            )
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent(max_retries=3, retry_delay=0.0)

            with pytest.raises(CLIExecutionError, match="SDK query timed out"):
                await agent.run(judgment_context)

            assert mock_agent.run.call_count == 3

    async def test_no_retry_on_non_cli_exception(
        self,
        judgment_context: JudgmentContext,
    ) -> None:
        """Non-CLIExecutionError exceptions should raise immediately without retry."""
        from endless8.agents.judgment import JudgmentAgent

        with patch("endless8.agents.judgment.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = ValueError("unexpected error")
            mock_agent_class.return_value = mock_agent

            agent = JudgmentAgent(max_retries=3, retry_delay=0.0)

            with pytest.raises(ValueError, match="unexpected error"):
                await agent.run(judgment_context)

            assert mock_agent.run.call_count == 1
