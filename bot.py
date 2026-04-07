# -*- coding: utf-8 -*-
"""
消息处理模块 - 接收直播间消息，分发到响应器，触发发送

继承 blivedm.BaseHandler，桥接 responder 和 sender。
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

import blivedm
import blivedm.models.web as web_models

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
                 sender: DanmakuSender, real_room_id: int = 0, bot_uid: int = 0,
                 msg_callback: Callable[[str, dict], None] = None):
        self._song_handler = song_handler
        self._responder = responder
        self._sender = sender
        self._real_room_id = real_room_id
        self._bot_uid = bot_uid
        self._msg_callback = msg_callback

    def _notify(self, msg_type: str, data: dict):
        if self._msg_callback:
            self._msg_callback(msg_type, data)

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        logger.debug("[%d] 心跳", client.room_id)

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        logger.info("[弹幕] %s (uid=%s, 房间=%s, 勋章=%s): %s",
                     message.uname, message.uid, message.medal_room_id,
                     message.medal_level, message.msg)

        self._notify("danmaku", {
            "uname": message.uname,
            "uid": message.uid,
            "medal_room_id": message.medal_room_id,
            "medal_level": message.medal_level,
            "msg": message.msg,
        })

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
        )
        if response:
            asyncio.create_task(self._safe_send(response))

    async def _safe_send(self, text: str):
        try:
            await self._sender.send(text)
        except Exception as e:
            logger.error("发送响应失败: %s", e)
