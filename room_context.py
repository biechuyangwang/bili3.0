# -*- coding: utf-8 -*-
"""
Per-room bot state aggregation root.

Holds all per-room state: bot components (client, handler, sender, live_room,
fan_ranking, stats), GUI panel reference, message queue, and state flags.
Created when a room connects, destroyed when it disconnects.
"""

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

        # State flags
        self.connected: bool = False
        self.popularity: int = 0
