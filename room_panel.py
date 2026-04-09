# -*- coding: utf-8 -*-
"""
Per-room GUI widgets: danmaku text, song tree, rank tabs, stats panel, send bar.

Extracted from BiliBotGUI in gui.py. Each RoomPanel encapsulates all widgets
for one room's view -- danmaku display, song list, ranking tabs, stats panel,
and the manual send bar. The panel is created with a parent frame, an
on_send_callback (for manual danmaku sending), and an on_refresh_ranking
callback (for ranking refresh button).
"""

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable

from theme import (ACCENT, ACCENT_HOVER, BG_BASE, BG_ELEVATED, BG_INPUT,
                   BG_SURFACE, COLOR_BORDER, COLOR_BAN, COLOR_DANMAKU,
                   COLOR_ERROR, COLOR_GIFT, COLOR_GUARD, COLOR_GUARD_LEVEL,
                   COLOR_SC, COLOR_SONG, COLOR_SUCCESS, FG_MUTED, FG_PRIMARY,
                   FG_SECONDARY, GUARD_NAMES, BG_HOVER)


class RoomPanel:
    """Per-room GUI widgets: danmaku text, song tree, rank tabs, stats panel, send bar."""

    def __init__(self, parent: tk.Widget, on_send_callback: Callable,
                 on_refresh_ranking: Callable):
        self.on_send_callback = on_send_callback
        self.on_refresh_ranking = on_refresh_ranking

        # ── Main paned window ─────────────────────────────────────
        self.pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        self.pane.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # ── LEFT: Danmaku area ────────────────────────────────────
        self._build_left_panel()

        # ── Send bar ──────────────────────────────────────────────
        self._build_send_bar()

        # ── RIGHT: Feature notebook ───────────────────────────────
        self._build_right_panel()

    # ── Left panel (danmaku area) ─────────────────────────────────

    def _build_left_panel(self):
        self._danmaku_outer = tk.Frame(self.pane, bg=BG_BASE)
        self.pane.add(self._danmaku_outer, weight=3)

        # Danmaku header
        danmaku_header = tk.Frame(self._danmaku_outer, bg=BG_BASE, padx=12, pady=10)
        danmaku_header.pack(fill=tk.X)
        tk.Label(danmaku_header, text="弹幕消息",
                 font=("Microsoft YaHei UI", 11, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(side=tk.LEFT)

        # Danmaku text area
        danmaku_text_frame = tk.Frame(self._danmaku_outer, bg=BG_BASE, padx=12, pady=12)
        danmaku_text_frame.pack(fill=tk.BOTH, expand=True)

        self.danmaku_text = tk.Text(
            danmaku_text_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 10), bg=BG_ELEVATED, fg=COLOR_DANMAKU,
            insertbackground=FG_PRIMARY, selectbackground="#2a3a5c",
            padx=10, pady=8, borderwidth=0, relief="flat",
            highlightthickness=1, highlightcolor=COLOR_BORDER,
            highlightbackground=COLOR_BORDER,
        )
        danmaku_sb = ttk.Scrollbar(danmaku_text_frame, orient=tk.VERTICAL,
                                    command=self.danmaku_text.yview,
                                    style="Dark.Vertical.TScrollbar")
        self.danmaku_text.configure(yscrollcommand=danmaku_sb.set)
        self.danmaku_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        danmaku_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Text color tags
        self.danmaku_text.tag_configure("danmaku", foreground=COLOR_DANMAKU)
        self.danmaku_text.tag_configure("ban", foreground=COLOR_BAN)
        self.danmaku_text.tag_configure("sc", foreground=COLOR_SC)
        self.danmaku_text.tag_configure("gift", foreground=COLOR_GIFT)
        self.danmaku_text.tag_configure("song", foreground=COLOR_SONG)
        self.danmaku_text.tag_configure("guard", foreground=COLOR_GUARD)
        self.danmaku_text.tag_configure("timestamp", foreground=FG_MUTED,
                                          font=("Consolas", 9))
        self.danmaku_text.tag_configure("uname", foreground="#c678dd")
        self.danmaku_text.tag_configure("manual", foreground=ACCENT)

    # ── Send bar ──────────────────────────────────────────────────

    def _build_send_bar(self):
        send_bar = tk.Frame(self._danmaku_outer, bg=BG_BASE, padx=12, pady=8)
        send_bar.pack(fill=tk.X)

        self.send_entry_var = tk.StringVar()
        self.send_entry = tk.Entry(
            send_bar, textvariable=self.send_entry_var,
            font=("Microsoft YaHei UI", 10), bg=BG_INPUT, fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY, selectbackground="#2a3a5c",
            borderwidth=0, relief="flat", highlightthickness=1,
            highlightcolor=ACCENT, highlightbackground=COLOR_BORDER,
        )
        self.send_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self.send_entry.bind("<Return>", lambda e: self.on_send_callback())

        self.send_btn = tk.Button(
            send_bar, text="发 送", font=("Microsoft YaHei UI", 10, "bold"),
            bg=ACCENT, fg="#ffffff", activebackground=ACCENT_HOVER,
            activeforeground="#ffffff", relief="flat", padx=16, pady=4,
            cursor="hand2", command=self.on_send_callback,
        )
        self.send_btn.pack(side=tk.RIGHT)

    # ── Right panel (feature notebook) ────────────────────────────

    def _build_right_panel(self):
        right_outer = tk.Frame(self.pane, bg=BG_BASE)
        self.pane.add(right_outer, weight=2)

        self.notebook = ttk.Notebook(right_outer, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Song list
        song_tab = tk.Frame(self.notebook, bg=BG_BASE)
        self.notebook.add(song_tab, text=" 点歌 ")
        self._build_song_tab(song_tab)

        # Tab 2: Ranking
        rank_tab = tk.Frame(self.notebook, bg=BG_BASE)
        self.notebook.add(rank_tab, text=" 排行 ")
        self._build_rank_tab(rank_tab)

        # Tab 3: Stats
        stats_tab = tk.Frame(self.notebook, bg=BG_BASE)
        self.notebook.add(stats_tab, text=" 统计 ")
        self._build_stats_tab(stats_tab)

    # ── Tab: Song list ────────────────────────────────────────────

    def _build_song_tab(self, parent):
        """Song request list tab"""
        cols = ("song", "uname", "time")
        self.song_tree = ttk.Treeview(parent, columns=cols,
                                        show="headings", height=20,
                                        style="Song.Treeview")
        self.song_tree.heading("song", text="歌曲")
        self.song_tree.heading("uname", text="点歌人")
        self.song_tree.heading("time", text="时间")
        self.song_tree.column("song", width=160, minwidth=80)
        self.song_tree.column("uname", width=100, minwidth=60)
        self.song_tree.column("time", width=70, minwidth=50, anchor=tk.CENTER)

        song_sb = ttk.Scrollbar(parent, orient=tk.VERTICAL,
                                 command=self.song_tree.yview,
                                 style="Dark.Vertical.TScrollbar")
        self.song_tree.configure(yscrollcommand=song_sb.set)
        self.song_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        song_sb.pack(side=tk.RIGHT, fill=tk.Y)

    # ── Tab: Ranking ──────────────────────────────────────────────

    def _build_rank_tab(self, parent):
        """Ranking tab - fan medal / guard"""
        # Sub-notebook
        self.rank_notebook = ttk.Notebook(parent, style="Dark.TNotebook")
        self.rank_notebook.pack(fill=tk.BOTH, expand=True)

        # Fan medal ranking
        medal_frame = tk.Frame(self.rank_notebook, bg=BG_BASE)
        self.rank_notebook.add(medal_frame, text=" 粉丝勋章 ")

        medal_cols = ("rank", "uname", "medal_level")
        self.medal_tree = ttk.Treeview(medal_frame, columns=medal_cols,
                                         show="headings", style="Song.Treeview")
        self.medal_tree.heading("rank", text="#")
        self.medal_tree.heading("uname", text="用户")
        self.medal_tree.heading("medal_level", text="勋章等级")
        self.medal_tree.column("rank", width=40, minwidth=30, anchor=tk.CENTER)
        self.medal_tree.column("uname", width=120, minwidth=80)
        self.medal_tree.column("medal_level", width=80, minwidth=50, anchor=tk.CENTER)

        medal_sb = ttk.Scrollbar(medal_frame, orient=tk.VERTICAL,
                                  command=self.medal_tree.yview,
                                  style="Dark.Vertical.TScrollbar")
        self.medal_tree.configure(yscrollcommand=medal_sb.set)
        self.medal_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        medal_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Guard ranking
        guard_frame = tk.Frame(self.rank_notebook, bg=BG_BASE)
        self.rank_notebook.add(guard_frame, text=" 大航海 ")

        guard_cols = ("rank", "uname", "guard_level")
        self.guard_tree = ttk.Treeview(guard_frame, columns=guard_cols,
                                         show="headings", style="Song.Treeview")
        self.guard_tree.heading("rank", text="#")
        self.guard_tree.heading("uname", text="用户")
        self.guard_tree.heading("guard_level", text="等级")
        self.guard_tree.column("rank", width=40, minwidth=30, anchor=tk.CENTER)
        self.guard_tree.column("uname", width=120, minwidth=80)
        self.guard_tree.column("guard_level", width=80, minwidth=50, anchor=tk.CENTER)

        guard_sb = ttk.Scrollbar(guard_frame, orient=tk.VERTICAL,
                                  command=self.guard_tree.yview,
                                  style="Dark.Vertical.TScrollbar")
        self.guard_tree.configure(yscrollcommand=guard_sb.set)
        self.guard_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        guard_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Refresh button
        btn_frame = tk.Frame(parent, bg=BG_BASE, padx=8, pady=8)
        btn_frame.pack(fill=tk.X)

        refresh_btn = tk.Button(btn_frame, text="刷新排行", font=("Microsoft YaHei UI", 9),
                                bg=BG_SURFACE, fg=FG_PRIMARY, activebackground=BG_HOVER,
                                activeforeground=FG_PRIMARY, relief="flat", padx=12, pady=4,
                                command=self.on_refresh_ranking)
        refresh_btn.pack(side=tk.RIGHT)

    # ── Tab: Stats ────────────────────────────────────────────────

    def _build_stats_tab(self, parent):
        """Stats panel - live counts + revenue + ranking + trend chart"""
        # Upper: number panels
        top_frame = tk.Frame(parent, bg=BG_BASE, padx=12, pady=8)
        top_frame.pack(fill=tk.X)

        # Live counts
        counts_frame = tk.Frame(top_frame, bg=BG_BASE)
        counts_frame.pack(fill=tk.X)
        tk.Label(counts_frame, text="实时数据",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        grid_frame = tk.Frame(counts_frame, bg=BG_BASE)
        grid_frame.pack(fill=tk.X)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)

        self.stat_labels = {}
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
            self.stat_labels[key] = lbl

        # Revenue stats
        rev_frame = tk.Frame(top_frame, bg=BG_BASE)
        rev_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(rev_frame, text="收入统计",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        rev_grid = tk.Frame(rev_frame, bg=BG_BASE)
        rev_grid.pack(fill=tk.X)

        tk.Label(rev_grid, text="SC 总收入", font=("Microsoft YaHei UI", 9),
                 bg=BG_BASE, fg=FG_SECONDARY).pack(side=tk.LEFT, padx=(0, 6))
        self.sc_revenue_lbl = tk.Label(rev_grid, text="¥0", font=("Consolas", 11, "bold"),
                                         bg=BG_BASE, fg=COLOR_SC)
        self.sc_revenue_lbl.pack(side=tk.LEFT, padx=(0, 24))

        tk.Label(rev_grid, text="礼物总价值", font=("Microsoft YaHei UI", 9),
                 bg=BG_BASE, fg=FG_SECONDARY).pack(side=tk.LEFT, padx=(0, 6))
        self.gift_value_lbl = tk.Label(rev_grid, text="0 金瓜子", font=("Consolas", 11, "bold"),
                                         bg=BG_BASE, fg=COLOR_GIFT)
        self.gift_value_lbl.pack(side=tk.LEFT)

        # Divider
        tk.Frame(parent, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=12, pady=4)

        # User ranking
        rank_frame = tk.Frame(parent, bg=BG_BASE, padx=12, pady=4)
        rank_frame.pack(fill=tk.X)
        tk.Label(rank_frame, text="用户排行 Top 3",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        self.user_rank_text = tk.Text(rank_frame, height=4, wrap=tk.WORD, state=tk.DISABLED,
                                        font=("Consolas", 9), bg=BG_ELEVATED, fg=COLOR_DANMAKU,
                                        borderwidth=0, relief="flat", padx=8, pady=4)
        self.user_rank_text.pack(fill=tk.X)

        # Divider
        tk.Frame(parent, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=12, pady=4)

        # Trend chart (Canvas)
        chart_frame = tk.Frame(parent, bg=BG_BASE, padx=12, pady=4)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(chart_frame, text="每分钟弹幕趋势",
                 font=("Microsoft YaHei UI", 10, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 4))

        self.chart_canvas = tk.Canvas(chart_frame, bg=BG_ELEVATED, height=140,
                                        highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)

    # ── Display methods (extracted from BiliBotGUI._append_*) ─────

    def append_danmaku(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self.danmaku_text.insert(tk.END, f" (勋章={d['medal_level']}): ", "danmaku")
        self.danmaku_text.insert(tk.END, f"{d['msg']}\n", "danmaku")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)

    def append_danmaku_song(self, d: dict):
        display = d["song"] + (f" - {d['singer']}" if d.get("singer") else "")
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{d['time']}] ", "timestamp")
        self.danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self.danmaku_text.insert(tk.END, f" 点歌: ", "danmaku")
        self.danmaku_text.insert(tk.END, f"{display}\n", "song")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)

    def append_sc(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.danmaku_text.insert(tk.END, f"[SC ¥{d['price']}] ", "sc")
        self.danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self.danmaku_text.insert(tk.END, f": {d['message']}\n", "sc")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)

    def append_ban(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.danmaku_text.insert(tk.END, f"[禁言] ", "ban")
        self.danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self.danmaku_text.insert(tk.END, f" 触发敏感词 '{d['word']}': {d['msg']}\n", "ban")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)

    def append_gift(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.danmaku_text.insert(tk.END, f"[礼物] ", "gift")
        self.danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self.danmaku_text.insert(tk.END,
            f" 赠送 {d['gift_name']}x{d['num']} ({d['coin_type']})\n", "gift")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)

    def append_guard(self, d: dict):
        ts = datetime.now().strftime('%H:%M:%S')
        guard_name = GUARD_NAMES.get(d.get("guard_level", 3), "舰长")
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.danmaku_text.insert(tk.END, f"[上舰] ", "guard")
        self.danmaku_text.insert(tk.END, f"{d['uname']}", "uname")
        self.danmaku_text.insert(tk.END, f" 开通{guard_name}x{d.get('num', 1)}\n", "guard")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)

    def add_song(self, d: dict):
        display = d["song"] + (f" - {d['singer']}" if d.get("singer") else "")
        self.song_tree.insert("", 0, values=(display, d["uname"], d["time"]))

    def update_stats_display(self, stats: dict):
        counts = stats["counts"]

        # Update count labels
        for key in ("danmaku", "sc", "gift", "guard"):
            if key in self.stat_labels:
                self.stat_labels[key].config(text=str(counts.get(key, 0)))

        # Revenue
        self.sc_revenue_lbl.config(text=f"¥{stats['sc_revenue']:.0f}")
        self.gift_value_lbl.config(text=f"{stats['gift_value']:,} 金瓜子")

        # User ranking
        self.user_rank_text.config(state=tk.NORMAL)
        self.user_rank_text.delete("1.0", tk.END)

        for label, items in [("弹幕", stats["top_danmaku"]),
                              ("送礼", stats["top_gift"]),
                              ("SC", stats["top_sc"])]:
            if items:
                line = f"{label}: " + " | ".join(f"{n}({c})" for n, c in items) + "\n"
                self.user_rank_text.insert(tk.END, line)

        self.user_rank_text.config(state=tk.DISABLED)

    def draw_trend_chart(self, stats: dict):
        """Draw per-minute danmaku trend bar chart on Canvas"""
        canvas = self.chart_canvas
        canvas.delete("all")

        timeline = stats.get("timeline", [])

        if not timeline:
            # No data hint
            w = canvas.winfo_width() or 300
            h = canvas.winfo_height() or 140
            canvas.create_text(w // 2, h // 2, text="等待数据...",
                              fill=FG_MUTED, font=("Microsoft YaHei UI", 9))
            return

        # Last 30 minutes
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

        # Y-axis labels
        canvas.create_text(margin_left - 4, margin_top, text=str(max_val),
                          anchor="e", fill=FG_MUTED, font=("Consolas", 7))
        canvas.create_text(margin_left - 4, margin_top + chart_h, text="0",
                          anchor="e", fill=FG_MUTED, font=("Consolas", 7))

        # Bars
        for i, (ts, count) in enumerate(data):
            x0 = margin_left + i * (chart_w / len(data))
            bar_h = (count / max_val) * chart_h if max_val > 0 else 0
            y0 = margin_top + chart_h - bar_h
            y1 = margin_top + chart_h
            canvas.create_rectangle(x0, y0, x0 + bar_w, y1,
                                     fill=ACCENT, outline="")

        # X-axis
        canvas.create_line(margin_left, margin_top + chart_h,
                          w - 8, margin_top + chart_h,
                          fill=COLOR_BORDER)

    def on_manual_send_result(self, data: dict):
        """Callback for manual danmaku send result -- display in danmaku area"""
        ts = datetime.now().strftime('%H:%M:%S')
        self.danmaku_text.config(state=tk.NORMAL)
        self.danmaku_text.insert(tk.END, f"[{ts}] ", "timestamp")
        if data.get("ok"):
            self.danmaku_text.insert(tk.END, f"[我] ", "manual")
            self.danmaku_text.insert(tk.END, f"{data['text']}\n", "manual")
        else:
            self.danmaku_text.insert(tk.END, f"[发送失败] ", "ban")
            self.danmaku_text.insert(tk.END, f"{data['text']}", "ban")
            if data.get("error"):
                self.danmaku_text.insert(tk.END, f" ({data['error']})", "ban")
            self.danmaku_text.insert(tk.END, "\n", "ban")
        self.danmaku_text.see(tk.END)
        self.danmaku_text.config(state=tk.DISABLED)
