# Phase 3+4 Design: Utility & Interaction

## Context

Claudium is now a distributable package (Phase 1 complete). Next: add practical utility and interactivity to the aquarium TUI.

**Goals**: Make the aquarium informative (not just decorative), add navigation, keep it fun.

## Screen Layout

Split the current fullscreen aquarium into **aquarium (top) + bottom panel (~6 rows)**.

```
┌──────────────────────────────────┐
│                                  │
│        Aquarium (main area)      │
│    ><(((°>     ><((°>            │
│     Edit: cli.py 3s              │
│                                  │
├──────────────────────────────────┤
│ 12:03:15  tool_start  Bash: npm  │
│ 12:03:14  agent_start  explore   │
│ [Tab: Log] [Tab: Stats]         │
└──────────────────────────────────┘
```

Bottom panel modes (cycle with `Tab`):
- **Log**: Recent event timeline
- **Stats**: Session statistics dashboard
- **Detail**: Agent detail view (auto-activates on fish selection)

## Speech Bubbles

Each fish displays its last tool call above it: `Edit: cli.py 3s`. Fades after ~10 seconds. Extends the existing `ToolBubble` label system.

## Cursor Navigation

- `←` `→` arrow keys: cycle through active fish
- Selected fish: highlighted (bold/reverse color)
- `Esc`: deselect
- Selection auto-switches bottom panel to Detail mode

## Event Log (Bottom Panel: Log)

- Recent N events in reverse chronological order
- Format: `HH:MM:SS  event_type  detail`
- Scrollable with `↑` `↓` when panel is focused
- Error events in red

## Session Stats (Bottom Panel: Stats)

- Total agents / currently active
- Tool usage counts (top 5)
- Total events
- Session elapsed time
- Error count

## Agent Detail (Bottom Panel: Detail)

Shown when a fish is selected via cursor:

```
Agent: explore (abc123) | Status: WORKING 12s | Tools: Read(3) Grep(2) Bash(1) | Last: Read server.py
```

## Milestone Easter Eggs

- 100th tool call → whale appears
- 10th agent → shark appears
- Error-free session completion → rainbow effect

## Keyboard Summary

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `D` | Spawn demo fish |
| `Tab` | Cycle bottom panel mode |
| `←` `→` | Select fish |
| `Esc` | Deselect fish |
| `↑` `↓` | Scroll log (when in Log mode) |
