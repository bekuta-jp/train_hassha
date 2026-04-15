from __future__ import annotations

from datetime import date, datetime
import unittest

from train_hassha.timetable import current_day_type, get_next_departures, get_station_names


def sample_data() -> dict:
    return {
        "stations": [
            {
                "station_name": "テスト駅",
                "directions": [
                    {
                        "direction_name": "テスト方面",
                        "departures": {
                            "weekday": [
                                {"time": "06:30", "minutes": 390, "symbol": "", "destination": "平日列車"},
                                {"time": "07:00", "minutes": 420, "symbol": "", "destination": "平日列車"},
                            ],
                            "holiday": [
                                {"time": "08:00", "minutes": 480, "symbol": "", "destination": "休日列車"},
                                {"time": "09:00", "minutes": 540, "symbol": "", "destination": "休日列車"},
                            ],
                        },
                    }
                ],
            }
        ]
    }


class TimetableTests(unittest.TestCase):
    def test_after_last_train_uses_next_day_holiday_schedule(self) -> None:
        data = sample_data()
        current = datetime(2026, 4, 17, 23, 59, 0)  # Friday

        departures = get_next_departures(data, "テスト駅", "テスト方面", now=current, count=1)

        self.assertEqual("2026-04-18", departures[0]["date_label"])
        self.assertEqual("holiday", departures[0]["day_type"])
        self.assertEqual("休日列車", departures[0]["destination"])

    def test_after_last_train_uses_next_day_weekday_schedule_after_holiday(self) -> None:
        data = sample_data()
        current = datetime(2026, 5, 6, 23, 59, 0)  # Substitute holiday

        departures = get_next_departures(data, "テスト駅", "テスト方面", now=current, count=1)

        self.assertEqual("2026-05-07", departures[0]["date_label"])
        self.assertEqual("weekday", departures[0]["day_type"])
        self.assertEqual("平日列車", departures[0]["destination"])

    def test_holiday_detection_uses_actual_japanese_holiday(self) -> None:
        self.assertEqual("holiday", current_day_type(date(2026, 2, 23)))

    def test_24xx_departure_rolls_to_next_calendar_day(self) -> None:
        data = {
            "stations": [
                {
                    "station_name": "テスト駅",
                    "directions": [
                        {
                            "direction_name": "テスト方面",
                            "departures": {
                                "weekday": [
                                    {"time": "24:05", "minutes": 1445, "symbol": "", "destination": "深夜列車"},
                                ],
                                "holiday": [],
                            },
                        }
                    ],
                }
            ]
        }

        current = datetime(2026, 4, 17, 23, 59, 0)
        departures = get_next_departures(data, "テスト駅", "テスト方面", now=current, count=1)

        self.assertEqual("2026-04-18", departures[0]["date_label"])
        self.assertTrue(departures[0]["is_next_day"])
        self.assertEqual("weekday", departures[0]["day_type"])
        self.assertEqual("00:05", departures[0]["time"])
        self.assertEqual("24:05", departures[0]["timetable_time"])

    def test_station_names_are_sorted_by_station_code(self) -> None:
        data = {
            "stations": [
                {"station_code": "PL08", "station_name": "中埠頭"},
                {"station_code": "P03", "station_name": "ポートターミナル"},
                {"station_code": "P01", "station_name": "三宮"},
                {"station_code": "P09", "station_name": "神戸空港"},
                {"station_code": "PL07", "station_name": "南公園"},
            ]
        }

        self.assertEqual(
            ["三宮", "ポートターミナル", "神戸空港", "南公園", "中埠頭"],
            get_station_names(data),
        )


if __name__ == "__main__":
    unittest.main()
