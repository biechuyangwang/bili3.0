# -*- coding: utf-8 -*-
"""
数据统计模块 - 线程安全的会话级事件计数器

在弹幕机器人运行期间收集弹幕、SC、礼物、上舰等统计数据，
支持按用户排行和时间线追踪。重连时自动重置。
"""

import threading
import time


class StatsCollector:
    """Thread-safe session statistics collector.

    All increment methods are safe to call from any thread.
    Reset on reconnect.
    """

    def __init__(self):
        self._reset()

    def _reset(self):
        self._counts = {"danmaku": 0, "sc": 0, "gift": 0, "guard": 0}
        self._sc_revenue = 0.0  # yuan
        self._gift_value = 0    # gold coins (金瓜子)
        self._user_danmaku = {}  # uname -> count
        self._user_gift = {}     # uname -> total gold coins
        self._user_sc = {}       # uname -> total yuan
        self._timeline = []      # [(minute_timestamp, danmaku_count)]
        self._current_minute = 0
        self._current_minute_count = 0
        self._lock = threading.Lock()

    def reset(self):
        """Reset all stats, typically called on reconnect."""
        with self._lock:
            self._reset()

    def record_danmaku(self, uname: str):
        with self._lock:
            self._counts["danmaku"] += 1
            self._user_danmaku[uname] = self._user_danmaku.get(uname, 0) + 1
            # Timeline tracking
            now_min = int(time.time()) // 60
            if now_min != self._current_minute:
                if self._current_minute > 0:
                    self._timeline.append((self._current_minute, self._current_minute_count))
                self._current_minute = now_min
                self._current_minute_count = 1
            else:
                self._current_minute_count += 1

    def record_sc(self, uname: str, price: int):
        with self._lock:
            self._counts["sc"] += 1
            self._sc_revenue += price
            self._user_sc[uname] = self._user_sc.get(uname, 0) + price

    def record_gift(self, uname: str, total_gold: int):
        with self._lock:
            self._counts["gift"] += 1
            self._gift_value += total_gold
            self._user_gift[uname] = self._user_gift.get(uname, 0) + total_gold

    def record_guard(self):
        with self._lock:
            self._counts["guard"] += 1

    def get_stats(self) -> dict:
        """Return snapshot of all stats."""
        with self._lock:
            return {
                "counts": dict(self._counts),
                "sc_revenue": self._sc_revenue,
                "gift_value": self._gift_value,
                "top_danmaku": sorted(self._user_danmaku.items(), key=lambda x: -x[1])[:5],
                "top_gift": sorted(self._user_gift.items(), key=lambda x: -x[1])[:5],
                "top_sc": sorted(self._user_sc.items(), key=lambda x: -x[1])[:5],
                "timeline": list(self._timeline),
            }
