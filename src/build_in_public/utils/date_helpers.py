import re
from datetime import date, datetime, timedelta
from typing import Tuple


def get_week_bounds(week_str: str | None = None, date_str: str | None = None) -> Tuple[date, date]:
    """
    週の開始日（月曜）と終了日（日曜）を返す。
    week_str: '2026-W23' 形式
    date_str: '2026-06-01' 形式（その日を含む週）
    どちらも指定がなければ先週（月曜〜日曜）を返す。
    """
    if week_str:
        match = re.match(r"^(\d{4})-W(\d{2})$", week_str)
        if not match:
            raise ValueError(f"Invalid week format: {week_str}. Expected YYYY-Www.")
        year = int(match.group(1))
        week = int(match.group(2))
        # ISO week date: その週の月曜日
        start = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w").date()
        end = start + timedelta(days=6)
        return start, end

    if date_str:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = d - timedelta(days=d.weekday())
        end = start + timedelta(days=6)
        return start, end

    # デフォルト: 先週
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=6)
    return start, end


def iso_week_str(d: date) -> str:
    """date から '2026-W23' 形式の文字列を返す。"""
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def format_date_range(start: date, end: date) -> str:
    return f"{start.isoformat()} ~ {end.isoformat()}"
