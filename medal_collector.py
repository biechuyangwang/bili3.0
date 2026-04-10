# -*- coding: utf-8 -*-
"""
粉丝勋章映射收集器

从弹幕、礼物、SC 消息中被动收集 勋章名→主播/房间 映射，
定期持久化到 JSON 文件，供 query_medal.py 查询。

数据结构 (medal_cache.json):
{
    "勋章名": {
        "streamer": "主播名",
        "room_id": 12345,
        "streamer_uid": 67890,
        "updated_at": "2026-04-10T12:00:00"
    }
}

不同消息类型提供的字段不同：
- DanmakuMessage: medal_name, runame(主播名), medal_room_id
- GiftMessage:    medal_name, medal_room_id, medal_ruid(主播UID)
- SuperChatMessage: 同 GiftMessage
收集时会自动合并互补信息。
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("danmaku_bot.medal")

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medal_cache.json")


class MedalCollector:
    """粉丝勋章映射收集器，线程安全，定期落盘。"""

    def __init__(self, save_interval: float = 60.0):
        """
        Args:
            save_interval: 自动保存间隔秒数，默认 60 秒。
        """
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}
        self._dirty = False
        self._save_interval = save_interval
        self._timer: Optional[threading.Timer] = None
        self._load()

    # ── 持久化 ──

    def _load(self):
        """从 JSON 文件加载缓存。"""
        if not os.path.exists(CACHE_FILE):
            logger.debug("勋章缓存文件不存在，从空开始收集")
            return
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info("已加载 %d 条勋章映射", len(self._cache))
        except Exception as e:
            logger.warning("加载勋章缓存失败，从空开始: %s", e)
            self._cache = {}

    def save(self):
        """将当前缓存写入 JSON 文件。"""
        with self._lock:
            if not self._dirty:
                return
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, ensure_ascii=False, indent=2)
                self._dirty = False
                logger.debug("勋章缓存已保存 (%d 条)", len(self._cache))
            except Exception as e:
                logger.error("保存勋章缓存失败: %s", e)

    def start_periodic_save(self):
        """启动定期保存定时器。"""
        self._schedule_next()

    def stop(self):
        """停止定时器并做最后一次保存。"""
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self.save()

    def _schedule_next(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self._save_interval, self._periodic_save)
        self._timer.daemon = True
        self._timer.start()

    def _periodic_save(self):
        self.save()
        self._schedule_next()

    # ── 数据收集 ──

    def collect_from_danmaku(self, medal_name: str, runame: str, medal_room_id: int):
        """从弹幕消息收集勋章信息（提供主播名）。

        Args:
            medal_name: 勋章名，为空则跳过。
            runame: 勋章房间主播名。
            medal_room_id: 勋章房间ID。
        """
        if not medal_name or not medal_room_id:
            return
        self._update(medal_name, streamer=runame, room_id=medal_room_id)

    def collect_from_gift_or_sc(self, medal_name: str, medal_room_id: int, medal_ruid: int):
        """从礼物/SC 消息收集勋章信息（提供主播UID）。

        Args:
            medal_name: 勋章名，为空则跳过。
            medal_room_id: 勋章房间ID。
            medal_ruid: 勋章主播UID。
        """
        if not medal_name or not medal_room_id:
            return
        self._update(medal_name, room_id=medal_room_id, streamer_uid=medal_ruid)

    def _update(self, medal_name: str, streamer: str = "", room_id: int = 0,
                streamer_uid: int = 0):
        with self._lock:
            entry = self._cache.get(medal_name)
            if entry is None:
                entry = {}
                self._cache[medal_name] = entry

            updated = False

            # 合并：仅在新值非空且与旧值不同时更新
            if streamer and entry.get("streamer") != streamer:
                entry["streamer"] = streamer
                updated = True
            if room_id and entry.get("room_id") != room_id:
                entry["room_id"] = room_id
                updated = True
            if streamer_uid and entry.get("streamer_uid") != streamer_uid:
                entry["streamer_uid"] = streamer_uid
                updated = True

            if updated:
                entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._dirty = True

    # ── 查询 ──

    def get(self, medal_name: str) -> Optional[dict]:
        """查询单条映射。"""
        with self._lock:
            return self._cache.get(medal_name)

    def search(self, keyword: str) -> list[tuple[str, dict]]:
        """模糊搜索，返回 (medal_name, entry) 列表。"""
        keyword_lower = keyword.lower()
        with self._lock:
            results = []
            for name, entry in self._cache.items():
                if keyword_lower in name.lower():
                    results.append((name, entry))
                elif keyword_lower in entry.get("streamer", "").lower():
                    results.append((name, entry))
            return results

    def count(self) -> int:
        with self._lock:
            return len(self._cache)
