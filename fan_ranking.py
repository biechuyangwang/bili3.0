# -*- coding: utf-8 -*-
"""
粉丝排行服务 - 封装 bilibili-api 的粉丝勋章排行和大航海贡献榜查询

提供带缓存的异步接口，避免频繁调用 B 站 API。
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("danmaku_bot.fan_ranking")

# Cache TTL in seconds
_CACHE_TTL = 300  # 5 minutes


class FanRankingService:
    """Fan ranking API wrapper with caching.

    Takes a LiveRoom instance from bilibili_api.
    All methods are async and return lists of dicts.
    """

    def __init__(self, live_room):
        self._live_room = live_room
        self._cache: dict[str, tuple[float, list]] = {}

    def _get_cached(self, key: str) -> Optional[list]:
        """Return cached data if still fresh, else None."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.time() - ts < _CACHE_TTL:
            return data
        return None

    def _set_cache(self, key: str, data: list):
        self._cache[key] = (time.time(), data)

    async def get_fans_medal_rank(self) -> list[dict]:
        """Get fan medal ranking. Returns list of {uid, uname, medal_level}."""
        cached = self._get_cached("fans_medal")
        if cached is not None:
            return cached

        try:
            resp = await self._live_room.get_fans_medal_rank()
            items = resp.get("list", [])
            result = [
                {
                    "uid": item.get("uid", 0),
                    "uname": item.get("uname", ""),
                    "medal_level": item.get("medal_level", 0),
                }
                for item in items
            ]
            self._set_cache("fans_medal", result)
            return result
        except Exception as e:
            logger.warning("获取粉丝勋章排行失败: %s", e)
            return []

    async def get_dahanghai(self, page: int = 1) -> list[dict]:
        """Get guard member list (paginated). Returns list of {uid, uname, guard_level}."""
        cache_key = f"dahanghai_{page}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            resp = await self._live_room.get_dahanghai(page=page)
            items = resp.get("list", [])
            result = [
                {
                    "uid": item.get("uid", 0),
                    "uname": item.get("uname", ""),
                    "guard_level": item.get("guard_level", 0),
                }
                for item in items
            ]
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.warning("获取大航海贡献榜失败 (page=%d): %s", page, e)
            return []
