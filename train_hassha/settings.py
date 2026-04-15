from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any


@dataclass(frozen=True)
class AppSettings:
    default_station_name: str = "三宮"
    default_direction_name: str = "神戸空港・北埠頭方面行"
    web_site_title: str = "トレイン発車 Web"
    web_site_description: str = "神戸新交通ポートアイランド線の保存済み時刻表から、先発・次発・次々発をブラウザで表示します。"
    timezone: str = "Asia/Tokyo"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_settings_path() -> Path:
    return project_root() / "config" / "app_settings.json"


def candidate_settings_paths() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.getenv("TRAIN_HASSHA_SETTINGS_FILE")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "app_settings.json")
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(Path(bundle_dir) / "app_settings.json")

    candidates.append(default_settings_path())
    return candidates


def load_app_settings() -> AppSettings:
    data: dict[str, Any] = {}

    for path in candidate_settings_paths():
        if not path.exists():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(loaded, dict):
            data = loaded
            break

    defaults = asdict(AppSettings())
    defaults.update({key: value for key, value in data.items() if key in defaults and isinstance(value, str)})
    return AppSettings(**defaults)


def public_settings_dict(settings: AppSettings | None = None) -> dict[str, str]:
    loaded = settings or load_app_settings()
    return asdict(loaded)
