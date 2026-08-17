"""Deterministic Chinese date and time parsing for the SideQuest Agent."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import re
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")
WEEKDAY_NAMES = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}


@dataclass(frozen=True)
class ParsedDateTime:
    """Normalized date/time window extracted from one natural-language query."""

    start_date: date
    end_date: date
    start_time: time | None = None
    end_time: time | None = None
    label: str = ""
    resolution: str = "exact"


def _parse_clock(hour: int, minute: int, meridiem: str | None) -> time:
    if meridiem in {"下午", "晚上", "傍晚", "今晚"} and hour < 12:
        hour += 12
    if meridiem == "中午" and hour < 11:
        hour += 12
    return time(hour=hour % 24, minute=minute)


def _parse_date_from_calendar(query: str, today: date) -> date | None:
    full_date = re.search(r"(20\d{2})\s*[年/-]\s*(\d{1,2})\s*[月/-]\s*(\d{1,2})\s*(?:日)?", query)
    if full_date:
        try:
            return date(int(full_date.group(1)), int(full_date.group(2)), int(full_date.group(3)))
        except ValueError:
            return None

    month_day = re.search(r"(?<!\d)(\d{1,2})\s*[月/]\s*(\d{1,2})\s*(?:日)?", query)
    if month_day:
        month, day = int(month_day.group(1)), int(month_day.group(2))
        try:
            candidate = date(today.year, month, day)
        except ValueError:
            return None
        if candidate < today and month <= today.month:
            candidate = date(today.year + 1, month, day)
        return candidate

    if any(token in query for token in ("大後天", "後天")):
        return today + timedelta(days=2)
    if any(token in query for token in ("明天", "明日")):
        return today + timedelta(days=1)
    if any(token in query for token in ("今天", "今日")):
        return today

    weekday = re.search(r"(?:下週|下周|下星期|下禮拜)?(?:週|周|星期|禮拜)([一二三四五六日天])", query)
    if weekday:
        target = WEEKDAY_NAMES[weekday.group(1)]
        days_ahead = (target - today.weekday()) % 7
        if days_ahead == 0 or any(token in query for token in ("下週", "下周", "下星期", "下禮拜")):
            days_ahead = days_ahead or 7
        return today + timedelta(days=days_ahead)

    if any(token in query for token in ("本週末", "這週末", "這周末")):
        return today + timedelta(days=(5 - today.weekday()) % 7)
    return None


def _parse_time_window(query: str) -> tuple[time | None, time | None, str]:
    clock_range = re.search(
        r"(?:(上午|早上|中午|下午|傍晚|晚上|今晚)\s*)?(\d{1,2})(?::|：|點|時)(\d{1,2})?\s*(?:到|至|[-~～])\s*"
        r"(?:(上午|早上|中午|下午|傍晚|晚上|今晚)\s*)?(\d{1,2})(?::|：|點|時)(\d{1,2})?",
        query,
    )
    if clock_range:
        first_meridiem, first_hour, first_minute, second_meridiem, second_hour, second_minute = clock_range.groups()
        start = _parse_clock(int(first_hour), int(first_minute or 0), first_meridiem or second_meridiem)
        end = _parse_clock(int(second_hour), int(second_minute or 0), second_meridiem or first_meridiem)
        return start, end, f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"

    single_clock = re.search(
        r"(?:(上午|早上|中午|下午|傍晚|晚上|今晚)\s*)?(\d{1,2})(?::|：|點|時)(\d{1,2})?",
        query,
    )
    if single_clock:
        meridiem, hour, minute = single_clock.groups()
        start = _parse_clock(int(hour), int(minute or 0), meridiem)
        end = (datetime.combine(date.today(), start) + timedelta(hours=2)).time()
        return start, end, f"{start.strftime('%H:%M')} 起"

    for tokens, start, end, label in (
        (("早上", "上午"), time(9), time(12), "上午"),
        (("中午",), time(11), time(14), "中午"),
        (("下午",), time(12), time(18), "下午"),
        (("傍晚",), time(16), time(20), "傍晚"),
        (("晚上", "今晚"), time(18), time(23, 59), "晚上"),
    ):
        if any(token in query for token in tokens):
            return start, end, label
    return None, None, ""


def parse_natural_date_time(query: str, now: datetime | None = None) -> ParsedDateTime | None:
    """Parse explicit or relative Chinese date/time phrases using Taipei time."""
    now_taipei = (now or datetime.now(TAIPEI_TZ)).astimezone(TAIPEI_TZ)
    today = now_taipei.date()
    selected_date = _parse_date_from_calendar(query, today)
    if selected_date is None:
        return None

    start_time, end_time, time_label = _parse_time_window(query)
    label = f"{selected_date.isoformat()} {time_label}".strip()
    has_explicit_date = bool(re.search(r"20\d{2}|\d{1,2}\s*[月/]\s*\d{1,2}", query))
    return ParsedDateTime(
        start_date=selected_date,
        end_date=selected_date,
        start_time=start_time,
        end_time=end_time,
        label=label,
        resolution="exact" if has_explicit_date else "relative",
    )
