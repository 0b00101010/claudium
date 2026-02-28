# entities.py
"""Data models for Claudium aquarium entities."""

import json
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ──────────────────────────────────────────────
#  ASCII Art Constants
# ──────────────────────────────────────────────

FISH_ARTS = [
    # idx 0: small (Explore)
    (
        ["><(((°>"],
        ["<°)))><"],
        7, 1,
    ),
    # idx 1: medium (general-purpose)
    (
        ["><((°>"],
        ["<°))><"],
        6, 1,
    ),
    # idx 2: large (Plan, code-reviewer)
    (
        [
            "  .  . ",
            "><(°)> ",
            "  `  ' ",
        ],
        [
            " .  .  ",
            " <(°)><",
            " '  `  ",
        ],
        7, 3,
    ),
    # idx 3: decorated (feature-dev)
    (
        [
            "   __  ",
            "><(oo)>",
            "  (__) ",
        ],
        [
            "  __   ",
            "<(oo)><",
            " (__)  ",
        ],
        7, 3,
    ),
    # idx 4: sea turtle (main agent, adapted from jgs)
    (
        [
            "  .----.  _    ",
            ",_/      \\/(_) ",
            "'~uu----uu'    ",
        ],
        [
            "   _  .----.   ",
            "  (_\\/      \\_,",
            "    'uu----uu~'",
        ],
        15, 3,
    ),
]

SEAWEED_FRAMES = [
    ["(", "|", "(", "|", "("],
    [")", "|", ")", "|", ")"],
]

# Wide seaweed variants (frame0, frame1) — each frame is bottom-to-top
SEAWEED_WIDE = [
    # bushy seaweed
    ([")(", "|(", ")("], ["(|", ")|", "(|"]),
    # kelp
    (["/\\", "\\/", "/\\"], ["\\/", "/\\", "\\/"]),
]

# Floor decoration arts: (lines_bottom_to_top, width, height, color_name)
CORAL_ARTS = [
    # branch coral
    (["\\|/", " | "], 3, 2, "red"),
    # fan coral
    (["(())", " )( "], 4, 2, "magenta"),
    # tall branch coral
    (["\\|/", "\\|/", " | "], 3, 3, "red"),
]

SHELL_ART = ("\\_^_/", 5, 1, "yellow")

STARFISH_ART = ("-*-", 3, 1, "yellow")

ROCK_ARTS = [
    # small rock
    (["(__)"], 4, 1, "white"),
    # medium rock
    ([".--.", "(__)"], 4, 2, "white"),
]

FLOOR_PATTERN = ",._.:'\"._.,:'\"._.,:'\"._.,:'\"._.,:'\"._.,:'\"._.,:'\"._.,:'\"._.,"

BUBBLE_CHARS = ["o", "O", "°", "."]

WAVE_FRAMES = [
    "~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^",
    "^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~",
]

CLOUD_ARTS = [
    # large
    [" .-(  ).  ", "(  __  )  "],
    # small
    [" .--.  ", "(    ) "],
]
SUN_ART = [" \\ | / ", "- O - ", " / | \\ "]
MOON_ART = [" _  ", "( ) ", " ~  "]
STAR_CHARS = [".", "*", "+"]

# Sailboat art (by jgs, classic ASCII sailboat)
SAILBOAT_ART = (
    # right-facing
    [
        "    ,~     ",
        "    |\\     ",
        "   /| \\    ",
        " _/__|__\\_ ",
        "  '======'  ",
    ],
    # left-facing
    [
        "     ~,    ",
        "     /|    ",
        "    / |\\   ",
        " _/__|__\\_ ",
        "  '======'  ",
    ],
    11, 5,
)

# Dolphin art (adapted from ASCIIQuarium, GPL v2)
DOLPHIN_ART = (
    # right-facing
    [
        "       ,   ",
        "     __/)  ",
        "\\_.-' a '-.",
        "/~~'``(/~^^'",
    ],
    # left-facing
    [
        "   ,       ",
        "  (\\__     ",
        ".-' a '-._/",
        "'^^~\\)``'~~\\",
    ],
    12, 4,
)

TOOL_CREATURE_ARTS = [
    # shrimp (새우)
    (["~}>"], ["<{~"], 3, 1),
    # small fish (작은 물고기)
    ([">°>"], ["<°<"], 3, 1),
    # crab (게) - 해저 전용
    ([",V,"], [",V,"], 3, 1),
]

JELLYFISH_ARTS = [
    [" .-. ", "(   )", " /|\\ "],
    [" .-. ", "(   )", " \\|/ "],
]

AMBIENT_FISH_ART = (
    ["-><>"],
    ["<><-"],
    4, 1,
)

