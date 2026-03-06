"""Command executor for structured completion criteria.

Executes shell commands and returns results for command-type criteria evaluation.
"""

import asyncio
import logging
import time

from endless8.config.settings import COMMAND_OUTPUT_MAX_BYTES
from endless8.models import CommandResult

logger = logging.getLogger(__name__)


class CommandExecutionError(Exception):
    """コマンドの実行エラー（FR-009）。

    以下の場合に送出される:
    - プロセス起動失敗（OSError）
    - タイムアウト
    - 終了コード 2 以上（POSIX 規約に基づくコマンド自体のエラー）
    """


class CommandExecutor:
    """コマンド条件の実行器。

    asyncio.create_subprocess_shell を使用してシェルコマンドを実行する。
    """

    async def execute(
        self,
        command: str,
        cwd: str,
        timeout: float,
    ) -> CommandResult:
        """コマンドを実行し結果を返す。

        Args:
            command: 実行するシェルコマンド
            cwd: 作業ディレクトリ（FR-014）
            timeout: タイムアウト（秒）（FR-008）

        Returns:
            CommandResult: 実行結果

        Raises:
            CommandExecutionError: プロセス起動失敗またはタイムアウト時（FR-009）
        """
        start_time = time.monotonic()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
        except OSError as e:
            raise CommandExecutionError(
                f"Failed to start command '{command}': {e}"
            ) from e

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except TimeoutError as e:
            process.kill()
            await process.wait()
            raise CommandExecutionError(
                f"Command '{command}' timed out after {timeout}s"
            ) from e

        execution_time = time.monotonic() - start_time

        stdout = stdout_bytes[:COMMAND_OUTPUT_MAX_BYTES].decode(
            "utf-8", errors="replace"
        )
        stderr = stderr_bytes[:COMMAND_OUTPUT_MAX_BYTES].decode(
            "utf-8", errors="replace"
        )

        exit_code = process.returncode
        if exit_code is None:
            raise CommandExecutionError(
                f"Command '{command}' finished without return code"
            )

        if exit_code >= 2:
            raise CommandExecutionError(
                f"Command '{command}' failed with exit code {exit_code}.\n"
                f"stderr: {stderr}"
            )

        return CommandResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            execution_time_sec=execution_time,
        )


__all__ = ["CommandExecutionError", "CommandExecutor"]
