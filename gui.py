# -*- coding: utf-8 -*-
"""
BiliBot 图形界面

基于 tkinter 的弹幕机器人控制面板，现代暗色主题。
机器人运行在后台线程，通过消息队列与 GUI 通信。
"""

import asyncio
import http.cookies
import logging
import logging.handlers
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import aiohttp
import blivedm
from bilibili_api.live import LiveRoom
from bilibili_api.utils.network import Credential

import config
from bot import DanmakuBotHandler
from fan_ranking import FanRankingService
from responder import KeywordResponseHandler
from sender import DanmakuSender
from song_request import SongRequestHandler
from stats_collector import StatsCollector

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


class BiliBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BiliBot")
        self.root.configure(bg=BG_BASE)
        self.root.geometry("1200x720")
        self.root.minsize(900, 540)

        # 去掉默认 tk 背景，使用暗色
        self._setup_styles()

        self._bot_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: blivedm.BLiveClient | None = None
        self._session: aiohttp.ClientSession | None = None
        self._stop_event = threading.Event()
        self._msg_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self._stats = StatsCollector()
        self._handler: DanmakuBotHandler | None = None
        self._live_room: LiveRoom | None = None
        self._fan_ranking: FanRankingService | None = None

        # 功能开关变量
        self._guard_var = tk.BooleanVar(value=True)
        self._welcome_var = tk.BooleanVar(value=True)
        self._auto_ban_var = tk.BooleanVar(value=True)

        # 人气值
        self._popularity = 0

        self._build_ui()
        self._poll_queue()
        self._refresh_stats_timer()

    # ── 主题样式 ───────────────────────────────────────────

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        # 全局
        s.configure(".", background=BG_BASE, foreground=FG_PRIMARY,
                     borderwidth=0, focusthickness=0)
        s.map(".", background=[("active", BG_HOVER)])

        # 顶栏容器
        s.configure("TopBar.TFrame", background=BG_SURFACE)

        # 连接按钮 - 默认状态 (连接)
        s.configure("Connect.TButton",
                     background=ACCENT, foreground="#ffffff",
                     font=("Microsoft YaHei UI", 10, "bold"),
                     padding=(20, 8), borderwidth=0, relief="flat")
        s.map("Connect.TButton",
               background=[("active", ACCENT_HOVER), ("disabled", ACCENT_DISABLED)],
               foreground=[("disabled", "#666666")])

        # 断开按钮 - 活动状态
        s.configure("Disconnect.TButton",
                     background="#333333", foreground=FG_PRIMARY,
                     font=("Microsoft YaHei UI", 10, "bold"),
                     padding=(20, 8), borderwidth=0, relief="flat")
        s.map("Disconnect.TButton",
               background=[("active", "#444444")])

        # LabelFrame
        s.configure("Dark.TLabelframe", background=BG_BASE, foreground=FG_SECONDARY,
                     font=("Microsoft YaHei UI", 9), borderwidth=1, relief="flat")
        s.configure("Dark.TLabelframe.Label", background=BG_BASE, foreground=FG_SECONDARY,
                     font=("Microsoft YaHei UI", 10, "bold"))

        # 输入框
        s.configure("Room.TEntry",
                     fieldbackground=BG_INPUT, foreground=FG_PRIMARY,
                     insertcolor=FG_PRIMARY, borderwidth=1,
                     focusthickness=2, focuscolor=ACCENT)

        # Treeview (共用样式)
        s.configure("Song.Treeview",
                     background=BG_ELEVATED, foreground=FG_PRIMARY,
                     fieldbackground=BG_ELEVATED,
                     borderwidth=0, rowheight=32,
                     font=("Microsoft YaHei UI", 9))
        s.configure("Song.Treeview.Heading",
                     background=BG_SURFACE, foreground=FG_SECONDARY,
                     borderwidth=0, font=("Microsoft YaHei UI", 9, "bold"),
                     relief="flat")
        s.map("Song.Treeview",
               background=[("selected", "#2a2a3d")],
               foreground=[("selected", FG_PRIMARY)])
        s.map("Song.Treeview.Heading",
               background=[("active", BG_HOVER)])

        # Scrollbar
        s.configure("Dark.Vertical.TScrollbar",
                     background=BG_SURFACE, troughcolor=BG_BASE,
                     borderwidth=0, arrowsize=14,
                     arrowcolor=FG_MUTED)
        s.map("Dark.Vertical.TScrollbar",
               background=[("active", BG_HOVER), ("hover", BG_HOVER)])

        # 状态标签
        s.configure("Status.TLabel",
                     background=BG_SURFACE, foreground=FG_MUTED,
                     font=("Microsoft YaHei UI", 9))

        # Notebook (Tab 样式)
        s.configure("Dark.TNotebook", background=BG_BASE, borderwidth=0)
        s.configure("Dark.TNotebook.Tab",
                     background=BG_SURFACE, foreground=FG_SECONDARY,
                     padding=(16, 8), font=("Microsoft YaHei UI", 10))
        s.map("Dark.TNotebook.Tab",
               background=[("selected", BG_BASE)],
               foreground=[("selected", FG_PRIMARY)])

        # Settings menubutton
        s.configure("Settings.TMenubutton",
                     background=BG_SURFACE, foreground=FG_SECONDARY,
                     font=("Microsoft YaHei UI", 9),
                     padding=(8, 4))
        s.map("Settings.TMenubutton",
               background=[("active", BG_HOVER)])

    # ── UI 构建 ──────────────────────────────────────────────

    def _build_ui(self):
        # ── 顶栏 ──
        top = ttk.Frame(self.root, style="TopBar.TFrame", padding=(16, 10, 16, 10))
        top.pack(fill=tk.X)
        top.columnconfigure(2, weight=1)

        # 标题
        title_frame = ttk.Frame(top, style="TopBar.TFrame")
        title_frame.grid(row=0, column=0, sticky="w")

        self._status_dot = tk.Canvas(title_frame, width=10, height=10,
                                      bg=BG_SURFACE, highlightthickness=0)
        self._status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self._dot_item = self._status_dot.create_oval(1, 1, 9, 9, fill=COLOR_ERROR, outline="")

        tk.Label(title_frame, text="BiliBot",
                 font=("Microsoft YaHei UI", 14, "bold"),
                 bg=BG_SURFACE, fg=FG_PRIMARY).pack(side=tk.LEFT)

        # 设置下拉菜单
        settings_frame = ttk.Frame(top, style="TopBar.TFrame")
        settings_frame.grid(row=0, column=1, sticky="w", padx=(24, 0))

        settings_btn = tk.Menubutton(settings_frame, text="⚙ 设置",
                                      bg=BG_SURFACE, fg=FG_SECONDARY,
                                      activebackground=BG_HOVER, activeforeground=FG_PRIMARY,
                                      font=("Microsoft YaHei UI", 9), relief="flat",
                                      highlightthickness=0, bd=0, padx=8, pady=4,
                                      indicatoron=True)
        settings_menu = tk.Menu(settings_btn, tearoff=0,
                                bg=BG_ELEVATED, fg=FG_PRIMARY,
                                activebackground=BG_HOVER, activeforeground=FG_PRIMARY,
                                font=("Microsoft YaHei UI", 9),
                                selectcolor=ACCENT)
        settings_menu.add_checkbutton(label="上舰感谢", variable=self._guard_var,
                                       command=self._on_toggle_guard)
        settings_menu.add_checkbutton(label="进场欢迎", variable=self._welcome_var,
                                       command=self._on_toggle_welcome)
        settings_menu.add_checkbutton(label="自动禁言", variable=self._auto_ban_var,
                                       command=self._on_toggle_auto_ban)
        settings_btn.config(menu=settings_menu)
        settings_btn.pack(side=tk.LEFT)

        # 房间号输入区
        input_frame = ttk.Frame(top, style="TopBar.TFrame")
        input_frame.grid(row=0, column=2, sticky="w", padx=(16, 0))

        tk.Label(input_frame, text="房间号",
                 font=("Microsoft YaHei UI", 9),
                 bg=BG_SURFACE, fg=FG_SECONDARY).pack(side=tk.LEFT, padx=(0, 6))

        self._room_var = tk.StringVar(value=str(config.ROOM_ID) if config.ROOM_ID else "")
        self._room_entry = ttk.Entry(input_frame, textvariable=self._room_var, width=12,
                                      font=("Consolas", 12), style="Room.TEntry")
        self._room_entry.pack(side=tk.LEFT, padx=(0, 12))

        self._connect_btn = ttk.Button(input_frame, text="连 接", width=8,
                                        style="Connect.TButton", command=self._toggle)
        self._connect_btn.pack(side=tk.LEFT)

        # 右侧：人气 + 状态
        right_frame = ttk.Frame(top, style="TopBar.TFrame")
        right_frame.grid(row=0, column=3, sticky="e")

        self._pop_var = tk.StringVar(value="人气: --")
        tk.Label(right_frame, textvariable=self._pop_var,
                 font=("Consolas", 10), bg=BG_SURFACE, fg=COLOR_SC).pack(side=tk.LEFT, padx=(0, 16))

        self._status_var = tk.StringVar(value="未连接")
        self._status_label = tk.Label(right_frame, textvariable=self._status_var,
                                       font=("Microsoft YaHei UI", 9),
                                       bg=BG_SURFACE, fg=FG_MUTED)
        self._status_label.pack(side=tk.LEFT)

        # 分割线
        tk.Frame(self.root, bg=COLOR_BORDER, height=1).pack(fill=tk.X)

        # ── 主区域：左右分栏 ──
        pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # 左侧：弹幕区
        danmaku_outer = tk.Frame(pane, bg=BG_BASE)
        pane.add(danmaku_outer, weight=3)

        # 弹幕标题栏
        danmaku_header = tk.Frame(danmaku_outer, bg=BG_BASE, padx=12, pady=10)
        danmaku_header.pack(fill=tk.X)
        tk.Label(danmaku_header, text="弹幕消息",
                 font=("Microsoft YaHei UI", 11, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(side=tk.LEFT)

        # 弹幕文本区
        danmaku_text_frame = tk.Frame(danmaku_outer, bg=BG_BASE, padx=12, pady=12)
        danmaku_text_frame.pack(fill=tk.BOTH, expand=True)

        self._danmaku_text = tk.Text(
            danmaku_text_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 10), bg=BG_ELEVATED, fg=COLOR_DANMAKU,
            insertbackground=FG_PRIMARY, selectbackground="#2a3a5c",
            padx=10, pady=8, borderwidth=0, relief="flat",
            highlightthickness=1, highlightcolor=COLOR_BORDER,
            highlightbackground=COLOR_BORDER,
        )
        danmaku_sb = ttk.Scrollbar(danmaku_text_frame, orient=tk.VERTICAL,
                                    command=self._danmaku_text.yview,
                                    style="Dark.Vertical.TScrollbar")
        self._danmaku_text.configure(yscrollcommand=danmaku_sb.set)
        self._danmaku_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        danmaku_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # 弹幕颜色标签
        self._danmaku_text.tag_configure("danmaku", foreground=COLOR_DANMAKU)
        self._danmaku_text.tag_configure("ban", foreground=COLOR_BAN)
        self._danmaku_text.tag_configure("sc", foreground=COLOR_SC)
        self._danmaku_text.tag_configure("gift", foreground=COLOR_GIFT)
        self._danmaku_text.tag_configure("song", foreground=COLOR_SONG)
        self._danmaku_text.tag_configure("guard", foreground=COLOR_GUARD)
        self._danmaku_text.tag_configure("timestamp", foreground=FG_MUTED,
                                          font=("Consolas", 9))
        self._danmaku_text.tag_configure("uname", foreground="#c678dd")

        # 右侧：Notebook (点歌 / 排行 / 统计)
        right_outer = tk.Frame(pane, bg=BG_BASE)
        pane.add(right_outer, weight=2)

        self._notebook = ttk.Notebook(right_outer, style="Dark.TNotebook")
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: 点歌列表
        song_tab = tk.Frame(self._notebook, bg=BG_BASE)
        self._notebook.add(song_tab, text=" 点歌 ")
        self._build_song_tab(song_tab)

        # Tab 2: 排行榜
        rank_tab = tk.Frame(self._notebook, bg=BG_BASE)
        self._notebook.add(rank_tab, text=" 排行 ")
        self._build_rank_tab(rank_tab)

        # Tab 3: 统计
        stats_tab = tk.Frame(self._notebook, bg=BG_BASE)
        self._notebook.add(stats_tab, text=" 统计 ")
        self._build_stats_tab(stats_tab)

    # ── Tab 构建 ──────────────────────────────────────────

    def _build_song_tab(self, parent):
        """点歌列表 tab"""
        cols = ("song", "uname", "time")
        self._song_tree = ttk.Treeview(parent, columns=cols,
                                        show="headings", height=20,
                                        style="Song.Treeview")
        self._song_tree.heading("song", text="歌曲")
        self._song_tree.heading("uname", text="点歌人")
        self._song_tree.heading("time", text="时间")
        self._song_tree.column("song", width=160, minwidth=80)
        self._song_tree.column("uname", width=100, minwidth=60)
        self._song_tree.column("time", width=70, minwidth=50, anchor=tk.CENTER)

        song_sb = ttk.Scrollbar(parent, orient=tk.VERTICAL,
                                 command=self._song_tree.yview,
                                 style="Dark.Vertical.TScrollbar")
        self._song_tree.configure(yscrollcommand=song_sb.set)
        self._song_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        song_sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_rank_tab(self, parent):
        """排行榜 tab - 粉丝勋章 / 大航海"""
        # 子 tab
        self._rank_notebook = ttk.Notebook(parent, style="Dark.TNotebook")
        self._rank_notebook.pack(fill=tk.BOTH, expand=True)

        # 粉丝勋章排行
        medal_frame = tk.Frame(self._rank_notebook, bg=BG_BASE)
        self._rank_notebook.add(medal_frame, text=" 粉丝勋章 ")

        medal_cols = ("rank", "uname", "medal_level")
        self._medal_tree = ttk.Treeview(medal_frame, columns=medal_cols,
                                         show="headings", style="Song.Treeview")
        self._medal_tree.heading("rank", text="#")
        self._medal_tree.heading("uname", text="用户")
        self._medal_tree.heading("medal_level", text="勋章等级")
        self._medal_tree.column("rank", width=40, minwidth=30, anchor=tk.CENTER)
        self._medal_tree.column("uname", width=120, minwidth=80)
        self._medal_tree.column("medal_level", width=80, minwidth=50, anchor=tk.CENTER)

        medal_sb = ttk.Scrollbar(medal_frame, orient=tk.VERTICAL,
                                  command=self._medal_tree.yview,
                                  style="Dark.Vertical.TScrollbar")
        self._medal_tree.configure(yscrollcommand=medal_sb.set)
        self._medal_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        medal_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # 大航海排行
        guard_frame = tk.Frame(self._rank_notebook, bg=BG_BASE)
        self._rank_notebook.add(guard_frame, text=" 大航海 ")

        guard_cols = ("rank", "uname", "guard_level")
        self._guard_tree = ttk.Treeview(guard_frame, columns=guard_cols,
                                         show="headings", style="Song.Treeview")
        self._guard_tree.heading("rank", text="#")
        self._guard_tree.heading("uname", text="用户")
        self._guard_tree.heading("guard_level", text="等级")
        self._guard_tree.column("rank", width=40, minwidth=30, anchor=tk.CENTER)
        self._guard_tree.column("uname", width=120, minwidth=80)
        self._guard_tree.column("guard_level", width=80, minwidth=50, anchor=tk.CENTER)

        guard_sb = ttk.Scrollbar(guard_frame, orient=tk.VERTICAL,
                                  command=self._guard_tree.yview,
                                  style="Dark.Vertical.TScrollbar")
        self._guard_tree.configure(yscrollcommand=guard_sb.set)
        self._guard_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        guard_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # 刷新按钮
        btn_frame = tk.Frame(parent, bg=BG_BASE, padx=8, pady=8)
        btn_frame.pack(fill=tk.X)

        refresh_btn = tk.Button(btn_frame, text="刷新排行", font=("Microsoft YaHei UI", 9),
                                bg=BG_SURFACE, fg=FG_PRIMARY, activebackground=BG_HOVER,
                                activeforeground=FG_PRIMARY, relief="flat", padx=12, pady=4,
                                command=self._refresh_ranking)
        refresh_btn.pack(side=tk.RIGHT)

    def _build_stats_tab(self, parent):
        """统计面板 - 实时计数 + 收入 + 排行 + 趋势图"""
        # 上半部分: 数字面板
        top_frame = tk.Frame(parent, bg=BG_BASE, padx=12, pady=8)
        top_frame.pack(fill=tk.X)

        # 实时计数
        counts_frame = tk.Frame(top_frame, bg=BG_BASE)
        counts_frame.pack(fill=tk.X)
        tk.Label(counts_frame, text="实时数据",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        grid_frame = tk.Frame(counts_frame, bg=BG_BASE)
        grid_frame.pack(fill=tk.X)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)

        self._stat_labels = {}
        stat_items = [
            ("弹幕数", "danmaku"), ("SC 数", "sc"),
            ("礼物数", "gift"), ("上舰数", "guard"),
        ]
        for i, (label, key) in enumerate(stat_items):
            row, col = divmod(i, 2)
            tk.Label(grid_frame, text=label, font=("Microsoft YaHei UI", 9),
                     bg=BG_BASE, fg=FG_SECONDARY).grid(row=row, column=col * 2, sticky="w", padx=(0, 6))
            lbl = tk.Label(grid_frame, text="0", font=("Consolas", 11, "bold"),
                          bg=BG_BASE, fg=FG_PRIMARY)
            lbl.grid(row=row, column=col * 2 + 1, sticky="w", padx=(0, 20))
            self._stat_labels[key] = lbl

        # 收入统计
        rev_frame = tk.Frame(top_frame, bg=BG_BASE)
        rev_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(rev_frame, text="收入统计",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        rev_grid = tk.Frame(rev_frame, bg=BG_BASE)
        rev_grid.pack(fill=tk.X)

        tk.Label(rev_grid, text="SC 总收入", font=("Microsoft YaHei UI", 9),
                 bg=BG_BASE, fg=FG_SECONDARY).pack(side=tk.LEFT, padx=(0, 6))
        self._sc_revenue_lbl = tk.Label(rev_grid, text="¥0", font=("Consolas", 11, "bold"),
                                         bg=BG_BASE, fg=COLOR_SC)
        self._sc_revenue_lbl.pack(side=tk.LEFT, padx=(0, 24))

        tk.Label(rev_grid, text="礼物总价值", font=("Microsoft YaHei UI", 9),
                 bg=BG_BASE, fg=FG_SECONDARY).pack(side=tk.LEFT, padx=(0, 6))
        self._gift_value_lbl = tk.Label(rev_grid, text="0 金瓜子", font=("Consolas", 11, "bold"),
                                         bg=BG_BASE, fg=COLOR_GIFT)
        self._gift_value_lbl.pack(side=tk.LEFT)

        # 分割线
        tk.Frame(parent, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=12, pady=4)

        # 用户排行
        rank_frame = tk.Frame(parent, bg=BG_BASE, padx=12, pady=4)
        rank_frame.pack(fill=tk.X)
        tk.Label(rank_frame, text="用户排行 Top 3",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        self._user_rank_text = tk.Text(rank_frame, height=4, wrap=tk.WORD, state=tk.DISABLED,
                                        font=("Consolas", 9), bg=BG_ELEVATED, fg=COLOR_DANMAKU,
                                        borderwidth=0, relief="flat", padx=8, pady=4)
        self._user_rank_text.pack(fill=tk.X)

        # 分割线
        tk.Frame(parent, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=12, pady=4)

        # 趋势图 (Canvas)
        chart_frame = tk.Frame(parent, bg=BG_BASE, padx=12, pady=4)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(chart_frame, text="每分钟弹幕趋势",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        self._chart_canvas = tk.Canvas(chart_frame, bg=BG_ELEVATED, height=140,
                                        highlightthickness=0)
        self._chart_canvas.pack(fill=tk.BOTH, expand=True)

    # ── 功能开关回调 ────────────────────────────────────────

    def _on_toggle_guard(self):
        if self._handler:
            self._handler.guard_enabled = self._guard_var.get()

    def _on_toggle_welcome(self):
        if self._handler:
            self._handler.welcome_enabled = self._welcome_var.get()

    def _on_toggle_auto_ban(self):
        if self._handler:
            self._handler.auto_ban_enabled = self._auto_ban_var.get()

    # ── 连接控制 ─────────────────────────────────────────────

    def _toggle(self):
        if self._bot_thread and self._bot_thread.is_alive():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        room_str = self._room_var.get().strip()
        if not room_str:
            messagebox.showwarning("提示", "请输入房间号")
            return
        try:
            room_id = int(room_str)
        except ValueError:
            messagebox.showerror("错误", "房间号必须是数字")
            return

        if not config.SESSDATA or not config.BILI_JCT:
            messagebox.showerror("错误", "请先在 config.py 中配置凭据")
            return

        self._stop_event.clear()
        self._stats.reset()
        self._handler = None
        self._live_room = None
        self._fan_ranking = None
        self._bot_thread = threading.Thread(target=self._run_bot, args=(room_id,), daemon=True)
        self._bot_thread.start()

        self._connect_btn.config(text="断 开", style="Disconnect.TButton")
        self._status_var.set("连接中...")
        self._status_label.config(fg=COLOR_SC)
        self._status_dot.itemconfig(self._dot_item, fill=COLOR_SC)
        self._room_entry.config(state=tk.DISABLED)

    def _disconnect(self):
        self._stop_event.set()
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(
                self._client.stop_and_close(), self._loop
            )
        if self._bot_thread:
            self._bot_thread.join(timeout=5)

        self._connect_btn.config(text="连 接", style="Connect.TButton")
        self._status_var.set("未连接")
        self._status_label.config(fg=FG_MUTED)
        self._status_dot.itemconfig(self._dot_item, fill=COLOR_ERROR)
        self._room_entry.config(state=tk.NORMAL)
        self._handler = None
        self._live_room = None
        self._fan_ranking = None

    # ── 后台线程运行机器人 ───────────────────────────────────

    def _run_bot(self, room_id: int):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._start_bot(room_id))
        except Exception as e:
            self._msg_queue.put(("error", {"message": str(e)}))

    async def _start_bot(self, room_id: int):
        credential = Credential(
            sessdata=config.SESSDATA,
            bili_jct=config.BILI_JCT,
            buvid3=config.BUVID3,
        )

        song_handler = SongRequestHandler(
            keyword=config.SONG_REQUEST_KEYWORD,
            source=config.SONG_REQUEST_SOURCE,
        )
        responder = KeywordResponseHandler(
            rules=config.RESPONSE_RULES,
            sc_template=config.SC_THANK_YOU_TEMPLATE,
        )
        sender = DanmakuSender(
            room_display_id=room_id,
            credential=credential,
            cooldown=config.SEND_COOLDOWN,
        )

        live_room = LiveRoom(room_display_id=room_id, credential=credential)
        room_info = await live_room.get_room_play_info()
        real_room_id = room_info["room_id"]

        handler = DanmakuBotHandler(
            song_handler=song_handler,
            responder=responder,
            sender=sender,
            live_room=live_room,
            real_room_id=real_room_id,
            bot_uid=config.BOT_UID,
            msg_callback=self._on_bot_message,
            stats=self._stats,
        )

        # 存储引用供 GUI 使用
        self._handler = handler
        self._live_room = live_room
        self._fan_ranking = FanRankingService(live_room)

        # 同步功能开关状态
        handler.guard_enabled = self._guard_var.get()
        handler.welcome_enabled = self._welcome_var.get()
        handler.auto_ban_enabled = self._auto_ban_var.get()

        cookies = http.cookies.SimpleCookie()
        cookies["SESSDATA"] = config.SESSDATA
        cookies["SESSDATA"]["domain"] = "bilibili.com"

        self._session = aiohttp.ClientSession()
        self._session.cookie_jar.update_cookies(cookies)

        self._client = blivedm.BLiveClient(room_id=room_id, session=self._session)
        self._client.set_handler(handler)
        self._client.start()

        self._msg_queue.put(("status", {"text": f"已连接房间 {room_id}"}))

        await self._client.join()

        # 正常退出后清理
        if self._session:
            await self._session.close()
        self._msg_queue.put(("status", {"text": "已断开"}))

    def _on_bot_message(self, msg_type: str, data: dict):
        """bot 线程回调 → 线程安全地放入队列"""
        self._msg_queue.put((msg_type, data))

    # ── GUI 主线程轮询队列 ───────────────────────────────────

    def _poll_queue(self):
        while True:
            try:
                msg_type, data = self._msg_queue.get_nowait()
            except queue.Empty:
                break

            if msg_type == "danmaku":
                self._append_danmaku(data)
            elif msg_type == "song":
                self._append_danmaku_song(data)
                self._add_song(data)
            elif msg_type == "sc":
                self._append_sc(data)
            elif msg_type == "ban":
                self._append_ban(data)
            elif msg_type == "gift":
                self._append_gift(data)
            elif msg_type == "guard":
                self._append_guard(data)
            elif msg_type == "heartbeat":
                self._on_heartbeat(data)
            elif msg_type == "status":
                text = data["text"]
                self._status_var.set(text)
                if "已连接" in text:
                    self._status_label.config(fg=COLOR_SUCCESS)
                    self._status_dot.itemconfig(self._dot_item, fill=COLOR_SUCCESS)
                else:
                    self._status_label.config(fg=FG_MUTED)
                    self._status_dot.itemconfig(self._dot_item, fill=COLOR_ERROR)
            elif msg_type == "error":
                messagebox.showerror("错误", data["message"])
                self._connect_btn.config(text="连 接", style="Connect.TButton")
                self._status_var.set("连接失败")
                self._status_label.config(fg=COLOR_ERROR)
                self._status_dot.itemconfig(self._dot_item, fill=COLOR_ERROR)
                self._room_entry.config(state=tk.NORMAL)
            elif msg_type == "ranking_data":
                self._update_ranking_display(data)

        self.root.after(100, self._poll_queue)

    # ── 弹幕显示 ─────────────────────────────────────────────

    def _append_danmaku(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self._danmaku_text.config(state=tk.NORMAL)
        self._danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self._danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self._danmaku_text.insert(tk.END, f" (勋章={d['medal_level']}): ", "danmaku")
        self._danmaku_text.insert(tk.END, f"{d['msg']}\n", "danmaku")
        self._danmaku_text.see(tk.END)
        self._danmaku_text.config(state=tk.DISABLED)

    def _append_danmaku_song(self, d: dict):
        display = d["song"] + (f" - {d['singer']}" if d.get("singer") else "")
        self._danmaku_text.config(state=tk.NORMAL)
        self._danmaku_text.insert(tk.END, f"[{d['time']}] ", "timestamp")
        self._danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self._danmaku_text.insert(tk.END, f" 点歌: ", "danmaku")
        self._danmaku_text.insert(tk.END, f"{display}\n", "song")
        self._danmaku_text.see(tk.END)
        self._danmaku_text.config(state=tk.DISABLED)

    def _append_sc(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self._danmaku_text.config(state=tk.NORMAL)
        self._danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self._danmaku_text.insert(tk.END, f"[SC ¥{d['price']}] ", "sc")
        self._danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self._danmaku_text.insert(tk.END, f": {d['message']}\n", "sc")
        self._danmaku_text.see(tk.END)
        self._danmaku_text.config(state=tk.DISABLED)

    def _append_ban(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self._danmaku_text.config(state=tk.NORMAL)
        self._danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self._danmaku_text.insert(tk.END, f"[禁言] ", "ban")
        self._danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self._danmaku_text.insert(tk.END, f" 触发敏感词 '{d['word']}': {d['msg']}\n", "ban")
        self._danmaku_text.see(tk.END)
        self._danmaku_text.config(state=tk.DISABLED)

    def _append_gift(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self._danmaku_text.config(state=tk.NORMAL)
        self._danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self._danmaku_text.insert(tk.END, f"[礼物] ", "gift")
        self._danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self._danmaku_text.insert(tk.END,
            f" 赠送 {d['gift_name']}x{d['num']} ({d['coin_type']})\n", "gift")
        self._danmaku_text.see(tk.END)
        self._danmaku_text.config(state=tk.DISABLED)

    def _append_guard(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        guard_name = GUARD_NAMES.get(d.get("guard_level", 3), "舰长")
        self._danmaku_text.config(state=tk.NORMAL)
        self._danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self._danmaku_text.insert(tk.END, f"[上舰] ", "guard")
        self._danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self._danmaku_text.insert(tk.END, f" 开通{guard_name}x{d.get('num', 1)}\n", "guard")
        self._danmaku_text.see(tk.END)
        self._danmaku_text.config(state=tk.DISABLED)

    def _on_heartbeat(self, data: dict):
        pop = data.get("popularity", 0)
        self._popularity = pop
        self._pop_var.set(f"人气: {pop:,}")

    def _add_song(self, d: dict):
        display = d["song"] + (f" - {d['singer']}" if d.get("singer") else "")
        self._song_tree.insert("", 0, values=(display, d["uname"], d["time"]))

    # ── 排行榜刷新 ──────────────────────────────────────────

    def _refresh_ranking(self):
        """刷新排行榜数据 (在 asyncio loop 中执行)"""
        if not self._fan_ranking or not self._loop:
            return

        async def _fetch():
            try:
                medal_data = await self._fan_ranking.get_fans_medal_rank()
                guard_data = await self._fan_ranking.get_dahanghai()
                self._msg_queue.put(("ranking_data", {
                    "medal": medal_data,
                    "guard": guard_data,
                }))
            except Exception as e:
                logging.getLogger("danmaku_bot.gui").warning("刷新排行榜失败: %s", e)

        asyncio.run_coroutine_threadsafe(_fetch(), self._loop)

    def _update_ranking_display(self, data: dict):
        """更新排行榜 Treeview (主线程)"""
        # 粉丝勋章
        self._medal_tree.delete(*self._medal_tree.get_children())
        for i, item in enumerate(data.get("medal", [])[:50], 1):
            self._medal_tree.insert("", tk.END, values=(i, item["uname"], item["medal_level"]))

        # 大航海
        self._guard_tree.delete(*self._guard_tree.get_children())
        for i, item in enumerate(data.get("guard", [])[:50], 1):
            level_name = GUARD_NAMES.get(item["guard_level"], "舰长")
            self._guard_tree.insert("", tk.END, values=(i, item["uname"], level_name))

    # ── 统计刷新 ────────────────────────────────────────────

    def _refresh_stats_timer(self):
        """每 2 秒刷新统计面板"""
        self._update_stats_display()
        self._draw_trend_chart()
        self.root.after(2000, self._refresh_stats_timer)

    def _update_stats_display(self):
        stats = self._stats.get_stats()
        counts = stats["counts"]

        # 更新计数标签
        for key in ("danmaku", "sc", "gift", "guard"):
            if key in self._stat_labels:
                self._stat_labels[key].config(text=str(counts.get(key, 0)))

        # 收入
        self._sc_revenue_lbl.config(text=f"¥{stats['sc_revenue']:.0f}")
        self._gift_value_lbl.config(text=f"{stats['gift_value']:,} 金瓜子")

        # 用户排行
        self._user_rank_text.config(state=tk.NORMAL)
        self._user_rank_text.delete("1.0", tk.END)

        for label, items in [("弹幕", stats["top_danmaku"]),
                              ("送礼", stats["top_gift"]),
                              ("SC", stats["top_sc"])]:
            if items:
                line = f"{label}: " + " | ".join(f"{n}({c})" for n, c in items) + "\n"
                self._user_rank_text.insert(tk.END, line)

        self._user_rank_text.config(state=tk.DISABLED)

    def _draw_trend_chart(self):
        """用 Canvas 绘制每分钟弹幕趋势柱状图"""
        canvas = self._chart_canvas
        canvas.delete("all")

        stats = self._stats.get_stats()
        timeline = stats.get("timeline", [])

        if not timeline:
            # 无数据时显示提示
            w = canvas.winfo_width() or 300
            h = canvas.winfo_height() or 140
            canvas.create_text(w // 2, h // 2, text="等待数据...",
                              fill=FG_MUTED, font=("Microsoft YaHei UI", 9))
            return

        # 最近 30 分钟
        data = timeline[-30:]
        max_val = max((count for _, count in data), default=1)
        if max_val == 0:
            max_val = 1

        w = canvas.winfo_width() or 300
        h = canvas.winfo_height() or 140
        margin_left = 30
        margin_bottom = 16
        margin_top = 8
        chart_w = w - margin_left - 8
        chart_h = h - margin_top - margin_bottom
        bar_w = max(chart_w / len(data) - 2, 4)

        # Y 轴标签
        canvas.create_text(margin_left - 4, margin_top, text=str(max_val),
                          anchor="e", fill=FG_MUTED, font=("Consolas", 7))
        canvas.create_text(margin_left - 4, margin_top + chart_h, text="0",
                          anchor="e", fill=FG_MUTED, font=("Consolas", 7))

        # 柱子
        for i, (ts, count) in enumerate(data):
            x0 = margin_left + i * (chart_w / len(data))
            bar_h = (count / max_val) * chart_h if max_val > 0 else 0
            y0 = margin_top + chart_h - bar_h
            y1 = margin_top + chart_h
            canvas.create_rectangle(x0, y0, x0 + bar_w, y1,
                                     fill=ACCENT, outline="")

        # X 轴
        canvas.create_line(margin_left, margin_top + chart_h,
                          w - 8, margin_top + chart_h,
                          fill=COLOR_BORDER)

    # ── 启动 ─────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    # GUI 模式下的日志只写文件，不输出到控制台
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    log_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "danmaku.log"),
        when="midnight", interval=1, backupCount=30, encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)

    app = BiliBotGUI()
    app.run()


if __name__ == "__main__":
    main()
