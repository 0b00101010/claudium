# Phase 1: Package Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure Claudium from flat scripts into an installable Python package with a unified CLI.

**Architecture:** Move all source modules under `src/claudium/`, merge `main.py` + `install.py` into a single `cli.py` with subcommands, and configure `pyproject.toml` with entry points so `pip install .` yields `claudium` and `claudium-hook` commands.

**Tech Stack:** Python 3.10+, stdlib only, pyproject.toml (no setup.py)

---

### Task 1: Create package directory and `__init__.py`

**Files:**
- Create: `src/claudium/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p src/claudium
```

**Step 2: Create `__init__.py`**

```python
"""Claudium - Claude Code Aquarium Visualizer."""

__version__ = "0.1.0"
```

**Step 3: Commit**

```bash
git add src/claudium/__init__.py
git commit -m "chore: create src/claudium package skeleton"
```

---

### Task 2: Move source modules into package

**Files:**
- Move: `entities.py` → `src/claudium/entities.py`
- Move: `server.py` → `src/claudium/server.py`
- Move: `aquarium.py` → `src/claudium/aquarium.py`
- Move: `hook_sender.py` → `src/claudium/hook_sender.py`

**Step 1: Move files**

```bash
git mv entities.py src/claudium/entities.py
git mv server.py src/claudium/server.py
git mv aquarium.py src/claudium/aquarium.py
git mv hook_sender.py src/claudium/hook_sender.py
```

**Step 2: Update internal imports to relative imports**

In `src/claudium/server.py`, change:
```python
# Before
from entities import Event, parse_event
# After
from .entities import Event, parse_event
```

In `src/claudium/aquarium.py`, change:
```python
# Before
from entities import (
    AgentStatus, Fish, Bubble, ToolBubble, TaskCoral,
    Creature, CreatureType, mcp_tool_to_creature_type,
    ToolCreature, AmbientCreature, FloorDecor,
    Cloud, Event, agent_type_to_art_idx,
    FISH_ARTS, BUBBLE_CHARS, SEAWEED_FRAMES, WAVE_FRAMES,
    SAILBOAT_ART, DOLPHIN_ART, CLOUD_ARTS, SUN_ART, MOON_ART, STAR_CHARS,
    TOOL_CREATURE_ARTS, JELLYFISH_ARTS, AMBIENT_FISH_ART, BIRD_ARTS,
    SEAWEED_WIDE, CORAL_ARTS, SHELL_ART, STARFISH_ART, ROCK_ARTS, FLOOR_PATTERN,
)
from server import EventServer
# After
from .entities import (
    AgentStatus, Fish, Bubble, ToolBubble, TaskCoral,
    Creature, CreatureType, mcp_tool_to_creature_type,
    ToolCreature, AmbientCreature, FloorDecor,
    Cloud, Event, agent_type_to_art_idx,
    FISH_ARTS, BUBBLE_CHARS, SEAWEED_FRAMES, WAVE_FRAMES,
    SAILBOAT_ART, DOLPHIN_ART, CLOUD_ARTS, SUN_ART, MOON_ART, STAR_CHARS,
    TOOL_CREATURE_ARTS, JELLYFISH_ARTS, AMBIENT_FISH_ART, BIRD_ARTS,
    SEAWEED_WIDE, CORAL_ARTS, SHELL_ART, STARFISH_ART, ROCK_ARTS, FLOOR_PATTERN,
)
from .server import EventServer
```

`hook_sender.py` and `entities.py` have no internal imports — no changes needed.

**Step 3: Verify imports parse correctly**

```bash
python3 -c "from claudium.entities import Fish; print('OK')"
```

Expected: FAIL (src layout not on path yet — this is expected until pip install)

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move source modules into src/claudium package"
```

---

### Task 3: Create unified `cli.py`

**Files:**
- Create: `src/claudium/cli.py`
- Reference: `main.py` (current run logic), `install.py` (current install logic)

**Step 1: Create `cli.py` with subcommands**

```python
#!/usr/bin/env python3
"""Claudium CLI - Claude Code Aquarium Visualizer."""

import argparse
import curses
import json
import os
import shutil
import sys
import threading
import time
import random

from .aquarium import Aquarium
from .server import EventServer


DEFAULT_SOCK = "/tmp/claudium.sock"
DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")


# --- Run command ---

