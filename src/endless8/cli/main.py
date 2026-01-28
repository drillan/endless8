"""CLI main module for endless8.

Provides command-line interface for running tasks.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from claude_agent_sdk.types import Message

from endless8 import __version__
from endless8.agents.execution import ExecutionAgent
from endless8.agents.intake import IntakeAgent
from endless8.agents.judgment import JudgmentAgent
from endless8.agents.summary import SummaryAgent
from endless8.config import EngineConfig, load_config
from endless8.engine import Engine
from endless8.history import History, KnowledgeBase
from endless8.models import LoopStatus, ProgressEvent, ProgressEventType, TaskInput

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="e8",
    help="endless8 - コンテキスト効率の良いタスク実行ループエンジン",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"endless8 version {__version__}")
        raise typer.Exit()


def _format_tool_call(tool_name: str, tool_input: dict[str, object]) -> str:
    """Format a tool call for display.

    Args:
        tool_name: Name of the tool.
        tool_input: Tool input parameters.

    Returns:
        Formatted string like "Write: path/to/file" or "Bash: command".
    """
    if tool_name in ("Read", "Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            return f"{tool_name}: {file_path}"
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            # Truncate long commands
            if len(str(command)) > 40:
                command = str(command)[:40] + "..."
            return f"{tool_name}: {command}"
    elif tool_name == "Glob" or tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        if pattern:
            return f"{tool_name}: {pattern}"

    return tool_name


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="バージョン情報を表示",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """endless8 - コンテキスト効率の良いタスク実行ループエンジン。"""
    pass


@app.command()
def run(
    task: Annotated[str, typer.Option("--task", "-t", help="タスクの説明")] = "",
    # Typer requires mutable default for multi-option; noqa suppresses B006
    criteria: Annotated[
        list[str], typer.Option("--criteria", "-c", help="完了条件（複数指定可）")
    ] = [],  # noqa: B006
    max_iterations: Annotated[
        int | None, typer.Option("--max-iterations", "-m", help="最大イテレーション数")
    ] = None,
    config_file: Annotated[
        Path | None, typer.Option("--config", help="YAML設定ファイル")
    ] = None,
    project: Annotated[
        Path, typer.Option("--project", "-p", help="プロジェクトディレクトリ")
    ] = Path.cwd(),
    resume: Annotated[
        str | None, typer.Option("--resume", "-r", help="タスクIDを指定して再開")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-V", help="詳細な実行ログを表示")
    ] = False,
) -> None:
    """タスクを実行します。"""
    # Load config from file if provided
    if config_file is not None:
        try:
            engine_config = load_config(config_file)
        except FileNotFoundError:
            typer.echo(f"エラー: 設定ファイルが見つかりません: {config_file}", err=True)
            raise typer.Exit(1) from None
        except ValueError as e:
            typer.echo(f"エラー: 設定ファイルが不正です: {e}", err=True)
            raise typer.Exit(1) from None

        # CLI options override config file
        if task:
            engine_config.task = task
        if criteria:
            engine_config.criteria = criteria
        if max_iterations is not None:
            engine_config.max_iterations = max_iterations

        # Use config values
        task = engine_config.task
        criteria = engine_config.criteria
        max_iterations = engine_config.max_iterations
    else:
        # No config file - require task and criteria from CLI
        if not task:
            typer.echo(
                "エラー: タスクを指定してください (--task または --config)", err=True
            )
            raise typer.Exit(1)

        if not criteria:
            typer.echo(
                "エラー: 完了条件を指定してください (--criteria または --config)",
                err=True,
            )
            raise typer.Exit(1)

        if max_iterations is None:
            max_iterations = 10

        # Create engine config
        engine_config = EngineConfig(
            task=task,
            criteria=criteria,
            max_iterations=max_iterations,
        )

    # Ensure .e8 directory exists
    e8_dir = project / ".e8"
    e8_dir.mkdir(parents=True, exist_ok=True)

    # Setup History and KnowledgeBase for persistence
    history_store: History | None = None
    knowledge_base: KnowledgeBase | None = None
    resume_mode = False

    if resume:
        # Resume from existing task
        task_dir = e8_dir / "tasks" / resume
        if not task_dir.exists():
            typer.echo(f"エラー: タスクが見つかりません: {resume}", err=True)
            raise typer.Exit(1)

        history_path = task_dir / "history.jsonl"
        knowledge_path = task_dir / "knowledge.jsonl"

        history_store = History(history_path)
        knowledge_base = KnowledgeBase(knowledge_path)
        resume_mode = True

        typer.echo(f"タスク再開: {resume}")
    else:
        # New task - create task directory with timestamp-based ID
        from datetime import datetime

        task_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        task_dir = e8_dir / "tasks" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        history_path = task_dir / "history.jsonl"
        knowledge_path = task_dir / "knowledge.jsonl"

        history_store = History(history_path)
        knowledge_base = KnowledgeBase(knowledge_path)

        typer.echo(f"タスクID: {task_id}")

    typer.echo(f"タスク: {task}")
    typer.echo(f"完了条件: {', '.join(criteria)}")
    typer.echo(f"最大イテレーション: {max_iterations}")
    typer.echo("")

    # Create task input
    task_input = TaskInput(
        task=task,
        criteria=criteria,
        max_iterations=max_iterations,
    )

    def progress_callback(event: ProgressEvent) -> None:
        """Display progress events in CLI."""
        event_type = event.event_type
        message = event.message
        iteration = event.iteration

        # Format based on event type
        if event_type == ProgressEventType.TASK_START:
            typer.secho("▶ " + message, fg=typer.colors.CYAN)
        elif event_type == ProgressEventType.ITERATION_START:
            typer.echo("")
            typer.secho(
                f"── イテレーション {iteration} ──", fg=typer.colors.BLUE, bold=True
            )
        elif event_type == ProgressEventType.INTAKE_COMPLETE:
            typer.echo(f"  受付: {message}")
        elif event_type == ProgressEventType.EXECUTION_COMPLETE:
            typer.echo(f"  実行: {message}")
        elif event_type == ProgressEventType.JUDGMENT_COMPLETE:
            is_complete = event.data.get("is_complete", False) if event.data else False
            if is_complete:
                typer.secho(f"  判定: {message}", fg=typer.colors.GREEN)
            else:
                typer.echo(f"  判定: {message}")
        elif event_type == ProgressEventType.ITERATION_END:
            result_value = (
                event.data.get("result", "unknown") if event.data else "unknown"
            )
            typer.echo(f"  結果: {result_value}")
        elif event_type == ProgressEventType.TASK_END:
            pass  # Handled separately after run() returns

    async def run_engine() -> None:
        """Run the engine asynchronously."""
        # Setup message callback for verbose mode
        message_callback = None
        if verbose:

            def on_message(message: "Message") -> None:
                try:
                    from claude_agent_sdk.types import (
                        AssistantMessage,
                        StreamEvent,
                        TextBlock,
                        ToolUseBlock,
                    )

                    if isinstance(message, AssistantMessage):
                        for block in message.content or []:
                            if isinstance(block, ToolUseBlock):
                                # Skip internal pydantic-ai tools (case-insensitive)
                                if block.name.lower() == "structuredoutput":
                                    continue
                                # Format tool call with key input parameters
                                tool_input = (
                                    block.input if isinstance(block.input, dict) else {}
                                )
                                tool_display = _format_tool_call(block.name, tool_input)
                                typer.echo(f"    → {tool_display}")
                            elif isinstance(block, TextBlock):
                                if block.text:
                                    text = block.text[:80]
                                    if len(block.text) > 80:
                                        text += "..."
                                    typer.echo(f"    📝 {text}")
                    elif isinstance(message, StreamEvent):
                        event = message.event
                        if not isinstance(event, dict):
                            return
                        event_type = event.get("type", "")
                        # Handle content_block_start for tool_use
                        if event_type == "content_block_start":
                            content_block = event.get("content_block", {})
                            block_type = content_block.get("type", "")
                            if block_type == "tool_use":
                                tool_name = content_block.get("name", "")
                                # Skip internal pydantic-ai tools (case-insensitive)
                                if (
                                    tool_name
                                    and tool_name.lower() != "structuredoutput"
                                ):
                                    typer.echo(f"    → {tool_name}")
                except Exception as e:
                    # Log error but don't interrupt main execution
                    logger.warning("Verbose callback error (ignored): %s", e)

            message_callback = on_message

        max_turns = engine_config.claude_options.max_turns
        engine = Engine(
            config=engine_config,
            intake_agent=IntakeAgent(
                model_name=engine_config.agent_model,
                timeout=engine_config.claude_options.timeout,
                max_turns=max_turns.intake,
            ),
            execution_agent=ExecutionAgent(
                append_system_prompt=engine_config.prompts.append_system_prompt,
                model_name=engine_config.agent_model,
                allowed_tools=engine_config.claude_options.allowed_tools,
                timeout=engine_config.claude_options.timeout,
                message_callback=message_callback,
                max_turns=max_turns.execution,
            ),
            summary_agent=SummaryAgent(
                task_description=task,
                model_name=engine_config.agent_model,
                timeout=engine_config.claude_options.timeout,
                max_turns=max_turns.summary,
            ),
            judgment_agent=JudgmentAgent(
                model_name=engine_config.agent_model,
                timeout=engine_config.claude_options.timeout,
                max_turns=max_turns.judgment,
            ),
            history=history_store,
            knowledge_base=knowledge_base,
        )
        result = await engine.run(
            task_input, on_progress=progress_callback, resume=resume_mode
        )

        typer.echo("")
        typer.echo("=" * 50)
        if result.status == LoopStatus.COMPLETED:
            typer.secho("✓ タスク完了", fg=typer.colors.GREEN, bold=True)
        elif result.status == LoopStatus.MAX_ITERATIONS:
            typer.secho(
                f"✗ 最大イテレーション ({result.iterations_used}) に達しました",
                fg=typer.colors.YELLOW,
                bold=True,
            )
        elif result.status == LoopStatus.ERROR:
            if result.error_message and "Tool mismatch" in result.error_message:
                typer.secho("✗ ツール設定エラー", fg=typer.colors.RED, bold=True)
                typer.echo("")
                typer.echo("タスクに必要なツールが allowed_tools に含まれていません。")
                typer.echo("")
                # Parse and show details
                if result.intake_result and result.intake_result.suggested_tools:
                    suggested = result.intake_result.suggested_tools
                    allowed = engine_config.claude_options.allowed_tools
                    missing = set(suggested) - set(allowed)
                    typer.echo(f"必要なツール: {', '.join(sorted(suggested))}")
                    typer.echo(f"現在の設定: {', '.join(sorted(allowed))}")
                    typer.echo(f"不足: {', '.join(sorted(missing))}")
                    typer.echo("")
                    typer.echo(
                        "設定ファイルの claude_options.allowed_tools を更新してください:"
                    )
                    typer.echo("")
                    typer.echo("  claude_options:")
                    typer.echo("    allowed_tools:")
                    for tool in sorted(set(allowed) | missing):
                        typer.echo(f'      - "{tool}"')
            else:
                typer.secho(
                    f"✗ エラー: {result.error_message}", fg=typer.colors.RED, bold=True
                )
        elif result.status == LoopStatus.CANCELLED:
            typer.secho("キャンセルされました", fg=typer.colors.YELLOW, bold=True)
        else:
            typer.secho(f"ステータス: {result.status.value}", fg=typer.colors.BLUE)

        typer.echo(f"使用イテレーション: {result.iterations_used}")

        # Show final judgment details if available
        if result.final_judgment:
            judgment = result.final_judgment
            typer.echo("")
            typer.echo("判定結果:")
            typer.echo(f"  理由: {judgment.overall_reason}")

            # Show evaluation of each criterion
            if judgment.evaluations:
                typer.echo("  条件評価:")
                for ev in judgment.evaluations:
                    status_icon = "✓" if ev.is_met else "✗"
                    color = typer.colors.GREEN if ev.is_met else typer.colors.RED
                    typer.secho(
                        f"    {status_icon} {ev.criterion} (確信度: {ev.confidence:.0%})",
                        fg=color,
                    )
                    typer.echo(f"      根拠: {ev.evidence}")

            # Show suggested next action if not complete
            if not judgment.is_complete and judgment.suggested_next_action:
                typer.echo(f"  推奨アクション: {judgment.suggested_next_action}")

        # Show history path if available
        if result.history_path:
            typer.echo(f"履歴: {result.history_path}")

    asyncio.run(run_engine())


@app.command(name="list")
def list_tasks(
    project: Annotated[
        Path, typer.Option("--project", "-p", help="プロジェクトディレクトリ")
    ] = Path.cwd(),
) -> None:
    """タスク一覧を表示します。"""
    e8_dir = project / ".e8"
    tasks_dir = e8_dir / "tasks"

    if not tasks_dir.exists():
        typer.echo("endless8 タスク一覧")
        typer.echo("")
        typer.echo("タスクが見つかりません")
        typer.echo(f"ディレクトリ: {tasks_dir}")
        raise typer.Exit(0)

    # Get all task directories
    task_dirs = sorted(
        [d for d in tasks_dir.iterdir() if d.is_dir()],
        key=lambda x: x.name,
        reverse=True,
    )

    if not task_dirs:
        typer.echo("endless8 タスク一覧")
        typer.echo("")
        typer.echo("タスクが見つかりません")
        raise typer.Exit(0)

    typer.echo("endless8 タスク一覧")
    typer.echo("")
    typer.echo(f"{'TASK_ID':<24} {'STATUS':<12} {'ITERATIONS':<12} {'LAST_UPDATED'}")

    for task_dir in task_dirs:
        task_id = task_dir.name
        history_file = task_dir / "history.jsonl"

        if history_file.exists():
            # Count iterations and determine status
            import json

            line_count = 0
            last_result = "unknown"
            for line_num, line in enumerate(history_file.open(), start=1):
                line = line.strip()
                if line:
                    line_count += 1
                    # Parse last line to get result
                    try:
                        data = json.loads(line)
                        last_result = data.get("result", "unknown")
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "Invalid JSON in history file %s:%d: %s",
                            history_file,
                            line_num,
                            e,
                        )

            # Determine status
            status = "in_progress"
            if last_result == "success":
                # Check if completed (need to look at judgment)
                status = "in_progress"
            elif last_result == "failure":
                status = "failed"
            elif last_result == "error":
                status = "error"

            # Get last modified time
            mtime = history_file.stat().st_mtime
            from datetime import datetime

            last_updated = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        else:
            line_count = 0
            status = "unknown"
            last_updated = "-"

        typer.echo(f"{task_id:<24} {status:<12} {line_count:<12} {last_updated}")

    typer.echo("")
    typer.echo(f"合計: {len(task_dirs)} タスク")


@app.command()
def status(
    project: Annotated[
        Path, typer.Option("--project", "-p", help="プロジェクトディレクトリ")
    ] = Path.cwd(),
) -> None:
    """現在の実行状態を表示します。"""
    e8_dir = project / ".e8"

    if not e8_dir.exists():
        typer.echo("endless8の履歴が見つかりません")
        typer.echo(f"ディレクトリ: {e8_dir}")
        raise typer.Exit(0)

    # Count tasks
    tasks_dir = e8_dir / "tasks"
    task_count = 0
    if tasks_dir.exists():
        task_count = len([d for d in tasks_dir.iterdir() if d.is_dir()])
    typer.echo(f"タスク数: {task_count}")

    # Count knowledge entries
    knowledge_file = e8_dir / "knowledge.jsonl"
    if knowledge_file.exists():
        line_count = sum(1 for _ in knowledge_file.open())
        typer.echo(f"ナレッジエントリ: {line_count}")
    else:
        typer.echo("ナレッジエントリ: 0")


if __name__ == "__main__":
    app()
