from __future__ import annotations

import unittest

from train_hassha.line_status import build_line_status_summary, compare_line_statuses, compute_line_data_hash


def sample_line_data(fetched_at: str, fetched_at_utc: str, destination: str = "普通") -> dict:
    return {
        "line_id": "port_liner",
        "line_name": "神戸新交通ポートアイランド線",
        "source_url": "https://example.com",
        "fetched_at": fetched_at,
        "fetched_at_utc": fetched_at_utc,
        "stations": [
            {
                "station_code": "P01",
                "station_name": "三宮",
                "directions": [
                    {
                        "direction_name": "神戸空港方面",
                        "departures": {
                            "weekday": [
                                {"time": "06:00", "minutes": 360, "symbol": "", "destination": destination},
                            ],
                            "holiday": [],
                        },
                    }
                ],
            }
        ],
    }


class LineStatusTests(unittest.TestCase):
    def test_hash_ignores_fetch_timestamps(self) -> None:
        left = sample_line_data("2026-04-15 10:00:00", "2026-04-15T01:00:00+00:00")
        right = sample_line_data("2026-04-16 10:00:00", "2026-04-16T01:00:00+00:00")

        self.assertEqual(compute_line_data_hash(left), compute_line_data_hash(right))

    def test_compare_detects_remote_newer(self) -> None:
        local = build_line_status_summary(sample_line_data("2026-04-15 10:00:00", "2026-04-15T01:00:00+00:00"))
        remote = build_line_status_summary(sample_line_data("2026-04-16 10:00:00", "2026-04-16T01:00:00+00:00", destination="快速"))

        comparison = compare_line_statuses(local, remote)

        self.assertEqual("remote_newer", comparison["relation"])

    def test_compare_detects_same_hash(self) -> None:
        local = build_line_status_summary(sample_line_data("2026-04-15 10:00:00", "2026-04-15T01:00:00+00:00"))
        remote = build_line_status_summary(sample_line_data("2026-04-16 10:00:00", "2026-04-16T01:00:00+00:00"))

        comparison = compare_line_statuses(local, remote)

        self.assertEqual("same", comparison["relation"])


if __name__ == "__main__":
    unittest.main()
