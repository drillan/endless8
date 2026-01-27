"""Unit tests for the Summary Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from endless8.models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionSummary,
    KnowledgeType,
    SemanticMetadata,
)
from endless8.models.summary import KnowledgeEntry, SummaryLLMOutput


class TestSummaryLLMOutputValidation:
    """Tests for SummaryLLMOutput field validation."""

    def test_reason_rejects_over_4000_chars(self) -> None:
        """Test that SummaryLLMOutput rejects reason exceeding 4000 characters."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SummaryLLMOutput(
                approach="テスト",
                reason="x" * 4001,
                artifacts=[],
                next_action=None,
                knowledge_entries=[],
            )

    def test_reason_accepts_4000_chars(self) -> None:
        """Test that SummaryLLMOutput accepts reason with exactly 4000 characters."""
        output = SummaryLLMOutput(
            approach="テスト",
            reason="x" * 4000,
            artifacts=[],
            next_action=None,
            knowledge_entries=[],
        )
        assert len(output.reason) == 4000


class TestSummaryAgent:
    """Tests for SummaryAgent class."""

    @pytest.fixture
    def execution_result(self) -> ExecutionResult:
        """Create sample execution result."""
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テストを追加しました。カバレッジが向上しました。",
            artifacts=["tests/test_main.py", "src/main.py"],
            semantic_metadata=SemanticMetadata(
                approach="TDD approach",
                strategy_tags=["test-first", "coverage"],
                discoveries=["新しいパターンを発見"],
            ),
        )

    @pytest.fixture
    def llm_output(self) -> SummaryLLMOutput:
        """Create sample LLM output for mocking."""
        return SummaryLLMOutput(
            approach="TDD approach",
            reason="テストを追加し、カバレッジが向上した。",
            artifacts=["tests/test_main.py"],
            next_action=None,
            knowledge_entries=[
                KnowledgeEntry(
                    type="discovery",
                    category="execution",
                    content="新しいパターンを発見",
                    confidence="medium",
                ),
            ],
        )

    @pytest.fixture
    def failure_llm_output(self) -> SummaryLLMOutput:
        """Create failure LLM output for mocking."""
        return SummaryLLMOutput(
            approach="タスク実行失敗",
            reason="テストが失敗しました。",
            artifacts=[],
            next_action="前回の失敗を分析して再試行",
            knowledge_entries=[
                KnowledgeEntry(
                    type="lesson",
                    category="error_handling",
                    content="失敗: テストが失敗しました: assertion error",
                    confidence="low",
                ),
            ],
        )

    def _mock_agent_run(self, llm_output: SummaryLLMOutput) -> AsyncMock:
        """Create a mock for pydantic-ai Agent.run()."""
        mock_result = MagicMock()
        mock_result.output = llm_output
        return AsyncMock(return_value=mock_result)

    async def test_summary_agent_returns_summary_and_knowledge(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent returns summary and extracted knowledge."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(
                task_description="テストカバレッジ向上", model_name="test-model"
            )
            summary, knowledge_list = await agent.run(
                execution_result, iteration=1, criteria=["テスト条件"]
            )

            assert isinstance(summary, ExecutionSummary)
            assert summary.iteration == 1
            assert isinstance(knowledge_list, list)

    async def test_summary_agent_extracts_metadata_from_result(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent extracts metadata from execution result."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                execution_result, iteration=1, criteria=["テスト条件"]
            )

            assert summary.approach == "TDD approach"
            assert "test-first" in summary.metadata.strategy_tags

    async def test_summary_agent_extracts_knowledge_from_discoveries(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent extracts knowledge from discoveries."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            _, knowledge_list = await agent.run(
                execution_result, iteration=1, criteria=["テスト条件"]
            )

            # Knowledge should be extracted from LLM
            assert len(knowledge_list) >= 1
            discovery_knowledge = [
                k for k in knowledge_list if k.type == KnowledgeType.DISCOVERY
            ]
            assert len(discovery_knowledge) >= 1

    async def test_summary_agent_handles_failure_result(
        self,
        failure_llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent handles failure results properly."""
        from endless8.agents.summary import SummaryAgent

        failure_result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="テストが失敗しました: assertion error",
            artifacts=[],
        )

        mock_run = self._mock_agent_run(failure_llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, knowledge_list = await agent.run(
                failure_result, iteration=1, criteria=["テスト条件"]
            )

            assert summary.result == ExecutionStatus.FAILURE
            # Lessons should be extracted from LLM
            lessons = [k for k in knowledge_list if k.type == KnowledgeType.LESSON]
            assert len(lessons) >= 1

    async def test_summary_agent_parses_raw_log(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent can parse raw log content."""
        from endless8.agents.summary import SummaryAgent

        raw_log = """
        {"type":"tool_use","name":"Read","input":{"path":"src/main.py"}}
        {"type":"tool_use","name":"Edit","input":{"path":"tests/test_main.py"}}
        {"type":"tool_result","name":"Bash","content":"Tests passed"}
        """

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                execution_result,
                iteration=1,
                criteria=["テスト条件"],
                raw_log_content=raw_log,
            )

            # Tools should be extracted from raw log
            assert "Read" in summary.metadata.tools_used
            assert "Edit" in summary.metadata.tools_used

    async def test_summary_agent_includes_next_action(
        self,
        failure_llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent includes next action suggestions for failures."""
        from endless8.agents.summary import SummaryAgent

        result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="一部失敗",
            artifacts=["src/main.py"],
        )

        mock_run = self._mock_agent_run(failure_llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(result, iteration=1, criteria=["テスト条件"])

            # Failure should have next action
            assert summary.next is not None
            assert summary.next.suggested_action is not None

    async def test_summary_agent_handles_malformed_json_in_log(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent handles malformed JSON in raw log gracefully."""
        from endless8.agents.summary import SummaryAgent

        # Mix of valid and invalid JSON lines
        raw_log = """
        {"type":"tool_use","name":"Read","input":{"path":"src/main.py"}}
        {invalid json line
        {"type":"tool_use","name":"Edit","input":{"path":"tests/test_main.py"}}
        not even json
        {"usage":{"input_tokens":100,"output_tokens":50}}
        """

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                execution_result,
                iteration=1,
                criteria=["テスト条件"],
                raw_log_content=raw_log,
            )

            # Should still extract valid tools despite malformed lines
            assert "Read" in summary.metadata.tools_used
            assert "Edit" in summary.metadata.tools_used
            # Should still parse token usage
            assert summary.metadata.tokens_used > 0

    async def test_summary_agent_parses_files_from_log(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent extracts modified files from log."""
        from endless8.agents.summary import SummaryAgent

        raw_log = """
        {"type":"tool_use","name":"Write","input":{"file_path":"src/new_file.py","content":"..."}}
        {"type":"tool_use","name":"Edit","input":{"file_path":"src/existing.py","old_string":"...","new_string":"..."}}
        {"type":"tool_use","name":"Read","input":{"file_path":"src/read_only.py"}}
        """

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                execution_result,
                iteration=1,
                criteria=["テスト条件"],
                raw_log_content=raw_log,
            )

            # Only Write and Edit tools should be counted as file modifications
            assert "src/new_file.py" in summary.metadata.files_modified
            assert "src/existing.py" in summary.metadata.files_modified
            assert "src/read_only.py" not in summary.metadata.files_modified


class TestSummaryAgentTimeout:
    """Tests for SummaryAgent timeout propagation."""

    @pytest.fixture
    def execution_result(self) -> ExecutionResult:
        """Create sample execution result."""
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=[],
        )

    @pytest.fixture
    def llm_output(self) -> SummaryLLMOutput:
        """Create sample LLM output."""
        return SummaryLLMOutput(
            approach="アプローチ",
            reason="理由",
            artifacts=[],
            next_action=None,
            knowledge_entries=[],
        )

    def _mock_agent_run(self, llm_output: SummaryLLMOutput) -> AsyncMock:
        """Create a mock for pydantic-ai Agent.run()."""
        mock_result = MagicMock()
        mock_result.output = llm_output
        return AsyncMock(return_value=mock_result)

    async def test_timeout_propagated_to_create_agent_model(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that timeout is passed to create_agent_model()."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with (
            patch("endless8.agents.summary.Agent") as mock_agent_cls,
            patch(
                "endless8.agents.summary.create_agent_model",
                return_value="test-model",
            ) as mock_create_model,
        ):
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(
                task_description="テスト",
                model_name="test-model",
                timeout=120.0,
            )
            await agent.run(execution_result, iteration=1, criteria=["テスト条件"])

            # Verify create_agent_model was called with correct timeout
            mock_create_model.assert_called_once_with(
                "test-model",
                max_turns=10,
                allowed_tools=[],
                timeout=120.0,
            )


class TestSummaryAgentLLM:
    """Tests for LLM-based summary functionality."""

    @pytest.fixture
    def execution_result(self) -> ExecutionResult:
        """Create sample execution result."""
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="テストを追加しました。カバレッジが向上しました。",
            artifacts=["tests/test_main.py", "src/main.py"],
            semantic_metadata=SemanticMetadata(
                approach="TDD approach",
                strategy_tags=["test-first", "coverage"],
                discoveries=["新しいパターンを発見"],
            ),
        )

    @pytest.fixture
    def llm_output(self) -> SummaryLLMOutput:
        """Create sample LLM output."""
        return SummaryLLMOutput(
            approach="TDDアプローチでテストを追加",
            reason="テストファイルを作成し、カバレッジが80%から92%に向上した。",
            artifacts=["tests/test_main.py"],
            next_action=None,
            knowledge_entries=[
                KnowledgeEntry(
                    type="discovery",
                    category="testing",
                    content="pytestのcovプラグインで正確にカバレッジ測定可能",
                    confidence="high",
                ),
            ],
        )

    def _mock_agent_run(self, llm_output: SummaryLLMOutput) -> AsyncMock:
        """Create a mock for pydantic-ai Agent.run()."""
        mock_result = MagicMock()
        mock_result.output = llm_output
        mock_run = AsyncMock(return_value=mock_result)
        return mock_run

    async def test_summary_agent_invokes_llm(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that summary agent invokes pydantic-ai Agent for LLM summarization."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            await agent.run(
                execution_result,
                iteration=1,
                criteria=["pytest --cov で90%以上"],
            )

            # LLM Agent should be called
            mock_run.assert_called_once()

    async def test_summary_agent_includes_criteria_in_prompt(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that criteria is included in the prompt sent to the LLM."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            await agent.run(
                execution_result,
                iteration=1,
                criteria=["pytest --cov で90%以上", "型チェック通過"],
            )

            # Check that the prompt passed to run() contains criteria
            call_args = mock_run.call_args
            prompt = (
                call_args[0][0] if call_args[0] else call_args[1].get("user_prompt", "")
            )
            assert "pytest --cov で90%以上" in prompt
            assert "型チェック通過" in prompt

    async def test_summary_agent_uses_llm_reason(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that LLM reason is used instead of mechanical truncation."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                execution_result,
                iteration=1,
                criteria=["テスト条件"],
            )

            # reason should come from LLM, not from output[:200]
            assert summary.reason == llm_output.reason
            assert summary.reason != execution_result.output[:200]

    async def test_summary_agent_extracts_knowledge_from_llm(
        self,
        execution_result: ExecutionResult,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that LLM knowledge entries are converted to Knowledge objects."""
        from endless8.agents.summary import SummaryAgent

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            _, knowledge_list = await agent.run(
                execution_result,
                iteration=1,
                criteria=["テスト条件"],
            )

            # Knowledge should include LLM-extracted entries
            assert len(knowledge_list) >= 1
            # Check LLM knowledge entry was converted
            llm_knowledge = [
                k
                for k in knowledge_list
                if k.content == "pytestのcovプラグインで正確にカバレッジ測定可能"
            ]
            assert len(llm_knowledge) == 1
            assert llm_knowledge[0].type == KnowledgeType.DISCOVERY
            assert llm_knowledge[0].category == "testing"

    async def test_summary_agent_accepts_model_name(self) -> None:
        """Test that model_name is configurable."""
        from endless8.agents.summary import SummaryAgent

        agent = SummaryAgent(
            task_description="テスト",
            model_name="anthropic:claude-haiku-3-5",
        )
        assert agent._model_name == "anthropic:claude-haiku-3-5"

    async def test_summary_agent_preserves_mechanical_metadata(
        self,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that mechanical metadata extraction from raw logs is preserved."""
        from endless8.agents.summary import SummaryAgent

        execution_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=["src/main.py"],
        )

        raw_log = '{"type":"tool_use","name":"Read","input":{"path":"src/main.py"}}\n{"usage":{"input_tokens":100,"output_tokens":50}}'

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                execution_result,
                iteration=1,
                criteria=["テスト条件"],
                raw_log_content=raw_log,
            )

            # Mechanical metadata should still be extracted from raw log
            assert "Read" in summary.metadata.tools_used
            assert summary.metadata.tokens_used == 150

    async def test_summary_agent_uses_execution_status_not_llm(
        self,
        llm_output: SummaryLLMOutput,
    ) -> None:
        """Test that result status comes from ExecutionResult, not LLM output."""
        from endless8.agents.summary import SummaryAgent

        # ExecutionResult says FAILURE, but LLM says "success"
        failure_result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="テスト失敗",
            artifacts=[],
        )

        mock_run = self._mock_agent_run(llm_output)
        with patch("endless8.agents.summary.Agent") as mock_agent_cls:
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = mock_run
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, _ = await agent.run(
                failure_result,
                iteration=1,
                criteria=["テスト条件"],
            )

            # Status should come from ExecutionResult, NOT from LLM
            assert summary.result == ExecutionStatus.FAILURE


class TestBuildPrompt:
    """Tests for _build_prompt function."""

    def test_build_prompt_includes_iteration(self) -> None:
        """Test that _build_prompt includes iteration number."""
        from endless8.agents.summary import _build_prompt

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=[],
        )
        prompt = _build_prompt(result, iteration=3, criteria=["条件1"])
        assert "イテレーション 3" in prompt

    def test_build_prompt_includes_criteria(self) -> None:
        """Test that _build_prompt includes all criteria."""
        from endless8.agents.summary import _build_prompt

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=["file.py"],
        )
        prompt = _build_prompt(
            result, iteration=1, criteria=["条件A", "条件B", "条件C"]
        )
        assert "条件A" in prompt
        assert "条件B" in prompt
        assert "条件C" in prompt

    def test_build_prompt_includes_execution_output(self) -> None:
        """Test that _build_prompt includes execution output."""
        from endless8.agents.summary import _build_prompt

        result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="エラーが発生しました",
            artifacts=[],
        )
        prompt = _build_prompt(result, iteration=1, criteria=["条件"])
        assert "エラーが発生しました" in prompt
        assert "failure" in prompt

    def test_build_prompt_includes_semantic_metadata(self) -> None:
        """Test that _build_prompt includes semantic metadata when available."""
        from endless8.agents.summary import _build_prompt

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="完了",
            artifacts=[],
            semantic_metadata=SemanticMetadata(
                approach="TDDアプローチ",
                strategy_tags=["test-first"],
                discoveries=["新発見"],
            ),
        )
        prompt = _build_prompt(result, iteration=1, criteria=["条件"])
        assert "TDDアプローチ" in prompt
        assert "test-first" in prompt
        assert "新発見" in prompt


class TestSummaryAgentLLMFallback:
    """Tests for SummaryAgent LLM failure fallback."""

    async def test_llm_failure_returns_fallback_summary(self) -> None:
        """Test that LLM failure returns a fallback summary with empty knowledge."""
        from endless8.agents.summary import SummaryAgent

        execution_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output="実行結果のテキスト" * 100,
            artifacts=["file1.py"],
        )

        with (
            patch("endless8.agents.summary.Agent") as mock_agent_cls,
            patch(
                "endless8.agents.summary.create_agent_model",
                return_value="test-model",
            ),
        ):
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(
                side_effect=RuntimeError("LLM connection failed")
            )
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, knowledge_list = await agent.run(
                execution_result, iteration=2, criteria=["条件"]
            )

            assert isinstance(summary, ExecutionSummary)
            assert summary.iteration == 2
            assert summary.approach == "LLM summarization failed"
            assert summary.result == ExecutionStatus.SUCCESS
            assert len(summary.reason) <= 500
            assert knowledge_list == []

    async def test_llm_failure_preserves_metadata(self) -> None:
        """Test that LLM failure still preserves mechanical metadata."""
        from endless8.agents.summary import SummaryAgent

        execution_result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            output="テスト失敗",
            artifacts=["src/main.py"],
            semantic_metadata=SemanticMetadata(
                approach="アプローチ",
                strategy_tags=["tag1"],
                discoveries=[],
            ),
        )

        raw_log = '{"type":"tool_use","name":"Read","input":{"path":"src/main.py"}}\n{"usage":{"input_tokens":50,"output_tokens":25}}'

        with (
            patch("endless8.agents.summary.Agent") as mock_agent_cls,
            patch(
                "endless8.agents.summary.create_agent_model",
                return_value="test-model",
            ),
        ):
            mock_agent_instance = MagicMock()
            mock_agent_instance.run = AsyncMock(side_effect=Exception("timeout"))
            mock_agent_cls.return_value = mock_agent_instance

            agent = SummaryAgent(task_description="テスト", model_name="test-model")
            summary, knowledge_list = await agent.run(
                execution_result,
                iteration=1,
                criteria=["条件"],
                raw_log_content=raw_log,
            )

            # Metadata should still be extracted from raw log
            assert "Read" in summary.metadata.tools_used
            assert summary.metadata.tokens_used == 75
            assert summary.metadata.strategy_tags == ["tag1"]
            assert knowledge_list == []


class TestKnowledgeEntryLiteralValidation:
    """Tests for Literal type validation on KnowledgeEntry."""

    def test_valid_knowledge_type(self) -> None:
        """Test that valid knowledge types are accepted."""
        for valid_type in ("discovery", "lesson", "pattern", "constraint", "codebase"):
            entry = KnowledgeEntry(
                type=valid_type,
                category="test",
                content="テスト内容",
            )
            assert entry.type == valid_type

    def test_invalid_knowledge_type_rejected(self) -> None:
        """Test that invalid knowledge type raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            KnowledgeEntry(
                type="invalid_type",
                category="test",
                content="テスト内容",
            )

    def test_valid_confidence_values(self) -> None:
        """Test that valid confidence values are accepted."""
        for valid_conf in ("high", "medium", "low"):
            entry = KnowledgeEntry(
                type="discovery",
                category="test",
                content="テスト内容",
                confidence=valid_conf,
            )
            assert entry.confidence == valid_conf

    def test_invalid_confidence_rejected(self) -> None:
        """Test that invalid confidence value raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            KnowledgeEntry(
                type="discovery",
                category="test",
                content="テスト内容",
                confidence="very_high",
            )
