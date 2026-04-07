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
import logging.handlers
import os
import sys

import aiohttp
import blivedm
from bilibili_api.live import LiveRoom
from bilibili_api.utils.network import Credential

import config
from bot import DanmakuBotHandler
from responder import KeywordResponseHandler
from sender import DanmakuSender
from song_request import SongRequestHandler


def setup_logging():
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    log_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # 按天轮转的文件日志
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "danmaku.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(file_handler)


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
    song_handler = SongRequestHandler(
        keyword=config.SONG_REQUEST_KEYWORD,
        source=config.SONG_REQUEST_SOURCE,
    )
    responder = KeywordResponseHandler(
        rules=config.RESPONSE_RULES,
        sc_template=config.SC_THANK_YOU_TEMPLATE,
    )
    sender = DanmakuSender(
        room_display_id=config.ROOM_ID,
        credential=credential,
        cooldown=config.SEND_COOLDOWN,
    )

    # 解析真实房间号（URL 中的短号可能和实际房间号不同，弹幕中的 medal_room_id 是真实房间号）
    live_room = LiveRoom(room_display_id=config.ROOM_ID, credential=credential)
    room_info = await live_room.get_room_play_info()
    real_room_id = room_info["room_id"]
    logger.info("房间号解析: %d -> %d", config.ROOM_ID, real_room_id)

    handler = DanmakuBotHandler(
        song_handler=song_handler,
        responder=responder,
        sender=sender,
        real_room_id=real_room_id,
        bot_uid=config.BOT_UID,
    )

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