BIRD_ARTS = [
    ["/^v^\\"],   # frame 0: wings up
    ["-.v.-"],    # frame 1: wings glide
]


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────

class CreatureType(Enum):
    SAILBOAT = "sailboat"
    DOLPHIN = "dolphin"


class AgentStatus(Enum):
    SPAWNING = "spawning"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


# ──────────────────────────────────────────────
#  Entity dataclasses
# ──────────────────────────────────────────────

@dataclass
class FloorDecor:
    kind: str  # "coral", "shell", "starfish", "rock", "seaweed_wide"
    x: int
    art_idx: int = 0  # index into the relevant ARTS list
    height: int = 1


@dataclass
class Bubble:
    x: float
    y: float
    char: str
    age: int = 0


@dataclass
class ToolBubble:
    """A bubble with a tool name label, spawned on tool_start events."""
    x: float
    y: float
    tool_name: str
    char: str
    age: int = 0


@dataclass
class Cloud:
    x: float
    y: int
    art_idx: int  # 0=large, 1=small
    speed: float
    direction: int = 1


@dataclass
class TaskCoral:
    """Sea floor decoration representing a task."""
    subject: str
    x: int
    completed: bool = False


@dataclass
class Creature:
    creature_type: CreatureType
    tool_name: str
    x: float
    y: float
    speed: float
    direction: int = 1
    alive: bool = True
    agent_id: str = ""
    leaving: bool = False
    start_time: float = field(default_factory=time.time)
    # Jump state (dolphin)
    jumping: bool = False
    jump_tick: int = 0
    jump_duration: int = 0
    jump_base_y: float = 0.0
    jump_apex_y: float = 0.0
    # Wake trail (sailboat)
    wake_trail: list = field(default_factory=list)


@dataclass
class ToolCreature:
    x: float
    y: float
    art_idx: int
    speed: float
    direction: int = 1
    age: int = 0


@dataclass
class AmbientCreature:
    kind: str  # "jellyfish", "fish", "bird"
    x: float
    y: float
    speed: float
    direction: int = 1


@dataclass
class Fish:
    agent_id: str
    label: str
    status: AgentStatus
    x: float
    y: float
    speed: float
    art_idx: int
    direction: int = 1
    bubbles: list = field(default_factory=list)
    alive: bool = True
    flip: bool = False
    start_time: float = field(default_factory=time.time)
    last_tool: str = ""
    last_tool_time: float = 0.0


@dataclass
class EventLogEntry:
    """A single entry in the event log panel."""
    timestamp: float
    kind: str
    detail: str


@dataclass
class SessionStats:
    """Accumulated session statistics."""
    tool_counts: dict = field(default_factory=dict)
    total_events: int = 0
    error_count: int = 0
    session_start: float = field(default_factory=time.time)


# ──────────────────────────────────────────────
#  Event parsing
# ──────────────────────────────────────────────

@dataclass
class Event:
    kind: str
    agent_id: str = ""
    agent_type: str = ""
    description: str = ""
    error: bool = False
    tool_name: str = ""
    tool_input_summary: str = ""
    success: bool = True
    task_subject: str = ""
    timestamp: float = 0.0


def parse_event(raw: str) -> Optional[Event]:
    try:
        d = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    kind = d.get("event")
    if not kind:
        return None
    return Event(
        kind=kind,
        agent_id=d.get("agent_id", ""),
        agent_type=d.get("agent_type", ""),
        description=d.get("description", ""),
        error=d.get("error", False),
        tool_name=d.get("tool_name", ""),
        tool_input_summary=d.get("tool_input_summary", ""),
        success=d.get("success", True),
        task_subject=d.get("task_subject", ""),
        timestamp=d.get("timestamp", 0.0),
    )


# ──────────────────────────────────────────────
#  Agent type → fish art mapping
# ──────────────────────────────────────────────

_AGENT_ART_MAP = {
    "Explore": 0,
    "general-purpose": 1,
    "Plan": 2,
    "code-reviewer": 2,
    "code-simplifier": 2,
}


def mcp_tool_to_creature_type(tool_name: str) -> CreatureType | None:
    """Map an MCP tool name to a creature type, or None for non-MCP tools."""
    if not tool_name.startswith("mcp__"):
        return None
    if tool_name.startswith("mcp__codex__"):
        return CreatureType.SAILBOAT
    return CreatureType.DOLPHIN


def agent_type_to_art_idx(agent_type: str) -> int:
    if agent_type in _AGENT_ART_MAP:
        return _AGENT_ART_MAP[agent_type]
    if agent_type.startswith("feature-dev:"):
        return 3
    if agent_type.startswith("superpowers:"):
        return 3
    return 1  # default medium
