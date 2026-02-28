# tests/test_entities.py
import json
import pytest
from claudium.entities import (
    AgentStatus, Fish, ToolBubble, TaskCoral, Bubble, Cloud,
    Event, parse_event, agent_type_to_art_idx,
    FISH_ARTS, BUBBLE_CHARS, SEAWEED_FRAMES, WAVE_FRAMES,
    CLOUD_ARTS, SUN_ART, MOON_ART, STAR_CHARS,
    CreatureType, Creature, mcp_tool_to_creature_type,
    SAILBOAT_ART, DOLPHIN_ART,
    TOOL_CREATURE_ARTS, ToolCreature, AmbientCreature,
    JELLYFISH_ARTS, AMBIENT_FISH_ART, BIRD_ARTS,
    EventLogEntry, SessionStats,
)


class TestParseEvent:
    def test_agent_start(self):
        raw = json.dumps({
            "event": "agent_start",
            "agent_id": "abc123",
            "agent_type": "Explore",
            "description": "Find endpoints",
            "timestamp": 1000,
        })
        ev = parse_event(raw)
        assert ev.kind == "agent_start"
        assert ev.agent_id == "abc123"
        assert ev.agent_type == "Explore"
        assert ev.description == "Find endpoints"

    def test_agent_stop(self):
        raw = json.dumps({
            "event": "agent_stop",
            "agent_id": "abc123",
            "agent_type": "Explore",
            "error": True,
            "timestamp": 2000,
        })
        ev = parse_event(raw)
        assert ev.kind == "agent_stop"
        assert ev.error is True

    def test_tool_start(self):
        raw = json.dumps({
            "event": "tool_start",
            "tool_name": "Bash",
            "tool_input_summary": "npm test",
            "agent_id": "abc123",
            "timestamp": 1000,
        })
        ev = parse_event(raw)
        assert ev.kind == "tool_start"
        assert ev.tool_name == "Bash"
        assert ev.tool_input_summary == "npm test"

    def test_tool_end(self):
        raw = json.dumps({
            "event": "tool_end",
            "tool_name": "Bash",
            "success": True,
            "agent_id": "abc123",
            "timestamp": 2000,
        })
        ev = parse_event(raw)
        assert ev.kind == "tool_end"
        assert ev.success is True

    def test_task_completed(self):
        raw = json.dumps({
            "event": "task_completed",
            "task_subject": "Fix auth",
            "timestamp": 3000,
        })
        ev = parse_event(raw)
        assert ev.kind == "task_completed"
        assert ev.task_subject == "Fix auth"

    def test_invalid_json_returns_none(self):
        assert parse_event("not json") is None

    def test_missing_event_field_returns_none(self):
        assert parse_event(json.dumps({"foo": "bar"})) is None


class TestAgentTypeMapping:
    def test_explore_small(self):
        idx = agent_type_to_art_idx("Explore")
        assert idx == 0  # small fish

    def test_general_purpose_medium(self):
        idx = agent_type_to_art_idx("general-purpose")
        assert idx == 1

    def test_plan_large(self):
        idx = agent_type_to_art_idx("Plan")
        assert idx == 2

    def test_code_reviewer_large(self):
        idx = agent_type_to_art_idx("code-reviewer")
        assert idx == 2

    def test_feature_dev_decorated(self):
        idx = agent_type_to_art_idx("feature-dev:code-architect")
        assert idx == 3

    def test_unknown_defaults_medium(self):
        idx = agent_type_to_art_idx("something-unknown")
        assert idx == 1


class TestCreatureType:
    def test_codex_returns_sailboat(self):
        assert mcp_tool_to_creature_type("mcp__codex__codex") == CreatureType.SAILBOAT

    def test_codex_reply_returns_sailboat(self):
        assert mcp_tool_to_creature_type("mcp__codex__codex-reply") == CreatureType.SAILBOAT

    def test_notion_returns_dolphin(self):
        assert mcp_tool_to_creature_type("mcp__claude_ai_Notion__notion-search") == CreatureType.DOLPHIN

    def test_context7_returns_dolphin(self):
        assert mcp_tool_to_creature_type("mcp__plugin_context7__query-docs") == CreatureType.DOLPHIN

    def test_non_mcp_returns_none(self):
        assert mcp_tool_to_creature_type("Bash") is None

    def test_sailboat_art_has_both_directions(self):
        right, left, w, h = SAILBOAT_ART
        assert len(right) == h
        assert len(left) == h

    def test_dolphin_art_has_both_directions(self):
        right, left, w, h = DOLPHIN_ART
        assert len(right) == h
        assert len(left) == h

    def test_creature_defaults(self):
        c = Creature(creature_type=CreatureType.SAILBOAT, tool_name="mcp__codex__codex",
                     x=0.0, y=2.0, speed=0.15)
        assert c.direction == 1
        assert c.alive is True

    def test_creature_jump_defaults(self):
        c = Creature(creature_type=CreatureType.DOLPHIN, tool_name="mcp__notion__search",
                     x=5.0, y=8.0, speed=0.5)
        assert c.jumping is False
        assert c.jump_tick == 0
        assert c.jump_duration == 0
        assert c.jump_base_y == 0.0
        assert c.jump_apex_y == 0.0

    def test_creature_wake_default(self):
        c = Creature(creature_type=CreatureType.SAILBOAT, tool_name="mcp__codex__codex",
                     x=0.0, y=2.0, speed=0.15)
        assert c.wake_trail == []

    def test_wake_trail_independence(self):
        c1 = Creature(creature_type=CreatureType.SAILBOAT, tool_name="t", x=0, y=0, speed=0.1)
        c2 = Creature(creature_type=CreatureType.SAILBOAT, tool_name="t", x=0, y=0, speed=0.1)
        c1.wake_trail.append((10, 0))
        assert c2.wake_trail == []


