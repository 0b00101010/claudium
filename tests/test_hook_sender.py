# tests/test_hook_sender.py
import json
import os
import socket
import threading
import time
import tempfile
import pytest
from hook_sender import send_to_socket, build_event_from_hook


@pytest.fixture
def sock_path():
    # Use tempfile directly to get a short path; macOS limits AF_UNIX paths to 104 bytes.
    fd, path = tempfile.mkstemp(suffix=".sock", prefix="clm_")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def listening_socket(sock_path):
    """A simple listening socket that captures received data."""
    received = []
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(1)
    srv.settimeout(2)

    def accept_one():
        try:
            conn, _ = srv.accept()
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            received.append(data.decode())
            conn.close()
        except socket.timeout:
            pass

    t = threading.Thread(target=accept_one, daemon=True)
    t.start()
    yield sock_path, received
    srv.close()
    t.join(timeout=1)


class TestBuildEvent:
    def test_subagent_start(self):
        hook_input = {
            "hook_event_name": "SubagentStart",
            "agent_id": "abc",
            "agent_type": "Explore",
        }
        ev = build_event_from_hook(hook_input)
        assert ev["event"] == "agent_start"
        assert ev["agent_id"] == "abc"
        assert ev["agent_type"] == "Explore"
        assert "timestamp" in ev

    def test_subagent_stop(self):
        hook_input = {
            "hook_event_name": "SubagentStop",
            "agent_id": "abc",
            "agent_type": "Explore",
        }
        ev = build_event_from_hook(hook_input)
        assert ev["event"] == "agent_stop"
        assert ev["error"] is False

    def test_pre_tool_use(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "npm test", "description": "run tests"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["event"] == "tool_start"
        assert ev["tool_name"] == "Bash"
        assert ev["tool_input_summary"] == "npm test"

    def test_post_tool_use(self):
        hook_input = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/foo/bar.py"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["event"] == "tool_end"
        assert ev["success"] is True

    def test_post_tool_use_failure(self):
        hook_input = {
            "hook_event_name": "PostToolUseFailure",
            "tool_name": "Bash",
            "tool_input": {"command": "false"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["event"] == "tool_end"
        assert ev["success"] is False

    def test_task_completed(self):
        hook_input = {
            "hook_event_name": "TaskCompleted",
            "task_subject": "Fix auth bug",
        }
        ev = build_event_from_hook(hook_input)
        assert ev["event"] == "task_completed"
        assert ev["task_subject"] == "Fix auth bug"

    def test_tool_input_summary_read(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/some/very/long/path/to/file.py"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "file.py"

    def test_tool_input_summary_grep(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Grep",
            "tool_input": {"pattern": "TODO"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "TODO"

    def test_tool_input_summary_write(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/a/b/c.py", "content": "..."},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "c.py"

    def test_tool_input_summary_edit(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/a/b/c.py", "old_string": "x", "new_string": "y"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "c.py"

    def test_tool_input_summary_glob(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Glob",
            "tool_input": {"pattern": "**/*.py"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "**/*.py"

    def test_tool_input_summary_mcp_codex(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__codex__codex",
            "tool_input": {"prompt": "Fix the auth bug"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "codex:codex"

    def test_tool_input_summary_mcp_notion(self):
        hook_input = {
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__claude_ai_Notion__notion-search",
            "tool_input": {"query": "meeting notes"},
        }
        ev = build_event_from_hook(hook_input)
        assert ev["tool_input_summary"] == "claude_ai_Notion:notion-search"

    def test_unknown_hook_returns_none(self):
        hook_input = {"hook_event_name": "ConfigChange"}
        ev = build_event_from_hook(hook_input)
        assert ev is None


class TestSendToSocket:
    def test_sends_json(self, listening_socket):
        sock_path, received = listening_socket
        time.sleep(0.05)  # let server start
        data = {"event": "agent_start", "agent_id": "x"}
        send_to_socket(sock_path, data)
        time.sleep(0.2)
        assert len(received) == 1
        parsed = json.loads(received[0].strip())
        assert parsed["event"] == "agent_start"

    def test_no_error_when_socket_missing(self, sock_path):
        # Should silently fail if socket doesn't exist
        send_to_socket(str(sock_path + "_nonexistent"), {"event": "test"})
