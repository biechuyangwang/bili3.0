# -*- coding: utf-8 -*-
"""
弹幕发送模块 - 封装 bilibili-api 发弹幕，带限流保护
"""

import asyncio
import logging
import time
from typing import Optional

from bilibili_api.live import LiveRoom
from bilibili_api.utils.danmaku import Danmaku
from bilibili_api.utils.network import Credential

logger = logging.getLogger("danmaku_bot.sender")


class DanmakuSender:
    """限流弹幕发送器"""

    def __init__(self, room_display_id: int, credential: Credential, cooldown: float = 3.0):
        self._live_room = LiveRoom(room_display_id=room_display_id, credential=credential)
        self._cooldown = cooldown
        self._last_send_time: float = 0.0
        self._real_room_id: Optional[int] = None
        self._lock = asyncio.Lock()

    async def _ensure_room_id(self):
        """缓存真实房间号，避免每次发送都调 API"""
        if self._real_room_id is None:
            info = await self._live_room.get_room_play_info()
            self._real_room_id = info["room_id"]

    async def send(self, text: str) -> bool:
        """发送弹幕，返回是否成功"""
        async with self._lock:
            # 限流：距离上次发送不足 cooldown 则等待
            now = time.monotonic()
            wait = self._cooldown - (now - self._last_send_time)
            if wait > 0:
                logger.debug("限流等待 %.1fs", wait)
                await asyncio.sleep(wait)

            try:
                await self._ensure_room_id()
                await self._live_room.send_danmaku(Danmaku(text), room_id=self._real_room_id)
                self._last_send_time = time.monotonic()
                logger.info("已发送弹幕: %s", text)
                return True
            except Exception as e:
                logger.error("发送弹幕失败 '%s': %s", text, e)
                return False
