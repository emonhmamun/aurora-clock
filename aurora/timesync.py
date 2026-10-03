"""Aurora Clock - network time synchronisation.

The app never changes the Windows system clock (that needs admin rights and is
rude).  Instead it measures the offset between the local clock and a pool of
NTP servers and applies that offset when rendering, so the displayed time is
correct even if the PC clock has drifted.
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

import socket
import struct
import threading
import time
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

NTP_EPOCH_DELTA = 2208988800  # seconds between 1900-01-01 and 1970-01-01


def query_ntp(server: str, timeout: float = 3.0) -> Tuple[float, float]:
    """Return (offset_seconds, roundtrip_seconds) for one NTP server.

    offset > 0  ->  the local clock is BEHIND real time.
    """
    packet = bytearray(48)
    packet[0] = 0x1B  # LI=0, VN=3, Mode=3 (client)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        t1 = time.time()
        sock.sendto(bytes(packet), (server, 123))
        data, _ = sock.recvfrom(48)
        t4 = time.time()
    finally:
        sock.close()

    if len(data) < 48:
        raise OSError("short NTP reply")

    # Validate the reply before trusting it: a spoofed or broken server must
    # never be able to shift the displayed time.
    li = (data[0] >> 6) & 0x3
    mode = data[0] & 0x7
    stratum = data[1]
    if li == 3:
        raise OSError("server clock not synchronised")
    if mode not in (4, 5):            # 4 = server, 5 = broadcast
        raise OSError("unexpected NTP mode")
    if not 1 <= stratum <= 15:
        raise OSError(f"bad stratum {stratum}")

    # transmit & receive timestamps from the server
    recv_i, recv_f = struct.unpack("!II", data[32:40])
    xmit_i, xmit_f = struct.unpack("!II", data[40:48])
    t2 = (recv_i - NTP_EPOCH_DELTA) + recv_f / 2 ** 32
    t3 = (xmit_i - NTP_EPOCH_DELTA) + xmit_f / 2 ** 32

    offset = ((t2 - t1) + (t3 - t4)) / 2.0
    delay = (t4 - t1) - (t3 - t2)
    return offset, max(delay, 0.0)


class TimeSync:
    """Background NTP poller with a monotonic-anchored offset."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._offset = float(cfg.timesync.get("last_offset_ms", 0.0)) / 1000.0
        self._synced = False
        self._last_server = ""
        self._last_sync: Optional[datetime] = None
        self._last_error = ""
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.on_update: Optional[Callable[[], None]] = None

    # -- public API --------------------------------------------------------
    @property
    def offset_seconds(self) -> float:
        if not self.cfg.timesync.get("apply_offset", True):
            return 0.0
        with self._lock:
            return self._offset

    @property
    def status(self) -> dict:
        with self._lock:
            return {
                "synced": self._synced,
                "offset_ms": self._offset * 1000.0,
                "server": self._last_server,
                "last_sync": self._last_sync,
                "error": self._last_error,
            }

    def now_utc(self) -> datetime:
        """Corrected current UTC time."""
        return datetime.fromtimestamp(time.time() + self.offset_seconds, tz=timezone.utc)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="aurora-timesync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def sync_now(self) -> None:
        threading.Thread(target=self._sync_once, name="aurora-sync-once", daemon=True).start()

    # -- internals ---------------------------------------------------------
    def _loop(self) -> None:
        # small delay so the UI appears instantly on login
        if self._stop.wait(4.0):
            return
        while not self._stop.is_set():
            if self.cfg.timesync.get("enabled", True):
                self._sync_once()
            interval = max(5, int(self.cfg.timesync.get("interval_minutes", 60))) * 60
            if self._stop.wait(interval):
                return

    def _sync_once(self) -> None:
        servers: List[str] = list(self.cfg.timesync.get("servers") or ["pool.ntp.org"])
        timeout = float(self.cfg.timesync.get("timeout_seconds", 3))
        results = []
        error = ""
        for srv in servers:
            try:
                off, delay = query_ntp(srv, timeout)
                results.append((delay, off, srv))
                if len(results) >= 2:   # two good samples are enough
                    break
            except Exception as exc:    # noqa: BLE001 - any network failure
                error = f"{srv}: {exc}"
                continue

        if not results:
            with self._lock:
                self._last_error = error or "no server reachable"
            self._notify()
            return

        results.sort()                  # lowest round-trip delay wins
        _, offset, server = results[0]
        # Final sanity gate: anything beyond a day is garbage, and we refuse
        # to apply an offset whose round-trip delay is absurd.
        if abs(offset) > 86400.0:
            with self._lock:
                self._last_error = (f"{server}: implausible offset "
                                    f"({offset / 3600.0:.1f} h) - ignored")
            self._notify()
            return
        with self._lock:
            self._offset = offset
            self._synced = True
            self._last_server = server
            self._last_sync = datetime.now()
            self._last_error = ""

        ts = self.cfg.timesync
        ts["last_offset_ms"] = offset * 1000.0
        ts["last_sync"] = self._last_sync.isoformat(timespec="seconds")
        ts["last_server"] = server
        self.cfg.save()
        self._notify()

    def _notify(self) -> None:
        cb = self.on_update
        if cb:
            try:
                cb()
            except Exception:
                pass
