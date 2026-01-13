from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class RunSummary:
    run_id: str
    run_name: Optional[str]
    started: Optional[datetime]
    duration: Optional[timedelta]
    status: str
    work_dir: Path
    log_path: Path
    source: str
    command: Optional[str] = None


@dataclass
class RunDetails:
    run_id: str
    run_name: Optional[str]
    started: Optional[datetime]
    ended: Optional[datetime]
    duration: Optional[timedelta]
    status: str
    work_dir: Path
    log_path: Path
    command: Optional[str]
    source: str


@dataclass
class RunStatus:
    run_id: str
    overall: str
    counts: dict
    details_from: str


@dataclass
class ErrorItem:
    run_id: str
    work_dir: Path
    process_name: Optional[str]
    exit_code: Optional[int]
    err_path: Optional[Path]
    log_path: Optional[Path]
    script_path: Optional[Path]
    err_excerpt: str
    note: Optional[str] = None
