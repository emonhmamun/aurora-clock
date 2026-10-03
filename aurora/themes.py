"""Aurora Clock - colour themes."""
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

from typing import Dict

# Each theme defines a small palette used by every clock face:
#   fg      primary text / hands
#   accent  seconds hand, highlights
#   dim     secondary text (date, label)
#   bg      panel background (when background != none)
#   glow    optional glow colour
THEMES: Dict[str, Dict[str, str]] = {
    "aurora":      {"fg": "#EAF6FF", "accent": "#38E1C6", "dim": "#8FA6B8", "bg": "#0D1724", "glow": "#38E1C6"},
    "midnight":    {"fg": "#E8EAF2", "accent": "#6C8CFF", "dim": "#7B839B", "bg": "#0B0D14", "glow": "#6C8CFF"},
    "pure_white":  {"fg": "#FFFFFF", "accent": "#FFFFFF", "dim": "#C9CFD6", "bg": "#101010", "glow": "#FFFFFF"},
    "ink":         {"fg": "#14181D", "accent": "#D8504B", "dim": "#5C6672", "bg": "#F4F5F7", "glow": "#D8504B"},
    "amber":       {"fg": "#FFC36B", "accent": "#FF8A3D", "dim": "#9A seventy", "bg": "#140D06", "glow": "#FF8A3D"},
    "neon_pink":   {"fg": "#FF5FC8", "accent": "#00E5FF", "dim": "#8E5F86", "bg": "#120718", "glow": "#FF5FC8"},
    "matrix":      {"fg": "#5BFF9B", "accent": "#A8FFC9", "dim": "#2E7E52", "bg": "#04100A", "glow": "#5BFF9B"},
    "sakura":      {"fg": "#FFE3EC", "accent": "#FF9EC4", "dim": "#C59AAC", "bg": "#1A0F15", "glow": "#FF9EC4"},
    "nord":        {"fg": "#ECEFF4", "accent": "#88C0D0", "dim": "#7A8699", "bg": "#2E3440", "glow": "#88C0D0"},
    "solar_gold":  {"fg": "#FFD873", "accent": "#FFB300", "dim": "#8E7A45", "bg": "#121009", "glow": "#FFB300"},
    "crimson":     {"fg": "#FFE9E9", "accent": "#FF4D4D", "dim": "#A07676", "bg": "#160909", "glow": "#FF4D4D"},
    "mono_grey":   {"fg": "#D5D8DC", "accent": "#9AA3AD", "dim": "#6B737B", "bg": "#15171A", "glow": "#9AA3AD"},
    # --- new in 1.5 -------------------------------------------------------
    "ocean":       {"fg": "#DFF6FF", "accent": "#00C2FF", "dim": "#6E93A8", "bg": "#071621", "glow": "#00C2FF"},
    "forest":      {"fg": "#E4F5E4", "accent": "#67D37A", "dim": "#6C8C72", "bg": "#0A1410", "glow": "#67D37A"},
    "royal":       {"fg": "#EFE8FF", "accent": "#A77BFF", "dim": "#8378A8", "bg": "#120C21", "glow": "#A77BFF"},
    "copper":      {"fg": "#FFE2CC", "accent": "#E08A45", "dim": "#9B7357", "bg": "#160F09", "glow": "#E08A45"},
    "cyberpunk":   {"fg": "#F7FF4D", "accent": "#FF00C8", "dim": "#8E8A3E", "bg": "#0C0415", "glow": "#FF00C8"},
    "ice_blue":    {"fg": "#F2FBFF", "accent": "#7FC3FF", "dim": "#8CA4B5", "bg": "#0A1119", "glow": "#7FC3FF"},
    "paper":       {"fg": "#23262B", "accent": "#2F7DD1", "dim": "#6D7680", "bg": "#FBFAF6", "glow": "#2F7DD1"},
    "coffee":      {"fg": "#F3E6D6", "accent": "#C89B6A", "dim": "#92795F", "bg": "#1A120B", "glow": "#C89B6A"},
    "mint":        {"fg": "#E6FFF7", "accent": "#3EE0B0", "dim": "#74A398", "bg": "#07150F", "glow": "#3EE0B0"},
    "lava":        {"fg": "#FFE8D6", "accent": "#FF6A2B", "dim": "#9C6A4E", "bg": "#160804", "glow": "#FF6A2B"},
    "steel_blue":  {"fg": "#DCE7F2", "accent": "#5A8FC2", "dim": "#74869A", "bg": "#101620", "glow": "#5A8FC2"},
    "bubblegum":   {"fg": "#FFF0F7", "accent": "#FF77B0", "dim": "#B98AA1", "bg": "#1A0D14", "glow": "#FF77B0"},
    "terminal":    {"fg": "#C8FFC8", "accent": "#00FF66", "dim": "#4E8A5B", "bg": "#000000", "glow": "#00FF66"},
    "sand":        {"fg": "#2B2419", "accent": "#C08B2E", "dim": "#7A6B50", "bg": "#F3EADA", "glow": "#C08B2E"},
    "deep_purple": {"fg": "#ECE4FF", "accent": "#7C4DFF", "dim": "#7A6FA0", "bg": "#0C0817", "glow": "#7C4DFF"},
    "high_vis":    {"fg": "#FFFFFF", "accent": "#FFE000", "dim": "#BFC4C9", "bg": "#000000", "glow": "#FFE000"},
}

# fix a typo-safe fallback
THEMES["amber"]["dim"] = "#9A7042"

THEME_LABELS = {
    "aurora": "Aurora Teal",
    "midnight": "Midnight Blue",
    "pure_white": "Pure White",
    "ink": "Ink (light background)",
    "amber": "Amber Glow",
    "neon_pink": "Neon Pink",
    "matrix": "Matrix Green",
    "sakura": "Sakura",
    "nord": "Nord",
    "solar_gold": "Solar Gold",
    "crimson": "Crimson",
    "mono_grey": "Mono Grey",
    "ocean": "Ocean Blue",
    "forest": "Forest Green",
    "royal": "Royal Purple",
    "copper": "Copper",
    "cyberpunk": "Cyberpunk",
    "ice_blue": "Ice Blue",
    "paper": "Paper (light background)",
    "coffee": "Coffee",
    "mint": "Mint",
    "lava": "Lava",
    "steel_blue": "Steel Blue",
    "bubblegum": "Bubblegum",
    "terminal": "Terminal Green",
    "sand": "Sand (light background)",
    "deep_purple": "Deep Purple",
    "high_vis": "High Visibility",
}


def palette(theme_name: str, overrides: dict | None = None) -> Dict[str, str]:
    pal = dict(THEMES.get(theme_name, THEMES["aurora"]))
    if overrides:
        pal.update({k: v for k, v in overrides.items() if v})
    return pal