def _run_tui(stdscr, args):
    server = EventServer(args.sock)
    server.start()
    try:
        aquarium = Aquarium(stdscr, server)
        if args.demo:
            def demo_spawner():
                time.sleep(0.5)
                for _ in range(3):
                    aquarium.spawn_demo_agent()
                    time.sleep(random.uniform(0.5, 1.5))
                while True:
                    time.sleep(random.uniform(2, 5))
                    aquarium.spawn_demo_agent()
            threading.Thread(target=demo_spawner, daemon=True).start()
        aquarium.run()
    finally:
        server.stop()


def cmd_run(args):
    print(f"Claudium starting on socket: {args.sock}")
    print("Press Q to quit, D to spawn demo fish")
    if not args.demo:
        print(f"\nWaiting for Claude Code hook events on {args.sock}")
        print("Tip: Run 'claudium install' to configure Claude Code hooks")
    print()
    curses.wrapper(lambda stdscr: _run_tui(stdscr, args))


# --- Install command ---

def _build_hooks_config(sock_path: str) -> dict:
    hook_cmd = f"CLAUDIUM_SOCK={sock_path} claudium-hook"
    def make_hook_entry(matcher: str = ""):
        entry = {
            "hooks": [{
                "type": "command",
                "command": hook_cmd,
                "timeout": 5,
                "async": True,
            }]
        }
        if matcher:
            entry["matcher"] = matcher
        return entry
    return {
        "hooks": {
            "SubagentStart": [make_hook_entry()],
            "SubagentStop": [make_hook_entry()],
            "PreToolUse": [make_hook_entry()],
            "PostToolUse": [make_hook_entry()],
            "PostToolUseFailure": [make_hook_entry()],
            "TaskCompleted": [make_hook_entry()],
        }
    }


def cmd_install(args):
    settings_path = args.settings
    sock_path = args.sock
    settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path) as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {settings_path} contains invalid JSON.")
            sys.exit(1)

    # Check for claudium-hook availability
    if not shutil.which("claudium-hook"):
        print("Warning: 'claudium-hook' not found on PATH.")
        print("Make sure claudium is installed: pip install -e .")
        print()

    claudium_events = ["SubagentStart", "SubagentStop", "PreToolUse",
                       "PostToolUse", "PostToolUseFailure", "TaskCompleted"]
    existing = settings.get("hooks", {})
    conflicts = [e for e in claudium_events if e in existing]
    if conflicts:
        print(f"Warning: Existing hooks found for: {', '.join(conflicts)}")
        print("Claudium hooks will be APPENDED to existing hooks.")
        answer = input("Continue? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    new_config = _build_hooks_config(sock_path)
    if "hooks" not in settings:
        settings["hooks"] = {}
    for event_name, entries in new_config["hooks"].items():
        if event_name in settings["hooks"]:
            settings["hooks"][event_name].extend(entries)
        else:
            settings["hooks"][event_name] = entries

    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"Claudium hooks installed to {settings_path}")
    print(f"Socket path: {sock_path}")
    print("\nRestart Claude Code to activate hooks.")


def cmd_uninstall(args):
    settings_path = args.settings
    if not os.path.exists(settings_path):
        print("No settings file found.")
        return

    with open(settings_path) as f:
        settings = json.load(f)

    if "hooks" not in settings:
        print("No hooks found in settings.")
        return

    changed = False
    for event_name in list(settings["hooks"].keys()):
        entries = settings["hooks"][event_name]
        filtered = [e for e in entries
                    if not any("claudium" in h.get("command", "").lower()
                               for h in e.get("hooks", []))]
        if len(filtered) < len(entries):
            changed = True
            if filtered:
                settings["hooks"][event_name] = filtered
            else:
                del settings["hooks"][event_name]

    if not settings["hooks"]:
        del settings["hooks"]

    if changed:
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print("Claudium hooks removed.")
    else:
        print("No Claudium hooks found to remove.")


def cmd_check(args):
    settings_path = args.settings
    try:
        with open(settings_path) as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
    except (FileNotFoundError, json.JSONDecodeError):
        hooks = {}
    if hooks:
        print("Current hooks in settings:")
        for name, entries in hooks.items():
            print(f"  {name}: {len(entries)} handler(s)")
    else:
        print("No hooks configured.")


# --- Main parser ---

