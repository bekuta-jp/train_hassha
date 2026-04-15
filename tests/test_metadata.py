from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from train_hassha.line_status import status_file_name
from train_hassha.metadata import load_app_metadata
from train_hassha.settings import load_app_settings
from train_hassha.web_export import export_web_site


def sample_line_data() -> dict:
    return {
        "line_id": "port_liner",
        "line_name": "神戸新交通ポートアイランド線",
        "fetched_at": "2026-04-15 12:00:00",
        "fetched_at_utc": "2026-04-15T03:00:00+00:00",
        "stations": [
            {
                "station_code": "P01",
                "station_name": "三宮",
                "directions": [
                    {
                        "direction_name": "神戸空港・北埠頭方面行",
                        "departures": {"weekday": [], "holiday": []},
                    }
                ],
            }
        ],
    }


class MetadataTests(unittest.TestCase):
    def test_load_app_metadata_returns_version_and_changelog(self) -> None:
        metadata = load_app_metadata()

        self.assertEqual("1.1", metadata.version)
        self.assertTrue(metadata.changelog)
        self.assertEqual("1.1", metadata.changelog[0].version)

    def test_export_web_site_writes_metadata_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "site"
            export_web_site(
                data=sample_line_data(),
                settings=load_app_settings(),
                metadata=load_app_metadata(),
                output_dir=output_dir,
            )

            metadata_path = output_dir / "assets" / "config" / "app_metadata.json"
            self.assertTrue(metadata_path.exists())

            exported = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual("1.1", exported["version"])
            self.assertEqual("1.1", exported["changelog"][0]["version"])

            status_path = output_dir / "assets" / "data" / status_file_name("port_liner")
            self.assertTrue(status_path.exists())


if __name__ == "__main__":
    unittest.main()
