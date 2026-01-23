"""CLI main module for endless8.

Provides command-line interface for running tasks.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from endless8 import __version__
from endless8.agents.execution import ExecutionAgent
from endless8.agents.intake import IntakeAgent
from endless8.agents.judgment import JudgmentAgent
from endless8.agents.summary import SummaryAgent
from endless8.config import EngineConfig, load_config
from endless8.engine import Engine
from endless8.models import LoopStatus, TaskInput

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

    async def run_engine() -> None:
        """Run the engine asynchronously."""
        engine = Engine(
            config=engine_config,
            intake_agent=IntakeAgent(),
            execution_agent=ExecutionAgent(),
            summary_agent=SummaryAgent(task_description=task),
            judgment_agent=JudgmentAgent(),
        )
        result = await engine.run(task_input)

        typer.echo("")
        if result.status == LoopStatus.COMPLETED:
            typer.secho("✓ タスク完了", fg=typer.colors.GREEN)
        elif result.status == LoopStatus.MAX_ITERATIONS:
            typer.secho(
                f"✗ 最大イテレーション ({result.iterations_used}) に達しました",
                fg=typer.colors.YELLOW,
            )
        elif result.status == LoopStatus.ERROR:
            typer.secho(f"✗ エラー: {result.error_message}", fg=typer.colors.RED)
        else:
            typer.secho(f"ステータス: {result.status.value}", fg=typer.colors.BLUE)

        typer.echo(f"使用イテレーション: {result.iterations_used}")

    asyncio.run(run_engine())


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

    history_file = e8_dir / "history.jsonl"
    if history_file.exists():
        line_count = sum(1 for _ in history_file.open())
        typer.echo(f"履歴エントリ: {line_count}")
    else:
        typer.echo("履歴エントリ: 0")

    knowledge_file = e8_dir / "knowledge.jsonl"
    if knowledge_file.exists():
        line_count = sum(1 for _ in knowledge_file.open())
        typer.echo(f"ナレッジエントリ: {line_count}")
    else:
        typer.echo("ナレッジエントリ: 0")


if __name__ == "__main__":
    app()
