from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import DEFAULT_LINE, LineConfig
from .holidays import is_japanese_holiday
from .storage import save_line_data


DAY_TYPE_MAP = {"平日": "weekday", "土日祝": "holiday"}
DAY_TYPE_LABELS = {"weekday": "平日", "holiday": "土日祝"}
USER_AGENT = "TrainHassha/1.0 (+https://www.knt-liner.co.jp/)"


class TimetableFetchError(RuntimeError):
    """Raised when official timetable fetching fails."""


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def station_code_sort_key(station_code: str) -> tuple[str, int, str]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", station_code)
    if match is None:
        return (station_code, 0, station_code)

    prefix, number = match.groups()
    return (prefix, int(number), station_code)


def to_japanese_url(url: str) -> str:
    absolute = urljoin("https://www.knt-liner.co.jp/", url)
    parsed = urlparse(absolute)
    path = parsed.path

    if path.startswith("/ja/"):
        return absolute

    if path.startswith(("/en/", "/cn/", "/ko/")):
        path = "/ja/" + path.split("/", 2)[2]
    elif path.startswith("/"):
        path = "/ja" + path
    else:
        path = "/ja/" + path

    return parsed._replace(path=path).geturl()


def parse_destination_legend(raw_text: str) -> dict[str, str]:
    text = normalize_text(raw_text)
    text = text.replace("[ 行先 ]", "").replace("[行先]", "").strip()
    pattern = re.compile(r"(\S+?)\s*：\s*([^：]+?)(?=(?:\s+\S+?\s*：)|$)")

    mapping: dict[str, str] = {}
    for token, destination in pattern.findall(text):
        key = "" if token == "無印" else normalize_text(token)
        mapping[key] = normalize_text(destination)
    return mapping


def current_day_type(target_date: date) -> str:
    if target_date.weekday() >= 5 or is_japanese_holiday(target_date):
        return "holiday"
    return "weekday"


def _download_html(session: requests.Session, url: str) -> str:
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TimetableFetchError(f"公式サイトの取得に失敗しました: {url}") from exc
    return response.text


def _parse_station_catalog(html: str, config: LineConfig) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    route_map = soup.select_one(config.route_selector)
    if route_map is None:
        raise TimetableFetchError("路線ページから駅一覧を見つけられませんでした。")

    stations: list[dict[str, str]] = []
    seen_codes: set[str] = set()

    for item in route_map.select("li"):
        classes = item.get("class", [])
        if any(css_class.endswith("-sp") for css_class in classes):
            continue

        timetable_link = item.select_one("a.v2-routemap-timetable")
        code_node = item.select_one(".v2-routemap-namber")
        station_name_node = item.select_one(".v2-routemap-name p")

        if not timetable_link or not code_node or not station_name_node:
            continue

        station_code = normalize_text(code_node.get_text())
        if station_code in seen_codes:
            continue

        seen_codes.add(station_code)
        stations.append(
            {
                "station_code": station_code,
                "station_name": normalize_text(station_name_node.get_text()),
                "timetable_url": to_japanese_url(timetable_link["href"]),
            }
        )

    if not stations:
        raise TimetableFetchError("路線ページから駅一覧を抽出できませんでした。")

    return sorted(stations, key=lambda station: station_code_sort_key(station["station_code"]))


def _parse_departures(table: Any, destination_map: dict[str, str]) -> list[dict[str, Any]]:
    departures: list[dict[str, Any]] = []

    for row in table.select("tbody > tr"):
        hour_node = row.select_one("th.hour")
        if hour_node is None:
            continue

        hour_text = normalize_text(hour_node.get_text())
        if not hour_text.isdigit():
            continue

        hour = int(hour_text)
        for item in row.select("div.timetablewrap > p.ttdata"):
            symbol_node = item.select_one("span.info01")
            minute_node = item.select_one("span.info02")
            if minute_node is None:
                continue

            minute_text = normalize_text(minute_node.get_text())
            if not minute_text.isdigit():
                continue

            minute = int(minute_text)
            symbol = normalize_text(symbol_node.get_text()) if symbol_node else ""
            departure_minutes = hour * 60 + minute
            departures.append(
                {
                    "time": f"{hour:02d}:{minute:02d}",
                    "minutes": departure_minutes,
                    "symbol": symbol,
                    "destination": destination_map.get(symbol, destination_map.get("", "")),
                }
            )

    return sorted(departures, key=lambda item: item["minutes"])


