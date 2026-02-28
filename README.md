# Claudium

Real-time ASCII aquarium that visualizes Claude Code agent and tool activity.

```
  \ | /                          .-(  ).
  - O -                         (  __  )
  / | \
~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
      Find API endpoints 12s
      ><(((°>                    ,
                               __/)
   Search docs 3s        \_.-' a '-.
   ><((°>                /~~'``(/~^^'
                                codex
(  |  (  |  (
```

- **Fish** = Sub-agents (size/shape varies by type)
- **Bubbles** = Tool calls (float up and fade)
- **Dolphin** = MCP tools (Notion, Context7, etc.)
- **Sailboat** = Codex MCP tools
- **Coral** = Completed tasks (sea floor)
- **Sky** = Real-time sun/moon + clouds + stars

## Quick Start

```bash
# Install
pip install -e .

# Install hooks (one-time)
claudium install

# Restart Claude Code (to activate hooks)

# Run the aquarium in a separate terminal
claudium
```

Agent and tool events will now appear in the aquarium as you use Claude Code.

## Demo Mode

Test without a Claude Code connection:

```bash
claudium --demo
```

## Keyboard

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `D` | Spawn demo fish |

## How It Works

```
Claude Code                    Claudium
┌──────────┐   hook event    ┌──────────────┐
│  Agent   │ ──────────────> │ claudium-hook│
│ Tool Use │   (stdin JSON)  │ (entry point)│
└──────────┘                 └──────┬───────┘
                                    │ Unix socket
                                    v
                             ┌──────────────┐
                             │    server    │
                             │ (socket recv)│
                             └──────┬───────┘
                                    │ event queue
                                    v
                             ┌──────────────┐
                             │   aquarium   │
                             │ (TUI render) │
                             └──────────────┘
```

1. `claudium install` registers 6 hooks in `~/.claude/settings.json`
2. Claude Code invokes `claudium-hook` on each event
3. `claudium-hook` sends JSON over a Unix socket (`/tmp/claudium.sock`)
4. `server` receives events and queues them
5. `aquarium` renders the aquarium at ~20fps

## File Structure

```
src/claudium/
├── __init__.py      # Package version
├── __main__.py      # python -m claudium support
├── cli.py           # Unified CLI (run/install/uninstall/check)
├── aquarium.py      # Curses TUI renderer
├── entities.py      # Data models + ASCII art
├── server.py        # Unix socket server
└── hook_sender.py   # Claude Code hooks → socket
tests/               # pytest tests
```

## Commands

```bash
# Start aquarium (default)
claudium
claudium run

# Demo mode
claudium --demo

# Custom socket path
claudium --sock /tmp/custom.sock

# Install hooks
claudium install
claudium install --sock /tmp/custom.sock

# Check hook status
claudium check

# Uninstall hooks
claudium uninstall
```

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## Visual Mapping

| Event | Visualization | Color |
|-------|--------------|-------|
| `agent_start` | Fish enters (from left) | White (spawning) |
| `agent_working` | Fish swims | Yellow (working) |
| `agent_stop` | Fish exits (to right) | Purple (done) / Red (error) |
| `tool_start` | Bubble spawns | Blue |
| MCP tool | Dolphin or Sailboat | Cyan / Yellow |
| `task_completed` | Coral on sea floor | Green |

## License

Dolphin ASCII art adapted from [ASCIIQuarium](https://robobunny.com/projects/asciiquarium/) (GPL v2).
Sailboat ASCII art by jgs.
