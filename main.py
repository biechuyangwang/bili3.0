# -*- coding: utf-8 -*-
"""
Bilibili 直播弹幕智能响应机器人 - 入口

使用方法：
1. pip install bilibili-api-python blivedm aiohttp
2. 编辑 config.py 填入凭据和房间号
3. python main.py
"""

import asyncio
import http.cookies
import logging
import sys

import aiohttp
import blivedm
from bilibili_api.utils.network import Credential

import config
from bot import DanmakuBotHandler
from responder import KeywordResponseHandler
from sender import DanmakuSender


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def main():
    setup_logging()
    logger = logging.getLogger("danmaku_bot")

    # 校验必填配置
    if not config.SESSDATA:
        logger.error("config.py 中 SESSDATA 未填写，请先配置")
        sys.exit(1)
    if not config.BILI_JCT:
        logger.error("config.py 中 BILI_JCT 未填写，请先配置")
        sys.exit(1)
    if not config.ROOM_ID:
        logger.error("config.py 中 ROOM_ID 未填写，请先配置")
        sys.exit(1)

    # 构建凭据
    credential = Credential(
        sessdata=config.SESSDATA,
        bili_jct=config.BILI_JCT,
        buvid3=config.BUVID3,
    )

    # 构建组件
    responder = KeywordResponseHandler(
        rules=config.RESPONSE_RULES,
        sc_template=config.SC_THANK_YOU_TEMPLATE,
    )
    sender = DanmakuSender(
        room_display_id=config.ROOM_ID,
        credential=credential,
        cooldown=config.SEND_COOLDOWN,
    )
    handler = DanmakuBotHandler(responder=responder, sender=sender)

    # 构建 aiohttp session（带 cookie 用于 blivedm 获取用户名）
    cookies = http.cookies.SimpleCookie()
    cookies["SESSDATA"] = config.SESSDATA
    cookies["SESSDATA"]["domain"] = "bilibili.com"

    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)

    client = None
    try:
        # 启动弹幕监听
        client = blivedm.BLiveClient(room_id=config.ROOM_ID, session=session)
        client.set_handler(handler)
        client.start()

        logger.info("=" * 40)
        logger.info("弹幕机器人已启动，监听房间 %d", config.ROOM_ID)
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 40)

        await client.join()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
    finally:
        if client:
            await client.stop_and_close()
        await session.close()
        logger.info("已停止")


if __name__ == "__main__":
    asyncio.run(main())
