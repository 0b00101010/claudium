# Claudium Evolution Design

## Context

Claudium is a TUI aquarium that visualizes Claude Code agent/tool activity in real-time.
Currently a flat Python project (~2000 LOC) with zero external dependencies.

**Goals**: Personal fun + community sharing + practical utility.
**Priority**: Make it distributable first, then enhance visuals/usability/interactivity.

## Phase 1: Package Structure Refactoring

Restructure from flat scripts to an installable Python package.

### Directory Layout

```
claudium/
├── pyproject.toml
├── src/
│   └── claudium/
│       ├── __init__.py
│       ├── __main__.py     # python -m claudium
│       ├── cli.py          # unified CLI (run, install, uninstall)
│       ├── aquarium.py
│       ├── entities.py
│       ├── server.py
│       └── hook_sender.py
├── tests/
└── README.md
```

### Key Changes

- **Unified CLI**: Merge `main.py` + `install.py` into `cli.py`
  - `claudium` or `claudium run` — start aquarium
  - `claudium install` — install Claude Code hooks
  - `claudium uninstall` — remove hooks
  - `claudium --demo` — demo mode
- **src layout**: Standard Python packaging convention
- **pyproject.toml**: Full metadata, `[project.scripts]` entry point
- **`python -m claudium`** support via `__main__.py`
- Tests updated for new import paths

### pyproject.toml Entry Points

```toml
[project.scripts]
claudium = "claudium.cli:main"
```

## Phase 2: Visual Quality Improvements

- New creature types: shark (large agent), seahorse, stingray
- Particle effects: sparkles on completion, lightning on error
- Time-based sky: real clock drives day/night cycle and colors
- Weather effects: rain/snow above water surface
- Smoother spawn/despawn animations

## Phase 3: Practical Utility

- Speech bubbles: show current file/tool info next to fish
- Event log panel: toggleable recent event timeline (bottom or side)
- Session stats: tool call counts, agent lifetimes, summary dashboard
- Error alerts: visual warning when agent errors occur

## Phase 4: Interactivity

- Cursor selection: navigate to a fish and view details
- Environment customization: background themes, floor styles
- Easter eggs: special creatures on milestones (e.g., whale at 100th tool call)
