from __future__ import annotations

from datetime import date, timedelta


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    first_day = date(year, month, 1)
    delta = (weekday - first_day.weekday()) % 7
    return first_day + timedelta(days=delta + (nth - 1) * 7)


def _vernal_equinox_day(year: int) -> date:
    day = int(20.8431 + 0.242194 * (year - 1980) - ((year - 1980) // 4))
    return date(year, 3, day)


def _autumnal_equinox_day(year: int) -> date:
    day = int(23.2488 + 0.242194 * (year - 1980) - ((year - 1980) // 4))
    return date(year, 9, day)


def _base_holidays(year: int) -> set[date]:
    holidays: set[date] = {
        date(year, 1, 1),
        _nth_weekday(year, 1, 0, 2),
        date(year, 2, 11),
        _vernal_equinox_day(year),
        date(year, 4, 29),
        date(year, 5, 3),
        date(year, 5, 5),
        _autumnal_equinox_day(year),
        date(year, 11, 3),
        date(year, 11, 23),
    }

    if year >= 2020:
        holidays.add(date(year, 2, 23))

    if year == 2020:
        holidays.add(date(2020, 7, 23))
        holidays.add(date(2020, 8, 10))
        holidays.add(date(2020, 7, 24))
    elif year == 2021:
        holidays.add(date(2021, 7, 22))
        holidays.add(date(2021, 8, 8))
        holidays.add(date(2021, 7, 23))
    else:
        holidays.add(_nth_weekday(year, 7, 0, 3))
        holidays.add(_nth_weekday(year, 10, 0, 2))
        if year >= 2016:
            holidays.add(date(year, 8, 11))

    holidays.add(_nth_weekday(year, 9, 0, 3))
    return holidays


def japanese_holidays(year: int) -> set[date]:
    holidays = set(_base_holidays(year))

    for month in range(1, 13):
        current = date(year, month, 1)
        while current.month == month:
            if (
                current.weekday() < 5
                and current not in holidays
                and current - timedelta(days=1) in holidays
                and current + timedelta(days=1) in holidays
            ):
                holidays.add(current)
            current += timedelta(days=1)

    for holiday in sorted(list(holidays)):
        if holiday.weekday() != 6:
            continue

        substitute = holiday + timedelta(days=1)
        while substitute in holidays:
            substitute += timedelta(days=1)
        holidays.add(substitute)

    return holidays


def is_japanese_holiday(target_date: date) -> bool:
    return target_date in japanese_holidays(target_date.year)
