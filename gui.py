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
import sys
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


class BiliBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BiliBot")
        self.root.configure(bg=BG_BASE)
        self.root.geometry("1080x680")
        self.root.minsize(780, 480)

        # 去掉默认 tk 背景，使用暗色
        self._setup_styles()

        self._bot_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: blivedm.BLiveClient | None = None
        self._session: aiohttp.ClientSession | None = None
        self._stop_event = threading.Event()
        self._msg_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self._stats = StatsCollector()

        self._build_ui()
        self._poll_queue()

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

        # Treeview
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

    # ── UI 构建 ──────────────────────────────────────────────

    def _build_ui(self):
        # ── 顶栏 ──
        top = ttk.Frame(self.root, style="TopBar.TFrame", padding=(16, 12, 16, 12))
        top.pack(fill=tk.X)
        top.columnconfigure(1, weight=1)

        # 标题
        title_frame = ttk.Frame(top, style="TopBar.TFrame")
        title_frame.grid(row=0, column=0, sticky="w")

        # 模拟 "红点" 状态指示灯
        self._status_dot = tk.Canvas(title_frame, width=10, height=10,
                                      bg=BG_SURFACE, highlightthickness=0)
        self._status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self._dot_item = self._status_dot.create_oval(1, 1, 9, 9, fill=COLOR_ERROR, outline="")

        tk.Label(title_frame, text="BiliBot",
                 font=("Microsoft YaHei UI", 14, "bold"),
                 bg=BG_SURFACE, fg=FG_PRIMARY).pack(side=tk.LEFT)

        # 房间号输入区
        input_frame = ttk.Frame(top, style="TopBar.TFrame")
        input_frame.grid(row=0, column=1, sticky="w", padx=(32, 0))

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

        # 状态文字
        self._status_var = tk.StringVar(value="未连接")
        self._status_label = tk.Label(top, textvariable=self._status_var,
                                       font=("Microsoft YaHei UI", 9),
                                       bg=BG_SURFACE, fg=FG_MUTED)
        self._status_label.grid(row=0, column=2, sticky="e", padx=(12, 0))

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
        self._danmaku_text.tag_configure("timestamp", foreground=FG_MUTED,
                                          font=("Consolas", 9))
        self._danmaku_text.tag_configure("uname", foreground="#c678dd")

        # 右侧：点歌列表
        song_outer = tk.Frame(pane, bg=BG_BASE)
        pane.add(song_outer, weight=2)

        # 点歌标题栏
        song_header = tk.Frame(song_outer, bg=BG_BASE, padx=12, pady=10)
        song_header.pack(fill=tk.X)
        tk.Label(song_header, text="点歌列表",
                 font=("Microsoft YaHei UI", 11, "bold"),
                 bg=BG_BASE, fg=FG_PRIMARY).pack(side=tk.LEFT)

        # 点歌表格区
        song_table_frame = tk.Frame(song_outer, bg=BG_BASE, padx=12, pady=12)
        song_table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("song", "uname", "time")
        self._song_tree = ttk.Treeview(song_table_frame, columns=cols,
                                        show="headings", height=20,
                                        style="Song.Treeview")
        self._song_tree.heading("song", text="歌曲")
        self._song_tree.heading("uname", text="点歌人")
        self._song_tree.heading("time", text="时间")
        self._song_tree.column("song", width=160, minwidth=80)
        self._song_tree.column("uname", width=100, minwidth=60)
        self._song_tree.column("time", width=70, minwidth=50, anchor=tk.CENTER)

        song_sb = ttk.Scrollbar(song_table_frame, orient=tk.VERTICAL,
                                 command=self._song_tree.yview,
                                 style="Dark.Vertical.TScrollbar")
        self._song_tree.configure(yscrollcommand=song_sb.set)
        self._song_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        song_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # 分隔线 (左右面板间)
        # 通过 pane sash 配置来实现

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

    def _add_song(self, d: dict):
        display = d["song"] + (f" - {d['singer']}" if d.get("singer") else "")
        self._song_tree.insert("", 0, values=(display, d["uname"], d["time"]))

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
