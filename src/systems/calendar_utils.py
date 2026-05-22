from dataclasses import dataclass, asdict
import json
import os
from datetime import date, timedelta

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# Default action duration estimates (minutes) — used by AI for time inference
ACTION_DURATIONS = {
    "吃饭": 30, "睡觉": 480, "洗澡": 20, "上厕所": 5,
    "刷牙": 5, "换衣服": 10, "化妆": 30, "做饭": 45,
    "通勤_短": 20, "通勤_中": 45, "通勤_长": 90,
    "购物": 60, "聊天": 30, "打电话": 15, "看电视": 60,
    "看书": 60, "运动": 60, "散步": 30, "打发时间": 30,
}


@dataclass
class GameDateTime:
    year: int = 2026
    month: int = 8
    day: int = 1
    hour: int = 8
    minute: int = 0

    def __post_init__(self):
        self._normalize()

    def _normalize(self):
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1
        while self.minute < 0:
            self.minute += 60
            self.hour -= 1
        while self.hour < 0:
            self.hour += 24
            self.day -= 1
        # Day/month normalization
        days_in_month = self._days_in_month(self.year, self.month)
        while self.day > days_in_month:
            self.day -= days_in_month
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1
            days_in_month = self._days_in_month(self.year, self.month)
        while self.day < 1:
            self.month -= 1
            if self.month < 1:
                self.month = 12
                self.year -= 1
            self.day += self._days_in_month(self.year, self.month)

    @staticmethod
    def _days_in_month(year: int, month: int) -> int:
        if month == 2:
            return 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28
        return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]

    def advance_minutes(self, n: int):
        self.minute += n
        self._normalize()

    def advance_hours(self, n: int):
        self.hour += n
        self._normalize()

    def advance_days(self, n: int):
        self.day += n
        self._normalize()

    def weekday(self) -> str:
        d = date(self.year, self.month, self.day)
        return WEEKDAYS[d.weekday()]

    def is_weekend(self) -> bool:
        return self.weekday() in ("星期六", "星期日")

    def is_holiday(self, holidays: list[dict] = None) -> bool:
        if holidays is None:
            return False
        for h in holidays:
            if self._match_holiday(h):
                return True
        return False

    def holiday_name(self, holidays: list[dict] = None) -> str | None:
        if holidays is None:
            return None
        for h in holidays:
            if self._match_holiday(h):
                return h.get("name", "节假日")
        return None

    def _match_holiday(self, h: dict) -> bool:
        rule = h.get("rule", "")
        if rule == "fixed":
            return self.month == h.get("month") and self.day == h.get("day")
        if rule == "lunar_spring_festival":
            # Approximate: Spring Festival = Jan 21 - Feb 20 range
            # Use simple estimation based on known years
            estimates = {2026: (2, 17), 2027: (2, 6), 2028: (1, 26),
                         2029: (2, 13), 2030: (2, 3)}
            if self.year in estimates:
                m, d = estimates[self.year]
                return self.month == m and self.day == d
            return False
        return False

    def to_display(self, holidays: list[dict] = None) -> str:
        wd = self.weekday()
        h_name = self.holiday_name(holidays)
        base = f"{self.year}年{self.month}月{self.day}日 {wd} {self.hour:02d}:{self.minute:02d}"
        if h_name:
            base += f"  [{h_name}]"
        return base

    def to_iso(self) -> str:
        return f"{self.year}-{self.month:02d}-{self.day:02d}T{self.hour:02d}:{self.minute:02d}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GameDateTime":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def load_holidays(filepath: str, country: str = None) -> list[dict]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    holidays = data if isinstance(data, list) else data.get("holidays", [])
    if country and country != "ALL":
        holidays = [h for h in holidays if h.get("country", "") == country]
    return holidays


def estimate_action_minutes(action_desc: str) -> int:
    """Estimate how many minutes an action takes based on keyword matching."""
    for keyword, minutes in ACTION_DURATIONS.items():
        if keyword in action_desc:
            return minutes
    return 30  # default
