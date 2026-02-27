# server.py
"""Unix domain socket server that receives hook events."""

import os
import socket
import threading
from collections import deque
from entities import Event, parse_event


class EventServer:
    def __init__(self, sock_path: str = "/tmp/claudium.sock"):
        self.sock_path = sock_path
        self._queue: deque[Event] = deque(maxlen=500)
        self._lock = threading.Lock()
        self._server_sock: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        if os.path.exists(self.sock_path):
            os.unlink(self.sock_path)
        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.bind(self.sock_path)
        self._server_sock.listen(5)
        self._server_sock.settimeout(0.5)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._server_sock:
            self._server_sock.close()
        if os.path.exists(self.sock_path):
            os.unlink(self.sock_path)

    def drain_events(self) -> list[Event]:
        with self._lock:
            events = list(self._queue)
            self._queue.clear()
            return events

    def _accept_loop(self):
        while self._running:
            try:
                conn, _ = self._server_sock.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, conn: socket.socket):
        try:
            buf = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
            for line in buf.decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                ev = parse_event(line)
                if ev:
                    with self._lock:
                        self._queue.append(ev)
        except OSError:
            pass
        finally:
            conn.close()
