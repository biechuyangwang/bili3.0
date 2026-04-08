# -*- coding: utf-8 -*-
"""
查歌模块 - 通过 QQ 音乐搜索歌曲信息

调用 QQ 音乐非官方 API，返回匹配的歌曲名和歌手列表。
"""

import logging
from typing import List, Tuple

import aiohttp

logger = logging.getLogger("danmaku_bot.song_search")

QQ_MUSIC_SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"


async def search_qq_music(keyword: str, session: aiohttp.ClientSession) -> List[Tuple[str, str]]:
    """搜索 QQ 音乐，返回最多 3 首 (歌名, 歌手) 结果。

    Args:
        keyword: 搜索关键词
        session: aiohttp 会话（复用 bot 的 session）

    Returns:
        列表，元素为 (songname, singer) 元组。出错或无结果返回空列表。
    """
    params = {
        "w": keyword,
        "format": "json",
        "p": 1,
        "n": 3,
    }
    try:
        async with session.get(QQ_MUSIC_SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status != 200:
                logger.warning("[查歌] QQ 音乐返回 HTTP %d", resp.status)
                return []
            data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning("[查歌] 请求 QQ 音乐失败: %s", e)
        return []

    try:
        song_list = data.get("data", {}).get("song", {}).get("list", [])
        results = []
        for item in song_list[:3]:
            songname = item.get("songname", "").strip()
            # singer 是列表，取所有 singer.name 拼接
            singers = item.get("singer", [])
            singer_name = "/".join(s.get("name", "") for s in singers) if singers else ""
            if songname:
                results.append((songname, singer_name))
        return results
    except Exception as e:
        logger.warning("[查歌] 解析 QQ 音乐响应失败: %s", e)
        return []
