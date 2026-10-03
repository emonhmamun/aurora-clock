"""NTP reply parsing and the anti-spoofing guards."""
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

import struct
import time

import pytest

from aurora import timesync


def _packet(li=0, vn=4, mode=4, stratum=2, t2=None, t3=None):
    now = time.time() + timesync.NTP_EPOCH_DELTA
    t2 = now if t2 is None else t2 + timesync.NTP_EPOCH_DELTA
    t3 = now if t3 is None else t3 + timesync.NTP_EPOCH_DELTA
    data = bytearray(48)
    data[0] = (li << 6) | (vn << 3) | mode
    data[1] = stratum
    struct.pack_into("!II", data, 32, int(t2), 0)
    struct.pack_into("!II", data, 40, int(t3), 0)
    return bytes(data)


class _FakeSocket:
    """Stands in for a UDP socket so the tests never touch the network."""

    def __init__(self, reply):
        self._reply = reply

    def settimeout(self, _t):
        pass

    def sendto(self, _data, _addr):
        pass

    def recvfrom(self, _n):
        return self._reply, ("127.0.0.1", 123)

    def close(self):
        pass


@pytest.fixture
def fake_socket(monkeypatch):
    def install(reply):
        monkeypatch.setattr(timesync.socket, "socket",
                            lambda *a, **k: _FakeSocket(reply))
    return install


def test_valid_reply_is_accepted(fake_socket):
    fake_socket(_packet())
    offset, delay = timesync.query_ntp("example.invalid")
    assert abs(offset) < 5.0
    assert delay >= 0.0


def test_offset_is_measured(fake_socket):
    """A server 90 seconds ahead must produce a ~+90 s offset."""
    future = time.time() + 90
    fake_socket(_packet(t2=future, t3=future))
    offset, _ = timesync.query_ntp("example.invalid")
    assert 85 < offset < 95


def test_unsynchronised_server_is_rejected(fake_socket):
    fake_socket(_packet(li=3))
    with pytest.raises(OSError, match="not synchronised"):
        timesync.query_ntp("example.invalid")


def test_wrong_mode_is_rejected(fake_socket):
    fake_socket(_packet(mode=3))  # 3 = client; a server must never send this
    with pytest.raises(OSError, match="mode"):
        timesync.query_ntp("example.invalid")


@pytest.mark.parametrize("stratum", [0, 16, 200])
def test_bad_stratum_is_rejected(fake_socket, stratum):
    fake_socket(_packet(stratum=stratum))
    with pytest.raises(OSError, match="stratum"):
        timesync.query_ntp("example.invalid")


def test_short_reply_is_rejected(fake_socket):
    fake_socket(b"\x24" * 20)
    with pytest.raises(OSError, match="short"):
        timesync.query_ntp("example.invalid")


def test_implausible_offset_is_never_applied(cfg, monkeypatch):
    """Even a well-formed reply cannot move the clock by more than a day."""
    monkeypatch.setattr(timesync, "query_ntp",
                        lambda srv, timeout=3.0: (99999.0, 0.01))
    ts = timesync.TimeSync(cfg)
    ts._sync_once()
    assert ts.offset_seconds == 0.0
    assert "implausible" in ts.status["error"]


def test_a_sane_offset_is_applied(cfg, monkeypatch):
    monkeypatch.setattr(timesync, "query_ntp",
                        lambda srv, timeout=3.0: (12.5, 0.01))
    ts = timesync.TimeSync(cfg)
    ts._sync_once()
    assert ts.offset_seconds == pytest.approx(12.5)
    assert ts.status["synced"] is True


def test_total_network_failure_is_survivable(cfg, monkeypatch):
    def boom(_srv, timeout=3.0):
        raise OSError("no route to host")
    monkeypatch.setattr(timesync, "query_ntp", boom)
    ts = timesync.TimeSync(cfg)
    ts._sync_once()
    assert ts.offset_seconds == 0.0
    assert ts.status["error"]
    # the app must still be able to tell the time
    assert ts.now_utc() is not None


def test_system_clock_is_never_modified(cfg):
    """Aurora applies the offset at render time - it must not call settime."""
    with open(timesync.__file__, encoding="utf-8") as fh:
        source = fh.read()
    for forbidden in ("SetSystemTime", "SetLocalTime", "clock_settime", "ntpdate"):
        assert forbidden not in source
