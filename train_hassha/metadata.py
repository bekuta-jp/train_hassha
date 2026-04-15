from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any

from .settings import project_root


@dataclass(frozen=True)
class ChangelogEntry:
    version: str
    date: str
    title: str
    items: tuple[str, ...] = ()


@dataclass(frozen=True)
class AppMetadata:
    version: str = "1.1"
    changelog: tuple[ChangelogEntry, ...] = field(default_factory=tuple)


def default_metadata_path() -> Path:
    return project_root() / "config" / "app_metadata.json"


def candidate_metadata_paths() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.getenv("TRAIN_HASSHA_METADATA_FILE")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "app_metadata.json")
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(Path(bundle_dir) / "app_metadata.json")

    candidates.append(default_metadata_path())
    return candidates


def default_app_metadata() -> AppMetadata:
    return AppMetadata(
        version="1.1",
        changelog=(
            ChangelogEntry(
                version="1.1",
                date="2026-04-15",
                title="公開版との更新連携を追加",
                items=(
                    "ローカル版が公開中の Web 版ダイヤと比較して更新案内を出すように改善",
                    "Web 版が公式サイトを日次確認して差分があるときだけ自動更新できるように準備",
                    "公開用のダイヤハッシュと更新状態 JSON を追加",
                ),
            ),
            ChangelogEntry(
                version="1.0",
                date="2026-04-15",
                title="初回リリース",
                items=(
                    "神戸新交通ポートアイランド線の発車案内を実装",
                    "公式サイトからの時刻表取得と保存に対応",
                    "デスクトップ版と Web 公開版を追加",
                    "現在時刻の大表示、5分以内の列車の赤点滅、デバッグ時刻変更に対応",
                    "駅番号順の駅選択とデフォルト表示設定に対応",
                ),
            ),
        ),
    )


def load_app_metadata() -> AppMetadata:
    loaded_data: dict[str, Any] = {}

    for path in candidate_metadata_paths():
        if not path.exists():
            continue
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(candidate, dict):
            loaded_data = candidate
            break

    defaults = default_app_metadata()
    version = loaded_data.get("version")
    if not isinstance(version, str) or not version.strip():
        version = defaults.version

    raw_changelog = loaded_data.get("changelog")
    changelog_entries: list[ChangelogEntry] = []
    if isinstance(raw_changelog, list):
        for raw_entry in raw_changelog:
            if not isinstance(raw_entry, dict):
                continue
            entry_version = raw_entry.get("version")
            entry_date = raw_entry.get("date")
            entry_title = raw_entry.get("title")
            raw_items = raw_entry.get("items")
            if not all(isinstance(value, str) and value.strip() for value in (entry_version, entry_date, entry_title)):
                continue
            items = tuple(item for item in raw_items if isinstance(item, str) and item.strip()) if isinstance(raw_items, list) else ()
            changelog_entries.append(
                ChangelogEntry(
                    version=entry_version,
                    date=entry_date,
                    title=entry_title,
                    items=items,
                )
            )

    if not changelog_entries:
        changelog_entries = list(defaults.changelog)

    return AppMetadata(version=version, changelog=tuple(changelog_entries))


def public_metadata_dict(metadata: AppMetadata | None = None) -> dict[str, Any]:
    loaded = metadata or load_app_metadata()
    return {
        "version": loaded.version,
        "changelog": [
            {
                "version": entry.version,
                "date": entry.date,
                "title": entry.title,
                "items": list(entry.items),
            }
            for entry in loaded.changelog
        ],
    }
