# aquarium.py
"""Curses-based aquarium TUI renderer."""

import curses
import math
import random
import time
import threading
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

SURFACE_ROW = 4   # wave surface starts here (rows 4-5)
OCEAN_TOP = SURFACE_ROW + 2  # first fully underwater row


class Aquarium:
    def __init__(self, stdscr, event_server: EventServer):
        self.stdscr = stdscr
        self.server = event_server
        self.tick = 0
        self.fishes: list[Fish] = []
        self.tool_bubbles: list[ToolBubble] = []
        self.creatures: list[Creature] = []
        self.task_corals: list[TaskCoral] = []
        self.main_fish: Fish | None = None
        self.tool_creatures: list[ToolCreature] = []
        self.ambient_creatures: list[AmbientCreature] = []
        self.floor_decors: list[FloorDecor] = []
        self.total_agents = 0
        self.total_tools = 0
        self.clouds: list[Cloud] = []
        self.sky_body = "sun"
        self.lock = threading.Lock()
        self._setup_curses()
        self._setup_seaweed()
        self._setup_floor_decor()
        self._setup_sky()
        self._setup_ambient()
        self._setup_main_fish()

    def _setup_curses(self):
        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # wave/water
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # seaweed
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # fish working
        curses.init_pair(4, curses.COLOR_WHITE, -1)    # fish spawning
        curses.init_pair(5, curses.COLOR_RED, -1)      # fish error
        curses.init_pair(6, curses.COLOR_BLUE, -1)     # bubbles
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)  # done
        curses.init_pair(8, curses.COLOR_WHITE, -1)    # label/hud text
        curses.init_pair(9, curses.COLOR_YELLOW, -1)    # sailboat
        curses.init_pair(10, curses.COLOR_CYAN, -1)    # dolphin body
        curses.init_pair(11, curses.COLOR_WHITE, -1)   # clouds
        curses.init_pair(12, curses.COLOR_GREEN, -1)   # main agent turtle

    def _setup_seaweed(self):
        h, w = self.stdscr.getmaxyx()
        count = min(12, max(1, w // 8))
        rng = range(2, max(3, w - 2))
        self.seaweed_xs = sorted(random.sample(list(rng), min(count, len(rng))))
        self.seaweed_heights = [random.randint(3, 7) for _ in self.seaweed_xs]

    def _setup_floor_decor(self):
        h, w = self.stdscr.getmaxyx()
        # Color name → curses color pair
        self._floor_color_map = {
            "red": curses.color_pair(5),
            "magenta": curses.color_pair(7),
            "yellow": curses.color_pair(3),
            "white": curses.color_pair(8) | curses.A_DIM,
            "green": curses.color_pair(2),
        }
        # Collect candidate x positions, avoid seaweed
        occupied = set(self.seaweed_xs)
        candidates = [x for x in range(3, max(4, w - 6)) if x not in occupied]
        random.shuffle(candidates)
        placed = 0
        idx = 0
        target = min(len(candidates) // 3, max(4, w // 10))
        while placed < target and idx < len(candidates):
            x = candidates[idx]
            idx += 1
            # Check spacing from already-placed decor
            if any(abs(x - d.x) < 4 for d in self.floor_decors):
                continue
            kind = random.choices(
                ["coral", "rock", "shell", "starfish", "seaweed_wide"],
                weights=[3, 2, 2, 2, 2],
            )[0]
            if kind == "coral":
                art_idx = random.randint(0, len(CORAL_ARTS) - 1)
                height = CORAL_ARTS[art_idx][2]
            elif kind == "rock":
                art_idx = random.randint(0, len(ROCK_ARTS) - 1)
                height = ROCK_ARTS[art_idx][2]
            elif kind == "seaweed_wide":
                art_idx = random.randint(0, len(SEAWEED_WIDE) - 1)
                height = len(SEAWEED_WIDE[art_idx][0])
            else:
                art_idx = 0
                height = 1
            self.floor_decors.append(FloorDecor(
                kind=kind, x=x, art_idx=art_idx, height=height,
            ))
            placed += 1

    def _setup_main_fish(self):
        h, w = self.stdscr.getmaxyx()
        ocean_top = OCEAN_TOP
        ocean_bot = h - 5
        mid_y = (ocean_top + ocean_bot) / 2
        self.main_fish = Fish(
            agent_id="__main__",
            label="Claude",
            status=AgentStatus.WORKING,
            x=float(w) / 2,
            y=mid_y,
            speed=random.uniform(0.3, 0.5),
            art_idx=4,
            direction=1,
        )

    def _setup_sky(self):
        h, w = self.stdscr.getmaxyx()
        count = random.randint(2, 4)
        for _ in range(count):
            self.clouds.append(Cloud(
                x=random.uniform(0, max(1, w - 12)),
                y=random.randint(0, 1),
                art_idx=random.choice([0, 1]),
                speed=random.uniform(0.03, 0.08),
                direction=random.choice([-1, 1]),
            ))

    def _setup_ambient(self):
        h, w = self.stdscr.getmaxyx()
        ocean_bot = h - 5
        # Jellyfish 2~3
        for _ in range(random.randint(2, 3)):
            self.ambient_creatures.append(AmbientCreature(
                kind="jellyfish",
                x=random.uniform(3, max(4, w - 8)),
                y=random.uniform(OCEAN_TOP + 1, max(OCEAN_TOP + 2, (OCEAN_TOP + ocean_bot) // 2)),
                speed=random.uniform(0.01, 0.03),
                direction=random.choice([-1, 1]),
            ))
        # Small fish 2~3
        for _ in range(random.randint(2, 3)):
            self.ambient_creatures.append(AmbientCreature(
                kind="fish",
                x=random.uniform(0, max(1, w - 5)),
                y=random.uniform(OCEAN_TOP + 1, max(OCEAN_TOP + 2, ocean_bot - 2)),
                speed=random.uniform(0.1, 0.2),
                direction=random.choice([-1, 1]),
            ))
        # Birds 1~2
        for _ in range(random.randint(1, 2)):
            self.ambient_creatures.append(AmbientCreature(
                kind="bird",
                x=random.uniform(0, max(1, w - 5)),
                y=random.randint(0, 2),
                speed=random.uniform(0.08, 0.15),
                direction=random.choice([-1, 1]),
            ))

    def _is_night(self):
        hour = time.localtime().tm_hour
        return hour < 6 or hour >= 19

    def _update_sky(self, w):
        # Drift clouds, wrap around edges
        for cloud in self.clouds:
            cloud.x += cloud.speed * cloud.direction
            art_w = len(CLOUD_ARTS[cloud.art_idx][0])
            if cloud.x > w:
                cloud.x = -art_w
            elif cloud.x < -art_w:
                cloud.x = float(w)
        # Sync sky body with real time
        self.sky_body = "moon" if self._is_night() else "sun"

    def _draw_sky(self, w):
        night = self._is_night()
        # Draw stars at night (stable positions seeded from tick // 200 for gentle twinkle)
        if night:
            rng = random.Random(self.tick // 200)
            for _ in range(min(15, w // 5)):
                sx = rng.randint(0, max(0, w - 2))
                sy = rng.randint(0, 3)
                ch = rng.choice(STAR_CHARS)
                attr = curses.color_pair(3) if ch == "*" else curses.color_pair(11)
                if rng.random() < 0.7:  # twinkle: some stars dimmer
                    attr |= curses.A_DIM
                self._safe_addstr(sy, sx, ch, attr)
        # Draw sun or moon in upper-right
        body_art = SUN_ART if self.sky_body == "sun" else MOON_ART
        body_x = w - len(body_art[0]) - 2
        body_color = curses.color_pair(3) if self.sky_body == "sun" else curses.color_pair(11)
        for i, line in enumerate(body_art):
            self._safe_addstr(i, body_x, line, body_color | curses.A_BOLD)
        # Draw clouds
        for cloud in self.clouds:
            art = CLOUD_ARTS[cloud.art_idx]
            for i, line in enumerate(art):
                self._safe_addstr(cloud.y + i, int(cloud.x), line,
                                  curses.color_pair(11) | curses.A_BOLD)

    # ──────────────────────────────────────────
    #  Event processing
    # ──────────────────────────────────────────

    def _process_events(self):
        events = self.server.drain_events()
        h, w = self.stdscr.getmaxyx()
        for ev in events:
            self._handle_event(ev, h, w)

    def _handle_event(self, ev: Event, h: int, w: int):
        if ev.kind == "agent_start":
            self._on_agent_start(ev, h, w)
        elif ev.kind == "agent_stop":
            self._on_agent_stop(ev)
        elif ev.kind == "tool_start":
            self._on_tool_start(ev, h, w)
        elif ev.kind == "tool_end":
            if ev.tool_name.startswith("mcp__"):
                self._on_creature_end(ev)
        elif ev.kind == "task_completed":
            self._on_task_completed(ev, w)

    def _on_agent_start(self, ev: Event, h: int, w: int):
        ocean_top = OCEAN_TOP
        ocean_bot = h - 5
        if ocean_bot <= ocean_top + 1:
            ocean_bot = ocean_top + 2
        art_idx = agent_type_to_art_idx(ev.agent_type)
        label = ev.description or ev.agent_type
        fish = Fish(
            agent_id=ev.agent_id,
            label=label,
            status=AgentStatus.SPAWNING,
            x=-10.0,
            y=random.uniform(ocean_top + 1, ocean_bot - 3),
            speed=random.uniform(0.3, 0.8),
            art_idx=art_idx,
            direction=1,
        )
        with self.lock:
            self.fishes.append(fish)
            self.total_agents += 1

    def _on_agent_stop(self, ev: Event):
        with self.lock:
            for f in self.fishes:
                if f.agent_id == ev.agent_id:
                    if ev.error:
                        f.status = AgentStatus.ERROR
                        f.flip = True
                        f.speed = 0.1
                    else:
                        f.status = AgentStatus.DONE
                        f.speed = max(f.speed, 0.6)  # swim out faster

    def _on_tool_start(self, ev: Event, h: int, w: int):
        creature_type = mcp_tool_to_creature_type(ev.tool_name)
        if creature_type is not None:
            self._on_mcp_tool(ev, creature_type, h, w)
            return

        with self.lock:
            # Main agent tool call: agent_id not in any sub-agent fish → bubble near turtle
            parent_fish = None
            for f in self.fishes:
                if f.agent_id == ev.agent_id:
                    parent_fish = f
                    break

            if parent_fish is None:
                # Main agent — bubble near turtle
                bx = self.main_fish.x + random.uniform(-2, 5)
                by = self.main_fish.y - 1
            else:
                # Sub-agent — bubble near its fish
                bx = parent_fish.x + random.uniform(-2, 5)
                by = parent_fish.y - 1

            summary = ev.tool_input_summary or ev.tool_name
            self.tool_bubbles.append(ToolBubble(
                x=bx, y=by,
                tool_name=f"{ev.tool_name}:{summary}"[:20],
                char=random.choice(BUBBLE_CHARS),
            ))
            self.total_tools += 1

            # Sub-agent: 30% chance to spawn a tool creature
            if parent_fish is not None and random.random() < 0.3:
                art_idx = random.randint(0, 2)
                if art_idx == 2:  # crab → sea floor
                    cx = bx + random.uniform(-3, 3)
                    cy = float(h - 3)
                else:  # shrimp or small fish → near parent
                    cx = bx + random.uniform(-3, 3)
                    cy = by + random.uniform(-1, 2)
                direction = -parent_fish.direction
                self.tool_creatures.append(ToolCreature(
                    x=cx, y=cy, art_idx=art_idx,
                    speed=random.uniform(0.2, 0.4),
                    direction=direction,
                ))

    def _on_task_completed(self, ev: Event, w: int):
        with self.lock:
            # Check if task already tracked
            for tc in self.task_corals:
                if tc.subject == ev.task_subject:
                    tc.completed = True
                    return
            # New task, place at a random x on sea floor
            self.task_corals.append(TaskCoral(
                subject=ev.task_subject,
                x=random.randint(3, max(4, w - 15)),
                completed=True,
            ))

    def _on_mcp_tool(self, ev: Event, creature_type: CreatureType, h: int, w: int):
        if creature_type == CreatureType.SAILBOAT:
            y = float(SURFACE_ROW - 3)  # sail above water, hull at waterline
            speed = 0.2
        else:  # dolphin
            ocean_bot = h - 5
            y = random.uniform(OCEAN_TOP, max(OCEAN_TOP + 1, ocean_bot - 4))
            speed = random.uniform(0.4, 0.7)

        creature = Creature(
            creature_type=creature_type,
            tool_name=ev.tool_name,
            x=-25.0,
            y=y,
            speed=speed,
            direction=1,
            agent_id=ev.agent_id,
        )
        with self.lock:
            self.creatures.append(creature)
            self.total_tools += 1

    def _on_creature_end(self, ev: Event):
        with self.lock:
            for c in self.creatures:
                if (c.agent_id == ev.agent_id
                        and c.tool_name == ev.tool_name
                        and not c.leaving):
                    c.leaving = True
                    c.speed = max(c.speed, 0.6)
                    c.jumping = False  # stop dolphin jump mid-air
                    break

    # ──────────────────────────────────────────
    #  Draw helpers
    # ──────────────────────────────────────────

    def _safe_addstr(self, y, x, text, attr=0):
        h, w = self.stdscr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        if x + len(text) >= w:
            text = text[:w - x - 1]
        if not text:
            return
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _draw_waves(self, w):
        frame = WAVE_FRAMES[self.tick // 4 % 2]
        tile = (frame * ((w // len(frame)) + 2))[:w]
        self._safe_addstr(SURFACE_ROW, 0, tile, curses.color_pair(1) | curses.A_BOLD)
        self._safe_addstr(SURFACE_ROW + 1, 0, tile[::-1][:w], curses.color_pair(1))

    def _depth_attr(self, y, h):
        ocean_depth = h - 3 - OCEAN_TOP
        if ocean_depth <= 0:
            return 0
        depth_ratio = (y - OCEAN_TOP) / ocean_depth
        if depth_ratio < 0.3:
            return curses.A_BOLD
        elif depth_ratio > 0.7:
            return curses.A_DIM
        return 0

    def _draw_water_bg(self, h, w):
        for row in range(OCEAN_TOP, h - 2):
            offset = (self.tick // 6 + row * 3) % 8
            depth = self._depth_attr(row, h)
            for col in range(offset, w - 1, 8):
                self._safe_addstr(row, col, ".", curses.color_pair(6) | curses.A_DIM | depth)

    def _draw_seaweed(self, h, w):
        frame_idx = (self.tick // 8) % 2
        for sx, sh in zip(self.seaweed_xs, self.seaweed_heights):
            if sx >= w:
                continue
            for i in range(sh):
                row = h - 3 - i
                if row < OCEAN_TOP:
                    continue
                ch = SEAWEED_FRAMES[frame_idx][i % len(SEAWEED_FRAMES[frame_idx])]
                self._safe_addstr(row, sx, ch, curses.color_pair(2) | curses.A_BOLD)

    def _draw_floor_decor(self, h, w):
        frame_idx = (self.tick // 10) % 2
        floor_row = h - 3  # row just above the HUD bar
        for d in self.floor_decors:
            if d.x >= w - 1:
                continue
            if d.kind == "coral":
                lines, cw, ch, color_name = CORAL_ARTS[d.art_idx]
                attr = self._floor_color_map.get(color_name, curses.color_pair(5))
                for i, line in enumerate(reversed(lines)):
                    row = floor_row - i
                    if row >= OCEAN_TOP:
                        self._safe_addstr(row, d.x, line, attr | curses.A_BOLD)
            elif d.kind == "rock":
                lines, rw, rh, color_name = ROCK_ARTS[d.art_idx]
                attr = self._floor_color_map.get(color_name, curses.color_pair(8))
                for i, line in enumerate(reversed(lines)):
                    row = floor_row - i
                    if row >= OCEAN_TOP:
                        self._safe_addstr(row, d.x, line, attr)
            elif d.kind == "shell":
                text, _, _, color_name = SHELL_ART
                attr = self._floor_color_map.get(color_name, curses.color_pair(3))
                self._safe_addstr(floor_row, d.x, text, attr)
            elif d.kind == "starfish":
                text, _, _, color_name = STARFISH_ART
                attr = self._floor_color_map.get(color_name, curses.color_pair(3))
                self._safe_addstr(floor_row, d.x, text, attr)
            elif d.kind == "seaweed_wide":
                frames = SEAWEED_WIDE[d.art_idx]
                frame = frames[frame_idx]
                for i, line in enumerate(reversed(frame)):
                    row = floor_row - i
                    if row >= OCEAN_TOP:
                        self._safe_addstr(row, d.x, line, curses.color_pair(2) | curses.A_BOLD)

    def _draw_floor(self, h, w):
        # Sandy floor with textured pattern (row above HUD)
        pattern = FLOOR_PATTERN
        tile = (pattern * ((w // len(pattern)) + 2))[:w - 1]
        self._safe_addstr(h - 2, 0, tile, curses.color_pair(3) | curses.A_DIM)

    def _draw_fish(self, fish: Fish, h, w):
        art_right, art_left, fw, fh = FISH_ARTS[fish.art_idx]
        art = art_right if fish.direction == 1 else art_left

        if fish.art_idx == 4:  # main agent turtle — always green
            color = curses.color_pair(12) | curses.A_BOLD
        elif fish.status == AgentStatus.SPAWNING:
            color = curses.color_pair(4)
        elif fish.status == AgentStatus.WORKING:
            color = curses.color_pair(3) | curses.A_BOLD
        elif fish.status == AgentStatus.DONE:
            color = curses.color_pair(7)
        else:
            color = curses.color_pair(5) | curses.A_BOLD

        wobble_y = int(math.sin(self.tick * 0.15 + fish.x * 0.1) * 0.7)
        draw_y = int(fish.y) + wobble_y
        depth = self._depth_attr(draw_y, h)

        for i, line in enumerate(art):
            self._safe_addstr(draw_y + i, int(fish.x), line, color | depth)

        # Label above fish
        label_y = draw_y - 1
        label_x = int(fish.x)
        if OCEAN_TOP <= label_y < h - 2:
            elapsed = time.time() - fish.start_time
            time_str = f" {elapsed:.0f}s" if fish.status == AgentStatus.WORKING else ""
            text = fish.label[:20] + time_str
            self._safe_addstr(label_y, label_x, text, curses.color_pair(8) | curses.A_DIM)

        # Fish bubbles
        for b in fish.bubbles:
            self._safe_addstr(int(b.y), int(b.x), b.char, curses.color_pair(6))

    def _draw_tool_bubbles(self, h, w):
        for tb in self.tool_bubbles:
            by, bx = int(tb.y), int(tb.x)
            if OCEAN_TOP <= by < h - 2:
                depth = self._depth_attr(by, h)
                self._safe_addstr(by, bx, tb.char, curses.color_pair(6) | depth)
                # Show tool name label next to bubble
                if tb.age < 15:
                    self._safe_addstr(by, bx + 2, tb.tool_name,
                                      curses.color_pair(8) | curses.A_DIM | depth)

    def _draw_task_corals(self, h, w):
        for tc in self.task_corals:
            row = h - 3
            color = curses.color_pair(2) | curses.A_BOLD if tc.completed else curses.color_pair(8) | curses.A_DIM
            marker = "V" if tc.completed else "?"
            text = f"[{marker}] {tc.subject[:12]}"
            self._safe_addstr(row, tc.x, text, color)

    def _draw_creature(self, creature: Creature, h, w):
        if creature.creature_type == CreatureType.SAILBOAT:
            art_data = SAILBOAT_ART
            color = curses.color_pair(9) | curses.A_BOLD
        else:
            art_data = DOLPHIN_ART
            color = curses.color_pair(10) | curses.A_BOLD

        art_right, art_left, art_w, art_h = art_data
        art = art_right if creature.direction == 1 else art_left

        draw_x = int(creature.x)
        draw_y = int(creature.y)

        for i, line in enumerate(art):
            self._safe_addstr(draw_y + i, draw_x, line, color)

        # Sailboat wake trail
        if creature.creature_type == CreatureType.SAILBOAT:
            wake_row = SURFACE_ROW + 1
            for wx, age in creature.wake_trail:
                wx_int = int(wx) + art_w // 2
                if age < 7:
                    ch, attr = "~", curses.color_pair(1) | curses.A_BOLD
                elif age < 14:
                    ch, attr = "~", curses.color_pair(1) | curses.A_DIM
                else:
                    ch, attr = ".", curses.color_pair(1) | curses.A_DIM
                self._safe_addstr(wake_row, wx_int, ch, attr)

        # Dolphin jump splash
        if creature.creature_type == CreatureType.DOLPHIN and creature.jumping:
            t = creature.jump_tick / max(1, creature.jump_duration)
            if t < 0.1 or t > 0.9:
                splash_x = int(creature.x) + art_w // 2 - 2
                self._safe_addstr(SURFACE_ROW, splash_x, "~*~*~",
                                  curses.color_pair(1) | curses.A_BOLD)

        # Label below creature
        label_y = draw_y + art_h
        if label_y < h - 2:
            parts = creature.tool_name.split("__")
            label = parts[1] if len(parts) >= 2 else creature.tool_name
            self._safe_addstr(label_y, draw_x, label[:15],
                              curses.color_pair(8) | curses.A_DIM)

    def _draw_hud(self, h, w):
        with self.lock:
            active = sum(1 for f in self.fishes if f.status in (AgentStatus.SPAWNING, AgentStatus.WORKING))
            creatures = len(self.creatures)

        sock_status = "connected" if self.server._running else "disconnected"
        hud = (f" Claudium  |  Agents: {active} active, {self.total_agents} total  |  "
               f"Tools: {self.total_tools}  |  Creatures: {creatures}  |  "
               f"Socket: {sock_status}  |  [Q] quit  [D] demo ")
        self._safe_addstr(h - 1, 0, hud[:w - 1], curses.color_pair(1) | curses.A_REVERSE)

    # ──────────────────────────────────────────
    #  Update logic
    # ──────────────────────────────────────────

    def _update_fish(self, fish: Fish, h, w):
        _, _, fw, fh = FISH_ARTS[fish.art_idx]
        fish.x += fish.speed * fish.direction

        # Working fish: random directional swimming within bounds
        if fish.status == AgentStatus.WORKING:
            if fish.x > w - fw - 5:
                fish.direction = -1
            elif fish.x < 5:
                fish.direction = 1
            if random.random() < 0.02:
                fish.direction *= -1

            # Emit occasional bubbles
            if random.random() < 0.06:
                bx = fish.x + (fw if fish.direction == 1 else 0)
                fish.bubbles.append(Bubble(
                    x=bx + random.uniform(-1, 1),
                    y=fish.y,
                    char=random.choice(BUBBLE_CHARS),
                ))

        # Update fish bubbles
        for b in fish.bubbles:
            b.y -= 0.3
            b.age += 1
        fish.bubbles = [b for b in fish.bubbles if b.age < 20 and b.y > SURFACE_ROW]

        # Done/Error fish swim out to the right
        if fish.status in (AgentStatus.DONE, AgentStatus.ERROR):
            fish.direction = 1
            if fish.x > w + 10:
                fish.alive = False

        # Spawning → Working once on screen
        if fish.status == AgentStatus.SPAWNING and fish.x > 2:
            fish.status = AgentStatus.WORKING

    def _update_creature(self, creature: Creature, h, w):
        creature.x += creature.speed * creature.direction

        if creature.leaving:
            # Leaving: just swim straight out, no bouncing
            if creature.x > w + 15 or creature.x < -15:
                creature.alive = False
            return

        if creature.creature_type == CreatureType.SAILBOAT:
            art_w = SAILBOAT_ART[2]
            if creature.x > w - art_w - 3:
                creature.direction = -1
            elif creature.x < 3:
                creature.direction = 1
            # Wake trail: append position every 3 ticks
            if self.tick % 3 == 0:
                creature.wake_trail.append((creature.x, 0))
            # Age and prune wake entries
            creature.wake_trail = [
                (wx, age + 1) for wx, age in creature.wake_trail if age < 20
            ]
        else:
            # Dolphin: bouncing swim + jump
            art_w = DOLPHIN_ART[2]
            if not creature.jumping:
                if creature.x > w - art_w - 3:
                    creature.direction = -1
                elif creature.x < 3:
                    creature.direction = 1
                if random.random() < 0.03:
                    creature.direction *= -1
                # Start jump if near surface
                if creature.y < OCEAN_TOP + 4 and random.random() < 0.02:
                    creature.jumping = True
                    creature.jump_tick = 0
                    creature.jump_duration = 30
                    creature.jump_base_y = creature.y
                    creature.jump_apex_y = float(SURFACE_ROW - 3)
            else:
                # Advance jump via parabolic arc
                creature.jump_tick += 1
                t = creature.jump_tick / creature.jump_duration
                if t >= 1.0:
                    creature.jumping = False
                    creature.y = creature.jump_base_y
                else:
                    height = creature.jump_base_y - creature.jump_apex_y
                    creature.y = creature.jump_base_y - height * 4 * t * (1 - t)

    def _update_tool_bubbles(self):
        for tb in self.tool_bubbles:
            tb.y -= 0.25
            tb.age += 1
        self.tool_bubbles = [tb for tb in self.tool_bubbles if tb.age < 30 and tb.y > SURFACE_ROW]

    def _update_tool_creatures(self, h, w):
        for tc in self.tool_creatures:
            tc.x += tc.speed * tc.direction
            tc.age += 1
        self.tool_creatures = [tc for tc in self.tool_creatures if tc.age < 40]

    def _draw_tool_creatures(self, h, w):
        for tc in self.tool_creatures:
            art_right, art_left, aw, ah = TOOL_CREATURE_ARTS[tc.art_idx]
            art = art_right if tc.direction == 1 else art_left
            dy = int(tc.y)
            depth = self._depth_attr(dy, h)
            for i, line in enumerate(art):
                self._safe_addstr(dy + i, int(tc.x), line, curses.color_pair(1) | depth)

    def _update_ambient(self, h, w):
        for ac in self.ambient_creatures:
            if ac.kind == "jellyfish":
                ac.x += ac.speed * ac.direction
                # Gentle sin-wave vertical float
                ac.y += math.sin(self.tick * 0.05 + ac.x * 0.1) * 0.05
                # Wrap around
                if ac.x > w:
                    ac.x = -5.0
                elif ac.x < -5:
                    ac.x = float(w)
            elif ac.kind == "fish":
                ac.x += ac.speed * ac.direction
                if ac.direction == 1 and ac.x > w + 4:
                    ac.x = -4.0
                elif ac.direction == -1 and ac.x < -4:
                    ac.x = float(w + 4)
            elif ac.kind == "bird":
                ac.x += ac.speed * ac.direction
                if ac.direction == 1 and ac.x > w + 3:
                    ac.x = -3.0
                elif ac.direction == -1 and ac.x < -3:
                    ac.x = float(w + 3)

    def _draw_ambient(self, h, w):
        for ac in self.ambient_creatures:
            if ac.kind == "jellyfish":
                frame = JELLYFISH_ARTS[self.tick // 10 % 2]
                for i, line in enumerate(frame):
                    self._safe_addstr(int(ac.y) + i, int(ac.x), line,
                                      curses.color_pair(7) | curses.A_DIM)
            elif ac.kind == "fish":
                art_r, art_l, _, _ = AMBIENT_FISH_ART
                art = art_r if ac.direction == 1 else art_l
                depth = self._depth_attr(int(ac.y), h)
                for i, line in enumerate(art):
                    self._safe_addstr(int(ac.y) + i, int(ac.x), line,
                                      curses.color_pair(1) | curses.A_DIM | depth)

    def _draw_birds(self, w):
        for ac in self.ambient_creatures:
            if ac.kind == "bird":
                frame = BIRD_ARTS[self.tick // 8 % 2]
                for i, line in enumerate(frame):
                    self._safe_addstr(int(ac.y) + i, int(ac.x), line,
                                      curses.color_pair(11))

    # ──────────────────────────────────────────
    #  Demo mode (for testing without hooks)
    # ──────────────────────────────────────────

    def spawn_demo_agent(self):
        labels = [
            "Find API endpoints", "Run test suite", "Write output.json",
            "Search documentation", "Analyze logs", "Edit config.toml",
            "Review PR changes", "Explore codebase",
        ]
        agent_types = ["Explore", "general-purpose", "Plan", "code-reviewer",
                       "feature-dev:code-architect"]
        h, w = self.stdscr.getmaxyx()
        ev = Event(
            kind="agent_start",
            agent_id=f"demo-{random.randint(100, 999)}",
            agent_type=random.choice(agent_types),
            description=random.choice(labels),
            timestamp=time.time(),
        )
        self._handle_event(ev, h, w)

        # Schedule lifecycle in background
        def lifecycle():
            time.sleep(random.uniform(2, 5))
            # Emit some tool events
            for _ in range(random.randint(2, 5)):
                time.sleep(random.uniform(0.5, 1.5))
                tool_ev = Event(
                    kind="tool_start",
                    tool_name=random.choice(["Read", "Bash", "Write", "Grep", "Edit"]),
                    tool_input_summary=random.choice(["main.py", "pytest", "*.ts", "TODO"]),
                    agent_id=ev.agent_id,
                    timestamp=time.time(),
                )
                self._handle_event(tool_ev, *self.stdscr.getmaxyx())
            # Occasionally spawn an MCP creature
            if random.random() < 0.55:
                mcp_tools = [
                    "mcp__codex__codex",
                    "mcp__claude_ai_Notion__notion-search",
                    "mcp__plugin_context7_context7__query-docs",
                ]
                mcp_tool = random.choice(mcp_tools)
                mcp_ev = Event(
                    kind="tool_start",
                    tool_name=mcp_tool,
                    tool_input_summary=mcp_tool.split("__")[1],
                    agent_id=ev.agent_id,
                    timestamp=time.time(),
                )
                self._handle_event(mcp_ev, *self.stdscr.getmaxyx())
                time.sleep(random.uniform(3, 6))
                mcp_end = Event(
                    kind="tool_end",
                    tool_name=mcp_tool,
                    success=True,
                    agent_id=ev.agent_id,
                    timestamp=time.time(),
                )
                self._handle_event(mcp_end, *self.stdscr.getmaxyx())

            time.sleep(0.5)
            stop_ev = Event(
                kind="agent_stop",
                agent_id=ev.agent_id,
                agent_type=ev.agent_type,
                error=random.random() < 0.1,
                timestamp=time.time(),
            )
            self._handle_event(stop_ev, *self.stdscr.getmaxyx())

        threading.Thread(target=lifecycle, daemon=True).start()

    # ──────────────────────────────────────────
    #  Main loop
    # ──────────────────────────────────────────

    def run(self):
        while True:
            h, w = self.stdscr.getmaxyx()

            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            if key in (ord('d'), ord('D')):
                self.spawn_demo_agent()

            # Process incoming events from socket
            self._process_events()

            self.stdscr.erase()

            self._update_sky(w)
            self._update_ambient(h, w)
            self._draw_sky(w)
            self._draw_birds(w)
            self._draw_waves(w)
            self._draw_water_bg(h, w)
            self._draw_ambient(h, w)

            with self.lock:
                for fish in self.fishes:
                    self._update_fish(fish, h, w)
                    self._draw_fish(fish, h, w)
                self.fishes = [f for f in self.fishes if f.alive]

                # Main agent turtle: always alive, update + draw
                if self.main_fish is not None:
                    self._update_fish(self.main_fish, h, w)
                    self.main_fish.alive = True  # never dies
                    self._draw_fish(self.main_fish, h, w)

                for creature in self.creatures:
                    self._update_creature(creature, h, w)
                    self._draw_creature(creature, h, w)
                self.creatures = [c for c in self.creatures if c.alive]

            with self.lock:
                self._update_tool_bubbles()
                self._draw_tool_bubbles(h, w)
                self._update_tool_creatures(h, w)
                self._draw_tool_creatures(h, w)
            self._draw_seaweed(h, w)
            self._draw_floor_decor(h, w)
            self._draw_task_corals(h, w)
            self._draw_floor(h, w)
            self._draw_hud(h, w)

            self.stdscr.refresh()
            self.tick += 1
            time.sleep(0.05)  # ~20fps
