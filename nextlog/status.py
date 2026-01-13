from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from .models import RunDetails, RunStatus
from .utils import file_mtime, iter_task_dirs, within_window

LOG = logging.getLogger("nextlog")


def get_status(run: RunDetails) -> RunStatus:
    counts: Dict[str, int] = {"succeeded": 0, "failed": 0, "cached": 0, "running": 0}
    considered = 0
    for task_dir in iter_task_dirs(run.work_dir):
        exit_path = task_dir / ".exitcode"
        ts = file_mtime(exit_path)
        if not within_window(ts, run.started, run.ended):
            continue
        considered += 1
        try:
            exit_code = int(exit_path.read_text().strip())
        except (ValueError, FileNotFoundError):
            continue
        if exit_code == 0:
            counts["succeeded"] += 1
        else:
            counts["failed"] += 1
    # Running tasks: .command.run exists but .exitcode missing
    for run_path in run.work_dir.rglob(".command.run"):
        task_dir = run_path.parent
        exit_path = task_dir / ".exitcode"
        if exit_path.exists():
            continue
        ts = file_mtime(run_path)
        if within_window(ts, run.started, run.ended):
            counts["running"] += 1
            considered += 1
    overall = _overall_status(counts, considered)
    return RunStatus(run_id=run.run_id, overall=overall, counts=counts, details_from="work/.exitcode files")


def _overall_status(counts: Dict[str, int], considered: int) -> str:
    if counts["failed"] > 0:
        return "fail"
    if counts["running"] > 0:
        return "running"
    if considered == 0:
        return "unknown"
    return "success"
