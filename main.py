#!/usr/bin/env python3
"""
Claudium - Claude Code Aquarium Visualizer

Usage:
    python main.py          # Start aquarium (listens on /tmp/claudium.sock)
    python main.py --demo   # Start with demo fish (no hooks needed)
    python main.py --sock /path/to/custom.sock  # Custom socket path
"""

import argparse
import curses
import threading
import time
import random

from aquarium import Aquarium
from server import EventServer


def parse_args():
    p = argparse.ArgumentParser(description="Claudium - Claude Code Aquarium Visualizer")
    p.add_argument("--sock", default="/tmp/claudium.sock",
                   help="Unix socket path (default: /tmp/claudium.sock)")
    p.add_argument("--demo", action="store_true",
                   help="Start with demo agents (no hooks needed)")
    return p.parse_args()


def run_tui(stdscr, args):
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


def main():
    args = parse_args()
    print(f"Claudium starting on socket: {args.sock}")
    print("Press Q to quit, D to spawn demo fish")
    if not args.demo:
        print(f"\nWaiting for Claude Code hook events on {args.sock}")
        print("Tip: Run 'python install.py' to configure Claude Code hooks")
    print()
    curses.wrapper(lambda stdscr: run_tui(stdscr, args))


if __name__ == "__main__":
    main()
