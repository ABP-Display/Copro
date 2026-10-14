"""Ordinary notice period, metropolitan national holidays and optional Alsace-Moselle."""

from datetime import date, timedelta


def easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    n = h + l - 7 * m + 114
    return date(year, n // 31, n % 31 + 1)


def holidays(year, local=False):
    sunday = easter(year)
    days = {
        date(year, m, d)
        for m, d in [
            (1, 1),
            (5, 1),
            (5, 8),
            (7, 14),
            (8, 15),
            (11, 1),
            (11, 11),
            (12, 25),
        ]
    }
    days.update(sunday + timedelta(days=offset) for offset in [1, 39, 50])
    if local:
        days.update([date(year, 12, 26), sunday - timedelta(days=2)])
    return days


def notice_expires(effective, count=21, local=False):
    end = effective + timedelta(days=count)
    return extend_nonworking(end, local)


def extend_nonworking(end, local=False):
    while end.weekday() >= 5 or end in holidays(end.year, local):
        end += timedelta(days=1)
    return end


def latest_notification(meeting_day, count=21, local=False):
    candidate = meeting_day - timedelta(days=count + 1)
    while notice_expires(candidate, count, local) >= meeting_day:
        candidate -= timedelta(days=1)
    return candidate
