---
phase: "07"
plan: "01"
subsystem: gui
tags: [multi-room, tabs, custom-tab-bar, welcome-placeholder, status-dots, context-menu]
dependency_graph:
  requires: [room_panel.py, room_context.py, theme.py, config.py]
  provides: [multi-tab-gui, custom-tab-bar, welcome-placeholder, top-bar-aggregation]
  affects: [gui.py]
tech_stack:
  added: []
  patterns: [custom-tab-bar-with-status-dots, pack-forget-content-switching, single-source-top-bar-state]
key_files:
  created: []
  modified:
    - path: gui.py
      changes: "Added custom tab bar infrastructure, welcome placeholder, content area, _update_top_bar_state; rewrote _connect/_disconnect_room/_disconnect/_toggle/_poll_queue for multi-tab management"
decisions:
  - "Custom tab bar (tk.Frame) instead of ttk.Notebook for room tabs -- enables Canvas status dots in tab buttons"
  - "pack/pack_forget for content switching instead of ttk.Notebook -- simpler, preserves widget state naturally"
  - "_update_top_bar_state as single source of truth for button text, status, dots -- prevents state machine desync"
  - "_toggle always calls _connect -- per-room disconnect is via right-click only"
metrics:
  duration: "5 minutes"
  completed: "2026-04-10"
---

# Phase 7 Plan 1: Dynamic Room Tabs GUI Summary

Custom tab bar with per-room status dots and welcome placeholder, replacing single-panel layout for multi-room simultaneous monitoring.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Build custom tab bar, welcome placeholder, and content area infrastructure | 5e4814e | gui.py |
| 2 | Reconnect _connect, _disconnect_room, _toggle, _disconnect, _poll_queue, _update_top_bar_state | 8a48125 | gui.py |
| 3 | Manual verification of multi-room tabbed GUI | auto-approved | N/A |

## Changes Made

### Task 1: Tab Bar Infrastructure
- Added `_tab_buttons`, `_room_frames`, `_welcome` data attributes to BiliBotGUI
- Modified `_build_ui` to include custom tab bar, separator, content area, and welcome placeholder
- Created `_build_welcome` with centered "BiliBot" title and instruction text using `place()` geometry
- Created `_create_tab_button` building tk.Frame with 8x8 Canvas dot + "房间 {id}" label, with Button-1 and Button-3 bindings
- Created `_select_room` for tab switching using pack/pack_forget with active room tracking
- Created `_update_tab_bar_selection` for active/inactive visual state (bg/fg color swap)
- Created `_show_tab_menu` for right-click "断开连接" context menu
- Created `_update_tab_dot` for per-room status dot color changes via `itemconfig`

### Task 2: Multi-Tab Method Rewiring
- Simplified `_toggle` to always call `_connect` (no disconnect from top bar)
- Rewrote `_connect` to create per-room content Frame, add tab button, hide welcome, select new room
- Rewrote `_disconnect_room` to destroy content Frame and tab button, show welcome if last room
- Rewrote `_disconnect` (app shutdown) to clean all tab infrastructure and show welcome
- Added `_update_top_bar_state` as single source of truth: "连 接" at 0 rooms, "添加房间" at 1+ rooms
- Removed multi-room prefix hack (`if len(self._rooms) > 1`) from all message handlers in `_poll_queue`
- Wired status handler to call `_update_top_bar_state` and `_update_tab_dot(COLOR_SUCCESS/FG_MUTED)`
- Wired error handler to show red dot on failed room tab and update top bar state
- Removed `_room_entry.config(state=tk.NORMAL)` toggles (entry stays enabled)

## Deviations from Plan

None -- plan executed exactly as written.

## Auto-Approved Checkpoints

- Task 3 (checkpoint:human-verify): Auto-approved in automation mode. All automated verification passed: methods exist, import succeeds, _toggle simplified, prefix hack removed, top bar state has both button texts.

## Verification Results

All automated checks passed:
- `from gui import BiliBotGUI` imports without error
- All 7 new methods exist: _build_welcome, _create_tab_button, _select_room, _update_tab_bar_selection, _show_tab_menu, _update_tab_dot, _update_top_bar_state
- _toggle body is just `self._connect()` with no _disconnect reference
- _poll_queue does not contain `len(self._rooms) > 1` prefix hack
- _update_top_bar_state contains both "连 接" and "添加房间" button text strings

## Self-Check: PASSED
