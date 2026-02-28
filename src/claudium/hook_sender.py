#!/usr/bin/env python3
"""
Hook sender script for Claudium.

Called by Claude Code hooks. Reads JSON from stdin, transforms it into
a Claudium event, and sends it to the Unix socket.

Usage in Claude Code hooks:
  cat | python /path/to/hook_sender.py
"""

import json
import os
import socket
import sys
import time


SOCKET_PATH = os.environ.get("CLAUDIUM_SOCK", "/tmp/claudium.sock")


def _summarize_tool_input(tool_name: str, tool_input: dict) -> str:
    """Extract a short summary from tool input."""
    if tool_name == "Bash":
        return tool_input.get("command", "")[:40]
    if tool_name in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        return os.path.basename(path) if path else ""
    if tool_name == "Grep":
        return tool_input.get("pattern", "")[:30]
    if tool_name == "Glob":
        return tool_input.get("pattern", "")[:30]
    if tool_name == "WebSearch":
        return tool_input.get("query", "")[:30]
    if tool_name == "WebFetch":
        return tool_input.get("url", "")[:40]
    if tool_name == "Task":
        return tool_input.get("description", "")[:30]
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return f"{parts[1]}:{parts[2]}"[:30]
        return tool_name[5:][:30]
    return ""


def build_event_from_hook(hook_input: dict) -> dict | None:
    """Transform Claude Code hook input into a Claudium event dict."""
    hook_name = hook_input.get("hook_event_name", "")
    ts = time.time()

    if hook_name == "SubagentStart":
        return {
            "event": "agent_start",
            "agent_id": hook_input.get("agent_id", ""),
            "agent_type": hook_input.get("agent_type", ""),
            "description": hook_input.get("description", ""),
            "timestamp": ts,
        }

    if hook_name == "SubagentStop":
        return {
            "event": "agent_stop",
            "agent_id": hook_input.get("agent_id", ""),
            "agent_type": hook_input.get("agent_type", ""),
            "error": hook_input.get("error", False),
            "timestamp": ts,
        }

    if hook_name == "PreToolUse":
        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        return {
            "event": "tool_start",
            "tool_name": tool_name,
            "tool_input_summary": _summarize_tool_input(tool_name, tool_input),
            "agent_id": hook_input.get("agent_id", ""),
            "timestamp": ts,
        }

    if hook_name == "PostToolUse":
        return {
            "event": "tool_end",
            "tool_name": hook_input.get("tool_name", ""),
            "success": True,
            "agent_id": hook_input.get("agent_id", ""),
            "timestamp": ts,
        }

    if hook_name == "PostToolUseFailure":
        return {
            "event": "tool_end",
            "tool_name": hook_input.get("tool_name", ""),
            "success": False,
            "agent_id": hook_input.get("agent_id", ""),
            "timestamp": ts,
        }

    if hook_name == "TaskCompleted":
        return {
            "event": "task_completed",
            "task_subject": hook_input.get("task_subject", ""),
            "timestamp": ts,
        }

    return None


def send_to_socket(sock_path: str, data: dict):
    """Send a JSON event to the Claudium Unix socket."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(sock_path)
        s.sendall((json.dumps(data) + "\n").encode())
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        pass  # Claudium not running, silently skip
    finally:
        s.close()


def main():
    raw = sys.stdin.read()
    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        return
    event = build_event_from_hook(hook_input)
    if event:
        send_to_socket(SOCKET_PATH, event)


if __name__ == "__main__":
    main()
