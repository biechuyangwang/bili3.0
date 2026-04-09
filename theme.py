# -*- coding: utf-8 -*-
"""
Shared theme constants for BiliBot GUI.

Centralized color palette, guard names, and style constants used by both
gui.py and room_panel.py to avoid circular imports.
"""

# ── 暗色主题色板 (Vercel/Linear 风格) ──────────────────────────
# 背景
BG_BASE = "#0a0a0a"
BG_SURFACE = "#141414"
BG_ELEVATED = "#1a1a1a"
BG_INPUT = "#1e1e1e"
BG_HOVER = "#262626"
# 文字
FG_PRIMARY = "#ededed"
FG_SECONDARY = "#888888"
FG_MUTED = "#555555"
# 强调色 (偏暖粉红，避免通用蓝)
ACCENT = "#e44d72"
ACCENT_HOVER = "#d63d62"
ACCENT_DISABLED = "#5c2230"
# 语义色
COLOR_SONG = "#61afef"
COLOR_SC = "#e5c07b"
COLOR_GIFT = "#98c379"
COLOR_DANMAKU = "#abb2bf"
COLOR_BORDER = "#2a2a2a"
COLOR_SUCCESS = "#3fb950"
COLOR_ERROR = "#f85149"
COLOR_BAN = "#f85149"
COLOR_GUARD = "#c678dd"
COLOR_GUARD_LEVEL = {1: "#e06c75", 2: "#d19a66", 3: "#61afef"}
GUARD_NAMES = {1: "总督", 2: "提督", 3: "舰长"}
