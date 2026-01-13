from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List

from .models import ErrorItem, RunDetails
from .utils import file_mtime, iter_task_dirs, tail_text, within_window

LOG = logging.getLogger("nextlog")


def get_errors(run: RunDetails, limit: int = 5) -> List[ErrorItem]:
    errors: List[ErrorItem] = []
    seen_dirs = set()
    for task_dir in iter_task_dirs(run.work_dir):
        exit_path = task_dir / ".exitcode"
        ts = file_mtime(exit_path)
        if not within_window(ts, run.started, run.ended):
            continue
        exit_code = _read_int(exit_path)
        err_path = task_dir / ".command.err"
        log_path = task_dir / ".command.log"
        script_path = task_dir / ".command.sh"
        process_name = _read_process_name(task_dir / ".command.run")
        err_excerpt = ""
        if err_path.exists():
            err_excerpt = tail_text(err_path, max_lines=30).strip()
        if not err_excerpt and log_path.exists():
            err_excerpt = tail_text(log_path, max_lines=30).strip()
        if exit_code and exit_code != 0:
            errors.append(
                ErrorItem(
                    run_id=run.run_id,
                    work_dir=task_dir,
                    process_name=process_name,
                    exit_code=exit_code,
                    err_path=err_path if err_path.exists() else None,
                    log_path=log_path if log_path.exists() else None,
                    script_path=script_path if script_path.exists() else None,
                    err_excerpt=err_excerpt,
                )
            )
        seen_dirs.add(task_dir)
        if len(errors) >= limit:
            break
    # Fallback: err files without exit codes
    if len(errors) < limit:
        for err_path in run.work_dir.rglob(".command.err"):
            task_dir = err_path.parent
            if task_dir in seen_dirs:
                continue
            ts = file_mtime(err_path)
            if not within_window(ts, run.started, run.ended):
                continue
            log_path = task_dir / ".command.log"
            script_path = task_dir / ".command.sh"
            process_name = _read_process_name(task_dir / ".command.run")
            err_excerpt = tail_text(err_path, max_lines=30).strip()
            errors.append(
                ErrorItem(
                    run_id=run.run_id,
                    work_dir=task_dir,
                    process_name=process_name,
                    exit_code=None,
                    err_path=err_path,
                    log_path=log_path if log_path.exists() else None,
                    script_path=script_path if script_path.exists() else None,
                    err_excerpt=err_excerpt,
                    note="Missing .exitcode; showing .command.err",
                )
            )
            if len(errors) >= limit:
                break
    return errors


def open_in_pager(paths: List[Path]) -> None:
    pager = shutil.which("less") or shutil.which("more")
    if not pager:
        LOG.warning("No pager available on PATH")
        return
    for path in paths:
        if not path.exists():
            continue
        subprocess.run([pager, str(path)])


def _read_process_name(run_path: Path) -> str | None:
    try:
        for line in run_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("### name:"):
                # Extract text between quotes if present
                start = line.find("'")
                end = line.rfind("'")
                if start != -1 and end != -1 and end > start:
                    return line[start + 1 : end]
                return line.split(":", maxsplit=1)[-1].strip()
    except FileNotFoundError:
        return None
    return None


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None
