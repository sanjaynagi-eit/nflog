from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

LOG = logging.getLogger("nextlog")


def parse_history_timestamp(raw: str) -> Optional[datetime]:
    raw = raw.strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        LOG.debug("Unable to parse history timestamp %s", raw)
        return None


def parse_log_timestamp(raw: str) -> Optional[datetime]:
    """
    Parse timestamps like 'Jan-13 16:16:24.765'. Year is assumed to be current year.
    """
    parts = raw.split()
    if not parts:
        return None
    raw_ts = parts[0]
    # raw_ts may contain month-day or month-day.millis; keep the time portion if present
    try:
        if len(parts) >= 2:
            raw_ts = f"{parts[0]} {parts[1]}"
        return datetime.strptime(f"{datetime.now().year} {raw_ts}", "%Y %b-%d %H:%M:%S.%f")
    except ValueError:
        try:
            return datetime.strptime(f"{datetime.now().year} {raw_ts}", "%Y %b-%d %H:%M:%S")
        except ValueError:
            LOG.debug("Unable to parse log timestamp %s", raw)
            return None


def parse_duration(raw: str) -> Optional[timedelta]:
    raw = (raw or "").strip()
    if not raw or raw == "-":
        return None
    seconds = 0
    minute_match = re.search(r"(\d+)m", raw)
    if minute_match:
        seconds += int(minute_match.group(1)) * 60
    second_match = re.search(r"(\d+(?:\.\d+)?)s", raw)
    if second_match:
        seconds += float(second_match.group(1))
    if seconds == 0:
        try:
            seconds = float(raw)
        except ValueError:
            return None
    return timedelta(seconds=seconds)


def map_status(raw: str) -> str:
    raw = (raw or "").strip().upper()
    if raw == "OK":
        return "success"
    if raw == "ERR":
        return "fail"
    if raw in {"RUNNING", "ACTIVE"}:
        return "running"
    return "unknown"


def fallback_run_id(base_dir: Path, started: Optional[datetime]) -> str:
    stamp = started.isoformat() if started else datetime.now().isoformat()
    base = hashlib.sha1(str(base_dir).encode()).hexdigest()[:8]
    return f"{stamp}-{base}"


def iter_task_dirs(work_dir: Path) -> Iterable[Path]:
    for exit_path in work_dir.rglob(".exitcode"):
        yield exit_path.parent


def file_mtime(path: Path) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except FileNotFoundError:
        return None


def within_window(ts: Optional[datetime], start: Optional[datetime], end: Optional[datetime]) -> bool:
    if ts is None:
        return start is None and end is None
    lower_bound = start - timedelta(minutes=5) if start else None
    upper_bound = end + timedelta(minutes=5) if end else None
    if lower_bound and ts < lower_bound:
        return False
    if upper_bound and ts > upper_bound:
        return False
    return True


def tail_text(path: Path, max_lines: int = 20) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def safe_read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        LOG.debug("Failed reading %s: %s", path, exc)
        return ""


def maybe_set_mtime(path: Path, target: datetime) -> None:
    ts = target.timestamp()
    os.utime(path, (ts, ts))
