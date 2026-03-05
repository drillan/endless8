"""Unit tests for CommandExecutor (T009, T018).

T009 [US1]: happy path (exit code 0 -> met, non-zero -> not met),
            error path (OSError -> CommandExecutionError, timeout -> CommandExecutionError),
            output truncation at COMMAND_OUTPUT_MAX_BYTES.
T018 [US3]: exit code 127 warning log.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from endless8.command.executor import CommandExecutionError, CommandExecutor
from endless8.config.settings import COMMAND_OUTPUT_MAX_BYTES


class TestCommandExecutorHappyPath:
    """T009: Happy path tests for CommandExecutor."""

    async def test_exit_code_zero_returns_result(self) -> None:
        """Exit code 0 produces a CommandResult with exit_code=0."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"ok\n", b"")
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("echo ok", cwd="/tmp", timeout=10.0)

        assert result.exit_code == 0
        assert result.stdout == "ok\n"
        assert result.stderr == ""
        assert result.execution_time_sec >= 0.0

    async def test_nonzero_exit_code_returns_result(self) -> None:
        """Non-zero exit code produces a CommandResult (not an error)."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"fail\n")
        mock_process.returncode = 1

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("false", cwd="/tmp", timeout=10.0)

        assert result.exit_code == 1
        assert result.stderr == "fail\n"

    async def test_stdout_and_stderr_captured(self) -> None:
        """Both stdout and stderr are captured in the result."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"out", b"err")
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        assert result.stdout == "out"
        assert result.stderr == "err"

    async def test_execution_time_measured(self) -> None:
        """Execution time is non-negative."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        assert result.execution_time_sec >= 0.0


class TestCommandExecutorErrorPath:
    """T009: Error path tests for CommandExecutor."""

    async def test_oserror_raises_command_execution_error(self) -> None:
        """OSError during process creation raises CommandExecutionError."""
        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            side_effect=OSError("No such file or directory"),
        ):
            executor = CommandExecutor()
            with pytest.raises(CommandExecutionError, match="Failed to start command"):
                await executor.execute("no_such_cmd", cwd="/tmp", timeout=10.0)

    async def test_timeout_raises_command_execution_error(self) -> None:
        """Timeout during communicate raises CommandExecutionError."""
        mock_process = AsyncMock()
        mock_process.communicate.side_effect = TimeoutError()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            with pytest.raises(CommandExecutionError, match="timed out"):
                await executor.execute("sleep 100", cwd="/tmp", timeout=0.1)

        mock_process.kill.assert_called_once()

    async def test_none_return_code_raises_command_execution_error(self) -> None:
        """Process finishing without return code raises CommandExecutionError."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = None

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            with pytest.raises(CommandExecutionError, match="without return code"):
                await executor.execute("cmd", cwd="/tmp", timeout=10.0)


class TestCommandExecutorOutputTruncation:
    """T009: Output truncation at COMMAND_OUTPUT_MAX_BYTES."""

    async def test_stdout_truncated_at_max_bytes(self) -> None:
        """stdout exceeding COMMAND_OUTPUT_MAX_BYTES is truncated."""
        large_output = b"x" * (COMMAND_OUTPUT_MAX_BYTES + 1000)
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (large_output, b"")
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        assert len(result.stdout.encode("utf-8")) <= COMMAND_OUTPUT_MAX_BYTES

    async def test_stderr_truncated_at_max_bytes(self) -> None:
        """stderr exceeding COMMAND_OUTPUT_MAX_BYTES is truncated."""
        large_output = b"e" * (COMMAND_OUTPUT_MAX_BYTES + 1000)
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", large_output)
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        assert len(result.stderr.encode("utf-8")) <= COMMAND_OUTPUT_MAX_BYTES

    async def test_output_within_limit_not_truncated(self) -> None:
        """Output within COMMAND_OUTPUT_MAX_BYTES is preserved in full."""
        normal_output = b"hello world"
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (normal_output, b"")
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        assert result.stdout == "hello world"

    async def test_invalid_utf8_replaced(self) -> None:
        """Invalid UTF-8 bytes are replaced, not causing errors."""
        invalid_utf8 = b"\xff\xfe invalid"
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (invalid_utf8, b"")
        mock_process.returncode = 0

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        # Should not raise; replacement characters used
        assert "\ufffd" in result.stdout


class TestCommandExecutorExitCode127:
    """T018 [US3]: Exit code 127 warning log."""

    async def test_exit_code_127_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Exit code 127 emits a warning log about command not found."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            b"",
            b"bash: no_such_cmd: command not found",
        )
        mock_process.returncode = 127

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("no_such_cmd", cwd="/tmp", timeout=10.0)

        assert result.exit_code == 127
        assert any(
            "exit code 127" in record.message and record.levelname == "WARNING"
            for record in caplog.records
        )

    async def test_exit_code_127_is_not_an_error(self) -> None:
        """Exit code 127 returns a result, does NOT raise CommandExecutionError."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"command not found")
        mock_process.returncode = 127

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            result = await executor.execute("no_such_cmd", cwd="/tmp", timeout=10.0)

        assert result.exit_code == 127

    async def test_non_127_exit_code_no_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Exit codes other than 127 do not emit a warning log."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"error")
        mock_process.returncode = 1

        with patch(
            "endless8.command.executor.asyncio.create_subprocess_shell",
            return_value=mock_process,
        ):
            executor = CommandExecutor()
            await executor.execute("cmd", cwd="/tmp", timeout=10.0)

        warning_records = [
            r for r in caplog.records if r.levelname == "WARNING" and "127" in r.message
        ]
        assert len(warning_records) == 0
