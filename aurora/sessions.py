"""Aurora Clock - trading session engine.

Market sessions are defined in their *local* market time and converted with
full DST awareness through zoneinfo, which is the only correct way to do this:
London opens at 08:00 London time all year, but that is 07:00 UTC in summer
and 08:00 UTC in winter.
"""
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

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from .timezones import get_zone

# ---------------------------------------------------------------------------
# Session catalogue
# ---------------------------------------------------------------------------
# days: 0=Monday ... 6=Sunday  (evaluated in the market's own timezone)
WEEKDAYS = [0, 1, 2, 3, 4]


@dataclass
class Session:
    key: str
    name: str
    short: str
    tz: str
    open_t: Tuple[int, int]
    close_t: Tuple[int, int]
    color: str
    group: str = "forex"
    days: List[int] = field(default_factory=lambda: list(WEEKDAYS))


CATALOGUE: Dict[str, Session] = {s.key: s for s in [
    # ---- FX sessions (the classic four) ---------------------------------
    Session("sydney",    "Sydney",        "SYD", "Australia/Sydney",   (8, 0),  (17, 0), "#F2B544"),
    Session("tokyo",     "Tokyo",         "TKY", "Asia/Tokyo",         (9, 0),  (18, 0), "#FF6B6B"),
    Session("london",    "London",        "LDN", "Europe/London",      (8, 0),  (17, 0), "#4D9DE0"),
    Session("newyork",   "New York",      "NY",  "America/New_York",   (8, 0),  (17, 0), "#38E1C6"),
    # ---- extra FX centres -----------------------------------------------
    Session("frankfurt", "Frankfurt",     "FRA", "Europe/Berlin",      (8, 0),  (17, 0), "#B07BE0"),
    Session("hongkong",  "Hong Kong",     "HK",  "Asia/Hong_Kong",     (9, 0),  (18, 0), "#FF9EC4"),
    Session("singapore", "Singapore",     "SGP", "Asia/Singapore",     (9, 0),  (18, 0), "#7ED957"),
    Session("dubai",     "Dubai",         "DXB", "Asia/Dubai",         (8, 0),  (17, 0), "#E0C64D"),
    # ---- equity / derivatives exchanges ---------------------------------
    Session("nyse",      "NYSE",          "NYSE", "America/New_York",  (9, 30), (16, 0), "#5BFF9B", "stocks"),
    Session("nasdaq",    "Nasdaq",        "NDQ",  "America/New_York",  (9, 30), (16, 0), "#5BE8FF", "stocks"),
    Session("lse",       "London SE",     "LSE",  "Europe/London",     (8, 0),  (16, 30), "#8FA6FF", "stocks"),
    Session("tse",       "Tokyo SE",      "TSE",  "Asia/Tokyo",        (9, 0),  (15, 0), "#FFA76B", "stocks"),
    Session("dse",       "Dhaka SE",      "DSE",  "Asia/Dhaka",        (10, 0), (14, 30), "#39D98A", "stocks"),
    Session("nse",       "India NSE",     "NSE",  "Asia/Kolkata",      (9, 15), (15, 30), "#FF8A3D", "stocks"),
    # ---- ICT style kill zones -------------------------------------------
    Session("kz_london", "London KZ",     "LKZ", "America/New_York",   (2, 0),  (5, 0),  "#4D9DE0", "killzone"),
    Session("kz_ny",     "New York KZ",   "NKZ", "America/New_York",   (7, 0),  (10, 0), "#38E1C6", "killzone"),
    Session("kz_asia",   "Asia KZ",       "AKZ", "America/New_York",   (20, 0), (0, 0),  "#F2B544", "killzone"),
]}

DEFAULT_ENABLED = ["sydney", "tokyo", "london", "newyork"]

GROUP_LABELS = {"forex": "Forex sessions", "stocks": "Stock exchanges", "killzone": "Kill zones"}


# ---------------------------------------------------------------------------
# Status computation
# ---------------------------------------------------------------------------

@dataclass
class SessionStatus:
    session: Session
    is_open: bool
    opens_in: Optional[timedelta]       # when closed
    closes_in: Optional[timedelta]      # when open
    next_open: Optional[datetime]
    next_close: Optional[datetime]
    local_open: str                     # "HH:MM" in the *viewer's* timezone
    local_close: str
    progress: float                     # 0..1 through the session when open

    @property
    def countdown(self) -> timedelta:
        return (self.closes_in if self.is_open else self.opens_in) or timedelta(0)

    @property
    def countdown_text(self) -> str:
        return fmt_delta(self.countdown)

    @property
    def state_text(self) -> str:
        return "OPEN" if self.is_open else "CLOSED"


