"""Unit tests for CLI module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from endless8.cli.main import app, version_callback
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

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

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

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create temporary directory."""
        return tmp_path

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

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create temporary directory."""
        return tmp_path

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

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create temporary directory."""
        return tmp_path

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
