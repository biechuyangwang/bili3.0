# -*- coding: utf-8 -*-
"""
Per-room bot state aggregation root.

Holds all per-room state: bot components (client, handler, sender, live_room,
fan_ranking, stats), GUI panel reference, message queue, and state flags.
Created when a room connects, destroyed when it disconnects.
"""

import logging
import logging.handlers
import os
import queue
from typing import TYPE_CHECKING

import blivedm
from bilibili_api.live import LiveRoom

from fan_ranking import FanRankingService
from sender import DanmakuSender
from stats_collector import StatsCollector

if TYPE_CHECKING:
    from bot import DanmakuBotHandler
    from room_panel import RoomPanel


class RoomContext:
    """Holds all per-room state: bot components, GUI panel reference, message queue.

    Created when a room connects, destroyed when it disconnects.
    Bot-side fields (client, handler, sender, live_room, fan_ranking) are set
    during bot initialization in the asyncio thread.
    GUI-side field (panel) is set during RoomPanel creation in the GUI thread.
    """

    def __init__(self, room_id: int):
        self.room_id = room_id
        self.real_room_id: int | None = None

        # Bot-side (set during _start_room_bot in asyncio thread)
        self.client: blivedm.BLiveClient | None = None
        self.handler: DanmakuBotHandler | None = None
        self.sender: DanmakuSender | None = None
        self.live_room: LiveRoom | None = None
        self.fan_ranking: FanRankingService | None = None
        self.stats: StatsCollector = StatsCollector()

        # GUI-side (set after RoomPanel creation in main thread)
        self.panel: RoomPanel | None = None

        # Thread-safe message bridge
        self.msg_queue: queue.Queue[tuple[str, dict]] = queue.Queue()

        # Per-room logging
        self.logger: logging.Logger | None = None
        self.file_handler: logging.handlers.TimedRotatingFileHandler | None = None

        # State flags
        self.connected: bool = False
        self.popularity: int = 0
        self.error_message: str | None = None

    def setup_room_logger(self):
        """Create per-room log directory and file handler for danmaku logging."""
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", str(self.room_id))
        os.makedirs(log_dir, exist_ok=True)

        logger_name = f"danmaku_bot.room.{self.room_id}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        # Prevent propagation to root logger to avoid duplicate entries
        self.logger.propagate = False

        log_format = "%(asctime)s [%(levelname)s] %(message)s"
        self.file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "danmaku.log"),
            when="midnight", interval=1, backupCount=30, encoding="utf-8",
        )
        self.file_handler.suffix = "%Y-%m-%d.log"
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
        self.logger.addHandler(self.file_handler)

    def close_room_logger(self):
        """Close and remove the per-room log handler. Does NOT delete log files."""
        if self.file_handler and self.logger:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None
        if self.logger:
            # Remove all handlers to fully release the logger
            self.logger.handlers.clear()
            self.logger = None
