from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests


VOLATILE_DATA_KEYS = {"fetched_at", "fetched_at_utc", "data_hash"}


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _canonicalize(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_DATA_KEYS
        }
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value


def compute_line_data_hash(data: dict[str, Any]) -> str:
    canonical = _canonicalize(data)
    serialized = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def parse_timestamp(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None

    normalized = raw_value.strip()
    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(normalized, fmt)
                break
            except ValueError:
                continue
        else:
            return None

    if parsed.tzinfo is None:
        local_timezone = datetime.now().astimezone().tzinfo or timezone.utc
        parsed = parsed.replace(tzinfo=local_timezone)
    return parsed.astimezone(timezone.utc)


def best_fetched_at_utc(data: dict[str, Any]) -> str:
    explicit = parse_timestamp(data.get("timetable_fetched_at_utc") or data.get("fetched_at_utc"))
    if explicit is not None:
        return explicit.isoformat(timespec="seconds")

    fallback = parse_timestamp(data.get("timetable_fetched_at") or data.get("fetched_at"))
    if fallback is not None:
        return fallback.isoformat(timespec="seconds")

    return ""


def build_line_status_summary(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "line_id": data.get("line_id", ""),
        "line_name": data.get("line_name", ""),
        "source_url": data.get("source_url", ""),
        "station_count": len(data.get("stations", [])),
        "data_hash": data.get("data_hash") or compute_line_data_hash(data),
        "timetable_fetched_at": data.get("fetched_at", ""),
        "timetable_fetched_at_utc": best_fetched_at_utc(data),
    }


def status_file_name(line_id: str) -> str:
    return f"{line_id}_status.json"


def data_file_name(line_id: str) -> str:
    return f"{line_id}_timetable.json"


def build_published_status_url(published_site_url: str, line_id: str) -> str:
    base = published_site_url.rstrip("/") + "/"
    return urljoin(base, f"assets/data/{status_file_name(line_id)}")


def build_published_data_url(published_site_url: str, line_id: str) -> str:
    base = published_site_url.rstrip("/") + "/"
    return urljoin(base, f"assets/data/{data_file_name(line_id)}")


def with_cache_buster(url: str) -> str:
    split = urlsplit(url)
    query = parse_qsl(split.query, keep_blank_values=True)
    query.append(("_ts", str(int(time.time()))))
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def fetch_published_line_status(url: str, timeout: int = 15) -> dict[str, Any]:
    response = requests.get(with_cache_buster(url), timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("公開版ステータスの形式が不正です。")
    return payload


def build_published_line_status(data: dict[str, Any], published_site_url: str) -> dict[str, Any]:
    summary = build_line_status_summary(data)
    published_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        **summary,
        "published_at_utc": published_at,
        "status_url": build_published_status_url(published_site_url, summary["line_id"]),
        "data_url": build_published_data_url(published_site_url, summary["line_id"]),
    }


def compare_line_statuses(local_status: dict[str, Any] | None, remote_status: dict[str, Any] | None) -> dict[str, Any]:
    local = local_status or {}
    remote = remote_status or {}
    local_hash = str(local.get("data_hash") or "")
    remote_hash = str(remote.get("data_hash") or "")
    local_timestamp = parse_timestamp(local.get("timetable_fetched_at_utc") or local.get("timetable_fetched_at"))
    remote_timestamp = parse_timestamp(remote.get("timetable_fetched_at_utc") or remote.get("timetable_fetched_at"))

    relation = "different"
    if not remote_hash:
        relation = "remote_unavailable"
    elif not local_hash:
        relation = "local_missing"
    elif local_hash == remote_hash:
        relation = "same"
    elif local_timestamp and remote_timestamp:
        if local_timestamp > remote_timestamp:
            relation = "local_newer"
        elif remote_timestamp > local_timestamp:
            relation = "remote_newer"

    return {
        "relation": relation,
        "same_hash": relation == "same",
        "local_hash": local_hash,
        "remote_hash": remote_hash,
        "local_fetched_at_utc": local_timestamp.isoformat(timespec="seconds") if local_timestamp else "",
        "remote_fetched_at_utc": remote_timestamp.isoformat(timespec="seconds") if remote_timestamp else "",
        "local_status": local_status,
        "remote_status": remote_status,
    }
