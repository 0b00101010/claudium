# tests/test_server.py
import json
import os
import socket
import time
import tempfile
import pytest
from server import EventServer


@pytest.fixture
def sock_path():
    # Use tempfile directly to get a short path; macOS limits AF_UNIX paths to 104 bytes.
    fd, path = tempfile.mkstemp(suffix=".sock", prefix="clm_")
    os.close(fd)
    os.unlink(path)  # server.start() will create the socket file
    yield path
    # Cleanup in case a test didn't remove it
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def server(sock_path):
    srv = EventServer(sock_path)
    srv.start()
    yield srv
    srv.stop()


def send_event(sock_path: str, data: dict):
    """Helper: connect and send one JSON line."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_path)
    s.sendall((json.dumps(data) + "\n").encode())
    s.close()


class TestEventServer:
    def test_receives_event(self, server, sock_path):
        send_event(sock_path, {
            "event": "agent_start",
            "agent_id": "a1",
            "agent_type": "Explore",
            "description": "test",
            "timestamp": 1000,
        })
        time.sleep(0.1)
        events = server.drain_events()
        assert len(events) == 1
        assert events[0].kind == "agent_start"

    def test_multiple_events(self, server, sock_path):
        for i in range(3):
            send_event(sock_path, {
                "event": "tool_start",
                "tool_name": f"Tool{i}",
                "agent_id": "a1",
                "timestamp": 1000 + i,
            })
        time.sleep(0.2)
        events = server.drain_events()
        assert len(events) == 3

    def test_drain_clears_queue(self, server, sock_path):
        send_event(sock_path, {
            "event": "agent_start",
            "agent_id": "a1",
            "agent_type": "X",
            "description": "t",
            "timestamp": 1,
        })
        time.sleep(0.1)
        first = server.drain_events()
        assert len(first) == 1
        second = server.drain_events()
        assert len(second) == 0

    def test_invalid_json_ignored(self, server, sock_path):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock_path)
        s.sendall(b"not json\n")
        s.close()
        time.sleep(0.1)
        events = server.drain_events()
        assert len(events) == 0

    def test_cleanup_removes_socket(self, sock_path):
        srv = EventServer(sock_path)
        srv.start()
        assert os.path.exists(sock_path)
        srv.stop()
        assert not os.path.exists(sock_path)
