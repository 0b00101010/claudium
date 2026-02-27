import json
import os
import pytest
from install import build_hooks_config, check_existing_hooks


@pytest.fixture
def hook_sender_path():
    return "/abs/path/to/hook_sender.py"


class TestBuildHooksConfig:
    def test_contains_all_hook_events(self, hook_sender_path):
        config = build_hooks_config(hook_sender_path, "/tmp/claudium.sock")
        hooks = config["hooks"]
        assert "SubagentStart" in hooks
        assert "SubagentStop" in hooks
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks
        assert "PostToolUseFailure" in hooks
        assert "TaskCompleted" in hooks

    def test_hook_command_uses_sender_path(self, hook_sender_path):
        config = build_hooks_config(hook_sender_path, "/tmp/claudium.sock")
        cmd = config["hooks"]["SubagentStart"][0]["hooks"][0]["command"]
        assert hook_sender_path in cmd

    def test_hook_command_sets_socket_env(self, hook_sender_path):
        config = build_hooks_config(hook_sender_path, "/custom/path.sock")
        cmd = config["hooks"]["SubagentStart"][0]["hooks"][0]["command"]
        assert "CLAUDIUM_SOCK=/custom/path.sock" in cmd

    def test_all_hooks_are_async(self, hook_sender_path):
        config = build_hooks_config(hook_sender_path, "/tmp/claudium.sock")
        for event_name, matchers in config["hooks"].items():
            for matcher in matchers:
                for hook in matcher["hooks"]:
                    assert hook.get("async") is True, f"{event_name} hook should be async"


class TestCheckExistingHooks:
    def test_no_existing_hooks(self, tmp_path):
        settings_path = tmp_path / "settings.json"
        settings_path.write_text("{}")
        result = check_existing_hooks(str(settings_path))
        assert result == {}

    def test_existing_hooks_detected(self, tmp_path):
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({
            "hooks": {"SubagentStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}
        }))
        result = check_existing_hooks(str(settings_path))
        assert "SubagentStart" in result

    def test_missing_file_returns_empty(self, tmp_path):
        result = check_existing_hooks(str(tmp_path / "nonexistent.json"))
        assert result == {}
