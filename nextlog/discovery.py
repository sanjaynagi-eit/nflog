from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, List, Optional

from .models import RunDetails, RunSummary
from .utils import fallback_run_id, map_status, parse_duration, parse_history_timestamp, parse_log_timestamp

LOG = logging.getLogger("nextlog")


def list_runs(base_dir: Path | str = ".") -> List[RunSummary]:
    base = Path(base_dir)
    history_runs = _from_history(base)
    log_runs = _from_log(base)
    merged = {}
    for run in log_runs + history_runs:
        if run.run_id not in merged or _is_newer(run, merged[run.run_id]):
            merged[run.run_id] = run
    runs = list(merged.values())
    runs.sort(key=lambda r: r.started or parse_log_timestamp("Jan-01 00:00:00"), reverse=True)
    return runs


def get_run(run_id: Optional[str] = None, base_dir: Path | str = ".") -> RunDetails:
    runs = list_runs(base_dir)
    if not runs:
        raise RuntimeError("No Nextflow runs found in this directory.")
    if run_id is None:
        summary = runs[0]
    else:
        summary = _pick_run_by_id(runs, run_id)
    end_time = summary.started + summary.duration if summary.started and summary.duration else None
    return RunDetails(
        run_id=summary.run_id,
        run_name=summary.run_name,
        started=summary.started,
        ended=end_time,
        duration=summary.duration,
        status=summary.status,
        work_dir=summary.work_dir,
        log_path=summary.log_path,
        command=summary.command,
        source=summary.source,
    )


def _pick_run_by_id(runs: Iterable[RunSummary], run_id: str) -> RunSummary:
    for run in runs:
        if run.run_id == run_id or run.run_id.startswith(run_id):
            return run
    raise RuntimeError(f"Run {run_id} not found.")


def _from_history(base_dir: Path) -> List[RunSummary]:
    history_path = base_dir / ".nextflow" / "history"
    if not history_path.exists():
        return []
    runs: List[RunSummary] = []
    for line in history_path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", maxsplit=6)
        if len(parts) < 6:
            continue
        timestamp = parse_history_timestamp(parts[0])
        duration = parse_duration(parts[1])
        run_name = parts[2] or None
        status_raw = parts[3] if len(parts) > 3 else ""
        session_id = parts[5] if len(parts) > 5 else ""
        command = parts[6] if len(parts) > 6 else None
        run_id = session_id or fallback_run_id(base_dir, timestamp)
        runs.append(
            RunSummary(
                run_id=run_id,
                run_name=run_name,
                started=timestamp,
                duration=duration,
                status=map_status(status_raw),
                work_dir=base_dir / "work",
                log_path=base_dir / ".nextflow.log",
                source="history",
                command=command,
            )
        )
    return runs


def _from_log(base_dir: Path) -> List[RunSummary]:
    log_path = base_dir / ".nextflow.log"
    if not log_path.exists():
        return []
    runs: List[RunSummary] = []
    current: Optional[RunSummary] = None
    session_re = re.compile(r"Session UUID: ([a-z0-9-]+)", re.IGNORECASE)
    name_re = re.compile(r"Run name: ([\w\-]+)")
    work_re = re.compile(r"Work-dir: (.+?)\s")
    command_re = re.compile(r"\$>\s+(nextflow .+)")

    for line in log_path.read_text(errors="replace").splitlines():
        if match := session_re.search(line):
            ts = parse_log_timestamp(line.split("[")[0].strip())
            run_id = match.group(1)
            current = RunSummary(
                run_id=run_id,
                run_name=None,
                started=ts,
                duration=None,
                status="unknown",
                work_dir=base_dir / "work",
                log_path=log_path,
                source="log",
            )
            runs.append(current)
            continue
        if current:
            if not current.run_name and (m := name_re.search(line)):
                current.run_name = m.group(1)
            if m := work_re.search(line):
                current.work_dir = Path(m.group(1).strip())
            if not current.command and (m := command_re.search(line)):
                current.command = m.group(1)
    if not runs:
        # No explicit sessions in the log; synthesize a single entry based on mtime
        lines = log_path.read_text(errors="replace").splitlines()
        started = parse_log_timestamp(lines[0].split("[")[0].strip()) if lines else None
        runs.append(
            RunSummary(
                run_id=fallback_run_id(base_dir, started),
                run_name=None,
                started=started,
                duration=None,
                status="unknown",
                work_dir=base_dir / "work",
                log_path=log_path,
                source="log",
            )
        )
    return runs


def _is_newer(a: RunSummary, b: RunSummary) -> bool:
    if a.started and b.started:
        return a.started > b.started
    if a.started and not b.started:
        return True
    return False
