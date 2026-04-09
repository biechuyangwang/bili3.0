# Roadmap: BiliBot 直播弹幕机器人

## Milestones

### v1.0 — 功能增强 MVP (2026-04-09)
[Full roadmap →](milestones/v1.0-ROADMAP.md) | [Requirements →](milestones/v1.0-REQUIREMENTS.md)

4 phases, 12 plans, 30 requirements — all complete.

Guard thanks, entry welcome, QQ Music search, auto-ban, stats collection, fan ranking, full GUI integration (settings toggles, popularity, ranking tabs, statistics panel with Canvas charts).

### v2.0 — 多房间同时监控 (In Progress)

4 phases, 23 requirements — 0 complete.

Multi-room simultaneous live stream monitoring. Each room gets isolated bot components and its own GUI tab with danmaku view, song list, ranking, and statistics. Rooms are dynamically added/removed at runtime.

## Phases

- [x] **Phase 5: Abstraction Extraction** - Extract RoomPanel and RoomContext abstractions from singleton GUI state
- [ ] **Phase 6: Multi-Client Bot Thread** - Run multiple BLiveClient instances in a shared asyncio event loop
- [ ] **Phase 7: Dynamic Room Tabs GUI** - Outer Notebook with per-room panels, add/remove tabs at runtime
- [ ] **Phase 8: Polish and Error Recovery** - Room limits, per-room logging, error isolation, retry flow

## Phase Details

### Phase 5: Abstraction Extraction
**Goal**: The existing single-room code is reorganized into reusable abstractions (RoomPanel for GUI, RoomContext for bot state) while single-room behavior remains identical.
**Depends on**: Nothing (foundation phase)
**Requirements**: MROOM-04, MROOM-05
**Success Criteria** (what must be TRUE):
  1. A single room connects and all existing features work exactly as before (danmaku, songs, ranking, stats, settings toggles)
  2. All per-room state (handler, stats, fan ranking, sender, GUI widgets) is contained in a RoomContext/RoomPanel class, not loose attributes on BiliBotGUI
  3. One shared aiohttp.ClientSession and one asyncio event loop are explicitly managed and passed to room components
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md — Create RoomPanel (GUI widgets) and RoomContext (bot state) abstraction classes
- [x] 05-02-PLAN.md — Refactor gui.py to use RoomContext/RoomPanel, verify single-room behavior unchanged

### Phase 6: Multi-Client Bot Thread
**Goal**: The bot daemon thread can manage multiple simultaneous BLiveClient connections, each independently startable and stoppable.
**Depends on**: Phase 5
**Requirements**: MROOM-01, MROOM-02, MROOM-03
**Success Criteria** (what must be TRUE):
  1. User can connect to 2+ rooms simultaneously and receive danmaku from all rooms
  2. User can add a new room connection while existing rooms continue receiving messages uninterrupted
  3. User can disconnect one room without affecting other rooms' connections or message flow
**Plans**: 1 plan

Plans:
- [x] 06-01-PLAN.md — Add MAX_ROOMS config and rewrite bot thread for multi-client lifecycle with runtime add/disconnect

### Phase 7: Dynamic Room Tabs GUI
**Goal**: Users see one tab per connected room in a Notebook, with each tab containing the full panel set and independently scrollable content.
**Depends on**: Phase 6
**Requirements**: TABS-01, TABS-02, TABS-03, TABS-04, TABS-05, GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06
**Success Criteria** (what must be TRUE):
  1. User can switch between room tabs and see each room's danmaku, song list, ranking, and statistics independently
  2. Switching away from a tab and back preserves that room's scroll position and message history
  3. Each tab label shows the room number and a colored connection status dot
  4. User can close a room tab, which disconnects that room and removes its tab
  5. Top bar shows total connected room count and highlights the active room
**Plans**: TBD
**UI hint**: yes

### Phase 8: Polish and Error Recovery
**Goal**: Multi-room operation is production-ready with per-room logging, error isolation, and resource limits.
**Depends on**: Phase 7
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, LOG-01, LOG-02, LOG-03
**Success Criteria** (what must be TRUE):
  1. One room disconnecting or crashing shows a red error indicator on its tab while all other rooms continue normally
  2. Each room's danmaku log writes to logs/{room_id}/danmaku.log with daily rotation and 30-day retention
  3. User can retry a failed room by closing its tab and re-adding the room number
  4. Application refuses to add rooms beyond the configured maximum (default 5) and shows a message explaining the limit
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 5. Abstraction Extraction | 2/2 | Complete | 2026-04-09 |
| 6. Multi-Client Bot Thread | 0/1 | Not started | - |
| 7. Dynamic Room Tabs GUI | 0/? | Not started | - |
| 8. Polish and Error Recovery | 0/? | Not started | - |
