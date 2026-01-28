"""Unit tests for CLI module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from endless8.cli.main import _format_tool_call, app, version_callback
from endless8.models import (
    CriteriaEvaluation,
    JudgmentResult,
    LoopResult,
    LoopStatus,
)


class TestVersionCallback:
    """Tests for version_callback function."""

    def test_version_callback_shows_version(self) -> None:
        """Test that version_callback shows version and exits."""
        import typer

        with pytest.raises(typer.Exit):
            version_callback(value=True)

    def test_version_callback_no_op_when_false(self) -> None:
        """Test that version_callback does nothing when value is False."""
        # Should not raise - function returns None implicitly
        version_callback(value=False)
        # If we reach here, no exception was raised


class TestMainCallback:
    """Tests for main callback function."""

    def test_main_help_shows_description(self, runner: CliRunner) -> None:
        """Test that main --help shows description."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "endless8" in result.stdout

    def test_version_option(self, runner: CliRunner) -> None:
        """Test that --version works."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "endless8" in result.stdout
        assert "version" in result.stdout


class TestRunCommand:
    """Tests for run command."""

    def test_run_requires_task_or_config(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that run requires --task or --config."""
        result = runner.invoke(
            app,
            ["run", "--project", str(temp_dir)],
        )
        assert result.exit_code == 1
        assert "タスク" in result.output or "task" in result.output.lower()

    def test_run_requires_criteria_when_no_config(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that run requires --criteria when no config file."""
        result = runner.invoke(
            app,
            ["run", "--task", "Test task", "--project", str(temp_dir)],
        )
        assert result.exit_code == 1
        assert "完了条件" in result.output or "criteria" in result.output.lower()

    def _create_completed_result(self, iterations: int = 1) -> LoopResult:
        """Create a completed LoopResult with proper final_judgment."""
        judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="条件を満たしている",
                    confidence=1.0,
                )
            ],
            overall_reason="タスク完了",
        )
        return LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=iterations,
            final_judgment=judgment,
        )

    def test_run_shows_task_info(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows task information before execution."""
        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "テストタスク",
                    "--criteria",
                    "条件1",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "タスク: テストタスク" in result.output
            assert "条件1" in result.output

    def test_run_creates_e8_directory(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run creates .e8 directory."""
        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            e8_dir = temp_dir / ".e8"
            assert e8_dir.exists()

    def test_run_default_max_iterations(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that run uses default max_iterations of 10."""
        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "最大イテレーション: 10" in result.output

    def test_run_completed_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows completed status."""
        mock_result = self._create_completed_result(iterations=3)

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "タスク完了" in result.output
            assert "使用イテレーション: 3" in result.output

    def test_run_max_iterations_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows max iterations status."""
        mock_result = LoopResult(
            status=LoopStatus.MAX_ITERATIONS,
            iterations_used=10,
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "最大イテレーション" in result.output
            assert "10" in result.output

    def test_run_error_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows error status."""
        mock_result = LoopResult(
            status=LoopStatus.ERROR,
            iterations_used=1,
            error_message="Test error",
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "エラー" in result.output
            assert "Test error" in result.output


class TestListCommand:
    """Tests for list command."""

    def test_list_no_tasks(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test list with no tasks."""
        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "タスクが見つかりません" in result.output

    def test_list_with_tasks(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test list with tasks."""
        import json

        # Create task directory structure
        tasks_dir = temp_dir / ".e8" / "tasks"
        task_dir = tasks_dir / "20240101-120000-abc123"
        task_dir.mkdir(parents=True)

        # Create history file
        history_file = task_dir / "history.jsonl"
        history_data = {"result": "success", "iteration": 1}
        history_file.write_text(json.dumps(history_data) + "\n")

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "20240101-120000-abc123" in result.output
        assert "合計: 1 タスク" in result.output

    def test_list_header_format(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that list shows proper header."""
        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert "endless8 タスク一覧" in result.output


class TestStatusCommand:
    """Tests for status command."""

    def test_status_no_e8_dir(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test status with no .e8 directory."""
        result = runner.invoke(app, ["status", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "見つかりません" in result.output

    def test_status_with_e8_dir(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test status with .e8 directory."""
        e8_dir = temp_dir / ".e8"
        e8_dir.mkdir()

        result = runner.invoke(app, ["status", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "タスク数" in result.output

    def test_status_shows_task_count(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that status shows task count."""
        e8_dir = temp_dir / ".e8"
        tasks_dir = e8_dir / "tasks"
        (tasks_dir / "task1").mkdir(parents=True)
        (tasks_dir / "task2").mkdir(parents=True)

        result = runner.invoke(app, ["status", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "タスク数: 2" in result.output

    def test_status_shows_knowledge_count(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that status shows knowledge entry count."""
        e8_dir = temp_dir / ".e8"
        e8_dir.mkdir()

        # Create knowledge file with entries
        knowledge_file = e8_dir / "knowledge.jsonl"
        knowledge_file.write_text('{"type": "fact"}\n{"type": "constraint"}\n')

        result = runner.invoke(app, ["status", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "ナレッジエントリ: 2" in result.output


class TestResumeOption:
    """Tests for --resume option."""

    def test_resume_nonexistent_task(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that resume with nonexistent task_id returns error."""
        # Create .e8/tasks directory (empty)
        tasks_dir = temp_dir / ".e8" / "tasks"
        tasks_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "run",
                "--task",
                "タスク",
                "--criteria",
                "条件",
                "--project",
                str(temp_dir),
                "--resume",
                "nonexistent-task-id",
            ],
        )

        assert result.exit_code == 1
        assert "見つかりません" in result.output or "nonexistent" in result.output

    def test_resume_existing_task(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that resume with existing task_id works."""
        import json

        # Create existing task with history
        task_id = "20240101-120000"
        task_dir = temp_dir / ".e8" / "tasks" / task_id
        task_dir.mkdir(parents=True)

        # Create history file
        history_file = task_dir / "history.jsonl"
        history_data = {
            "type": "summary",
            "iteration": 1,
            "approach": "テスト",
            "result": "success",
            "reason": "理由",
            "artifacts": [],
            "metadata": {
                "tools_used": [],
                "files_modified": [],
                "tokens_used": 1000,
                "strategy_tags": [],
            },
            "timestamp": "2026-01-23T10:00:00Z",
        }
        history_file.write_text(json.dumps(history_data) + "\n")

        # Create knowledge file
        knowledge_file = task_dir / "knowledge.jsonl"
        knowledge_file.write_text("")

        mock_result = LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=2,
            final_judgment=JudgmentResult(
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
            ),
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                    "--resume",
                    task_id,
                ],
            )

            assert result.exit_code == 0
            assert "再開" in result.output or task_id in result.output


class TestListStatus:
    """Tests for list command status display."""

    def test_list_completed_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that completed task shows appropriate status."""
        import json

        # Create task directory
        tasks_dir = temp_dir / ".e8" / "tasks"
        task_dir = tasks_dir / "20240101-120000"
        task_dir.mkdir(parents=True)

        # Create history file with final_result showing completed
        history_file = task_dir / "history.jsonl"
        records = [
            {"type": "summary", "result": "success", "iteration": 1},
            {"type": "final_result", "status": "completed", "iterations_used": 1},
        ]
        history_file.write_text("\n".join(json.dumps(r) for r in records) + "\n")

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "20240101-120000" in result.output

    def test_list_with_corrupted_history(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that corrupted history does not crash list command."""
        import json

        # Create task directories
        tasks_dir = temp_dir / ".e8" / "tasks"

        # Task with corrupted history
        corrupted_task = tasks_dir / "20240101-100000"
        corrupted_task.mkdir(parents=True)
        corrupted_history = corrupted_task / "history.jsonl"
        corrupted_history.write_text("not valid json{{\n")

        # Task with valid history
        valid_task = tasks_dir / "20240101-110000"
        valid_task.mkdir(parents=True)
        valid_history = valid_task / "history.jsonl"
        valid_data = {"type": "summary", "result": "success", "iteration": 1}
        valid_history.write_text(json.dumps(valid_data) + "\n")

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])

        # Should not crash
        assert result.exit_code == 0
        # Both tasks should be listed
        assert "20240101-100000" in result.output
        assert "20240101-110000" in result.output
        # Total should be 2
        assert "合計: 2 タスク" in result.output


class TestVerboseOption:
    """Tests for --verbose option."""

    def _create_completed_result(self, iterations: int = 1) -> LoopResult:
        """Create a completed LoopResult with proper final_judgment."""
        judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="条件を満たしている",
                    confidence=1.0,
                )
            ],
            overall_reason="タスク完了",
        )
        return LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=iterations,
            final_judgment=judgment,
        )

    def test_verbose_option_accepted(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that --verbose option is accepted."""
        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                    "--verbose",
                ],
            )

            assert result.exit_code == 0

    def test_verbose_short_option(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that -V short option works."""
        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                    "-V",
                ],
            )

            assert result.exit_code == 0

    def test_verbose_passes_callback_to_execution_agent(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that verbose mode passes message_callback to ExecutionAgent."""
        mock_result = self._create_completed_result()

        with (
            patch("endless8.cli.main.Engine") as mock_engine_class,
            patch("endless8.cli.main.ExecutionAgent") as mock_exec_agent_class,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                    "--verbose",
                ],
            )

            assert result.exit_code == 0
            # Verify ExecutionAgent was called with message_callback
            mock_exec_agent_class.assert_called_once()
            call_kwargs = mock_exec_agent_class.call_args
            assert "message_callback" in call_kwargs.kwargs
            assert call_kwargs.kwargs["message_callback"] is not None

    def test_non_verbose_no_callback(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that non-verbose mode does not pass message_callback."""
        mock_result = self._create_completed_result()

        with (
            patch("endless8.cli.main.Engine") as mock_engine_class,
            patch("endless8.cli.main.ExecutionAgent") as mock_exec_agent_class,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert result.exit_code == 0
            # Verify ExecutionAgent was called without message_callback or with None
            mock_exec_agent_class.assert_called_once()
            call_kwargs = mock_exec_agent_class.call_args
            assert call_kwargs.kwargs.get("message_callback") is None


class TestFormatToolCall:
    """Tests for _format_tool_call helper function."""

    def test_format_write_with_file_path(self) -> None:
        """Test formatting Write tool with file_path."""
        result = _format_tool_call("Write", {"file_path": "/path/to/file.txt"})
        assert result == "Write: /path/to/file.txt"

    def test_format_read_with_file_path(self) -> None:
        """Test formatting Read tool with file_path."""
        result = _format_tool_call("Read", {"file_path": "src/main.py"})
        assert result == "Read: src/main.py"

    def test_format_edit_with_file_path(self) -> None:
        """Test formatting Edit tool with file_path."""
        result = _format_tool_call("Edit", {"file_path": "config.yaml"})
        assert result == "Edit: config.yaml"

    def test_format_bash_with_command(self) -> None:
        """Test formatting Bash tool with command."""
        result = _format_tool_call("Bash", {"command": "ls -la"})
        assert result == "Bash: ls -la"

    def test_format_bash_with_long_command(self) -> None:
        """Test formatting Bash tool with long command truncation."""
        long_cmd = "a" * 50
        result = _format_tool_call("Bash", {"command": long_cmd})
        assert result == f"Bash: {'a' * 40}..."
        assert len(result) < len(f"Bash: {long_cmd}")

    def test_format_glob_with_pattern(self) -> None:
        """Test formatting Glob tool with pattern."""
        result = _format_tool_call("Glob", {"pattern": "**/*.py"})
        assert result == "Glob: **/*.py"

    def test_format_grep_with_pattern(self) -> None:
        """Test formatting Grep tool with pattern."""
        result = _format_tool_call("Grep", {"pattern": "TODO:"})
        assert result == "Grep: TODO:"

    def test_format_unknown_tool(self) -> None:
        """Test formatting unknown tool returns just name."""
        result = _format_tool_call("CustomTool", {"some_param": "value"})
        assert result == "CustomTool"

    def test_format_tool_without_expected_param(self) -> None:
        """Test formatting tool without expected parameter returns just name."""
        result = _format_tool_call("Write", {"content": "some content"})
        assert result == "Write"

    def test_format_tool_with_empty_param(self) -> None:
        """Test formatting tool with empty parameter returns just name."""
        result = _format_tool_call("Read", {"file_path": ""})
        assert result == "Read"


class TestConfigFileOverride:
    """Tests for config file option override."""

    def _create_completed_result(self, iterations: int = 1) -> LoopResult:
        """Create a completed LoopResult with proper final_judgment."""
        judgment = JudgmentResult(
            is_complete=True,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=True,
                    evidence="条件を満たしている",
                    confidence=1.0,
                )
            ],
            overall_reason="タスク完了",
        )
        return LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=iterations,
            final_judgment=judgment,
        )

    def test_cli_task_overrides_config_task(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that CLI --task option overrides config file task."""
        import yaml

        # Create config file
        config_file = temp_dir / "config.yaml"
        config_data = {
            "task": "Config task",
            "criteria": ["Config criterion"],
            "max_iterations": 5,
        }
        config_file.write_text(yaml.dump(config_data))

        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--config",
                    str(config_file),
                    "--task",
                    "CLI task",
                    "--project",
                    str(temp_dir),
                ],
            )

            # CLI task should override
            assert "タスク: CLI task" in result.output
            assert "Config task" not in result.output

    def test_cli_criteria_overrides_config_criteria(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that CLI --criteria option overrides config file criteria."""
        import yaml

        # Create config file
        config_file = temp_dir / "config.yaml"
        config_data = {
            "task": "Test task",
            "criteria": ["Config criterion 1", "Config criterion 2"],
            "max_iterations": 5,
        }
        config_file.write_text(yaml.dump(config_data))

        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--config",
                    str(config_file),
                    "--criteria",
                    "CLI criterion",
                    "--project",
                    str(temp_dir),
                ],
            )

            # CLI criteria should override
            assert "CLI criterion" in result.output
            assert "Config criterion" not in result.output

    def test_cli_max_iterations_overrides_config_max_iterations(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that CLI --max-iterations overrides config file."""
        import yaml

        # Create config file
        config_file = temp_dir / "config.yaml"
        config_data = {
            "task": "Test task",
            "criteria": ["Test criterion"],
            "max_iterations": 5,
        }
        config_file.write_text(yaml.dump(config_data))

        mock_result = self._create_completed_result()

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--config",
                    str(config_file),
                    "--max-iterations",
                    "15",
                    "--project",
                    str(temp_dir),
                ],
            )

            # CLI max_iterations should override
            assert "最大イテレーション: 15" in result.output
            assert "最大イテレーション: 5" not in result.output

    def test_config_file_not_found_error(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test error message when config file is not found."""
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(temp_dir / "nonexistent.yaml"),
                "--project",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 1
        assert "見つかりません" in result.output or "not" in result.output.lower()

    def test_config_file_invalid_error(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test error message when config file is invalid."""
        import yaml

        # Create config file with missing required fields
        config_file = temp_dir / "config.yaml"
        # This is valid YAML but invalid for our schema (missing task/criteria)
        config_file.write_text(yaml.dump({"max_iterations": 5}))

        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "--project",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 1
        assert "不正" in result.output or "エラー" in result.output


class TestProgressCallbackEvents:
    """Tests for progress_callback event handling."""

    def test_run_cancelled_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows cancelled status."""
        mock_result = LoopResult(
            status=LoopStatus.CANCELLED,
            iterations_used=1,
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "キャンセル" in result.output

    def test_run_tool_mismatch_error(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows tool mismatch error details."""
        from endless8.models import IntakeResult, IntakeStatus

        intake_result = IntakeResult(
            status=IntakeStatus.ACCEPTED,
            task="Test task",
            criteria=["Criterion 1"],
            suggested_tools=["Bash", "Write", "Read"],
        )

        mock_result = LoopResult(
            status=LoopStatus.ERROR,
            iterations_used=1,
            error_message="Tool mismatch detected",
            intake_result=intake_result,
        )

        with (
            patch("endless8.cli.main.Engine") as mock_engine_class,
            patch("endless8.cli.main.load_config") as mock_load_config,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            # Create minimal config
            from endless8.config import ClaudeOptions, EngineConfig

            mock_config = EngineConfig(
                task="Test task",
                criteria=["Criterion 1"],
                max_iterations=10,
                claude_options=ClaudeOptions(allowed_tools=["Bash"]),
            )

            import yaml

            config_file = temp_dir / "config.yaml"
            config_file.write_text(yaml.dump({"task": "t", "criteria": ["c"]}))

            # Mock load_config to return our config
            mock_load_config.return_value = mock_config

            result = runner.invoke(
                app,
                [
                    "run",
                    "--config",
                    str(config_file),
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "ツール設定エラー" in result.output
            assert "必要なツール" in result.output
            assert "不足" in result.output

    def test_run_with_final_judgment_shows_evaluations(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that run shows evaluation details when final_judgment exists."""
        judgment = JudgmentResult(
            is_complete=False,  # Changed to False since not all criteria are met
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件1",
                    is_met=True,
                    evidence="達成されました",
                    confidence=0.95,
                ),
                CriteriaEvaluation(
                    criterion="条件2",
                    is_met=False,
                    evidence="未達成です",
                    confidence=0.80,
                ),
            ],
            overall_reason="一部完了",
        )

        mock_result = LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=2,
            final_judgment=judgment,
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "条件1" in result.output
            assert "条件2" in result.output
            assert "達成されました" in result.output
            assert "未達成です" in result.output
            assert "95%" in result.output or "0.95" in result.output
            assert "80%" in result.output or "0.80" in result.output

    def test_run_incomplete_shows_suggested_next_action(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that incomplete task shows suggested next action."""
        judgment = JudgmentResult(
            is_complete=False,
            evaluations=[
                CriteriaEvaluation(
                    criterion="条件",
                    is_met=False,
                    evidence="未達成",
                    confidence=0.90,
                )
            ],
            overall_reason="未完了",
            suggested_next_action="次のステップを実行してください",
        )

        mock_result = LoopResult(
            status=LoopStatus.MAX_ITERATIONS,
            iterations_used=10,
            final_judgment=judgment,
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "推奨アクション" in result.output
            assert "次のステップを実行してください" in result.output

    def test_run_shows_history_path(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test that run shows history path."""
        judgment = JudgmentResult(
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

        history_path = temp_dir / ".e8" / "tasks" / "20240101-120000" / "history.jsonl"
        mock_result = LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=1,
            final_judgment=judgment,
            history_path=str(history_path),  # Convert Path to string
        )

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--project",
                    str(temp_dir),
                ],
            )

            assert "履歴:" in result.output
            assert "history.jsonl" in result.output


class TestListCommandStatusParsing:
    """Tests for list command status parsing."""

    def test_list_with_no_history_file(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test list with task directory but no history file."""
        tasks_dir = temp_dir / ".e8" / "tasks"
        task_dir = tasks_dir / "20240101-120000"
        task_dir.mkdir(parents=True)

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "20240101-120000" in result.output
        assert "unknown" in result.output

    def test_list_with_failure_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test list with failure status."""
        import json

        tasks_dir = temp_dir / ".e8" / "tasks"
        task_dir = tasks_dir / "20240101-120000"
        task_dir.mkdir(parents=True)

        history_file = task_dir / "history.jsonl"
        history_data = {"result": "failure", "iteration": 1}
        history_file.write_text(json.dumps(history_data) + "\n")

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "20240101-120000" in result.output
        assert "failed" in result.output

    def test_list_with_error_status(self, runner: CliRunner, temp_dir: Path) -> None:
        """Test list with error status."""
        import json

        tasks_dir = temp_dir / ".e8" / "tasks"
        task_dir = tasks_dir / "20240101-120000"
        task_dir.mkdir(parents=True)

        history_file = task_dir / "history.jsonl"
        history_data = {"result": "error", "iteration": 1}
        history_file.write_text(json.dumps(history_data) + "\n")

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "20240101-120000" in result.output
        assert "error" in result.output

    def test_list_shows_last_modified_time(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that list shows last modified time."""
        import json

        tasks_dir = temp_dir / ".e8" / "tasks"
        task_dir = tasks_dir / "20240101-120000"
        task_dir.mkdir(parents=True)

        history_file = task_dir / "history.jsonl"
        history_data = {"result": "success", "iteration": 1}
        history_file.write_text(json.dumps(history_data) + "\n")

        result = runner.invoke(app, ["list", "--project", str(temp_dir)])
        assert result.exit_code == 0
        # Should show timestamp in YYYY-MM-DD HH:MM:SS format
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result.output)


class TestMaxTurnsWiring:
    """Tests for max_turns wiring from config to agents."""

    def _create_completed_result(self) -> LoopResult:
        """Create a completed LoopResult."""
        judgment = JudgmentResult(
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
        return LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=1,
            final_judgment=judgment,
        )

    def test_max_turns_from_config_passed_to_all_agents(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that max_turns from YAML config are passed to all agents."""
        import yaml

        config_data = {
            "task": "テスト",
            "criteria": ["条件"],
            "claude_options": {
                "max_turns": {
                    "intake": 5,
                    "execution": 100,
                    "summary": 15,
                    "judgment": 25,
                },
            },
        }
        config_file = temp_dir / "config.yaml"
        config_file.write_text(yaml.dump(config_data))

        mock_result = self._create_completed_result()

        with (
            patch("endless8.cli.main.Engine") as mock_engine_class,
            patch("endless8.cli.main.IntakeAgent") as mock_intake,
            patch("endless8.cli.main.ExecutionAgent") as mock_execution,
            patch("endless8.cli.main.SummaryAgent") as mock_summary,
            patch("endless8.cli.main.JudgmentAgent") as mock_judgment,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--config",
                    str(config_file),
                    "--project",
                    str(temp_dir),
                ],
            )

            assert result.exit_code == 0, f"CLI failed: {result.output}"

            # Verify max_turns passed to each agent
            mock_intake.assert_called_once()
            assert mock_intake.call_args.kwargs["max_turns"] == 5

            mock_execution.assert_called_once()
            assert mock_execution.call_args.kwargs["max_turns"] == 100

            mock_summary.assert_called_once()
            assert mock_summary.call_args.kwargs["max_turns"] == 15

            mock_judgment.assert_called_once()
            assert mock_judgment.call_args.kwargs["max_turns"] == 25


class TestModelNameWiring:
    """Tests for model_name wiring from config to all agents."""

    def _create_completed_result(self) -> LoopResult:
        """Create a completed LoopResult."""
        judgment = JudgmentResult(
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
        return LoopResult(
            status=LoopStatus.COMPLETED,
            iterations_used=1,
            final_judgment=judgment,
        )

    def test_model_name_passed_to_all_agents(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test that agent_model from config is passed to all 4 agents."""
        import yaml

        config_data = {
            "task": "テスト",
            "criteria": ["条件"],
            "agent_model": "anthropic:claude-haiku-3-5",
        }
        config_file = temp_dir / "config.yaml"
        config_file.write_text(yaml.dump(config_data))

        mock_result = self._create_completed_result()

        with (
            patch("endless8.cli.main.Engine") as mock_engine_class,
            patch("endless8.cli.main.IntakeAgent") as mock_intake,
            patch("endless8.cli.main.ExecutionAgent") as mock_execution,
            patch("endless8.cli.main.SummaryAgent") as mock_summary,
            patch("endless8.cli.main.JudgmentAgent") as mock_judgment,
        ):
            mock_engine = MagicMock()
            mock_engine.run = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--config",
                    str(config_file),
                    "--project",
                    str(temp_dir),
                ],
            )

            assert result.exit_code == 0, f"CLI failed: {result.output}"

            # Verify model_name passed to each agent
            mock_intake.assert_called_once()
            assert (
                mock_intake.call_args.kwargs["model_name"]
                == "anthropic:claude-haiku-3-5"
            )

            mock_execution.assert_called_once()
            assert (
                mock_execution.call_args.kwargs["model_name"]
                == "anthropic:claude-haiku-3-5"
            )

            mock_summary.assert_called_once()
            assert (
                mock_summary.call_args.kwargs["model_name"]
                == "anthropic:claude-haiku-3-5"
            )

            mock_judgment.assert_called_once()
            assert (
                mock_judgment.call_args.kwargs["model_name"]
                == "anthropic:claude-haiku-3-5"
            )


class TestStatusCommandKnowledge:
    """Tests for status command knowledge handling."""

    def test_status_with_no_knowledge_file(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        """Test status when knowledge file doesn't exist."""
        e8_dir = temp_dir / ".e8"
        e8_dir.mkdir()

        result = runner.invoke(app, ["status", "--project", str(temp_dir)])
        assert result.exit_code == 0
        assert "ナレッジエントリ: 0" in result.output
