import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


def _archive_path(archive_dir: str | Path, start: date) -> Path:
    return Path(archive_dir) / f"{start.isoformat()}.json"


def load_week_data(archive_dir: str | Path, start: date) -> Optional[Dict[str, Any]]:
    path = _archive_path(archive_dir, start)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_week_data(archive_dir: str | Path, start: date, data: Dict[str, Any]) -> None:
    path = _archive_path(archive_dir, start)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _github_archive_path(archive_dir: str | Path, date_str: str) -> Path:
    return Path(archive_dir) / f"github-{date_str}.json"


def save_github_data(archive_dir: str | Path, date_str: str, data: Dict[str, Any]) -> None:
    path = _github_archive_path(archive_dir, date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_github_data(archive_dir: str | Path, date_str: str) -> Optional[Dict[str, Any]]:
    path = _github_archive_path(archive_dir, date_str)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
