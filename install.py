#!/usr/bin/env python3
"""
Install Claudium hooks into Claude Code settings.

Usage:
    python install.py              # Install to user settings (~/.claude/settings.json)
    python install.py --uninstall  # Remove Claudium hooks
    python install.py --check      # Check current hook status
"""

import argparse
import json
import os
import sys


DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
DEFAULT_SOCK = "/tmp/claudium.sock"


def build_hooks_config(hook_sender_path: str, sock_path: str) -> dict:
    """Build the hooks configuration dict for Claude Code settings."""
    cmd = f"CLAUDIUM_SOCK={sock_path} python3 {hook_sender_path}"

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


def check_existing_hooks(settings_path: str) -> dict:
    """Check for existing hooks in settings. Returns the hooks dict or empty."""
    try:
        with open(settings_path) as f:
            data = json.load(f)
        return data.get("hooks", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def install_hooks(settings_path: str, sock_path: str):
    """Install Claudium hooks into Claude Code settings."""
    hook_sender_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "hook_sender.py")
    )

    if not os.path.exists(hook_sender_path):
        print(f"Error: hook_sender.py not found at {hook_sender_path}")
        sys.exit(1)

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
    new_config = build_hooks_config(hook_sender_path, sock_path)
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
    print(f"Hook sender: {hook_sender_path}")
    print("\nRestart Claude Code to activate hooks.")


def uninstall_hooks(settings_path: str):
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
                    if not any("hook_sender.py" in h.get("command", "")
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


def main():
    p = argparse.ArgumentParser(description="Install Claudium hooks for Claude Code")
    p.add_argument("--settings", default=DEFAULT_SETTINGS_PATH,
                   help=f"Path to Claude Code settings.json (default: {DEFAULT_SETTINGS_PATH})")
    p.add_argument("--sock", default=DEFAULT_SOCK,
                   help=f"Unix socket path (default: {DEFAULT_SOCK})")
    p.add_argument("--uninstall", action="store_true", help="Remove Claudium hooks")
    p.add_argument("--check", action="store_true", help="Check hook status")
    args = p.parse_args()

    if args.check:
        hooks = check_existing_hooks(args.settings)
        if hooks:
            print("Current hooks in settings:")
            for name, entries in hooks.items():
                print(f"  {name}: {len(entries)} handler(s)")
        else:
            print("No hooks configured.")
        return

    if args.uninstall:
        uninstall_hooks(args.settings)
        return

    install_hooks(args.settings, args.sock)


if __name__ == "__main__":
    main()