class TestSkyArt:
    def test_cloud_arts_structure(self):
        assert len(CLOUD_ARTS) == 2
        for art in CLOUD_ARTS:
            assert isinstance(art, list)
            assert len(art) >= 1

    def test_sun_art_structure(self):
        assert len(SUN_ART) == 3
        for line in SUN_ART:
            assert isinstance(line, str)

    def test_moon_art_structure(self):
        assert len(MOON_ART) == 3
        for line in MOON_ART:
            assert isinstance(line, str)

    def test_star_chars(self):
        assert len(STAR_CHARS) >= 2
        for ch in STAR_CHARS:
            assert len(ch) == 1

    def test_cloud_dataclass_defaults(self):
        c = Cloud(x=10.0, y=0, art_idx=0, speed=0.05)
        assert c.direction == 1
        assert c.x == 10.0
        assert c.y == 0
        assert c.art_idx == 0

    def test_cloud_large_and_small(self):
        large = Cloud(x=0, y=0, art_idx=0, speed=0.05)
        small = Cloud(x=0, y=0, art_idx=1, speed=0.05)
        assert len(CLOUD_ARTS[large.art_idx][0]) > len(CLOUD_ARTS[small.art_idx][0])


class TestSeaTurtle:
    def test_turtle_art_exists(self):
        assert len(FISH_ARTS) >= 5
        right, left, w, h = FISH_ARTS[4]
        assert len(right) == h
        assert len(left) == h
        assert w == 15
        assert h == 3

    def test_turtle_both_directions(self):
        right, left, _, _ = FISH_ARTS[4]
        assert right != left


class TestToolCreatures:
    def test_tool_creature_arts_structure(self):
        assert len(TOOL_CREATURE_ARTS) == 3
        for art_right, art_left, w, h in TOOL_CREATURE_ARTS:
            assert len(art_right) == h
            assert len(art_left) == h

    def test_tool_creature_defaults(self):
        tc = ToolCreature(x=5.0, y=10.0, art_idx=0, speed=0.3)
        assert tc.direction == 1
        assert tc.age == 0

    def test_tool_creature_crab_art(self):
        right, left, _, _ = TOOL_CREATURE_ARTS[2]
        assert right == left  # crab looks same both ways


class TestAmbientLife:
    def test_jellyfish_arts_structure(self):
        assert len(JELLYFISH_ARTS) == 2
        for frame in JELLYFISH_ARTS:
            assert len(frame) == 3

    def test_ambient_fish_art_structure(self):
        right, left, w, h = AMBIENT_FISH_ART
        assert len(right) == h
        assert len(left) == h

    def test_bird_arts_structure(self):
        assert len(BIRD_ARTS) == 2
        for frame in BIRD_ARTS:
            assert len(frame) == 1  # single-line bird

    def test_ambient_creature_defaults(self):
        ac = AmbientCreature(kind="jellyfish", x=10.0, y=8.0, speed=0.02)
        assert ac.direction == 1
        assert ac.kind == "jellyfish"

    def test_ambient_creature_kinds(self):
        for kind in ["jellyfish", "fish", "bird"]:
            ac = AmbientCreature(kind=kind, x=0, y=0, speed=0.1)
            assert ac.kind == kind


class TestFloorDecor:
    def test_coral_arts_structure(self):
        from claudium.entities import CORAL_ARTS
        assert len(CORAL_ARTS) >= 2
        for lines, w, h, color in CORAL_ARTS:
            assert len(lines) == h
            assert isinstance(color, str)

    def test_rock_arts_structure(self):
        from claudium.entities import ROCK_ARTS
        assert len(ROCK_ARTS) >= 1
        for lines, w, h, color in ROCK_ARTS:
            assert len(lines) == h

    def test_shell_and_starfish(self):
        from claudium.entities import SHELL_ART, STARFISH_ART
        text, w, h, color = SHELL_ART
        assert len(text) == w
        text2, w2, h2, color2 = STARFISH_ART
        assert len(text2) == w2

    def test_seaweed_wide_structure(self):
        from claudium.entities import SEAWEED_WIDE
        assert len(SEAWEED_WIDE) >= 1
        for frame0, frame1 in SEAWEED_WIDE:
            assert len(frame0) == len(frame1)

    def test_floor_pattern_nonempty(self):
        from claudium.entities import FLOOR_PATTERN
        assert len(FLOOR_PATTERN) > 10

    def test_floor_decor_dataclass(self):
        from claudium.entities import FloorDecor
        d = FloorDecor(kind="coral", x=10, art_idx=0, height=2)
        assert d.kind == "coral"
        assert d.x == 10
        assert d.height == 2


class TestFishCreation:
    def test_fish_defaults(self):
        f = Fish(agent_id="a1", label="test", status=AgentStatus.SPAWNING,
                 x=-10.0, y=5.0, speed=0.5, art_idx=0)
        assert f.direction == 1
        assert f.alive is True
        assert f.flip is False
        assert f.bubbles == []
        assert f.start_time > 0


class TestNewDataStructures:
    def test_event_log_entry(self):
        entry = EventLogEntry(timestamp=1.0, kind="tool_start", detail="Bash: npm test")
        assert entry.kind == "tool_start"
        assert entry.detail == "Bash: npm test"

    def test_session_stats_defaults(self):
        stats = SessionStats()
        assert stats.tool_counts == {}
        assert stats.total_events == 0
        assert stats.error_count == 0
        assert stats.session_start > 0

    def test_fish_last_tool(self):
        f = Fish(agent_id="a", label="test", status=AgentStatus.WORKING,
                 x=0, y=0, speed=1, art_idx=0)
        assert f.last_tool == ""
        assert f.last_tool_time == 0.0
