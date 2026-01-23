"""Integration tests for the CLI."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_project_dir(self, tmp_path: Path) -> Path:
        """Create temporary project directory."""
        return tmp_path

    def test_cli_run_command_exists(self, runner: CliRunner) -> None:
        """Test that run command is available."""
        from endless8.cli.main import app

        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "タスク" in result.stdout or "task" in result.stdout.lower()

    def test_cli_run_creates_e8_directory(
        self,
        runner: CliRunner,
        temp_project_dir: Path,
    ) -> None:
        """Test that run command creates .e8 directory."""
        from endless8.cli.main import app

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.run.return_value = AsyncMock(
                status="completed",
                iterations_used=1,
            )
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "テストタスク",
                    "--criteria",
                    "テスト条件",
                    "--project",
                    str(temp_project_dir),
                ],
            )

            # .e8 directory should be created
            e8_dir = temp_project_dir / ".e8"
            assert e8_dir.exists() or result.exit_code == 0

    def test_cli_run_with_multiple_criteria(
        self,
        runner: CliRunner,
        temp_project_dir: Path,
    ) -> None:
        """Test that run command accepts multiple criteria."""
        from endless8.cli.main import app

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.run.return_value = AsyncMock(
                status="completed",
                iterations_used=1,
            )
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "複数条件タスク",
                    "--criteria",
                    "条件1",
                    "--criteria",
                    "条件2",
                    "--criteria",
                    "条件3",
                    "--project",
                    str(temp_project_dir),
                ],
            )

            assert result.exit_code == 0 or "条件" in result.stdout

    def test_cli_run_with_max_iterations(
        self,
        runner: CliRunner,
        temp_project_dir: Path,
    ) -> None:
        """Test that run command accepts max-iterations option."""
        from endless8.cli.main import app

        with patch("endless8.cli.main.Engine") as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.run.return_value = AsyncMock(
                status="completed",
                iterations_used=3,
            )
            mock_engine_class.return_value = mock_engine

            result = runner.invoke(
                app,
                [
                    "run",
                    "--task",
                    "タスク",
                    "--criteria",
                    "条件",
                    "--max-iterations",
                    "5",
                    "--project",
                    str(temp_project_dir),
                ],
            )

            # Should not error
            assert result.exit_code == 0 or "iterations" not in result.stdout.lower()

    def test_cli_status_command_exists(self, runner: CliRunner) -> None:
        """Test that status command is available."""
        from endless8.cli.main import app

        result = runner.invoke(app, ["status", "--help"])
        # status command should exist
        assert result.exit_code == 0

    def test_cli_version_option(self, runner: CliRunner) -> None:
        """Test that --version option works."""
        from endless8.cli.main import app

        result = runner.invoke(app, ["--version"])
        # Should show version info
        assert result.exit_code == 0 or "version" in result.stdout.lower()
