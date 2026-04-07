# -*- coding: utf-8 -*-
"""
点歌模块 - 解析弹幕中的点歌指令，通过 LX Music scheme URL 搜索并播放

LX Music scheme URL 文档：https://lxmusic.toside.cn/desktop/scheme-url
本模块使用 music/searchPlay action，配合 playLater 参数实现稍后播放。
"""

import json
import logging
import urllib.parse
import webbrowser
from typing import Optional, Tuple

logger = logging.getLogger("danmaku_bot.song_request")


class SongRequestHandler:
    """点歌请求处理器

    弹幕格式：
        点歌 歌名           # 仅歌名
        点歌 歌名 歌手      # 歌名 + 歌手（空格分隔）

    触发后会通过 LX Music 的 lxmusic:// 协议 URL 在本地搜索并添加到稍后播放列表。
    """

    def __init__(self, keyword: str = "点歌", source: str = "tx"):
        """
        Args:
            keyword: 触发点歌的关键词前缀
            source: 搜索源，可选值见下方
                tx = 腾讯/QQ音乐, wy = 网易云, kg = 酷狗, kw = 酷我, mg = 咪咕
        """
        self._keyword = keyword
        self._source = source

    def handle_danmaku(self, uname: str, msg: str, uid: int, medal_level: int) -> Optional[str]:
        if not msg.startswith(self._keyword):
            return None

        # 去掉关键词前缀，剩余部分为 "歌名" 或 "歌名 歌手"
        content = msg[len(self._keyword):].strip()
        if not content:
            return None

        parts = content.split(None, 1)
        song_name = parts[0]
        singer = parts[1] if len(parts) > 1 else ""

        # 构建 LX Music searchPlay scheme URL
        data = {
            "name": song_name,
            "source": self._source,
            "playLater": True,
        }
        if singer:
            data["singer"] = singer

        data_json = json.dumps(data, ensure_ascii=False)
        data_encoded = urllib.parse.quote(data_json)
        url = f"lxmusic://music/searchPlay?data={data_encoded}"

        logger.info("[点歌] %s 请求: %s%s (source=%s)",
                     uname, song_name, f" - {singer}" if singer else "", self._source)
        webbrowser.open(url)

        display = song_name + (f" - {singer}" if singer else "")
        # return f"已收到点歌：{display}，稍后播放~"

    def parse_request(self, msg: str) -> Optional[Tuple[str, str]]:
        """解析点歌请求，返回 (歌名, 歌手) 或 None"""
        if not msg.startswith(self._keyword):
            return None
        content = msg[len(self._keyword):].strip()
        if not content:
            return None
        parts = content.split(None, 1)
        return (parts[0], parts[1] if len(parts) > 1 else "")

    def handle_super_chat(self, uname: str, message: str, price: int, uid: int) -> Optional[str]:
        return None

    def handle_gift(self, uname: str, gift_name: str, num: int, coin_type: str) -> Optional[str]:
        return None