def fmt_delta(td: Optional[timedelta]) -> str:
    if td is None:
        return "--:--"
    total = int(max(0, td.total_seconds()))
    d, rem = divmod(total, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h:02d}h"
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _span_for_day(sess: Session, day: date, zone) -> Tuple[datetime, datetime]:
    """Open/close datetimes (tz-aware) for a given local market day."""
    op = datetime.combine(day, time(*sess.open_t), tzinfo=zone)
    cl_t = time(*sess.close_t)
    cl_day = day if (sess.close_t > sess.open_t) else day + timedelta(days=1)
    cl = datetime.combine(cl_day, cl_t, tzinfo=zone)
    if sess.close_t == (0, 0):          # midnight close = end of this day
        cl = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=zone)
    return op, cl


def status_of(sess: Session, now_utc: datetime, viewer_tz: str = "") -> SessionStatus:
    zone = get_zone(sess.tz) or timezone.utc
    local_now = now_utc.astimezone(zone)

    is_open = False
    cur_open = cur_close = None
    # a session that started yesterday may still be running (overnight spans)
    for offset in (-1, 0):
        day = (local_now + timedelta(days=offset)).date()
        if day.weekday() not in sess.days:
            continue
        op, cl = _span_for_day(sess, day, zone)
        if op <= local_now < cl:
            is_open, cur_open, cur_close = True, op, cl
            break

    # find the next opening
    next_open = None
    for offset in range(0, 9):
        day = (local_now + timedelta(days=offset)).date()
        if day.weekday() not in sess.days:
            continue
        op, _cl = _span_for_day(sess, day, zone)
        if op > local_now:
            next_open = op
            break

    vzone = get_zone(viewer_tz) if viewer_tz else None

    def local_str(dt: datetime) -> str:
        return dt.astimezone(vzone).strftime("%H:%M") if vzone else dt.astimezone().strftime("%H:%M")

    ref_day = local_now.date()
    if ref_day.weekday() not in sess.days:
        ref_day = (next_open or local_now).date()
    ref_open, ref_close = _span_for_day(sess, ref_day, zone)

    progress = 0.0
    if is_open and cur_open and cur_close:
        total = (cur_close - cur_open).total_seconds()
        progress = min(1.0, max(0.0, (local_now - cur_open).total_seconds() / total)) if total else 0.0

    return SessionStatus(
        session=sess,
        is_open=is_open,
        opens_in=(next_open - local_now) if (next_open and not is_open) else None,
        closes_in=(cur_close - local_now) if is_open else None,
        next_open=next_open,
        next_close=cur_close,
        local_open=local_str(ref_open),
        local_close=local_str(ref_close),
        progress=progress,
    )


def statuses(keys: List[str], now_utc: datetime, viewer_tz: str = "") -> List[SessionStatus]:
    out = []
    for k in keys:
        s = CATALOGUE.get(k)
        if s:
            out.append(status_of(s, now_utc, viewer_tz))
    return out


def overlaps(sts: List[SessionStatus]) -> List[str]:
    """Names of the currently overlapping sessions (the high-volatility window)."""
    open_names = [s.session.short for s in sts if s.is_open]
    return open_names if len(open_names) >= 2 else []


def day_spans_utc(sess: Session, ref_utc: datetime) -> List[Tuple[float, float]]:
    """Session spans as (start_hour, end_hour) floats on the UTC day of `ref_utc`.

    Used to draw the 24-hour timeline. Spans crossing midnight are split.
    """
    zone = get_zone(sess.tz) or timezone.utc
    day_start = ref_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    spans: List[Tuple[float, float]] = []
    for offset in (-1, 0, 1):
        local_day = (ref_utc.astimezone(zone) + timedelta(days=offset)).date()
        if local_day.weekday() not in sess.days:
            continue
        op, cl = _span_for_day(sess, local_day, zone)
        op_u, cl_u = op.astimezone(timezone.utc), cl.astimezone(timezone.utc)
        a = max(op_u, day_start)
        b = min(cl_u, day_end)
        if b > a:
            spans.append(((a - day_start).total_seconds() / 3600.0,
                          (b - day_start).total_seconds() / 3600.0))
    return spans
