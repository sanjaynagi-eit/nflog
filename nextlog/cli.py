from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from . import get_errors, get_run, get_status, list_runs
from .errors import open_in_pager

LOG = logging.getLogger("nextlog")
console = Console()


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _status_style(value: str) -> str:
    palette = {
        "success": "green",
        "fail": "red",
        "running": "yellow",
        "unknown": "grey70",
    }
    color = palette.get((value or "").lower(), "cyan")
    return f"[{color}]{value}[/]"


@click.group()
@click.option("--base-dir", default=".", type=click.Path(file_okay=False, dir_okay=True), help="Nextflow project directory.")
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, base_dir: str, debug: bool) -> None:
    """Inspect and debug recent Nextflow runs."""
    _setup_logging(debug)
    ctx.obj = {"base_dir": Path(base_dir).resolve()}


@cli.command()
@click.option("--limit", default=10, show_default=True, help="Number of runs to show.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON instead of a table.")
@click.pass_context
def runs(ctx: click.Context, limit: int, as_json: bool) -> None:
    """List recent runs."""
    base_dir: Path = ctx.obj["base_dir"]
    runs = list_runs(base_dir)[:limit]
    if as_json:
        click.echo(json.dumps([asdict(r) for r in runs], default=str, indent=2))
        return
    if not runs:
        console.print("No runs found.")
        return
    table = Table(title="[bold cyan]Recent Nextflow runs[/bold cyan]", header_style="bold blue", box=None)
    table.add_column("Run ID")
    table.add_column("Name")
    table.add_column("Started")
    table.add_column("Duration")
    table.add_column("Status")
    table.add_column("Work dir")
    for run in runs:
        table.add_row(
            run.run_id,
            run.run_name or "-",
            run.started.isoformat() if run.started else "-",
            str(run.duration) if run.duration else "-",
            _status_style(run.status),
            str(run.work_dir),
        )
    console.print(table)


@cli.command()
@click.option("--run", "run_id", help="Run id or prefix (defaults to most recent).")
@click.option("--json", "as_json", is_flag=True, help="Output JSON.")
@click.pass_context
def status(ctx: click.Context, run_id: Optional[str], as_json: bool) -> None:
    """Show run status summary."""
    base_dir: Path = ctx.obj["base_dir"]
    run = get_run(run_id, base_dir)
    status_obj = get_status(run)
    if as_json:
        click.echo(json.dumps(asdict(status_obj), default=str, indent=2))
        return
    table = Table(title=f"[bold cyan]Run {run.run_id}[/bold cyan]", header_style="bold blue", box=None)
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Overall", _status_style(status_obj.overall))
    for key, value in status_obj.counts.items():
        table.add_row(key, str(value))
    table.add_row("Derived from", status_obj.details_from)
    console.print(table)


@cli.command()
@click.option("--run", "run_id", help="Run id or prefix (defaults to most recent).")
@click.option("--show", default=5, show_default=True, help="How many errors to display.")
@click.option("--open", "open_paths", is_flag=True, help="Open error files in $PAGER.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON.")
@click.pass_context
def errors(ctx: click.Context, run_id: Optional[str], show: int, open_paths: bool, as_json: bool) -> None:
    """Display failing tasks with .command.err content."""
    base_dir: Path = ctx.obj["base_dir"]
    run = get_run(run_id, base_dir)
    error_items = get_errors(run, limit=show)
    if as_json:
        click.echo(json.dumps([asdict(e) for e in error_items], default=str, indent=2))
        return
    if not error_items:
        console.print(f"No failing tasks found for run {run.run_id}")
        return
    table = Table(title=f"[bold red]Errors for {run.run_id}[/bold red]", header_style="bold blue", box=None)
    table.add_column("#")
    table.add_column("Process")
    table.add_column("Exit")
    table.add_column("Work dir")
    table.add_column(".command.err / .log tail")
    for idx, err in enumerate(error_items, start=1):
        table.add_row(
            str(idx),
            err.process_name or "-",
            str(err.exit_code) if err.exit_code is not None else "-",
            str(err.work_dir),
            (err.err_excerpt or "").splitlines()[-1] if err.err_excerpt else "",
        )
    console.print(table)
    console.print("Inspect .command.sh or rerun with -resume for reproduction guidance.")
    if open_paths:
        paths = [e.err_path for e in error_items if e.err_path] + [e.log_path for e in error_items if e.log_path]
        open_in_pager([p for p in paths if p])
    else:
        console.print("Pass --open to view .command.err in $PAGER.")


@cli.command()
@click.option("--run", "run_id", help="Run id or prefix (defaults to most recent).")
@click.option("--index", type=int, help="Index from `nextlog errors` (1-based).")
@click.option("--workdir", type=click.Path(file_okay=False, dir_okay=True), help="Explicit work directory path.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON.")
@click.pass_context
def errfile(ctx: click.Context, run_id: Optional[str], index: Optional[int], workdir: Optional[str], as_json: bool) -> None:
    """Print the .command.err path for scripting."""
    if index and workdir:
        raise click.UsageError("Use either --index or --workdir.")
    base_dir: Path = ctx.obj["base_dir"]
    run = get_run(run_id, base_dir)
    target_path: Optional[Path] = None
    if workdir:
        target_path = Path(workdir) / ".command.err"
    else:
        errors = get_errors(run, limit=max(index or 1, 1))
        if not errors:
            raise click.ClickException("No errors found.")
        pick = errors[(index - 1) if index else 0]
        target_path = pick.err_path
    if not target_path or not target_path.exists():
        raise click.ClickException("Error file not found.")
    if as_json:
        click.echo(json.dumps({"path": str(target_path), "content": target_path.read_text(errors="replace")}, default=str, indent=2))
        return
    click.echo(str(target_path))
    click.echo(target_path.read_text(errors="replace"))


def main() -> None:
    cli(prog_name="nextlog")


if __name__ == "__main__":
    main()
