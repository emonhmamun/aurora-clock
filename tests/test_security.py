"""Static safety guarantees that must hold for every future commit.

These tests are deliberately paranoid: they are the contract that lets users
trust a clock that starts automatically with Windows.
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

import ast
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = sorted(list((ROOT / "aurora").glob("*.py")) + [ROOT / "main.py"])


def _tree(path: pathlib.Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_everything_parses():
    for path in SOURCES:
        _tree(path)


def test_no_dynamic_code_execution():
    """No eval/exec/compile anywhere: there is no way to inject code."""
    banned = {"eval", "exec", "compile", "__import__"}
    for path in SOURCES:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned, f"{path.name}: {node.func.id}()"


def test_no_shell_or_process_spawning():
    banned_modules = {"subprocess", "pty", "popen2", "commands"}
    for path in SOURCES:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned_modules, path.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned_modules, path.name
        text = path.read_text(encoding="utf-8")
        for needle in ("os.system(", "os.popen(", "shell=True"):
            assert needle not in text, f"{path.name} contains {needle}"


def test_no_insecure_deserialisation():
    """Settings are plain JSON; pickle/marshal/shelve can execute code."""
    for path in SOURCES:
        text = path.read_text(encoding="utf-8")
        for needle in ("import pickle", "import marshal", "import shelve",
                       "yaml.load("):
            assert needle not in text, f"{path.name} contains {needle}"


def test_no_outbound_http_or_telemetry():
    """The only network traffic Aurora may generate is NTP (UDP/123)."""
    for path in SOURCES:
        text = path.read_text(encoding="utf-8")
        for needle in ("urllib.request", "urlopen(", "import requests",
                       "http.client", "httpx", "websocket"):
            assert needle not in text, f"{path.name} performs HTTP: {needle}"


def test_only_timesync_opens_a_socket():
    for path in SOURCES:
        text = path.read_text(encoding="utf-8")
        if "socket.socket(" in text:
            assert path.name == "timesync.py", f"unexpected socket in {path.name}"


def test_settings_are_written_atomically():
    text = (ROOT / "aurora" / "config.py").read_text(encoding="utf-8")
    assert "os.replace(" in text, "save() must rename a temp file into place"


def test_autostart_touches_only_the_current_user():
    """Aurora must never write to HKEY_LOCAL_MACHINE or Program Files."""
    text = (ROOT / "aurora" / "autostart.py").read_text(encoding="utf-8")
    assert "HKEY_LOCAL_MACHINE" not in text
    assert "HKLM" not in text
    assert "HKEY_CURRENT_USER" in text or "HKCU" in text


def test_installer_does_not_require_admin():
    iss = (ROOT / "build_assets" / "AuroraClock.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in iss
    # With PrivilegesRequired=lowest, Inno resolves {autopf} to
    # %LOCALAPPDATA%\\Programs, so no UAC prompt and no system-wide write.
    assert "DefaultDirName={autopf}" in iss
    assert "{commonpf}" not in iss, "must never force a system-wide install"
    assert "HKLM" not in iss and "HKEY_LOCAL_MACHINE" not in iss


def test_no_hardcoded_secrets():
    """Guard against a token or key being committed by accident."""
    import re
    patterns = [
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "build", "dist", "__pycache__",
                                    ".pytest_cache", "node_modules"}]
        for name in filenames:
            if not name.endswith((".py", ".md", ".txt", ".iss", ".spec",
                                  ".yml", ".yaml", ".json", ".cfg", ".toml")):
                continue
            path = pathlib.Path(dirpath) / name
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scanned += 1
            for pattern in patterns:
                assert not pattern.search(text), f"possible secret in {path}"
    assert scanned > 10, "the secret scanner did not actually read anything"


def test_version_strings_are_consistent():
    from aurora.config import APP_VERSION
    iss = (ROOT / "build_assets" / "AuroraClock.iss").read_text(encoding="utf-8")
    assert f'"{APP_VERSION}"' in iss, "installer version is out of step"

    vinfo = (ROOT / "build_assets" / "version_info.txt").read_text(encoding="utf-8")
    assert APP_VERSION in vinfo, "VERSIONINFO resource is out of step"

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{APP_VERSION}]" in changelog, "CHANGELOG has no entry for this version"
