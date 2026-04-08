<!-- GSD:project-start source:PROJECT.md -->
## Project

**BiliBot 直播弹幕机器人功能增强**

基于 blivedm + bilibili-api 的 B 站直播间弹幕自动响应机器人。已实现弹幕关键词回复、点歌（LX Music）、礼物感谢（>=990000金瓜子）、SC 感谢、暗色主题 GUI 控制面板。本次里程碑为机器人增加上舰感谢、进场欢迎、人气显示、自动禁言、查歌、粉丝排行榜、数据统计面板等功能，使其成为功能完整的直播间管理工具。

**Core Value:** 让主播专注于直播内容，机器人自动处理直播间互动（欢迎、感谢、禁言、统计）。

### Constraints

- **Tech Stack**: Python + tkinter — 不引入 web 框架
- **API 限制**: B 站 API 有频率限制，发送弹幕需冷却（当前 3 秒）
- **运行环境**: Windows 桌面应用
- **依赖**: blivedm 1.1.5（已安装），bilibili-api-python（已安装）
- **GUI 复杂度**: tkinter 图表能力有限，趋势图用简单文本/Canvas 实现
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack Additions
### New Dependencies
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| aiohttp (existing) | current | QQ Music search HTTP calls | Already in the project for blivedm WebSocket. Use the same session to call QQ Music search endpoint. No new HTTP client needed. |
| tkinter.Canvas (stdlib) | built-in | Trend charts in statistics dashboard | Zero dependencies. The dashboard only needs simple bar charts and line graphs. Canvas handles this natively and matches the existing dark theme seamlessly. matplotlib would be 30+ MB of dependency for a feature that draws 10 bars. |
### No New Package Installs Required
- **tkinter** is stdlib -- Canvas drawing for charts
- **aiohttp** already installed -- HTTP client for QQ Music API
- **blivedm** already has all needed message types (verified in source)
- **bilibili-api-python** already has `ban_user`, `get_dahanghai`, `get_fans_medal_rank` (verified in source)
- **json** (stdlib) -- for ban_words config file parsing
- **pathlib** (stdlib) -- for config file path handling
## Feature-by-Feature Stack Decisions
### 1. QQ Music Song Search -- Use aiohttp Directly
- `qq-music-api` on PyPI exists but is a third-party wrapper around the same unofficial endpoints. It adds a dependency for something that is a single HTTP GET call.
- The project already has aiohttp and already manages HTTP sessions. Adding another HTTP client library is unnecessary.
- QQ Music does not have an official public API. All approaches use the same unofficial endpoints. A thin wrapper in our own code is more maintainable than depending on a third-party package that could stop being maintained.
### 2. tkinter Charting -- Use Canvas Directly
- matplotlib is ~30 MB installed. For a desktop bot that needs to draw simple bar charts of message counts, this is massive overkill.
- matplotlib embedding in tkinter (`FigureCanvasTkAgg`) introduces threading complexity. The bot already runs an asyncio loop in a background thread; adding matplotlib's event loop interaction is a known source of bugs.
- matplotlib rendering is slower for real-time updates than direct Canvas drawing.
- The dark theme styling already defined in `gui.py` (BG_ELEVATED, FG_SECONDARY, ACCENT, etc.) applies directly to Canvas. With matplotlib, you would fight its own styling system.
- plotly requires a web server or webview -- contradicts the "no web framework" constraint.
- pyqtgraph requires PyQt -- would replace tkinter entirely.
- pygal generates SVG files, not live widgets.
### 3. File-Based Ban Words Config -- Plain Text with Comment Support
- The config is a flat list of banned words/phrases. JSON adds bracket/quote syntax noise for what is a simple list.
- YAML requires a PyYAML dependency. Not worth it for a list of strings.
- TOML is available in stdlib since Python 3.11, but the project targets 3.9+.
- Plain text is the most accessible format for a streamer who just wants to add "badword1" on a new line.
- The existing `config.py` pattern uses Python variables. A separate text file is cleaner because it separates "code config" from "data config" -- the streamer can edit `ban_words.txt` without touching Python code.
# ban_words.txt - sensitive words for auto-ban, one per line
# Lines starting with # are comments, blank lines are ignored
- Returns empty list (not error) if file missing -- auto-ban simply disabled if no config file.
- UTF-8 encoding -- Chinese ban words must work.
- Hot reload support: call `load_ban_words()` periodically or on a GUI "reload" button press. The function is cheap (reads one small file).
### 4. blivedm Message Types to Handle
- `_on_danmaku` (DANMU_MSG) -- yes
- `_on_super_chat` (SUPER_CHAT_MESSAGE) -- yes
- `_on_gift` (SEND_GIFT) -- yes
- `_on_heartbeat` (_HEARTBEAT) -- stub only, logs debug
| Handler Method | blivedm cmd | Message Class | Purpose | Key Fields |
|----------------|-------------|---------------|---------|------------|
| `_on_buy_guard` | `GUARD_BUY` | `GuardBuyMessage` | Guard purchase thanks | `uid`, `username`, `guard_level` (1=governor, 2=admiral, 3=captain), `num`, `price` |
| `_on_user_toast_v2` | `USER_TOAST_MSG_V2` | `UserToastV2Message` | Richer guard purchase data | Same + `unit`, `source`, `toast_msg` |
| `_on_interact_word_v2` | `INTERACT_WORD_V2` | `InteractWordV2Message` | Entry welcome | `uid`, `username`, `msg_type` (1=enter, 2=follow, etc.) |
| `_on_heartbeat` (enhance) | `_HEARTBEAT` | `HeartbeatMessage` | Popularity display | `popularity` (note: field marked "deprecated" in blivedm but still populated) |
- Line 93: `'_HEARTBEAT'` -> `_on_heartbeat`
- Line 101: `'GUARD_BUY'` -> `_on_buy_guard`
- Line 103: `'USER_TOAST_MSG_V2'` -> `_on_user_toast_v2`
- Line 109: `'INTERACT_WORD_V2'` -> `_on_interact_word_v2`
### 5. bilibili-api Methods for Fan Ranking
| Method | Line | Purpose | Key Return Fields |
|--------|------|---------|-------------------|
| `LiveRoom.get_fans_medal_rank()` | 411 | Fan medal ranking | `top3`, `list` with uid, uname, medal_level |
| `LiveRoom.get_dahanghai(page)` | 353 | Guard member list (paginated) | `top3`, `list` with uid, uname, guard_level |
| `LiveRoom.get_seven_rank()` | 395 | 7-day contribution ranking | Contribution data for top users |
| `LiveRoom.ban_user(uid, hour)` | 498 | Ban user from chat | Success/failure |
| `LiveRoom.unban_user(uid)` | 521 | Unban user | Success/failure |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| QQ Music search | aiohttp direct call | `qq-music-api` PyPI package | Adds dependency for one HTTP GET. Unofficial wrapper around same endpoints. |
| QQ Music search | aiohttp direct call | `requests` library | Project already uses aiohttp for async. Mixing sync requests with asyncio is a known anti-pattern. |
| Chart rendering | tkinter Canvas | matplotlib | 30+ MB dependency, threading issues with tkinter, styling mismatch with dark theme |
| Chart rendering | tkinter Canvas | pyqtgraph | Requires PyQt, would replace tkinter |
| Chart rendering | tkinter Canvas | customtkinter chart widgets | customtkinter does not provide chart widgets |
| Ban words config | Plain text file | JSON file | More syntax noise for a flat list. Streamers less likely to edit correctly. |
| Ban words config | Plain text file | Python dict in config.py | Separating data from code is better practice. Streamer can edit without touching Python. |
| Ban words config | Plain text file | TOML file | stdlib TOML requires Python 3.11+. Project targets 3.9+. |
| Ban words matching | Simple `in` check | regex patterns | Over-engineering. Ban words are literal phrases, not patterns. regex would need escaping. |
| Ban words matching | Simple `in` check | Aho-Corasick algorithm | Over-engineering for likely < 100 ban words. Linear scan is fast enough. |
## Installation
# No new packages needed!
# All features use existing dependencies:
#   aiohttp, blivedm, bilibili-api-python, tkinter (stdlib)
# The project should create one new data file:
#   ban_words.txt  (in project root, alongside config.py)
## Dependency Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| QQ Music search endpoint changes URL/response format | Medium | Low (feature degrades gracefully) | Wrap in try/except, log error, skip reply |
| HeartbeatMessage.popularity stops being populated | Low | Low (display shows 0) | Display "N/A" if value is 0 for extended time |
| blivedm needs update for new B站 protocol changes | Low | High (all WS features break) | blivedm is vendored, can patch locally |
| bilibili-api methods signature changes | Low | Medium | Methods are used as documented, vendored copy is frozen |
## Confidence Assessment
| Recommendation | Confidence | Source | Notes |
|---------------|------------|--------|-------|
| aiohttp for QQ Music search | MEDIUM | Training data + community patterns | Endpoint verified from docs/community, not live-tested. Unofficial API. |
| Canvas for charts | HIGH | stdlib, well-understood | Canvas is Python stdlib. Existing code already uses it for status dot. |
| Plain text ban words | HIGH | Standard pattern | No dependency. Simple. Proven. |
| blivedm message types | HIGH | Source code verified | Read `handlers.py` and `models/web.py` directly. |
| bilibili-api methods | HIGH | Source code verified | Read `live.py` directly. Method signatures confirmed. |
## Sources
- `D:/github/bili3.0/blivedm/blivedm/handlers.py` -- message type dispatch table, verified all CMD_CALLBACK_DICT entries
- `D:/github/bili3.0/blivedm/blivedm/models/web.py` -- all message model dataclasses, field names, types
- `D:/github/bili3.0/bilibili-api/bilibili_api/live.py` -- LiveRoom methods (ban_user, get_dahanghai, get_fans_medal_rank, get_seven_rank)
- `D:/github/bili3.0/gui.py` -- existing GUI architecture, threading model, message queue pattern
- `D:/github/bili3.0/bot.py` -- current handler implementation, message flow
- `D:/github/bili3.0/song_request.py` -- existing song request architecture
- QQ Music search API: community-documented unofficial endpoint at `c.y.qq.com/soso/fcgi-bin/client_search_cp`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
