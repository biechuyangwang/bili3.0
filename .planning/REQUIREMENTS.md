# Requirements: BiliBot v2.0

**Defined:** 2026-04-09
**Core Value:** 让主播专注直播内容，机器人自动处理直播间互动（欢迎、感谢、禁言、统计）

## v2 Requirements

### Multi-Room Core

- [x] **MROOM-01**: User can connect to multiple live rooms simultaneously via shared event loop
- [x] **MROOM-02**: User can add a new room connection at runtime without disconnecting existing rooms
- [x] **MROOM-03**: User can disconnect a specific room without affecting other room connections
- [x] **MROOM-04**: Each room has its own isolated DanmakuBotHandler, StatsCollector, FanRankingService, and DanmakuSender instance
- [x] **MROOM-05**: All BLiveClient instances share one aiohttp.ClientSession and one asyncio event loop

### Room Tab Switching

- [ ] **TABS-01**: User can switch between connected rooms via outer Notebook tabs
- [ ] **TABS-02**: Each room tab contains the full panel set: danmaku view, song list, ranking, statistics
- [ ] **TABS-03**: Switching tabs preserves each room's scroll position, stats state, and message history
- [ ] **TABS-04**: Tab label shows room number and connection status indicator (colored dot)
- [ ] **TABS-05**: User can close a room tab (disconnects that room)

### Per-Room GUI

- [ ] **GUI-01**: Each room has its own danmaku text area with color-coded messages
- [ ] **GUI-02**: Each room has its own song request treeview
- [ ] **GUI-03**: Each room has its own ranking tab (medal + guard)
- [ ] **GUI-04**: Each room has its own statistics panel (counts, revenue, trend chart)
- [ ] **GUI-05**: Each room has its own manual danmaku send bar
- [ ] **GUI-06**: Top bar shows aggregated status (total rooms connected, active room highlighted)

### Per-Room Logging

- [ ] **LOG-01**: Each room's log writes to a separate folder: logs/{room_id}/danmaku.log
- [ ] **LOG-02**: Log files use same TimedRotatingFileHandler pattern (daily rotation, 30-day retention)
- [ ] **LOG-03**: Adding a room creates its log folder; removing a room does not delete existing logs

### Error Recovery

- [ ] **ERR-01**: One room disconnecting does not crash or affect other room connections
- [ ] **ERR-02**: Failed room connection shows error status on its tab (red dot + error message)
- [ ] **ERR-03**: User can retry connecting to a failed room by closing and re-adding it
- [ ] **ERR-04**: Application enforces a configurable maximum room limit (default: 5)

## v2.1+ Requirements

Deferred to future milestone.

### Room Management Enhancements

- **RMGT-01**: User can save a list of favorite rooms for quick reconnection
- **RMGT-02**: Room tabs show streamer name (requires API call per room)
- **RMGT-03**: User can set per-room feature toggles independently

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web-based frontend | Tech stack constraint: tkinter only |
| Room data persistence across sessions | Requires database, defer to future |
| Cross-room message forwarding | New capability, not core multi-room |
| AI-powered responses | Requires LLM API, separate milestone |
| Auto stream start/stop detection | Separate milestone feature |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MROOM-01 | Phase 6 | Complete |
| MROOM-02 | Phase 6 | Complete |
| MROOM-03 | Phase 6 | Complete |
| MROOM-04 | Phase 5 | Complete |
| MROOM-05 | Phase 5 | Complete |
| TABS-01 | Phase 7 | Pending |
| TABS-02 | Phase 7 | Pending |
| TABS-03 | Phase 7 | Pending |
| TABS-04 | Phase 7 | Pending |
| TABS-05 | Phase 7 | Pending |
| GUI-01 | Phase 7 | Pending |
| GUI-02 | Phase 7 | Pending |
| GUI-03 | Phase 7 | Pending |
| GUI-04 | Phase 7 | Pending |
| GUI-05 | Phase 7 | Pending |
| GUI-06 | Phase 7 | Pending |
| LOG-01 | Phase 8 | Pending |
| LOG-02 | Phase 8 | Pending |
| LOG-03 | Phase 8 | Pending |
| ERR-01 | Phase 8 | Pending |
| ERR-02 | Phase 8 | Pending |
| ERR-03 | Phase 8 | Pending |
| ERR-04 | Phase 8 | Pending |

**Coverage:**
- v2 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 — traceability updated after roadmap creation*
