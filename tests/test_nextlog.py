from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from click.testing import CliRunner

from nextlog import get_errors, get_run, get_status, list_runs
from nextlog.cli import cli


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def touch_with_time(path: Path, when: datetime) -> None:
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def make_history_run(base: Path, ts: datetime, duration: str, name: str, status: str, session: str) -> None:
    history = base / ".nextflow" / "history"
    line = f"{ts.strftime('%Y-%m-%d %H:%M:%S')}\t{duration}\t{name}\t{status}\tabcd\t{session}\tnextflow run ."
    if history.exists():
        history.write_text(history.read_text() + "\n" + line)
    else:
        write_file(history, line)


def make_task(base: Path, rel: str, exit_code: int, err_content: str = "", name: str = "task") -> Path:
    task_dir = base / "work" / rel
    write_file(task_dir / ".exitcode", str(exit_code))
    write_file(task_dir / ".command.err", err_content)
    write_file(task_dir / ".command.run", f"### name: '{name}'")
    write_file(task_dir / ".command.sh", "#!/bin/bash\necho hi\n")
    return task_dir


def test_list_runs_from_history(tmp_path: Path) -> None:
    base = tmp_path / "proj"
    ts1 = datetime(2024, 1, 1, 10, 0, 0)
    ts2 = datetime(2024, 1, 2, 9, 0, 0)
    make_history_run(base, ts1, "30s", "first", "OK", "sess-1")
    make_history_run(base, ts2, "45s", "second", "ERR", "sess-2")

    runs = list_runs(base)
    assert len(runs) == 2
    assert runs[0].run_id == "sess-2"
    assert runs[0].status == "fail"
    assert runs[1].status == "success"


def test_get_run_from_log(tmp_path: Path) -> None:
    base = tmp_path / "proj"
    log = (
        "Jan-01 10:00:00.000 [main] DEBUG nextflow.cli.Launcher - $> nextflow run .\n"
        "Jan-01 10:00:00.001 [main] DEBUG nextflow.Session - Session UUID: sess-log\n"
        "Jan-01 10:00:00.002 [main] DEBUG nextflow.Session - Run name: mellow_wave\n"
    )
    write_file(base / ".nextflow.log", log)

    runs = list_runs(base)
    assert len(runs) == 1
    assert runs[0].run_id == "sess-log"
    assert runs[0].run_name == "mellow_wave"
    picked = get_run("sess-log", base)
    assert picked.run_id == "sess-log"


def test_status_counts(tmp_path: Path) -> None:
    base = tmp_path / "proj"
    start = datetime(2024, 1, 3, 12, 0, 0)
    make_history_run(base, start, "60s", "status", "OK", "sess-status")
    task_ok = make_task(base, "aa/task1", 0, name="ok_task")
    task_fail = make_task(base, "bb/task2", 1, name="bad_task")
    touch_with_time(task_ok / ".exitcode", start + timedelta(seconds=10))
    touch_with_time(task_fail / ".exitcode", start + timedelta(seconds=20))

    run = get_run("sess-status", base)
    status = get_status(run)
    assert status.counts["succeeded"] == 1
    assert status.counts["failed"] == 1
    assert status.overall == "fail"


def test_errors_collect_tail(tmp_path: Path) -> None:
    base = tmp_path / "proj"
    start = datetime(2024, 1, 4, 8, 30, 0)
    make_history_run(base, start, "30s", "errs", "ERR", "sess-err")
    task_dir = make_task(base, "cc/task3", 1, err_content="one\nlast line", name="failing_proc")
    touch_with_time(task_dir / ".exitcode", start + timedelta(seconds=5))
    touch_with_time(task_dir / ".command.err", start + timedelta(seconds=5))

    run = get_run("sess-err", base)
    errors = get_errors(run, limit=3)
    assert len(errors) == 1
    assert errors[0].process_name == "failing_proc"
    assert "last line" in errors[0].err_excerpt


def test_cli_runs_json(tmp_path: Path) -> None:
    base = tmp_path / "proj"
    ts = datetime(2024, 1, 5, 7, 0, 0)
    make_history_run(base, ts, "20s", "cli", "OK", "sess-cli")
    runner = CliRunner()
    result = runner.invoke(cli, ["--base-dir", str(base), "runs", "--json", "--limit", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["run_id"] == "sess-cli"
