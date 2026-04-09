# BiliBot 直播弹幕机器人

## What This Is

基于 blivedm + bilibili-api 的 B 站直播间弹幕自动响应机器人。v1.0 已实现完整的直播间管理功能：弹幕关键词回复、点歌（LX Music）、礼物感谢、SC 感谢、上舰感谢、进场欢迎、人气显示、自动禁言、查歌、粉丝排行榜、数据统计面板。暗色主题 tkinter GUI 控制面板。

## Core Value

让主播专注于直播内容，机器人自动处理直播间互动（欢迎、感谢、禁言、统计）。

## Current Milestone: v2.0 多房间同时监控

**Goal:** 将单房间弹幕机器人扩展为支持同时监控多个直播间，每个房间拥有独立的弹幕/点歌/排行/统计视图和日志。

**Target features:**
- 同时连接多个直播间（动态添加/移除房间）
- 多房间标签页切换（弹幕、点歌、排行、统计按房间独立）
- 日志按房间号分文件夹记录
- 手动发送弹幕（已实现）

## Current State

**Shipped:** v1.0 (2026-04-09) — 功能增强 MVP
- 30 requirements, 4 phases, 12 plans — all complete
- 1,929 LOC (app code), 20/20 success criteria verified
- See: [v1.0 Roadmap](milestones/v1.0-ROADMAP.md), [v1.0 Requirements](milestones/v1.0-REQUIREMENTS.md)

**Shipped:** v2.0 (2026-04-10) — 多房间同时监控
- 23 requirements, 4 phases, 5 plans — all complete
- 2,502 LOC (app code), all success criteria verified
- See: [v2.0 Roadmap](milestones/v2.0-ROADMAP.md), [v2.0 Requirements](milestones/v2.0-REQUIREMENTS.md)

**Planning:** Next milestone TBD

## Requirements

### Validated

- ✓ 弹幕关键词自动回复 — 已实现 (pre-v1.0)
- ✓ 点歌功能（LX Music scheme URL） — 已实现 (pre-v1.0)
- ✓ 礼物感谢（金瓜子 >= 990000） — 已实现 (pre-v1.0)
- ✓ SC 感谢 — 已实现 (pre-v1.0)
- ✓ 暗色主题 GUI 控制面板 — 已实现 (pre-v1.0)
- ✓ 弹幕过滤（自身弹幕、非本房间粉丝） — 已实现 (pre-v1.0)
- ✓ 上舰感谢（GuardBuyMessage 分级模板 + GUI 开关） — v1.0 Phase 1 & 4
- ✓ 进场欢迎（InteractWordV2Message 两级冷却 + GUI 开关） — v1.0 Phase 1 & 4
- ✓ 人气显示（HeartbeatMessage + GUI 顶栏） — v1.0 Phase 1 & 4
- ✓ 自动禁言（ban_words.txt + ban_user + GUI 开关 + 特殊颜色） — v1.0 Phase 2 & 4
- ✓ 查歌功能（QQ 音乐 API + 弹幕回复） — v1.0 Phase 2
- ✓ 粉丝排行榜（get_fans_medal_rank / get_dahanghai + GUI Tab） — v1.0 Phase 3 & 4
- ✓ 数据统计面板（实时计数/收入/排行/趋势图 + 重连重置） — v1.0 Phase 3 & 4
- ✓ 多房间同时连接（动态添加/移除，asyncio.gather） — v2.0 Phase 5 & 6
- ✓ 多房间标签页切换（自定义标签栏，状态点，右键断开） — v2.0 Phase 7
- ✓ 按房间日志（TimedRotatingFileHandler，30天保留） — v2.0 Phase 8
- ✓ 错误隔离（单房间故障不影响其他房间） — v2.0 Phase 8
- ✓ 房间数量限制（MAX_ROOMS=5） — v2.0 Phase 8

### Out of Scope

- AI 智能回复 — 需要 LLM API，属于下一个里程碑
- 定时公告 — 非核心功能，后续添加
- 自动开播/关播 — 后续里程碑
- 弹幕录制回放 — 后续里程碑
- Web 前端 — 保持 tkinter 桌面应用

## Context

- 技术栈：Python 3.9+ / tkinter / blivedm 1.1.5 / bilibili-api-python
- 消息处理架构：DanmakuBotHandler 继承 blivedm.BaseHandler，通过 msg_callback 回调通知 GUI
- GUI 架构：BiliBotGUI 使用 tkinter Notebook（点歌/排行/统计三 Tab），后台线程运行 bot，消息队列跨线程通信
- v2.0 抽象：RoomPanel（GUI 组件）、RoomContext（机器人状态）、theme.py（共享常量）
- 功能开关：guard_enabled / welcome_enabled / auto_ban_enabled，通过 GUI 设置菜单控制
- 数据统计：StatsCollector 线程安全计数器，FanRankingService 缓存 API 封装
- blivedm 已处理消息：DanmakuMessage, GiftMessage, GuardBuyMessage, HeartbeatMessage, InteractWordV2Message, SuperChatMessage
- bilibili_api.live.LiveRoom 已用方法：ban_user, get_dahanghai, get_fans_medal_rank, get_room_play_info

## Constraints

- **Tech Stack**: Python + tkinter — 不引入 web 框架
- **API 限制**: B 站 API 有频率限制，发送弹幕需冷却（当前 3 秒）
- **运行环境**: Windows 桌面应用
- **依赖**: blivedm 1.1.5, bilibili-api-python, aiohttp
- **GUI 复杂度**: tkinter 图表能力有限，趋势图用 Canvas 柱状图实现

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 上舰感谢用可配置模板 | 不同主播感谢风格不同 | ✓ 三级模板，config.py 可配 |
| 进场欢迎用两级冷却 | 避免高频房间刷屏 | ✓ 全局10s + 用户5min 冷却 |
| 敏感词用文件配置 | 方便主播随时编辑 | ✓ ban_words.txt, UTF-8 |
| 查歌用 QQ 音乐 API | 与现有点歌源一致 | ✓ aiohttp 直接调用 |
| 开关放 GUI 顶栏下拉 | 操作便捷 | ✓ Menubutton 三项 checkbox |
| 统计数据按连接会话 | 避免混淆不同房间 | ✓ reconnect 时 reset |
| 趋势图用 Canvas | 0 依赖，匹配暗色主题 | ✓ 最近30分钟柱状图 |
| 排行 API 带缓存 | 避免频繁调用 B 站 API | ✓ 5 分钟 TTL |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-09 — Phase 5 (Abstraction Extraction) complete*
*Updated: 2026-04-09 — v2.0 milestone started*
