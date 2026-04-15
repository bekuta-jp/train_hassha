from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from train_hassha.app import launch_app
from train_hassha.config import DEFAULT_LINE
from train_hassha.metadata import load_app_metadata
from train_hassha.storage import get_line_data_path, load_line_data
from train_hassha.timetable import TimetableFetchError, fetch_and_save_line, get_direction_names, get_next_departures, get_station_names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="トレイン発車")
    parser.add_argument("--version", action="version", version=f"トレイン発車 ver{load_app_metadata().version}")
    parser.add_argument("--fetch-only", action="store_true", help="公式サイトから時刻表を取得して保存します。")
    parser.add_argument("--list-stations", action="store_true", help="保存済み時刻表の駅一覧を表示します。")
    parser.add_argument("--list-directions", metavar="STATION", help="指定駅の方面一覧を表示します。")
    parser.add_argument("--station", help="次の列車を表示したい駅名")
    parser.add_argument("--direction", help="次の列車を表示したい方面")
    parser.add_argument("--now", help="デバッグ用の基準時刻。形式: YYYY-MM-DD HH:MM[:SS]")
    parser.add_argument("--count", type=int, default=3, help="表示する本数")
    parser.add_argument("--show-data-path", action="store_true", help="保存先パスを表示します。")
    return parser


def parse_reference_now(raw: str | None) -> datetime | None:
    if not raw:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d %H:%M":
                return parsed.replace(second=0)
            return parsed
        except ValueError:
            continue
    raise ValueError("時刻の形式が不正です。YYYY-MM-DD HH:MM[:SS] で指定してください。")


def print_next_departures(station: str, direction: str, count: int, reference_now: datetime | None = None) -> int:
    data = load_line_data(DEFAULT_LINE.line_id)
    departures = get_next_departures(data, station, direction, now=reference_now, count=count)

    print(f"駅名: {station}")
    print(f"方面: {direction}")
    if reference_now is not None:
        print(f"基準時刻: {reference_now.strftime('%Y-%m-%d %H:%M:%S')}")

    labels = ["先発", "次発", "次々発"]
    for index, departure in enumerate(departures):
        label = labels[index] if index < len(labels) else f"{index + 1}本目"
        when_label = "翌日" if departure["is_next_day"] else "当日"
        timetable_note = ""
        if departure["timetable_time"] != departure["time"]:
            timetable_note = f" / 時刻表表記 {departure['timetable_time']}"
        print(
            f"{label}: {departure['date_label']} {departure['time']} {departure['destination']} "
            f"({when_label} {departure['day_type_label']}ダイヤ / あと {departure['minutes_until']} 分{timetable_note})"
        )

    if not departures:
        print("該当する列車は見つかりませんでした。")

    return 0


def load_saved_data_or_report() -> dict | None:
    try:
        return load_line_data(DEFAULT_LINE.line_id)
    except FileNotFoundError:
        print("保存済み時刻表がありません。先に --fetch-only か GUI の取得ボタンで保存してください。")
        return None


def gui_preflight_error() -> str | None:
    if sys.platform == "darwin" and os.getenv("CODEX_CI") == "1":
        return "Codex 内の macOS サンドボックスでは Tkinter GUI を起動できません。Terminal または Finder から run_unix.sh を実行してください。"

    if sys.platform.startswith("linux") and not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")):
        return "GUI 表示環境が見つかりません。DISPLAY または WAYLAND_DISPLAY を確認してください。"

    return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.show_data_path:
        print(get_line_data_path(DEFAULT_LINE.line_id))
        return 0

    if args.fetch_only:
        try:
            data, path = fetch_and_save_line(DEFAULT_LINE)
        except TimetableFetchError as exc:
            print(str(exc))
            return 1
        print(f"保存先: {path}")
        print(f"取得駅数: {len(data.get('stations', []))}")
        return 0

    if args.list_stations:
        data = load_saved_data_or_report()
        if data is None:
            return 1
        for station_name in get_station_names(data):
            print(station_name)
        return 0

    if args.list_directions:
        data = load_saved_data_or_report()
        if data is None:
            return 1
        try:
            for direction_name in get_direction_names(data, args.list_directions):
                print(direction_name)
        except KeyError as exc:
            print(str(exc))
            return 1
        return 0

    if args.station or args.direction:
        if not args.station or not args.direction:
            parser.error("--station と --direction は一緒に指定してください。")
        try:
            reference_now = parse_reference_now(args.now)
            return print_next_departures(args.station, args.direction, args.count, reference_now=reference_now)
        except FileNotFoundError:
            print("保存済み時刻表がありません。先に --fetch-only か GUI の取得ボタンで保存してください。")
            return 1
        except ValueError as exc:
            print(str(exc))
            return 1
        except KeyError as exc:
            print(str(exc))
            return 1

    preflight_error = gui_preflight_error()
    if preflight_error:
        print(preflight_error)
        return 1

    launch_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
