"""Claudium CLI -- unified entry point for run / install / uninstall / check."""

import argparse
import curses
import json
import os
import random
import sys
import threading
import time

from . import __version__
from .aquarium import Aquarium
from .server import EventServer


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────

DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
DEFAULT_SOCK = "/tmp/claudium.sock"


# ──────────────────────────────────────────────
#  Hook installation helpers
# ──────────────────────────────────────────────

def _build_hooks_config(sock_path: str) -> dict:
    """Build the hooks configuration dict for Claude Code settings."""
    cmd = f"CLAUDIUM_SOCK={sock_path} claudium-hook"

    def make_hook_entry(matcher: str = ""):
        entry = {
            "hooks": [{
                "type": "command",
                "command": cmd,
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


def _check_existing_hooks(settings_path: str) -> dict:
    """Check for existing hooks in settings. Returns the hooks dict or empty."""
    try:
        with open(settings_path) as f:
            data = json.load(f)
        return data.get("hooks", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _install_hooks(settings_path: str, sock_path: str):
    """Install Claudium hooks into Claude Code settings."""
    # Load existing settings
    settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path) as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {settings_path} contains invalid JSON. Please fix it first.")
            sys.exit(1)

    # Check for existing hooks
    existing = settings.get("hooks", {})
    claudium_events = ["SubagentStart", "SubagentStop", "PreToolUse",
                       "PostToolUse", "PostToolUseFailure", "TaskCompleted"]

    conflicts = [e for e in claudium_events if e in existing]
    if conflicts:
        print(f"Warning: Existing hooks found for: {', '.join(conflicts)}")
        print("Claudium hooks will be APPENDED to existing hooks (not replaced).")
        answer = input("Continue? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    # Build and merge hooks
    new_config = _build_hooks_config(sock_path)
    if "hooks" not in settings:
        settings["hooks"] = {}

    for event_name, entries in new_config["hooks"].items():
        if event_name in settings["hooks"]:
            settings["hooks"][event_name].extend(entries)
        else:
            settings["hooks"][event_name] = entries

    # Write settings
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"Claudium hooks installed to {settings_path}")
    print(f"Socket path: {sock_path}")
    print("\nRestart Claude Code to activate hooks.")


def _uninstall_hooks(settings_path: str):
    """Remove Claudium hooks from settings."""
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


# ──────────────────────────────────────────────
#  TUI runner
# ──────────────────────────────────────────────

def _run_tui(stdscr, sock: str, demo: bool):
    server = EventServer(sock)
    server.start()

    try:
        aquarium = Aquarium(stdscr, server)

        if demo:
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


def _cmd_run(args):
    """Handler for the 'run' subcommand (also the default)."""
    print(f"Claudium v{__version__} starting on socket: {args.sock}")
    print("Press Q to quit, D to spawn demo fish")
    if not args.demo:
        print(f"\nWaiting for Claude Code hook events on {args.sock}")
        print("Tip: Run 'claudium install' to configure Claude Code hooks")
    print()
    curses.wrapper(lambda stdscr: _run_tui(stdscr, args.sock, args.demo))


def _cmd_install(args):
    """Handler for the 'install' subcommand."""
    _install_hooks(args.settings, args.sock)


def _cmd_uninstall(args):
    """Handler for the 'uninstall' subcommand."""
    _uninstall_hooks(args.settings)


def _cmd_check(args):
    """Handler for the 'check' subcommand."""
    hooks = _check_existing_hooks(args.settings)
    if hooks:
        print("Current hooks in settings:")
        for name, entries in hooks.items():
            print(f"  {name}: {len(entries)} handler(s)")
    else:
        print("No hooks configured.")


# ──────────────────────────────────────────────
#  Argument parser
# ──────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claudium",
        description="Claudium - Claude Code Aquarium Visualizer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # ---- run (default) ----
    p_run = subparsers.add_parser("run", help="Start the aquarium TUI")
    p_run.add_argument("--sock", default=DEFAULT_SOCK,
                       help=f"Unix socket path (default: {DEFAULT_SOCK})")
    p_run.add_argument("--demo", action="store_true",
                       help="Start with demo agents (no hooks needed)")
    p_run.set_defaults(func=_cmd_run)

    # ---- install ----
    p_install = subparsers.add_parser("install", help="Install hooks into Claude Code settings")
    p_install.add_argument("--settings", default=DEFAULT_SETTINGS_PATH,
                           help=f"Path to settings.json (default: {DEFAULT_SETTINGS_PATH})")
    p_install.add_argument("--sock", default=DEFAULT_SOCK,
                           help=f"Unix socket path (default: {DEFAULT_SOCK})")
    p_install.set_defaults(func=_cmd_install)

    # ---- uninstall ----
    p_uninstall = subparsers.add_parser("uninstall", help="Remove Claudium hooks")
    p_uninstall.add_argument("--settings", default=DEFAULT_SETTINGS_PATH,
                             help=f"Path to settings.json (default: {DEFAULT_SETTINGS_PATH})")
    p_uninstall.set_defaults(func=_cmd_uninstall)

    # ---- check ----
    p_check = subparsers.add_parser("check", help="Check hook status")
    p_check.add_argument("--settings", default=DEFAULT_SETTINGS_PATH,
                         help=f"Path to settings.json (default: {DEFAULT_SETTINGS_PATH})")
    p_check.set_defaults(func=_cmd_check)

    # Top-level --sock and --demo so `claudium --demo` works without subcommand
    parser.add_argument("--sock", default=DEFAULT_SOCK,
                        help=argparse.SUPPRESS)
    parser.add_argument("--demo", action="store_true",
                        help=argparse.SUPPRESS)

    return parser


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────

def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        # No subcommand: default to 'run'
        _cmd_run(args)
    else:
        args.func(args)
