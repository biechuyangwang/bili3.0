# -*- coding: utf-8 -*-
"""
消息处理模块 - 接收直播间消息，分发到响应器，触发发送

继承 blivedm.BaseHandler，桥接 responder 和 sender。
"""

import asyncio
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime

import blivedm
import blivedm.models.web as web_models

import config
from song_search import search_qq_music
from stats_collector import StatsCollector

from responder import KeywordResponseHandler
from sender import DanmakuSender
from song_request import SongRequestHandler

logger = logging.getLogger("danmaku_bot.handler")


class DanmakuBotHandler(blivedm.BaseHandler):
    """弹幕机器人消息处理器

    msg_callback: 可选回调函数，签名为 callback(type, data)，用于通知外部（如 GUI）。
                  type 为 "danmaku" / "song" / "sc" / "gift" / "status"。
                  不传则仅走日志，不影响 CLI 模式。
    """

    def __init__(self, song_handler: SongRequestHandler, responder: KeywordResponseHandler,
                 sender: DanmakuSender, live_room=None, real_room_id: int = 0, bot_uid: int = 0,
                 msg_callback: Callable[[str, dict], None] = None,
                 stats: StatsCollector = None):
        self._song_handler = song_handler
        self._responder = responder
        self._sender = sender
        self._live_room = live_room
        self._real_room_id = real_room_id
        self._bot_uid = bot_uid
        self._msg_callback = msg_callback
        self.stats = stats or StatsCollector()
        self._last_welcome_time: float = 0.0  # timestamp of last welcome sent
        self._welcomed_users: dict[int, float] = {}  # uid -> last welcome timestamp

        # 加载敏感词
        self._ban_words: set[str] = self._load_ban_words()

        # 功能开关（可通过 GUI 控制）
        self.guard_enabled = True
        self.welcome_enabled = True
        self.auto_ban_enabled = True

    def _notify(self, msg_type: str, data: dict):
        if self._msg_callback:
            self._msg_callback(msg_type, data)

    @staticmethod
    def _load_ban_words() -> set[str]:
        """从 ban_words.txt 加载敏感词集合，文件缺失或为空则返回空集合。"""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ban_words.txt")
        words: set[str] = set()
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        words.add(line)
        except FileNotFoundError:
            logger.debug("ban_words.txt 不存在，自动禁言功能未启用")
        except Exception as e:
            logger.warning("加载 ban_words.txt 失败: %s", e)
        if words:
            logger.info("已加载 %d 个敏感词", len(words))
        return words

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        logger.debug("[%d] 心跳 人气=%d", client.room_id, message.popularity)

        self._notify("heartbeat", {
            "popularity": message.popularity,
        })

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        logger.info("[弹幕] %s (uid=%s, 房间=%s, 勋章=%s): %s",
                     message.uname, message.uid, message.medal_room_id,
                     message.medal_level, message.msg)

        self.stats.record_danmaku(message.uname)

        self._notify("danmaku", {
            "uname": message.uname,
            "uid": message.uid,
            "medal_room_id": message.medal_room_id,
            "medal_level": message.medal_level,
            "msg": message.msg,
        })

        # ── 自动禁言检查（最优先，不区分是否粉丝） ──
        if self.auto_ban_enabled and self._ban_words and self._live_room:
            for word in self._ban_words:
                if word in message.msg:
                    logger.info("[禁言] %s (uid=%d) 触发敏感词 '%s': %s",
                                message.uname, message.uid, word, message.msg)
                    self._notify("ban", {
                        "uname": message.uname,
                        "msg": message.msg,
                        "word": word,
                    })
                    asyncio.create_task(
                        self._live_room.ban_user(uid=message.uid, hour=config.BAN_DURATION)
                    )
                    return  # 禁言后不再处理

        # 点歌不过滤自身弹幕，优先处理
        song_info = self._song_handler.parse_request(message.msg)
        if song_info:
            song_name, singer = song_info
            self._song_handler.handle_danmaku(
                uname=message.uname,
                msg=message.msg,
                uid=message.uid,
                medal_level=message.medal_level,
            )
            self._notify("song", {
                "song": song_name,
                "singer": singer,
                "uname": message.uname,
                "time": datetime.now().strftime("%H:%M:%S"),
            })
            return

        # ── 查歌功能 ──
        if message.msg.startswith(config.SONG_SEARCH_KEYWORD):
            keyword = message.msg[len(config.SONG_SEARCH_KEYWORD):].strip()
            if keyword:
                asyncio.create_task(self._handle_song_search(keyword, client))
            return

        # 过滤自己的弹幕，避免死循环
        if self._bot_uid and message.uid == self._bot_uid:
            logger.debug("跳过自身弹幕: uid=%d", message.uid)
            return

        # 过滤非本房间粉丝（未佩戴勋章 或 勋章不属于本房间）
        if self._real_room_id and message.medal_room_id != self._real_room_id:
            logger.debug("跳过非本房间粉丝: uid=%d, 勋章房间=%d",
                         message.uid, message.medal_room_id)
            return

        response = self._responder.handle_danmaku(
            uname=message.uname,
            msg=message.msg,
            uid=message.uid,
            medal_level=message.medal_level,
        )
        if response:
            asyncio.create_task(self._safe_send(response))

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        logger.info("[SC] ¥%d %s: %s", message.price, message.uname, message.message)

        self.stats.record_sc(message.uname, message.price)

        self._notify("sc", {
            "uname": message.uname,
            "price": message.price,
            "message": message.message,
        })

        response = self._responder.handle_super_chat(
            uname=message.uname,
            message=message.message,
            price=message.price,
            uid=message.uid,
        )
        if response:
            asyncio.create_task(self._safe_send(response))

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        logger.info("[礼物] %s 赠送 %sx%d (%s)",
                     message.uname, message.gift_name, message.num, message.coin_type)

        # 只统计金瓜子礼物价值（coin_type == "gold"）
        total_gold = message.total_coin if message.coin_type == "gold" else 0
        self.stats.record_gift(message.uname, total_gold)

        self._notify("gift", {
            "uname": message.uname,
            "gift_name": message.gift_name,
            "num": message.num,
            "coin_type": message.coin_type,
        })

        response = self._responder.handle_gift(
            uname=message.uname,
            gift_name=message.gift_name,
            num=message.num,
            coin_type=message.coin_type,
            price=message.price,
        )
        if response:
            asyncio.create_task(self._safe_send(response))

    def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        logger.info("[上舰] %s 开通 %s (等级=%d, 数量=%d)",
                     message.username, message.gift_name, message.guard_level, message.num)

        self.stats.record_guard()

        if not self.guard_enabled:
            return

        self._notify("guard", {
            "uname": message.username,
            "uid": message.uid,
            "guard_level": message.guard_level,
            "gift_name": message.gift_name,
            "num": message.num,
            "price": message.price,
        })

        template = config.GUARD_TEMPLATES.get(message.guard_level)
        if template:
            text = template.format(uname=message.username, num=message.num)
            asyncio.create_task(self._safe_send(text))

    def _on_interact_word_v2(self, client: blivedm.BLiveClient, message: web_models.InteractWordV2Message):
        # Only handle enter events (msg_type=1)
        if message.msg_type != 1:
            return

        logger.info("[进场] %s (uid=%d, msg_type=%d)", message.username, message.uid, message.msg_type)

        if not self.welcome_enabled:
            return

        self._notify("welcome", {
            "uname": message.username,
            "uid": message.uid,
            "msg_type": message.msg_type,
        })

        now = time.time()

        # Global cooldown check
        if now - self._last_welcome_time < config.WELCOME_COOLDOWN_GLOBAL:
            logger.debug("全局冷却中，跳过欢迎: 距上次 %.1fs", now - self._last_welcome_time)
            return

        # Per-user cooldown check
        last_user_welcome = self._welcomed_users.get(message.uid, 0.0)
        if now - last_user_welcome < config.WELCOME_COOLDOWN_USER * 60:
            logger.debug("用户冷却中，跳过欢迎: uid=%d", message.uid)
            return

        # Send welcome
        text = config.WELCOME_TEMPLATE.format(uname=message.username)
        self._last_welcome_time = now
        self._welcomed_users[message.uid] = now
        asyncio.create_task(self._safe_send(text))

    async def _safe_send(self, text: str):
        try:
            await self._sender.send(text)
        except Exception as e:
            logger.error("发送响应失败: %s", e)

    async def _handle_song_search(self, keyword: str, client: blivedm.BLiveClient):
        """异步查歌：调用 QQ 音乐搜索并回复结果。"""
        try:
            session = client.session
            results = await search_qq_music(keyword, session)
            if not results:
                await self._safe_send("未找到相关歌曲")
                return
            parts = [f"{song} - {singer}" if singer else song for song, singer in results]
            reply = "; ".join(parts)
            await self._safe_send(reply)
        except Exception as e:
            logger.error("[查歌] 查歌服务异常: %s", e)
            await self._safe_send("查歌服务暂时不可用")
