# -*- coding: utf-8 -*-
"""
粉丝勋章查询工具

用法:
    python query_medal.py                  # 交互模式
    python query_medal.py 小星星           # 直接查询
    python query_medal.py --list           # 列出所有
    python query_medal.py --stats          # 统计信息
"""

import json
import os
import sys

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medal_cache.json")


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def print_entry(medal_name: str, entry: dict):
    streamer = entry.get("streamer", "未知")
    room_id = entry.get("room_id", "未知")
    uid = entry.get("streamer_uid", "")
    updated = entry.get("updated_at", "")

    uid_str = f"  主播UID:  {uid}" if uid else ""
    updated_str = f"  更新时间: {updated}" if updated else ""
    print(f"  勋章名:   {medal_name}")
    print(f"  主播名:   {streamer}")
    print(f"  直播间:   {room_id}")
    if uid_str:
        print(uid_str)
    if updated_str:
        print(updated_str)


def cmd_search(keyword: str, cache: dict):
    keyword_lower = keyword.lower()
    results = []
    for name, entry in cache.items():
        if keyword_lower in name.lower():
            results.append((name, entry))
        elif keyword_lower in entry.get("streamer", "").lower():
            results.append((name, entry))

    if not results:
        print(f"未找到与 '{keyword}' 相关的勋章")
        return
    print(f"找到 {len(results)} 条结果:\n")
    for name, entry in results:
        print_entry(name, entry)
        print()


def cmd_list(cache: dict):
    if not cache:
        print("缓存为空，还没有收集到任何勋章数据")
        return
    print(f"共 {len(cache)} 条勋章映射:\n")
    # 按勋章名排序
    for name in sorted(cache.keys()):
        entry = cache[name]
        streamer = entry.get("streamer", "?")
        room_id = entry.get("room_id", "?")
        print(f"  {name:<20s} -> {streamer} (房间 {room_id})")


def cmd_stats(cache: dict):
    total = len(cache)
    has_streamer = sum(1 for e in cache.values() if e.get("streamer"))
    has_uid = sum(1 for e in cache.values() if e.get("streamer_uid"))
    print(f"总勋章数:   {total}")
    print(f"有主播名:   {has_streamer}")
    print(f"有主播UID:  {has_uid}")


def interactive(cache: dict):
    print("粉丝勋章查询 (输入勋章名或主播名搜索, q 退出, list 全部, stats 统计)")
    print()
    while True:
        try:
            query = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query.lower() == "q":
            break
        if query.lower() == "list":
            cmd_list(cache)
        elif query.lower() == "stats":
            cmd_stats(cache)
        else:
            cmd_search(query, cache)
        print()


def main():
    cache = load_cache()
    if not cache:
        print("缓存为空 (medal_cache.json 不存在或无数据)")
        print("请先运行机器人收集弹幕数据，或检查 medal_cache.json 文件")
        if len(sys.argv) <= 1:
            print("\n进入交互模式 (输入 q 退出)")
            interactive(cache)
        return

    args = sys.argv[1:]
    if not args:
        interactive(cache)
    elif args[0] == "--list":
        cmd_list(cache)
    elif args[0] == "--stats":
        cmd_stats(cache)
    else:
        keyword = " ".join(args)
        cmd_search(keyword, cache)


if __name__ == "__main__":
    main()
