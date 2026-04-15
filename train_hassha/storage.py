from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


APP_DIR_NAME = "TrainHassha"


def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_DIR_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME

    base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "train-hassha"


def get_line_data_path(line_id: str) -> Path:
    return get_app_data_dir() / f"{line_id}_timetable.json"


def save_line_data(line_id: str, data: dict[str, Any]) -> Path:
    path = get_line_data_path(line_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_line_data(line_id: str) -> dict[str, Any]:
    path = get_line_data_path(line_id)
    return json.loads(path.read_text(encoding="utf-8"))
