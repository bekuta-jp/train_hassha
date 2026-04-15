from __future__ import annotations

import argparse
from pathlib import Path
import sys

from train_hassha.config import DEFAULT_LINE
from train_hassha.settings import load_app_settings
from train_hassha.storage import load_line_data
from train_hassha.timetable import TimetableFetchError, fetch_and_save_line
from train_hassha.web_export import export_web_site


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="トレイン発車 Web サイト生成")
    parser.add_argument("--refresh-data", action="store_true", help="公式サイトから時刻表を再取得してから Web サイトを生成します。")
    parser.add_argument("--output-dir", default="site", help="出力ディレクトリ")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.refresh_data:
            data, _ = fetch_and_save_line(DEFAULT_LINE)
        else:
            data = load_line_data(DEFAULT_LINE.line_id)
    except FileNotFoundError:
        print("保存済み時刻表がありません。先に main.py --fetch-only を実行するか、--refresh-data を付けてください。")
        return 1
    except TimetableFetchError as exc:
        print(str(exc))
        return 1

    output_dir = Path(args.output_dir).resolve()
    exported = export_web_site(data=data, settings=load_app_settings(), output_dir=output_dir)
    print(f"Web サイトを書き出しました: {exported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
