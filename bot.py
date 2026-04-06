# -*- coding: utf-8 -*-
"""
消息处理模块 - 接收直播间消息，分发到响应器，触发发送

继承 blivedm.BaseHandler，桥接 responder 和 sender。
"""

import asyncio
import logging

import blivedm
import blivedm.models.web as web_models

from responder import KeywordResponseHandler
from sender import DanmakuSender

logger = logging.getLogger("danmaku_bot.handler")


class DanmakuBotHandler(blivedm.BaseHandler):
    """弹幕机器人消息处理器"""

    def __init__(self, responder: KeywordResponseHandler, sender: DanmakuSender):
        self._responder = responder
        self._sender = sender

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        logger.debug("[%d] 心跳", client.room_id)

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        logger.info("[弹幕] %s (uid=%s, 勋章=%s): %s",
                     message.uname, message.uid, message.medal_level, message.msg)

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