def main():
    parser = argparse.ArgumentParser(
        prog="claudium",
        description="Claudium - Claude Code Aquarium Visualizer",
    )
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    # claudium run (default)
    p_run = sub.add_parser("run", help="Start the aquarium (default)")
    p_run.add_argument("--sock", default=DEFAULT_SOCK)
    p_run.add_argument("--demo", action="store_true")

    # claudium install
    p_inst = sub.add_parser("install", help="Install Claude Code hooks")
    p_inst.add_argument("--settings", default=DEFAULT_SETTINGS_PATH)
    p_inst.add_argument("--sock", default=DEFAULT_SOCK)

    # claudium uninstall
    p_uninst = sub.add_parser("uninstall", help="Remove Claude Code hooks")
    p_uninst.add_argument("--settings", default=DEFAULT_SETTINGS_PATH)

    # claudium check
    p_check = sub.add_parser("check", help="Check hook status")
    p_check.add_argument("--settings", default=DEFAULT_SETTINGS_PATH)

    # Support "claudium --demo" and "claudium --sock" without subcommand
    parser.add_argument("--sock", default=DEFAULT_SOCK)
    parser.add_argument("--demo", action="store_true")

    args = parser.parse_args()

    if args.command is None:
        cmd_run(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "uninstall":
        cmd_uninstall(args)
    elif args.command == "check":
        cmd_check(args)


from . import __version__


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add src/claudium/cli.py
git commit -m "feat: add unified CLI with run/install/uninstall/check subcommands"
```

---

### Task 4: Create `__main__.py`

**Files:**
- Create: `src/claudium/__main__.py`

**Step 1: Create `__main__.py`**

```python
"""Allow running as `python -m claudium`."""

from .cli import main

main()
```

**Step 2: Commit**

```bash
git add src/claudium/__main__.py
git commit -m "feat: add __main__.py for python -m claudium support"
```

---

### Task 5: Update `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml with full metadata and entry points**

```toml
[project]
name = "claudium"
version = "0.1.0"
description = "Claude Code Aquarium Visualizer"
requires-python = ">=3.10"
license = "MIT"
readme = "README.md"

[project.scripts]
claudium = "claudium.cli:main"
claudium-hook = "claudium.hook_sender:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/claudium"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: complete pyproject.toml with entry points and build config"
```

---

### Task 6: Update test imports

**Files:**
- Modify: `tests/test_entities.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_hook_sender.py`
- Modify: `tests/test_install.py`

**Step 1: Update test imports**

In `tests/test_entities.py`, change:
```python
# Before
from entities import (
# After
from claudium.entities import (
```

In `tests/test_server.py`, change:
```python
# Before
from server import EventServer
# After
from claudium.server import EventServer
```

In `tests/test_hook_sender.py`, change:
```python
# Before
from hook_sender import send_to_socket, build_event_from_hook
# After
from claudium.hook_sender import send_to_socket, build_event_from_hook
```

In `tests/test_install.py`, change:
```python
# Before
from install import build_hooks_config, check_existing_hooks
# After
from claudium.cli import _build_hooks_config, cmd_check
```

Note: `test_install.py` needs more rework since `build_hooks_config` signature changed
(no longer takes `hook_sender_path` — it uses `claudium-hook` entry point now).
The tests should be updated to match the new `_build_hooks_config(sock_path)` signature.

**Step 2: Commit**

```bash
git add tests/
git commit -m "test: update imports for new package structure"
```

---

### Task 7: Install package and run tests

**Step 1: Install in editable mode**

```bash
pip install -e ".[dev]" 2>/dev/null || pip install -e .
```

**Step 2: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass.

**Step 3: Verify CLI commands work**

```bash
claudium --version
claudium check
claudium --demo  # (Ctrl+C after visual confirmation)
```

**Step 4: Fix any failing tests**

Update test assertions that reference old `hook_sender_path` or `python3` command patterns.
The hook command is now `CLAUDIUM_SOCK=/tmp/claudium.sock claudium-hook` instead of
`CLAUDIUM_SOCK=/tmp/claudium.sock python3 /abs/path/hook_sender.py`.

---

### Task 8: Clean up old root-level files

**Files:**
- Delete: `main.py`
- Delete: `install.py`

**Step 1: Remove old files**

```bash
git rm main.py install.py
```

**Step 2: Update README.md**

Update usage instructions:
```
# Before
python install.py
python main.py --demo

# After
pip install -e .
claudium install
claudium --demo
```

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove old root-level scripts, update README"
```

---

### Task 9: Final verification

**Step 1: Clean install test**

```bash
pip install -e .
```

**Step 2: Full test suite**

```bash
python -m pytest tests/ -v
```

**Step 3: End-to-end smoke test**

```bash
claudium --version          # prints "claudium 0.1.0"
claudium check              # shows hook status
claudium install --sock /tmp/test.sock  # installs hooks
claudium uninstall          # removes hooks
python -m claudium --demo   # runs aquarium via __main__
```

**Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final cleanup for phase 1 package restructure"
```
