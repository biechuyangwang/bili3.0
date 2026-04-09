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
from tkinter import messagebox, ttk

import aiohttp
import blivedm
from bilibili_api.live import LiveRoom
from bilibili_api.utils.network import Credential

import config
from bot import DanmakuBotHandler
from fan_ranking import FanRankingService
from responder import KeywordResponseHandler
from room_context import RoomContext
from room_panel import RoomPanel
from sender import DanmakuSender
from song_request import SongRequestHandler
from theme import (ACCENT, ACCENT_DISABLED, ACCENT_HOVER, BG_BASE, BG_ELEVATED,
                   BG_HOVER, BG_INPUT, BG_SURFACE, COLOR_BAN, COLOR_BORDER,
                   COLOR_DANMAKU, COLOR_ERROR, COLOR_GIFT, COLOR_GUARD, COLOR_SC,
                   COLOR_SONG, COLOR_SUCCESS, FG_MUTED, FG_PRIMARY, FG_SECONDARY,
                   GUARD_NAMES)


class BiliBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BiliBot")
        self.root.configure(bg=BG_BASE)
        self.root.geometry("1200x720")
        self.root.minsize(900, 540)

        # 去掉默认 tk 背景，使用暗色
        self._setup_styles()

        # Shared infrastructure
        self._shared_session: aiohttp.ClientSession | None = None
        self._rooms: dict[int, RoomContext] = {}

        self._bot_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event = threading.Event()

        # Multi-client state
        self._active_room_id: int | None = None  # last connected room (for manual danmaku, popularity display)
        self._room_tasks: dict[int, asyncio.Task] = {}  # track runtime-added room bot tasks
        self._loop_ready = threading.Event()  # signals bot thread has created its event loop

        # 功能开关变量
        self._guard_var = tk.BooleanVar(value=True)
        self._welcome_var = tk.BooleanVar(value=True)
        self._auto_ban_var = tk.BooleanVar(value=True)

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

        # ── 主区域：由 RoomPanel 创建 ──
        # (No per-room widgets created here. RoomPanel is created in _connect when a room connects.)
        # For Phase 5 single-room, the panel will pack directly into self.root.

    # ── 功能开关回调 ────────────────────────────────────────

    def _on_toggle_guard(self):
        for ctx in self._rooms.values():
            if ctx.handler:
                ctx.handler.guard_enabled = self._guard_var.get()

    def _on_toggle_welcome(self):
        for ctx in self._rooms.values():
            if ctx.handler:
                ctx.handler.welcome_enabled = self._welcome_var.get()

    def _on_toggle_auto_ban(self):
        for ctx in self._rooms.values():
            if ctx.handler:
                ctx.handler.auto_ban_enabled = self._auto_ban_var.get()

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

        # Create RoomContext + RoomPanel for this room
        ctx = RoomContext(room_id)
        ctx.panel = RoomPanel(
            parent=self.root,
            on_send_callback=lambda: self._send_manual_danmaku(room_id),
            on_refresh_ranking=lambda: self._refresh_ranking(room_id),
        )
        self._rooms[room_id] = ctx

        # Start bot thread
        self._bot_thread = threading.Thread(target=self._run_bot, args=(room_id,), daemon=True)
        self._bot_thread.start()

        self._connect_btn.config(text="断 开", style="Disconnect.TButton")
        self._status_var.set("连接中...")
        self._status_label.config(fg=COLOR_SC)
        self._status_dot.itemconfig(self._dot_item, fill=COLOR_SC)
        self._room_entry.config(state=tk.DISABLED)

    def _disconnect(self):
        self._stop_event.set()

        # Stop all room clients
        for room_id, ctx in list(self._rooms.items()):
            if self._loop and ctx.client:
                asyncio.run_coroutine_threadsafe(
                    ctx.client.stop_and_close(), self._loop
                )

        if self._bot_thread:
            self._bot_thread.join(timeout=5)

        # Clean up all room panels
        for ctx in self._rooms.values():
            if ctx.panel and ctx.panel.pane:
                ctx.panel.pane.destroy()

        self._rooms.clear()

        self._connect_btn.config(text="连 接", style="Connect.TButton")
        self._status_var.set("未连接")
        self._status_label.config(fg=FG_MUTED)
        self._status_dot.itemconfig(self._dot_item, fill=COLOR_ERROR)
        self._room_entry.config(state=tk.NORMAL)

    # ── 后台线程运行机器人 ───────────────────────────────────

    def _run_bot(self, room_id: int):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._bot_main(room_id))
        except Exception as e:
            # Put error on any available room's queue
            for ctx in self._rooms.values():
                ctx.msg_queue.put(("error", {"message": str(e)}))
                break

    async def _bot_main(self, room_id: int):
        """Create shared session, then start the single room bot."""
        # Create shared session INSIDE the event loop (critical for blivedm)
        cookies = http.cookies.SimpleCookie()
        cookies["SESSDATA"] = config.SESSDATA
        cookies["SESSDATA"]["domain"] = "bilibili.com"

        self._shared_session = aiohttp.ClientSession()
        self._shared_session.cookie_jar.update_cookies(cookies)

        # Start the single room (Phase 5)
        await self._start_room_bot(room_id)

        # Cleanup
        for ctx in self._rooms.values():
            if ctx.client:
                await ctx.client.stop_and_close()
        if self._shared_session:
            await self._shared_session.close()
            self._shared_session = None

    async def _start_room_bot(self, room_id: int):
        """Initialize bot components for one room and run until disconnect."""
        ctx = self._rooms.get(room_id)
        if not ctx:
            return

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

        ctx.sender = DanmakuSender(
            room_display_id=room_id,
            credential=credential,
            cooldown=config.SEND_COOLDOWN,
        )

        ctx.live_room = LiveRoom(room_display_id=room_id, credential=credential)
        room_info = await ctx.live_room.get_room_play_info()
        ctx.real_room_id = room_info["room_id"]

        ctx.handler = DanmakuBotHandler(
            song_handler=song_handler,
            responder=responder,
            sender=ctx.sender,
            live_room=ctx.live_room,
            real_room_id=ctx.real_room_id,
            bot_uid=config.BOT_UID,
            msg_callback=lambda msg_type, data, rid=room_id: self._on_room_message(rid, msg_type, data),
            stats=ctx.stats,
        )

        ctx.fan_ranking = FanRankingService(ctx.live_room)

        # Sync feature toggles
        ctx.handler.guard_enabled = self._guard_var.get()
        ctx.handler.welcome_enabled = self._welcome_var.get()
        ctx.handler.auto_ban_enabled = self._auto_ban_var.get()

        ctx.client = blivedm.BLiveClient(room_id=room_id, session=self._shared_session)
        ctx.client.set_handler(ctx.handler)
        ctx.client.start()

        ctx.msg_queue.put(("status", {"text": f"已连接房间 {room_id}"}))
        ctx.connected = True

        await ctx.client.join()

        ctx.connected = False
        ctx.msg_queue.put(("status", {"text": "已断开"}))

    def _on_room_message(self, room_id: int, msg_type: str, data: dict):
        """Bot thread callback -- route message to correct room's queue."""
        ctx = self._rooms.get(room_id)
        if ctx:
            ctx.msg_queue.put((msg_type, data))

    # ── GUI 主线程轮询队列 ───────────────────────────────────

    def _poll_queue(self):
        """Poll all room queues for pending messages."""
        for room_id, ctx in list(self._rooms.items()):
            while True:
                try:
                    msg_type, data = ctx.msg_queue.get_nowait()
                except queue.Empty:
                    break

                panel = ctx.panel
                if not panel:
                    continue

                if msg_type == "danmaku":
                    panel.append_danmaku(data)
                elif msg_type == "song":
                    panel.append_danmaku_song(data)
                    panel.add_song(data)
                elif msg_type == "sc":
                    panel.append_sc(data)
                elif msg_type == "ban":
                    panel.append_ban(data)
                elif msg_type == "gift":
                    panel.append_gift(data)
                elif msg_type == "guard":
                    panel.append_guard(data)
                elif msg_type == "heartbeat":
                    pop = data.get("popularity", 0)
                    ctx.popularity = pop
                    self._pop_var.set(f"人气: {pop:,}")
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
                    self._update_ranking_display(room_id, data)
                elif msg_type == "manual_send":
                    panel.on_manual_send_result(data)

        self.root.after(100, self._poll_queue)

    # ── 排行榜刷新 ──────────────────────────────────────────

    def _refresh_ranking(self, room_id: int = None):
        """Refresh ranking data for a specific room."""
        if room_id is None:
            # Fallback: use first room
            if not self._rooms:
                return
            room_id = next(iter(self._rooms))

        ctx = self._rooms.get(room_id)
        if not ctx or not ctx.fan_ranking or not self._loop:
            return

        async def _fetch():
            try:
                medal_data = await ctx.fan_ranking.get_fans_medal_rank()
                guard_data = await ctx.fan_ranking.get_dahanghai()
                ctx.msg_queue.put(("ranking_data", {
                    "medal": medal_data,
                    "guard": guard_data,
                }))
            except Exception as e:
                logging.getLogger("danmaku_bot.gui").warning("刷新排行榜失败: %s", e)

        asyncio.run_coroutine_threadsafe(_fetch(), self._loop)

    def _update_ranking_display(self, room_id: int, data: dict):
        """Update ranking treeviews for a specific room."""
        ctx = self._rooms.get(room_id)
        if not ctx or not ctx.panel:
            return

        # 粉丝勋章
        ctx.panel.medal_tree.delete(*ctx.panel.medal_tree.get_children())
        for i, item in enumerate(data.get("medal", [])[:50], 1):
            ctx.panel.medal_tree.insert("", tk.END, values=(i, item["uname"], item["medal_level"]))

        # 大航海
        ctx.panel.guard_tree.delete(*ctx.panel.guard_tree.get_children())
        for i, item in enumerate(data.get("guard", [])[:50], 1):
            level_name = GUARD_NAMES.get(item["guard_level"], "舰长")
            ctx.panel.guard_tree.insert("", tk.END, values=(i, item["uname"], level_name))

    # ── 统计刷新 ────────────────────────────────────────────

    def _refresh_stats_timer(self):
        """Refresh stats for active room every 2 seconds."""
        # Get active room (Phase 5: single room = first room in dict)
        for ctx in self._rooms.values():
            if ctx.panel and ctx.connected:
                stats = ctx.stats.get_stats()
                ctx.panel.update_stats_display(stats)
                ctx.panel.draw_trend_chart(stats)
                break  # Phase 5: only one room
        self.root.after(2000, self._refresh_stats_timer)

    # ── 手动发送弹幕 ─────────────────────────────────────────

    def _send_manual_danmaku(self, room_id: int = None):
        """Send manual danmaku to a specific room."""
        if room_id is None:
            if not self._rooms:
                messagebox.showwarning("提示", "请先连接直播间")
                return
            room_id = next(iter(self._rooms))

        ctx = self._rooms.get(room_id)
        if not ctx or not ctx.handler or not self._loop:
            messagebox.showwarning("提示", "请先连接直播间")
            return

        text = ctx.panel.send_entry_var.get().strip()
        if not text:
            return

        async def _do_send():
            try:
                ok = await ctx.sender.send(text)
                ctx.msg_queue.put(("manual_send", {"text": text, "ok": ok}))
            except Exception as e:
                ctx.msg_queue.put(("manual_send", {"text": text, "ok": False, "error": str(e)}))

        asyncio.run_coroutine_threadsafe(_do_send(), self._loop)
        ctx.panel.send_entry_var.set("")

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
