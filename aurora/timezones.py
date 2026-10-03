"""Aurora Clock - timezone helpers."""
# Aurora Clock - a lightweight desktop clock overlay for Windows.
# Copyright (C) 2026 Emon Hasan Mamun
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

try:
    from zoneinfo import ZoneInfo, available_timezones
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None  # type: ignore

    def available_timezones():  # type: ignore
        return set()

# A short, friendly list shown first in the picker.
POPULAR = [
    "Asia/Dhaka", "Asia/Kolkata", "Asia/Karachi", "Asia/Dubai", "Asia/Riyadh",
    "Asia/Singapore", "Asia/Tokyo", "Asia/Shanghai", "Asia/Seoul", "Asia/Jakarta",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow", "Europe/Istanbul",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Sao_Paulo", "America/Toronto", "Australia/Sydney", "Pacific/Auckland", "UTC",
]


def all_timezones() -> List[str]:
    try:
        return sorted(available_timezones())
    except Exception:
        return list(POPULAR)


def get_zone(name: str):
    if not name or ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None


def localize(utc_dt: datetime, tz_name: str) -> datetime:
    """Convert a corrected UTC datetime to the requested zone (or local)."""
    if not tz_name:
        return utc_dt.astimezone()
    zone = get_zone(tz_name)
    return utc_dt.astimezone(zone) if zone else utc_dt.astimezone()


def city_label(tz_name: str) -> str:
    if not tz_name:
        return "Local"
    return tz_name.split("/")[-1].replace("_", " ")


def offset_label(tz_name: str, ref: Optional[datetime] = None) -> str:
    ref = ref or datetime.now(timezone.utc)
    dt = localize(ref, tz_name)
    off = dt.utcoffset()
    if off is None:
        return ""
    mins = int(off.total_seconds() // 60)
    sign = "+" if mins >= 0 else "-"
    mins = abs(mins)
    return f"UTC{sign}{mins // 60:02d}:{mins % 60:02d}"