def _parse_station_page(station_meta: dict[str, str], html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    sections = [section for section in soup.select("section.v2-section[data-tabs]") if section.select_one("table.datatable")]
    if not sections:
        raise TimetableFetchError(f"{station_meta['station_name']} の時刻表を解析できませんでした。")

    revised_match = re.search(r"改正日：\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)", soup.get_text(" ", strip=True))
    revised_date = revised_match.group(1) if revised_match else ""

    directions: list[dict[str, Any]] = []

    for section in sections:
        legend_node = section.select_one(".v2-tab-body > p")
        destination_map = parse_destination_legend(legend_node.get_text(" ", strip=True) if legend_node else "")
        tab_labels = [normalize_text(node.get_text(" ", strip=True)) for node in section.select(".v2-tab-list .v2-tab")]
        tab_contents = section.select(".v2-tab-body > .v2-tab-content")

        day_departures: dict[str, list[dict[str, Any]]] = {}
        direction_name = ""

        for tab_label, tab_content in zip(tab_labels, tab_contents):
            table = tab_content.select_one("table.datatable")
            if table is None:
                continue

            direction_node = table.select_one("p.direction")
            direction_name = normalize_text(direction_node.get_text(" ", strip=True)) if direction_node else direction_name

            day_key = DAY_TYPE_MAP.get(tab_label)
            if day_key is None:
                continue

            day_departures[day_key] = _parse_departures(table, destination_map)

        if direction_name:
            directions.append(
                {
                    "direction_name": direction_name,
                    "departures": day_departures,
                }
            )

    return {
        "station_code": station_meta["station_code"],
        "station_name": station_meta["station_name"],
        "timetable_url": station_meta["timetable_url"],
        "revised_date": revised_date,
        "directions": directions,
    }


def fetch_line_data(config: LineConfig = DEFAULT_LINE) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    index_html = _download_html(session, config.route_page_url)
    station_catalog = _parse_station_catalog(index_html, config)

    stations = []
    for station_meta in station_catalog:
        station_html = _download_html(session, station_meta["timetable_url"])
        stations.append(_parse_station_page(station_meta, station_html))

    return {
        "line_id": config.line_id,
        "line_name": config.line_name,
        "source_url": config.route_page_url,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "stations": sorted(stations, key=lambda station: station_code_sort_key(station["station_code"])),
    }


def fetch_and_save_line(config: LineConfig = DEFAULT_LINE) -> tuple[dict[str, Any], str]:
    data = fetch_line_data(config)
    path = save_line_data(config.line_id, data)
    return data, str(path)


def get_station_names(data: dict[str, Any]) -> list[str]:
    stations = sorted(data.get("stations", []), key=lambda station: station_code_sort_key(station.get("station_code", "")))
    return [station["station_name"] for station in stations]


def get_station(data: dict[str, Any], station_name: str) -> dict[str, Any]:
    for station in data.get("stations", []):
        if station["station_name"] == station_name:
            return station
    raise KeyError(f"駅が見つかりません: {station_name}")


def get_direction_names(data: dict[str, Any], station_name: str) -> list[str]:
    station = get_station(data, station_name)
    return [direction["direction_name"] for direction in station.get("directions", [])]


def get_next_departures(
    data: dict[str, Any],
    station_name: str,
    direction_name: str,
    now: datetime | None = None,
    count: int = 3,
) -> list[dict[str, Any]]:
    current = now or datetime.now()
    station = get_station(data, station_name)

    direction_data = None
    for direction in station.get("directions", []):
        if direction["direction_name"] == direction_name:
            direction_data = direction
            break

    if direction_data is None:
        raise KeyError(f"方面が見つかりません: {direction_name}")

    results: list[dict[str, Any]] = []

    for offset in range(3):
        target_date = current.date() + timedelta(days=offset)
        day_type = current_day_type(target_date)
        departures = direction_data.get("departures", {}).get(day_type, [])

        for departure in departures:
            departure_at = datetime.combine(target_date, datetime.min.time()) + timedelta(minutes=departure["minutes"])
            if departure_at <= current:
                continue

            results.append(
                {
                    **departure,
                    "timetable_time": departure["time"],
                    "time": departure_at.strftime("%H:%M"),
                    "day_type": day_type,
                    "day_type_label": DAY_TYPE_LABELS[day_type],
                    "departure_at": departure_at.isoformat(timespec="minutes"),
                    "minutes_until": max(0, int((departure_at - current).total_seconds() // 60)),
                    "date_label": departure_at.strftime("%Y-%m-%d"),
                    "is_next_day": departure_at.date() > current.date(),
                }
            )

            if len(results) >= count:
                return results

    return results
