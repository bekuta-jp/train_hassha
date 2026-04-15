from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from .config import DEFAULT_LINE
from .settings import AppSettings, load_app_settings, project_root, public_settings_dict
from .storage import load_line_data
from .timetable import station_code_sort_key


WEB_SOURCE_DIR = project_root() / "web"
DEFAULT_OUTPUT_DIR = project_root() / "site"


def export_web_site(
    data: dict[str, Any] | None = None,
    settings: AppSettings | None = None,
    output_dir: Path | None = None,
) -> Path:
    line_data = data or load_line_data(DEFAULT_LINE.line_id)
    app_settings = settings or load_app_settings()
    destination = output_dir or DEFAULT_OUTPUT_DIR

    if not WEB_SOURCE_DIR.exists():
        raise FileNotFoundError(f"Web テンプレートが見つかりません: {WEB_SOURCE_DIR}")

    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(WEB_SOURCE_DIR, destination)

    assets_dir = destination / "assets"
    data_dir = assets_dir / "data"
    config_dir = assets_dir / "config"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    exported_data = dict(line_data)
    exported_data["stations"] = sorted(
        line_data.get("stations", []),
        key=lambda station: station_code_sort_key(station.get("station_code", "")),
    )

    (destination / ".nojekyll").write_text("", encoding="utf-8")
    (data_dir / f"{DEFAULT_LINE.line_id}_timetable.json").write_text(
        json.dumps(exported_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (config_dir / "app_settings.json").write_text(
        json.dumps(public_settings_dict(app_settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return destination
