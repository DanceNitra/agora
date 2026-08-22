#!/usr/bin/env python3
"""agora-game-server — MCP game server for Dungeon OS.

Runs three services in one process:
  1. MCP stdio server (for Hermes agent tool calls)
  2. WebSocket server on port 5175 (for browser real-time sync)
  3. HTTP server on port 5174 (for serving static files)

Usage:
  python3 mcp_server.py          # Start all services
  python3 mcp_server.py --stdio  # MCP stdio mode (for Hermes config.yaml)

Environment:
  DUNGEON_HTTP_PORT=5174   (default)
  DUNGEON_WS_PORT=5175     (default)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

# ── No flashing console windows ── this process runs WITHOUT a console (launched hidden/detached), so
# every subprocess that runs a console program (git, gh, …) makes Windows pop a NEW console window —
# the recurring popup. Default all children to CREATE_NO_WINDOW so they stay invisible. (run/call/
# check_output all go through Popen, so patching Popen.__init__ covers them; explicit creationflags,
# e.g. the watchdog's DETACHED|CREATE_NO_WINDOW, are left untouched.)
if sys.platform == "win32":
    _CREATE_NO_WINDOW = 0x08000000
    _orig_popen_init = subprocess.Popen.__init__

    def _popen_no_window(self, *a, **kw):
        if not kw.get("creationflags"):
            kw["creationflags"] = _CREATE_NO_WINDOW
        return _orig_popen_init(self, *a, **kw)

    subprocess.Popen.__init__ = _popen_no_window

from mcp.server.fastmcp import FastMCP

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from game_state import GameEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dungeon.mcp_server")

# ── Config ──────────────────────────────────────────────────

HERE = Path(__file__).parent
STATIC_DIR = HERE / "static"
_HEARTBEAT_FILE = HERE / ".dungeon_heartbeat"   # life-loop liveness, watched by tools/dungeon_canary.py


def _atomic_write(path, data: str) -> None:
    """Write via a temp file in the same directory, then os.replace (atomic on NTFS).

    Every durable file this process keeps was written with a bare `Path.write_text`, which truncates
    at open and then writes — so a kill between those two steps leaves a truncated or empty file.
    That is not a rare event here: the brain's watchdog relaunches this process with p.kill()
    (TerminateProcess, no graceful stop) after two missed HTTP checks, and an unclean host shutdown
    can journal the new size without the data.

    Every reader catches the parse error and resets to empty, silently. The cost is recorded in this
    file's own comments: losing `_recent_intents` produced the "8x-duplicate output monoculture",
    and a lost `loop_n` restarts every `% N` task generator's countdown — the comment at the startup
    restore says that starved the Claude inbox for hours. A truncated state file is therefore a
    silent, self-inflicted outage, which is why this is worth four lines even though the window is
    tens of microseconds wide.
    """
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, p)


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a local .env (gitignored) into the environment."""
    envf = HERE / ".env"
    if not envf.exists():
        return
    for raw in envf.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()
HTTP_PORT = int(os.environ.get("DUNGEON_HTTP_PORT", "5174"))
WS_PORT = int(os.environ.get("DUNGEON_WS_PORT", "5175"))
# Loopback by default (the renderer/HUD is viewed locally). Set DUNGEON_HOST=0.0.0.0 only on a
# TRUSTED LAN — these servers have no auth.
BIND_HOST = os.environ.get("DUNGEON_HOST", "127.0.0.1")

# ── Game Engine (shared state) ──────────────────────────────

engine = GameEngine()
engine.set_auto_broadcast(True)

# ── WebSocket Broadcast ────────────────────────────────────

ws_clients: set[asyncio.Queue] = set()
ws_loop: asyncio.AbstractEventLoop | None = None


def broadcast(data: dict[str, Any]) -> None:
    """Send event to all connected WebSocket clients."""
    global ws_loop
    if not ws_loop:
        return
    msg = json.dumps(data)
    dead: list[asyncio.Queue] = []
    for q in ws_clients:
        try:
            ws_loop.call_soon_threadsafe(q.put_nowait, msg)
        except Exception:
            dead.append(q)
    for q in dead:
        ws_clients.discard(q)


engine.set_broadcast(broadcast)


# ── MCP Tools (Hermes agent interface) ─────────────────────

mcp = FastMCP("agora-game-server")


@mcp.tool()
def create_dungeon(width: int = 32, height: int = 18) -> str:
    """Initialize a new dungeon with the given dimensions. Generates walls, floor tiles, pillars, torches, and default lighting."""
    engine.create_default_dungeon(width, height)
    return f"Dungeon created: {width}×{height}"


@mcp.tool()
def spawn_agent(entity_id: str, name: str, x: float = 1, y: float = 1, color: str = "#ff6600") -> str:
    """Spawn an agent/dungeon entity at position (x, y). Color is a hex string like #ff6600."""
    engine.add_entity(entity_id, name, "agent", x, y, color)
    return f"Agent '{name}' spawned at ({x}, {y})"


@mcp.tool()
def move_agent(entity_id: str, x: float, y: float) -> str:
    """Move an agent to position (x, y). Smooth interpolation is handled by the Three.js client."""
    entity = engine.move_entity(entity_id, x, y)
    if not entity:
        return f"ERROR: Agent '{entity_id}' not found"
    return f"Agent '{entity.name}' moved to ({x}, {y})"


@mcp.tool()
def set_agent_state(entity_id: str, state: str) -> str:
    """Set agent animation state: idle, walking, thinking, casting."""
    valid_states = {"idle", "walking", "thinking", "casting"}
    if state not in valid_states:
        return f"ERROR: Invalid state '{state}'. Valid: {valid_states}"
    entity = engine.set_entity_state(entity_id, state)
    if not entity:
        return f"ERROR: Agent '{entity_id}' not found"
    return f"Agent '{entity.name}' state → {state}"


@mcp.tool()
def set_entity_thought(entity_id: str, text: str) -> str:
    """Set a thought bubble / speech text for an agent. Set empty string to clear."""
    if not text:
        engine.get_state().get("entities", {}).get(entity_id, {}).pop("thought", None)
    entity = engine.set_entity_thought(entity_id, text)
    if not entity:
        return f"ERROR: Agent '{entity_id}' not found"
    return f"Thought set for '{entity.name}'"


@mcp.tool()
def set_entity_health(entity_id: str, health: int) -> str:
    """Set entity health (0-100). Shows as health bar above the entity."""
    entity = engine.set_entity_health(entity_id, health)
    if not entity:
        return f"ERROR: Entity '{entity_id}' not found"
    return f"'{entity.name}' health → {entity.health}"


@mcp.tool()
def remove_agent(entity_id: str) -> str:
    """Remove an agent/entity from the dungeon."""
    if engine.remove_entity(entity_id):
        return f"Entity '{entity_id}' removed"
    return f"ERROR: Entity '{entity_id}' not found"


@mcp.tool()
def set_ambient_light(color: str = "#1a1a2e", intensity: float = 0.3) -> str:
    """Set the ambient light color and intensity for the dungeon."""
    engine.set_lighting(color, intensity)
    return f"Ambient light: {color} at {intensity}"


@mcp.tool()
def add_point_light(light_id: str, x: float, y: float, color: str = "#ffaa44",
                    intensity: float = 1.0, radius: float = 5.0) -> str:
    """Add a point light to the dungeon. Color is hex, radius is in grid units."""
    engine.add_light(light_id, x, y, color, intensity, radius)
    return f"Light '{light_id}' added at ({x}, {y})"


@mcp.tool()
def remove_light(light_id: str) -> str:
    """Remove a point light by its ID."""
    if engine.remove_light(light_id):
        return f"Light '{light_id}' removed"
    return f"ERROR: Light '{light_id}' not found"


@mcp.tool()
def add_effect(effect_type: str, x: float, y: float, color: str = "#ffffff", duration: float = 1.0) -> str:
    """Spawn a visual effect. effect_type: spark, glow, text, explosion."""
    effect_id = engine.add_effect(effect_type, x, y, 0, color, duration)
    return f"Effect '{effect_id}' spawned at ({x}, {y})"


@mcp.tool()
def set_camera(x: float | None = None, y: float | None = None, zoom: float | None = None) -> str:
    """Set camera position and zoom. Omit any parameter to keep current value. Zoom: 0.1-5.0."""
    cur = engine.state.camera_x, engine.state.camera_y
    engine.set_camera(
        x if x is not None else cur[0],
        y if y is not None else cur[1],
        zoom,
    )
    return f"Camera → ({engine.state.camera_x}, {engine.state.camera_y}) zoom={engine.state.camera_zoom}"


@mcp.tool()
def tick() -> str:
    """Advance one game tick. Triggers periodic effects and broadcasts to all clients."""
    t = engine.tick()
    return f"Tick {t}"


@mcp.tool()
def get_dungeon_state() -> str:
    """Get the full dungeon state as JSON. Useful for debugging."""
    return json.dumps(engine.get_snapshot(), indent=2)


# ── WebSocket Server ───────────────────────────────────────


async def ws_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle a WebSocket connection. Performs the WebSocket handshake, then streams state."""
    global ws_loop
    ws_loop = asyncio.get_event_loop()

    queue = None        # bound only after a successful handshake; guard the finally cleanup
    try:
        # Read HTTP upgrade request
        data = await reader.readuntil(b"\r\n\r\n")
        request = data.decode("utf-8")

        # Extract WebSocket key
        key = None
        for line in request.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
                break

        if not key:
            writer.close()
            return

        # Compute accept key
        import hashlib, base64
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept = base64.b64encode(
            hashlib.sha1((key + GUID).encode()).digest()
        ).decode()

        # Send upgrade response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        writer.write(response.encode())
        await writer.drain()

        # Register client
        queue: asyncio.Queue = asyncio.Queue()
        ws_clients.add(queue)
        addr = writer.get_extra_info("peername")
        logger.info(f"WebSocket client connected: {addr}")

        # Send initial snapshot
        snapshot = engine.get_snapshot()
        snapshot["_type"] = "snapshot"
        frame = _make_ws_frame(json.dumps(snapshot))
        writer.write(frame)
        await writer.drain()

        # Stream events. The keepalive lives INSIDE the loop: the `except asyncio.TimeoutError`
        # used to sit outside it, so the first 30-second idle window pinged once and then fell
        # through to `finally`, which discarded the queue and closed the connection. It was labelled
        # "Ping / keepalive" and kept nothing alive — there was no path back into the stream.
        #
        # Normal operation hid it (publish_goals broadcasts about every 1.7 s, so the window is
        # never reached). It fired precisely when the ambient loop had stalled — turning an
        # invisible stall into every open tab reconnecting every ~32 s, each reconnect rebuilding
        # the whole Three.js scene and clearing the HUD log, destroying the last events visible
        # before the stall. The symptom was worst exactly when diagnosis mattered most.
        missed_pongs = 0
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                try:
                    writer.write(_make_ws_frame("", opcode=0x9))      # ping
                    await writer.drain()
                    # Two raw bytes, not a parsed frame: any client frame satisfies this, so treat
                    # it as "the socket is alive", never as a verified pong.
                    await asyncio.wait_for(reader.readexactly(2), timeout=5)
                    missed_pongs = 0
                except asyncio.TimeoutError:
                    missed_pongs += 1
                    if missed_pongs >= 3:
                        break                                          # ~105 s silent -> give up
                continue
            frame = _make_ws_frame(msg)
            writer.write(frame)
            await writer.drain()

    except (asyncio.IncompleteReadError, ConnectionError, ConnectionResetError):
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        if queue is not None:
            ws_clients.discard(queue)
        try:
            writer.close()
        except Exception:
            pass


def _make_ws_frame(payload: str, opcode: int = 0x1) -> bytes:
    """Create a WebSocket frame (unmasked server→client)."""
    data = payload.encode("utf-8")
    length = len(data)
    frame = bytearray()
    frame.append(0x80 | opcode)  # FIN + opcode
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, "big"))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, "big"))
    frame.extend(data)
    return bytes(frame)


async def run_ws_server():
    """Start WebSocket server on WS_PORT."""
    server = await asyncio.start_server(ws_handler, BIND_HOST, WS_PORT)
    logger.info(f"WebSocket server on ws://{BIND_HOST}:{WS_PORT}")
    async with server:
        await server.serve_forever()


# ── HTTP Server (static files) ─────────────────────────────


async def http_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Simple HTTP server for static files."""
    try:
        data = await reader.readuntil(b"\r\n\r\n")
        request_line = data.decode("utf-8").split("\r\n")[0]
        method, path, _ = request_line.split(" ", 2)

        if path == "/":
            path = "/index.html"

        # Resolve file path
        NODE_MODULES_DIR = HERE / "node_modules"

        if path.startswith("/node_modules/"):
            # Serve from node_modules
            rel_path = path[len("/node_modules/"):]
            file_path = (NODE_MODULES_DIR / rel_path).resolve()
            try:
                file_path.relative_to(NODE_MODULES_DIR.resolve())
            except (ValueError, FileNotFoundError):
                file_path = None
        else:
            # Serve from static
            file_path = STATIC_DIR / path.lstrip("/")
            try:
                file_path = file_path.resolve()
                file_path.relative_to(STATIC_DIR.resolve())
            except (ValueError, FileNotFoundError):
                file_path = STATIC_DIR / "index.html"

        if file_path and file_path.exists() and file_path.is_file():
            content = file_path.read_bytes()
            ext = file_path.suffix.lower()
            content_types = {
                ".html": "text/html",
                ".js": "application/javascript",
                ".css": "text/css",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".svg": "image/svg+xml",
                ".map": "application/json",
            }
            ctype = content_types.get(ext, "application/octet-stream")
            header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {ctype}\r\n"
                f"Content-Length: {len(content)}\r\n"
                f"Access-Control-Allow-Origin: *\r\n"
                f"\r\n"
            ).encode()
            resp = header + content
            writer.write(resp)
        else:
            resp_404 = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 9\r\n\r\nNot Found"
            writer.write(resp_404)
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def run_http_server():
    """Start HTTP server on HTTP_PORT."""
    server = await asyncio.start_server(http_handler, BIND_HOST, HTTP_PORT)
    logger.info(f"HTTP server on http://{BIND_HOST}:{HTTP_PORT}")
    async with server:
        await server.serve_forever()


# ── Ambient Life (autonomous entity behaviour for the standalone demo) ──

import random
import re

_WALKABLE_TYPES = {"floor", "floor_vip", "throne", "arch", "door", "grass"}

# Idle/fallback musings — each agent ponders their REAL vault-research role.
_THOUGHTS = {
    "king":    ["These findings must cohere into doctrine.", "What should the OS become next?",
                "Time to turn this idea into a tool."],          # Aldric — Engineering Lead
    "guard_l": ["Where would this claim break?", "Stress-test it before it ships.",
                "Rigor first — prove it's robust."],             # Voss — Quality Assurance
    "guard_r": ["These two notes want connecting.", "This needs a feedback loop.",
                "A bridge is missing here."],                    # Elara — Bridge Builder
    "priest":  ["What's the deeper why here?", "A strange loop hides in this.",
                "Two distant ideas could fuse."],                # Orin — Idea Alchemist
    "thief":   ["Where's the gap no one sees?", "The frontier shifted again.",
                "The vault is silent on this."],                 # Kael — Research Scout
    "scholar": ["Cross-reference this with the vault.", "Knowledge wants structure.",
                "This deserves an evergreen note."],             # Mira — Knowledge Curator
    "artificer": ["Claimed — but does it compute?", "Re-run it from scratch.",
                  "A failed replication is still a result."],    # Rooke — Replication Unit
    "cartographer": ["Two continents, no bridge.", "The map shows a hole here.",
                     "Dense inside, silent between."],           # Wren — Cartographer
}


import heapq

_GUARDS = {"guard_l", "guard_r"}

# Posts around the keep that tasks send agents to. Each tile is a walkable standing
# spot; `role` is the agent who prefers it (others take it only if nothing else fits).
# Work spaces around the keep — RESEARCH names (these are the "location" choices the LLM
# sees, so they must not read as a dungeon). Tiles/visuals are unchanged.
_POSTS = {
    "workshop":     {"tile": (11, 4),  "title": "Build at the workshop",  "role": "king",    "act": "interact", "fx": "#ff66cc"},
    "frontier":     {"tile": (19, 4),  "title": "Scan the frontier desk", "role": "thief",   "act": "interact", "fx": "#ffd24d"},
    "library":      {"tile": (3, 3),   "title": "Work in the library",    "role": "scholar", "act": "interact", "fx": "#88aaff"},
    "atelier":      {"tile": (11, 8),  "title": "Ideate in the atelier",  "role": "priest",  "act": "casting",  "fx": "#a98bff"},
    "review-bench": {"tile": (11, 17), "title": "Review at the bench",    "role": "guard_l", "act": "interact", "fx": "#aaccff"},
    "atlas":        {"tile": (6, 11),  "title": "Map links at the atlas", "role": "guard_r", "act": "interact", "fx": "#ffae66"},
    "commons":      {"tile": (4, 16),  "title": "Meet in the commons",    "role": None,      "act": "interact", "fx": "#cfcfcf"},
    "forge":        {"tile": (19, 16), "title": "Prototype at the forge", "role": None,      "act": "interact", "fx": "#d4a35a"},
    "rep-bench":    {"tile": (17, 11), "title": "Replicate at the bench", "role": "artificer", "act": "casting", "fx": "#16a085"},
}

_ACT_LINES = {
    "interact": ["Done.", "All in order.", "As commanded."],
    "casting":  ["Blessings bestowed.", "The rite is complete.", "Spirits, hear me."],
    "guard":    ["Post secured.", "Nothing to report.", "All quiet here."],
}
_TALK = {  # research-shop openers (fallbacks)
    "king":    ["What did you find?", "Does that hold up?"],
    "guard_l": ["Where does this break?", "Prove it's robust."],
    "guard_r": ["I see a connection.", "These two notes link."],
    "priest":  ["What if we fused them?", "There's a deeper pattern."],
    "thief":   ["Found a gap in the vault.", "The frontier moved."],
    "scholar": ["I documented that.", "Let me cross-reference it."],
    "artificer": ["Show me the numbers.", "I re-ran it — want the result?"],
    "cartographer": ["Your domains don't talk.", "I found a hole in the map."],
}


# ── LLM Brain (OpenRouter / Nemotron) ───────────────────────────
# Agents think and converse in-character via a small, fast Nemotron model.
# Falls back to the canned _THOUGHTS/_TALK/_ACT_LINES tables when no key is set
# or any call fails, so the dungeon always runs.
import urllib.request as _urlreq
import time as _time

# LLM endpoint is fully env-configurable so we can point at any OpenAI-compatible
# provider (OpenRouter / DeepSeek / Ollama Cloud …). Set in agora-game-server/.env:
#   DUNGEON_LLM_URL   = https://api.deepseek.com/v1/chat/completions   (or ollama.com/v1/…)
#   LLM_API_KEY       = <provider key>     (OPENROUTER_API_KEY still works as a fallback)
#   DUNGEON_LLM_MODEL = deepseek-v4-flash  (or any hosted model)
_LLM_KEY = (os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")).strip()
_LLM_MODEL = os.environ.get("DUNGEON_LLM_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free").strip()
_LLM_URL = os.environ.get("DUNGEON_LLM_URL",
                          "https://openrouter.ai/api/v1/chat/completions").strip()
_LLM_ON = bool(_LLM_KEY)
# Output budget + reasoning toggle (reasoning models like Kimi K2.6 spend tokens on a `reasoning`
# channel and emit EMPTY content under a small budget — they need a bigger cap and/or think=false).
_LLM_MAX_TOKENS = int(os.environ.get("DUNGEON_LLM_MAX_TOKENS", "350"))
_LLM_THINK = os.environ.get("DUNGEON_LLM_THINK", "").strip().lower()  # "false" disables thinking

# Cloud concurrency throttle (2026-06-19): the ollama.com plan caps CONCURRENT requests and was
# returning HTTP 429 "too many concurrent requests" when the 8 agents + their per-tick activities
# fired cloud LLM calls all at once -> LLM_quests=0, agents starved. Gate every cloud call through a
# small semaphore so we stay under the cap (and leave headroom for the brain on the same account).
# Timeout-acquire (never blocks a worker thread > the timeout, never deadlocks): a waiter that can't
# get a slot returns None and the agent falls back to its renewable-quest pool. Env-tunable.
_LLM_CONCURRENCY = max(1, int(os.environ.get("DUNGEON_LLM_CONCURRENCY", "3")))   # ollama.com cap = 3
_LLM_SEM = threading.Semaphore(_LLM_CONCURRENCY)
# Wait long enough that waiters QUEUE and get served (FIFO-fair) rather than skip — so all 8 agents
# go through "na preskacku" (3 at a time, everyone in turn), not just the same fast few. A burst of 8
# drains in ~15s at 3-concurrency, so 30s almost never skips; the cap only ever holds 3 cloud calls.
_LLM_SEM_WAIT = float(os.environ.get("DUNGEON_LLM_SEM_WAIT", "30"))
# The per-agent LLM quest PLANNER (env DUNGEON_LLM_PLANNER) was switched off 2026-06-19 — it produced
# the self-referential "build a knowledge module" / "explore X" filler (the "gaming party") and its 8
# concurrent cloud calls per cycle were the dominant 429 cause — and DELETED 2026-07-31, because an
# off flag checked on the last line of the block that builds its input is not off: see the note in
# `replenish_quests`. Agents draw all work from the grounded `_renewable_quests` pool and from their
# own research organ.

# Pace: "study" = slow & deliberate (default; real research, light on the quota),
# "fast" = lively banter. Override with DUNGEON_PACE.
_PACE = os.environ.get("DUNGEON_PACE", "study").strip().lower()
_STUDY = _PACE != "fast"
_DECIDE_MIN, _DECIDE_MAX = (12.0, 24.0) if _STUDY else (3.0, 7.0)   # gap before PLANNING new goals
_BACKLOG_MIN, _BACKLOG_MAX = (4.0, 9.0)                             # gap to pull the NEXT queued quest
_CONV_COOLDOWN = 240.0 if _STUDY else 150.0                        # long gap between talks — chatter (agent-dialogue) was the #1 token sink at ROI 0.04; grounded collaboration is the default now
_WORK_DUR = (8.0, 18.0) if _STUDY else (3.0, 7.0)                   # how long an active quest "works" before it completes (telepathic, time-based)

_PERSONA = {
    "king":    "King Aldric — the keep's engineer-king who builds the tools and turns findings into doctrine. Commanding, decisive.",
    "guard_l": "Sergeant Voss — the keep's quality gate. Blunt, rigorous; stress-tests every claim before it ships.",
    "guard_r": "Dame Elara — the keep's bridge-builder. Sharp, dry-witted; finds the links between ideas others miss.",
    "priest":  "High Priest Orin — the idea alchemist. Solemn, cryptic; fuses distant concepts into new ones.",
    "thief":   "Shadow Kael — the frontier scout. Sly, quick, curious; hunts the gaps in the vault no one else sees.",
    "scholar": "Sage Mira — the obsessive archivist. Precise; structures raw research into evergreen knowledge.",
    "artificer": "Artificer Rooke — the replicator. Skeptical tinkerer; re-runs other people's claims as minimal models and trusts only what computes.",
    "cartographer": "Cartographer Wren — the map-maker. Quiet, far-sighted; charts the shape of the whole knowledge graph and points at the holes between continents.",
}

# Per-agent throttles (monotonic timestamps) + in-conversation guard.
_speech_cd: dict[str, float] = {}
_conv_cd: dict[str, float] = {}
_in_conv: set[str] = set()
_in_conv_seen: dict[str, float] = {}   # eid -> when it entered _in_conv (watchdog against leaks)


def _persona(eid: str) -> str:
    return _PERSONA.get(eid, "a weary dungeon dweller")


# ── Dogfood: the agents' working memory runs on inspeximus (Agora's own open-source memory layer) ──
# Each agent gets an inspeximus store; recall is value-ranked (relevance × accrued value), not recency.
# Guarded so a missing/broken memory layer never takes the dungeon down — it falls back to a plain list.
# Was: a sys.path.insert into a vendored copy of the library that sat beside the research
# probes, which had drifted a release behind. The library is now a normal installed dependency.
try:
    from inspeximus import Inspeximus as _Store
except Exception:
    _Store = None
_AGENT_MEM_DIR = Path(__file__).resolve().parent / ".agent_memory"
_agent_mem_stores: dict = {}
# A durable finding must survive whole: its `Source:` line and its falsifier live at the END of the
# text, which is exactly what a narrow cut removes. Quest chatter decays out and stays narrow.
_AGENT_MEM_FINDING_CHARS = 2000
_AGENT_MEM_CHATTER_CHARS = 300

# ── Semantic recall for the agents (dogfood the embedder path) ─────────────────────────────
# On a single GPU shared with the 30B planner, a live embed costs ~2s (it queues behind qwen). So
# embedding is kept OFF the hot path: writes stay fast (the vec is filled later by a throttled
# background worker) and recall query-embeds are cached. AGENT_SEMANTIC=0 -> pure lexical (original).
_SEMANTIC = os.environ.get("AGENT_SEMANTIC", "1") != "0"
_EMB_URL = os.environ.get("AGENT_EMBED_URL", "http://localhost:11434/api/embeddings")
_EMB_MODEL = os.environ.get("AGENT_EMBED_MODEL", "nomic-embed-text")
_emb_cache: dict = {}                       # text[:512] -> vec; FIFO-capped (query + write reuse)
_EMB_CACHE_MAX = 4000


def _ollama_embed(text: str):
    """text -> embedding via the local ollama embed model. Raises on failure (inspeximus then falls back
    to lexical, never crashes). keep_alive holds the embedder resident so it never cold-loads."""
    body = json.dumps({"model": _EMB_MODEL, "prompt": (text or "")[:512],
                       "keep_alive": "30m"}).encode()
    req = _urlreq.Request(_EMB_URL, data=body, headers={"Content-Type": "application/json"})
    with _urlreq.urlopen(req, timeout=8) as r:
        return json.loads(r.read())["embedding"]


def _cached_embed(text: str):
    key = (text or "")[:512]
    v = _emb_cache.get(key)
    if v is not None:
        return v
    v = _ollama_embed(text)
    if len(_emb_cache) >= _EMB_CACHE_MAX:
        _emb_cache.pop(next(iter(_emb_cache)), None)
    _emb_cache[key] = v
    return v


def _vec_backfill_worker():
    """Background + throttled: give vec-less ACTIVE memories a vector (highest value / most recent
    first) so semantic recall has a corpus to match — without blocking the game loop or starving the
    planner's GPU. inspeximus's atomic _save makes the shared-file writes corruption-safe."""
    _round = 0
    while True:
        try:
            _round += 1
            if _round % 40 == 0:                  # periodically re-bound the stores (superseded accrue on writes)
                _prune_superseded()
            did = 0
            for eid in list(_AGENT_NAMES):
                m = _agent_store(eid)
                if m is None:
                    continue
                cand = [r for r in list(m.items)
                        if r.get("status") == "active" and not r.get("vec")]
                if not cand:
                    continue
                cand.sort(key=lambda r: (-float(r.get("value", 1.0)), -float(r.get("ts", 0))))
                for r in cand[:8]:                    # small batch: this is BACKGROUND, must yield the GPU
                    try:
                        r["vec"] = list(_cached_embed(r.get("text", "")))
                        did += 1
                    except Exception:
                        pass
                    time.sleep(1.5)                   # GENTLE: the live agents' vault-search shares this one
                    # GPU embedder; a hot backfill starves them and freezes the visible world (2026-06-20).
                m._mat = None                         # invalidate cached vec-matrix -> recall sees new vecs
                try:
                    m._save()
                except Exception:
                    pass
            time.sleep(8.0 if did else 30.0)          # rest between batches so the embedder serves live work
        except Exception:
            time.sleep(30.0)


def _migrate_active_pool(target: int = 400):
    """One-time alignment with the keep=400 policy. Past keep=150 consolidations over-superseded, so
    each store sits below inspeximus's semantic crossover (300 active). Revive the highest-value superseded
    records up to `target` so recall actually runs the embedder. Idempotent (no-op once active>=target;
    the genuinely low-value tail stays superseded). Runs at startup, single-writer-safe."""
    if _Store is None:
        return
    for eid in list(_AGENT_NAMES):
        m = _agent_store(eid)
        if m is None:
            continue
        try:
            active = [r for r in m.items if r.get("status") == "active"]
            if len(active) >= target:
                continue
            cand = [r for r in m.items if r.get("status") == "superseded"]
            cand.sort(key=lambda r: -float(r.get("value", 1.0)))
            for r in cand[: target - len(active)]:
                r["status"] = "active"
            m._mat = None
            m._save()
            logger.info("active-pool migrate %s: %d -> %d active", eid, len(active),
                        min(target, len(active) + len(cand)))
        except Exception:
            pass


def _prune_superseded(keep_superseded: int = 1500) -> int:
    """Bound agent WORKING memory: keep every ACTIVE record plus the most-recent `keep_superseded` superseded
    (for history/revert), and hard-forget the older superseded tail. Agent working memory is ephemeral per-tick;
    without this the append-only store grows unbounded (found at ~56k records, 99% dead superseded), which
    drowns the vec-backfill worker in I/O (56k-item scans + ~2.4MB saves every round) so semantic recall never
    fills. Uses inspeximus's verified forget (scrubs links + toggle pointers). Idempotent; single-writer."""
    if _Store is None:
        return 0
    total = 0
    for eid in list(_AGENT_NAMES):
        m = _agent_store(eid)
        if m is None:
            continue
        try:
            # VALUE-PROTECTED: never drop a superseded record that carries durable knowledge — value>=2
            # (findings), a semantic/procedural type, or a source/key. Only the low-value EPISODIC chatter
            # tail is droppable, so a finding is never lost to pruning even as an old (superseded) value.
            # (The org's canonical research output also lives in the vault + shared brain store, not this
            # ephemeral per-tick scratchpad.)
            def _durable(r):
                return (float(r.get("value", 0) or 0) >= 2.0 or r.get("mtype") in ("semantic", "procedural")
                        or bool(r.get("source")) or bool(r.get("key")))
            droppable = [r for r in m.items if r.get("status") == "superseded" and not _durable(r)]
            if len(droppable) <= keep_superseded:
                continue
            droppable.sort(key=lambda r: -float(r.get("superseded_ts") or r.get("ts") or 0))
            drop = [r["id"] for r in droppable[keep_superseded:]]   # oldest LOW-VALUE superseded beyond the cap
            before = len(m.items)
            res = m.forget(ids=drop)
            total += res.get("forgotten", 0)
            logger.info("prune %s: dropped %d old superseded (store %d -> %d)", eid,
                        res.get("forgotten", 0), before, len(m.items))
        except Exception:
            pass
    return total


_vec_worker_started = False


def _start_vec_worker():
    global _vec_worker_started
    if _SEMANTIC and _Store is not None and not _vec_worker_started:
        _vec_worker_started = True
        _prune_superseded()              # unbloat FIRST (56k dead tail starved the worker) so vecs can fill
        _migrate_active_pool(400)        # cross the semantic crossover now, not in hours
        threading.Thread(target=_vec_backfill_worker, daemon=True, name="inspeximus-vec").start()
        logger.info("inspeximus semantic vec-backfill worker started (model=%s)", _EMB_MODEL)


def _agent_store(eid: str):
    if _Store is None:
        return None
    m = _agent_mem_stores.get(eid)
    if m is None:
        try:
            _AGENT_MEM_DIR.mkdir(exist_ok=True)
            # embed= gives recall the semantic path (query-embedded, value-ranked over vec-bearing
            # memories); vectors themselves are populated off the hot path by _vec_backfill_worker.
            m = _Store(str(_AGENT_MEM_DIR / f"{eid}.json"),
                       embed=(_cached_embed if _SEMANTIC else None))
            _agent_mem_stores[eid] = m
        except Exception:
            return None
    return m


def _recall_mem(eid: str, query: str, k: int = 4) -> str:
    """Value-ranked recall from the agent's inspeximus store — relevant past work, not just recent."""
    m = _agent_store(eid)
    if m is None:
        return ""
    try:
        return " | ".join(h.get("text", "") for h in m.recall(query, k=k))
    except Exception:
        return ""


# `_collective_recall` (top-k value-ranked memories pooled across ALL agents' stores) was deleted
# 2026-07-31 together with its only caller, the discarded LLM planner. It read every one of the eight
# inspeximus stores on every planning cycle to build a prompt that was never sent.


def _collective_top(query: str, exclude: str | None = None, min_score: float = 1.0):
    """The single strongest colleague memory for `query` across all other agents' inspeximus stores.
    Returns (colleague_eid, text, score) if it clears `min_score`, else None — the deterministic
    hook that lets an agent collaborate on a colleague's finding even when the flaky planner LLM
    returns nothing."""
    if _Store is None:
        return None
    best = None
    for oid in _AGENT_NAMES:
        if oid == exclude:
            continue
        m = _agent_store(oid)
        if m is None:
            continue
        try:
            for h in m.recall(query, k=2):
                if best is None or h.get("score", 0.0) > best[2]:
                    best = (oid, h.get("text", ""), h.get("score", 0.0))
        except Exception:
            pass
    return best if (best and best[2] >= min_score and best[1]) else None


def _keep_memory_signal() -> dict:
    """Reflect on the COLLECTIVE memory: the densest-value cohort + any flagged contradiction across
    all agents' stores. Uses inspeximus's value_by_cohort + contradictions — the product, on ourselves."""
    if _Store is None:
        return {}
    cohorts, contras = {}, []
    for oid in _AGENT_NAMES:
        m = _agent_store(oid)
        if m is None:
            continue
        try:
            for tag, c in m.value_by_cohort().items():
                agg = cohorts.setdefault(tag, {"count": 0, "value": 0.0})
                agg["count"] += c["count"]; agg["value"] += c["value"]
            contras.extend(m.contradictions())
        except Exception:
            pass
    top = max(cohorts.items(), key=lambda kv: kv[1]["value"], default=None)
    return {"top_cohort": (top[0] if top else None),
            "top_value": (round(top[1]["value"], 1) if top else 0.0),
            "contradictions": len(contras)}


def _llm_content_sync(system: str, user: str) -> str | None:
    """Blocking OpenRouter call → raw assistant message content, or None on failure."""
    if not _LLM_ON:
        return None
    body = {
        "model": _LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.95,
        "max_tokens": _LLM_MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }
    if _LLM_THINK == "false":     # reasoning models (Kimi K2.6): emit content directly, no reasoning channel
        body["think"] = False
    payload = json.dumps(body).encode()
    req = _urlreq.Request(_LLM_URL, data=payload, headers={
        "Authorization": f"Bearer {_LLM_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/DanceNitra/agora",
        "X-Title": "Dungeon OS",
    })
    if not _LLM_SEM.acquire(timeout=_LLM_SEM_WAIT):
        logger.debug("LLM call skipped: cloud concurrency gate busy (avoiding 429)")
        return None
    try:
        with _urlreq.urlopen(req, timeout=45) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug(f"LLM call failed: {e}")
        return None
    finally:
        _LLM_SEM.release()


#: A press draft is 400-900 words. `_llm_content_sync` caps at 350 tokens and forces a JSON object,
#: both correct for the one-line world chatter it was written for and both fatal for prose.
_LLM_PROSE_MAX_TOKENS = int(os.environ.get("DUNGEON_LLM_PROSE_MAX_TOKENS", "3000"))


def _llm_prose_sync(system: str, user: str, max_tokens: int = 0) -> str | None:
    """Blocking LLM call returning PROSE. No `response_format`, a real token budget, a longer timeout.

    Added 2026-08-01 because `_OrganCtx` had no `llm` attribute at all, while Sage Mira's press arm
    reads `getattr(ctx, "llm", None)` and refuses when it is not callable. The refusal is deliberate
    and right -- assembling a post out of note fragments and Telegramming it to the owner four times a
    day is exactly the stream of small notes he told us to stop -- but the capability was never wired,
    so the arm could not draft on ANY target, ever, and reported a polite idle every cycle. Another
    check that never saw its target: the organ said "ready but no composer available" and the gate
    read that as an agent with nothing to do.
    """
    if not _LLM_ON:
        return None
    body = {
        "model": _LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.7,
        "max_tokens": int(max_tokens) if max_tokens and max_tokens > 0 else _LLM_PROSE_MAX_TOKENS,
    }
    if _LLM_THINK == "false":
        body["think"] = False
    req = _urlreq.Request(_LLM_URL, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {_LLM_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/DanceNitra/agora",
        "X-Title": "Dungeon OS",
    })
    if not _LLM_SEM.acquire(timeout=_LLM_SEM_WAIT):
        logger.debug("prose LLM call skipped: concurrency gate busy")
        return None
    try:
        with _urlreq.urlopen(req, timeout=300) as r:      # a long local generation, not a chat line
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug(f"prose LLM call failed: {e}")
        return None
    finally:
        _LLM_SEM.release()


def _llm_say_sync(system: str, user: str) -> str | None:
    """OpenRouter call expecting {"line": "..."} → the line, or None."""
    content = _llm_content_sync(system, user)
    if not content:
        return None
    try:
        line = (json.loads(content).get("line") or "").strip()
        return line[:120] or None
    except Exception:
        return None


async def _llm_say(system: str, user: str, fallback: str) -> str:
    line = await asyncio.to_thread(_llm_say_sync, system, user)
    return line or fallback


def _schedule_thought(eid: str, situation: str, fallback: str) -> None:
    """Show the fallback line instantly, then replace it with an LLM line when ready."""
    engine.set_entity_thought(eid, fallback)
    if not _LLM_ON or eid in _in_conv:
        return
    now = _time.monotonic()
    if now < _speech_cd.get(eid, 0.0):
        return
    _speech_cd[eid] = now + 900.0           # flavor 'thought' LLM lines were agent-think: 1.7M tok / 0 research value. Keep them RARE — the instant fallback line still shows, so the world stays alive without the spend.

    async def _run():
        sysmsg = (f"You are {_persona(eid)} You are in a torch-lit medieval dungeon keep. "
                  f'Reply ONLY with JSON {{"line":"<one short in-character line, max 12 words>"}}.')
        line = await _llm_say(sysmsg, situation + " Your line:", fallback)
        if eid not in _in_conv:  # don't stomp an active conversation
            engine.set_entity_thought(eid, line)

    asyncio.create_task(_run())


async def _converse(a_id: str, b_id: str, hold: dict[str, int], memory: dict) -> None:
    """Two researchers talk shop about their CURRENT vault work — a few speech bubbles."""
    ents = engine.state.entities
    a, b = ents.get(a_id), ents.get(b_id)
    if not a or not b or a_id in _in_conv or b_id in _in_conv:
        return
    _in_conv.add(a_id)
    _in_conv.add(b_id)
    try:
        ax, ay = int(round(a.x)), int(round(a.y))
        bx, by = int(round(b.x)), int(round(b.y))
        engine.face_entity(a_id, bx, by)
        engine.face_entity(b_id, ax, ay)
        engine.set_entity_state(a_id, "thinking")
        engine.set_entity_state(b_id, "thinking")
        hold[a_id] = hold[b_id] = 99  # pause both while they talk

        turns = [(a_id, a.name, b.name), (b_id, b.name, a.name), (a_id, a.name, b.name)]
        history: list[str] = []
        for sid, sname, oname in turns:
            oid = b_id if sid == a_id else a_id
            my_work = " | ".join(memory.get(sid, [])[-3:]) or "(just arrived)"
            sysmsg = (f"You are {_persona(sid)} You are a researcher at the Vault Company talking "
                      f"shop with your colleague {oname}. Discuss your CURRENT research — a finding, "
                      f"a gap, a concept worth connecting, or a friendly debate about an idea drawn "
                      f"from the vault. Be concrete and substantive; NEVER dungeon chit-chat (no "
                      f"prisoners, smells, gold, guards, thrones, omens). Reply ONLY JSON "
                      f'{{"line":"<one spoken line about the work, max 16 words>"}}.')
            convo = "  ".join(history) if history else "(you open)"
            fb = random.choice(_TALK.get(sid, ["What did you find?", "..."]))
            line = await _llm_say(sysmsg, f"Your recent work: {my_work}\n"
                                  f"Dialogue so far: {convo}\nReply to {oname} about the research.", fb)
            engine.set_entity_thought(sid, line)
            # one-shot knowledge packet, speaker → listener, so you SEE who talks to whom
            # (carry the actual line + names so the Event Log shows real Q&A, not just "grew closer")
            broadcast({"type": "converse", "from": sid, "to": oid,
                       "from_name": sname, "to_name": oname, "text": line})
            history.append(f"{sname}: {line}")
            await asyncio.sleep(2.4)
        await asyncio.sleep(1.0)
        await record_trust(a_id, b_id, "cooperate")  # a friendly talk builds trust
        for cid in (a_id, b_id):
            engine.set_entity_thought(cid, "")
            engine.set_entity_state(cid, "idle")
    finally:
        now = _time.monotonic()
        _conv_cd[a_id] = _conv_cd[b_id] = now + _CONV_COOLDOWN
        hold[a_id] = hold[b_id] = 0
        _in_conv.discard(a_id)
        _in_conv.discard(b_id)


def _maybe_start_conversation(ents, dead: dict[str, int], hold: dict[str, int], memory: dict) -> None:
    """Find one eligible nearby pair and start a research conversation (one per tick)."""
    now = _time.monotonic()
    ids = [e for e in ents if e not in _in_conv
           and dead.get(e, 0) == 0 and now >= _conv_cd.get(e, 0.0)]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if a in _GUARDS and b in _GUARDS:
                continue  # two guards spar instead of chatting
            ea, eb = ents[a], ents[b]
            if abs(ea.x - eb.x) + abs(ea.y - eb.y) <= 2:  # within 2 tiles
                asyncio.create_task(_converse(a, b, hold, memory))
                return


# ── Meaningful collaboration: agents co-produce REAL grounded findings, varied + seeded ──
_collab_cd: dict = {}        # eid -> next monotonic time it may collaborate
_collab_recent: list = []    # recent "a|b" pairs, to vary partners
_collab_rot = {"i": 0}
_COLLAB_COOLDOWN = 40        # grounded co-production is the dominant activity now (it feeds verify-findings, ROI 0.92), so its per-agent gap is short

# what each role best CONTRIBUTES when joining another agent's work
_ROLE_CONTRIB = {
    "thief":   "scout sharper evidence and adjacent frontier work",
    "scholar": "curate it into one crisp, structured claim",
    "priest":  "connect it across domains into a novel idea",
    "king":    "turn it into something buildable — an experiment or a tool",
    "guard_r": "find what in the vault it should link to",
    "guard_l": "stress-test it — name the weakest assumption or the hole",
    "artificer": "say what a MINIMAL computational model of it would be and what number it must show",
    "cartographer": "name which DISTANT vault domain this should bridge to, and why the hole matters",
}


async def _on_board(text: str) -> bool:
    """Is this subject on the owner's standing priorities? Same terms the quest gate uses.

    Deliberately permissive when the board is silent: with no priorities set, everything is
    on-board, because a gate with nothing to gate on must not stop the organism.
    """
    await _gate_refresh()
    prio = _gate_cache.get("prio") or set()
    return (not prio) or bool(_theme_words(text or "") & prio)


async def _pick_collab_seed():
    """Rotate the collab/pipeline seed across REAL RESEARCH only: fresh papers to ground, Agora's own
    claims to test, under-explored thin frontier domains, and recent findings to deepen. Combinatorial
    'bridge' (A <-> B) and 'gap' seeds were removed 2026-06-19 — they produced the low-substance
    'AgentA + AgentB: X <-> Y' filler the owner called a 'gaming party'. No source = skip, never a bridge."""
    # EVERY SEED PASSES THE BOARD (2026-07-31). Not one of these four slots was filtered, so the
    # pipeline -- the dominant trust engine, five cooperations every ~57s and seven LLM stages per
    # artifact -- seeded itself on whatever arXiv happened to deliver. Measured on the live library:
    # 2 of 12 papers were on-board, so 83% of pipelines opened off-mission. The refusals prove where
    # they ended up: 16 of 25 post-restart write attempts were refused LAB-FIRST, on subjects like
    # "Multiplicity of closed Reeb orbits on contact manifolds", "TIME Commissioning Observations II"
    # and "Polynomial equivalence of the global transverse-field Ising model". The write door was
    # holding the line and the whole cost had already been paid upstream.
    #
    # An off-board slot now falls through to the next rather than seeding, and a cycle with nothing
    # on-mission opens no pipeline at all. Starvation is logged, never papered over with filler.
    i = _collab_rot["i"] % 4
    _collab_rot["i"] += 1
    try:
        if i == 0:                                        # FRESH PAPER — grounded, novel frontier literature
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/library", 60)
            ps = [p for p in (d or {}).get("papers", []) if (p.get("title") or "").strip()]
            on = [p for p in ps if await _on_board(p["title"])]
            if ps and not on:
                logger.info("[collab] %d library paper(s), none on-board - falling through", len(ps))
            if on:
                p = random.choice(on)
                return ("paper", p["title"][:80],
                        f"Ground ONE finding this paper directly supports, naming it (Author Year): {p['title']}")
        if i == 1:                                        # TEST AGORA'S OWN CLAIM (flywheel falsifiers)
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=4", 60)
            qs = [q for q in ((d or {}).get("open") or []) if await _on_board(q.get("question", ""))]
            if qs:
                q = random.choice(qs)
                return ("claim", q["question"][:80], f"Find real evidence on whether this holds: {q['question']}")
        if i == 2:                                        # FRONTIER — under-explored THIN domains (not combinatorial holes)
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/frontier-seed", 75)
            t = (d or {}).get("target") or {}
            if t.get("target") and t.get("kind") != "hole" and await _on_board(t["target"]):
                return ("frontier-thin", t["target"][:80], t.get("prompt", "")[:300])
        # i == 3, or any slot whose own source was empty → deepen a recent REAL finding
        d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=8")
        ks = [k for k in (d or {}).get("knowledge", []) if (k.get("content") or "")]
        # Judged on the TITLE the seed will carry, not the body: the body of an off-mission note can
        # still mention "memory" in passing and wave the whole subject through.
        ks = [k for k in ks
              if await _on_board((k.get("title") or "").replace("Pipeline: ", ""))]
        if ks:
            k = random.choice(ks)
            title = (k.get("title") or "a recent finding").replace("Pipeline: ", "").strip()
            return ("finding", title[:80], (k.get("content") or "")[:240])
        # final fallback → a fresh paper (NEVER a bridge, and never off-board)
        d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/library", 60)
        ps = [p for p in (d or {}).get("papers", []) if (p.get("title") or "").strip()
              and await _on_board(p["title"])]
        if ps:
            p = random.choice(ps)
            return ("paper", p["title"][:80], f"Ground ONE finding this paper supports: {p['title']}")
        logger.info("[collab] no on-board seed in any slot this cycle - opening no pipeline")
    except Exception:
        pass
    return None


async def _collaborate(a_id, b_id, seed_kind, seed_title, seed_text, hold) -> None:
    """Two agents co-produce a REAL grounded joint finding from a shared seed — visible + posted."""
    ents = engine.state.entities
    a, b = ents.get(a_id), ents.get(b_id)
    if not a or not b or a_id in _in_conv or b_id in _in_conv:
        return
    _in_conv.add(a_id)
    _in_conv.add(b_id)
    an, bn = a.name, b.name
    try:
        engine.face_entity(a_id, int(round(b.x)), int(round(b.y)))
        engine.face_entity(b_id, int(round(a.x)), int(round(a.y)))
        engine.set_entity_state(a_id, "thinking")
        engine.set_entity_state(b_id, "thinking")
        hold[a_id] = hold[b_id] = 99
        sources = await _brain_research(seed_title)
        if not sources or "(no external" in sources:
            sources = await _brain_research(seed_text[:90])    # second angle: the seed text itself
        a_line = await _llm_say(
            f"You are {_persona(a_id)} You and your colleague {bn} are co-working a {seed_kind}.",
            f"The {seed_kind}: '{seed_text}'. In ONE line (max 18 words), tell {bn} what it is "
            f"and exactly what you need from them.",
            f"{bn}, let's develop {seed_title} together.")
        engine.set_entity_thought(a_id, a_line)
        broadcast({"type": "converse", "from": a_id, "to": b_id,
                   "from_name": an, "to_name": bn, "text": a_line})
        await asyncio.sleep(2.4)
        contrib = _ROLE_CONTRIB.get(b_id, "add your angle")
        b_line = await _llm_say(
            f"You are {_persona(b_id)} Your colleague {an} brought you a {seed_kind} to work on.",
            f"It is: '{seed_text}'. Your job: {contrib}. Real sources: {sources[:400]}. "
            f"In ONE line (max 20 words), give your concrete contribution.",
            f"Here is my angle on {seed_title}.")
        engine.set_entity_thought(b_id, b_line)
        broadcast({"type": "converse", "from": b_id, "to": a_id,
                   "from_name": bn, "to_name": an, "text": b_line})
        await asyncio.sleep(2.4)
        # NO SOURCES, NO FINDING: with an empty literature block the joint-LLM (told NEVER to
        # invent sources) can only refuse — and those refusals were shipping as findings
        # ("Please provide the source you intend me to use" in the morning report). The agent's
        # source IS the internet fetch above; when both query angles return nothing, the honest
        # move is to skip the slot, not to beg a human for a citation.
        if not sources or "(no external" in sources:
            broadcast({"type": "os_build", "kind": "collab", "who": f"{an} + {bn}",
                       "text": f"no real source found for '{seed_title[:36]}' — joint finding skipped"})
        else:
            joint = await asyncio.to_thread(
                _llm_content_sync,
                f"Combine {an} and {bn}'s exchange into ONE joint FINDING (2 sentences) that a specific "
                f"source below DIRECTLY supports — paraphrase that paper's actual result and name it "
                f"(Author Year). Stay close to the evidence; do NOT over-generalize. NEVER invent sources.",
                f"Seed ({seed_kind}): {seed_text}\n{an}: {a_line}\n{bn}: {b_line}\n\nReal sources:\n{sources}")
            if joint and joint.strip():
                src = "\nSource: " + sources.splitlines()[0].lstrip("- ").strip()[:140]
                await _brain_contribute(a_id, f"{an} + {bn}: {seed_title}", joint.strip()[:420] + src)
                broadcast({"type": "os_build", "kind": "collab", "who": f"{an} + {bn}",
                           "text": f"co-produced: {seed_title}"})
        await record_trust(a_id, b_id, "cooperate")
        for cid in (a_id, b_id):
            engine.set_entity_thought(cid, "")
            engine.set_entity_state(cid, "idle")
    except Exception as e:
        logger.debug(f"collaborate {an}+{bn}: {e}")
    finally:
        now = _time.monotonic()
        _conv_cd[a_id] = _conv_cd[b_id] = now + _CONV_COOLDOWN
        _collab_cd[a_id] = _collab_cd[b_id] = now + _COLLAB_COOLDOWN
        hold[a_id] = hold[b_id] = 0
        _in_conv.discard(a_id)
        _in_conv.discard(b_id)


async def _maybe_collaborate(hold) -> None:
    """Pick an initiator + a complementary, NON-recent partner + a real seed → co-produce."""
    now = _time.monotonic()
    free = [e for e in _AGENT_NAMES if e not in _in_conv
            and now >= _collab_cd.get(e, 0.0) and now >= _conv_cd.get(e, 0.0)]
    if len(free) < 2:
        return
    seed = await _pick_collab_seed()
    if not seed:
        return
    random.shuffle(free)
    a_id = free[0]
    for b_id in free[1:]:
        pair = "|".join(sorted((a_id, b_id)))
        if pair in _collab_recent[-4:]:
            continue                                   # don't repeat the same pair
        _collab_recent.append(pair)
        del _collab_recent[:-8]
        asyncio.create_task(_collaborate(a_id, b_id, *seed, hold))
        return


# ── Orchestrated research pipeline: ONE artifact flows through every role, each adds value ──
# ALL EIGHT ROLES, fixed 2026-07-31. This list ran six agents and silently excluded `artificer` and
# `cartographer`, and the pipeline is the keep's dominant trust generator: one full pass records a
# cooperation for every consecutive pair, and it opens every ~9 ticks. Measured in dungeon_trust.db on
# 2026-07-31: the six agents on this list carry ~42,000 recorded interactions each, Rooke and Wren
# ~2,689 — a 15x deficit that is an artefact of THIS list, not of anything either agent did. That
# deficit lands them at the bottom of `_compute_standing`, and `_market_won` then prices standing into
# discovery slots (p = 0.5 + 0.5*(s-lo)/(hi-lo)), so the two agents nobody let into the assembly line
# were also charged double for their own research: p=0.50 against p=1.00 for the top of the roster.
# Excluded from the trust engine -> lowest standing -> priced out of half their cognition, on a loop.
# Positions are role-appropriate, not appended: Wren places the claim on the map before Orin fuses it,
# and Rooke reduces it to something that computes before Voss stress-tests it. Eight stages at ~9 ticks
# per stage makes a full pipeline ~76s instead of ~57s.
_PIPELINE_STAGES = [
    ("thief",   "scout",    "Scout the frontier and state the core claim, citing a real source."),
    ("cartographer", "locate", "Say which two domains this sits between, and what hole it fills."),
    ("priest",  "connect",  "Add ONE novel cross-domain connection or reframing."),
    ("scholar", "curate",   "Curate it into one crisp, well-structured claim."),
    ("guard_r", "link",     "Name which of the user's vault ideas this should connect to."),
    ("artificer", "reduce", "Name the smallest computation that would settle this, and what it outputs."),
    ("guard_l", "validate", "Stress-test it: name the weakest assumption, or say it holds and why."),
    ("king",    "commit",   "Synthesize the whole chain into the final, concrete finding."),
]
_pipeline = {"item": None, "busy": False, "shipped": 0}   # `shipped` rotates the artifact's byline

# BUDGET AGAINST THE CAP THAT ACTUALLY APPLIES -- the brain's, one layer below where anyone looking
# at the dungeon would check. It was 500 on both sides, and 500 was a size from when a contribution
# was one sentence of flavour text.
#
# The organs write a structured note of 1,500-3,000 characters with VERDICT, INDEPENDENCE and the
# Falsifier at the END, so the cap kept the preamble and deleted the evidence. Measured 2026-07-31:
# every one of the last 40 discoveries was stored at EXACTLY 500 chars, 0 of 40 stated a falsifier
# against 984 of 10,437 lifetime rows (9.4%), and Dame Elara's note ended mid-word -- "...a NUMBER
# disputed between a note and its own". A swarm-wide contract gap that was a substring operation.
#
# Raised WITH the brain (`agent_os._CONTRIB_MAX_CHARS`); a test pins the two together, because
# raising one alone changes nothing and the failure is silent on both sides.
_CONTRIB_CAP = 8000

_PIPELINE_STATE_FILE = HERE / ".pipeline_state.json"


def _pipeline_shipped_bump() -> int:
    """Increment and PERSIST the shipped counter that rotates the pipeline byline.

    In memory only, the counter resets to 0 on every restart and the first stage (`thief`) takes the
    byline again -- on a process the watchdog recycles, that is a permanent over-credit rather than the
    1/N share the rotation exists to give. `_recent_intents` and the organ schedule are persisted for
    exactly this reason; this one was not.
    """
    n = 0
    try:
        n = int(json.loads(_PIPELINE_STATE_FILE.read_text(encoding="utf-8")).get("shipped", 0))
    except Exception:
        n = int(_pipeline.get("shipped", 0) or 0)      # first run, or an unreadable file
    n += 1
    try:
        _atomic_write(_PIPELINE_STATE_FILE, json.dumps({"shipped": n}))
    except Exception:
        pass                                          # a lost counter must never drop a shipped artifact
    return n


async def _pipeline_tick(hold) -> None:
    """Aldric's assembly line: advance one stage per call; each role builds on the last; the
    finished artifact is committed to the vault. One pipeline at a time, so it's watchable."""
    if _pipeline["busy"]:
        return
    _pipeline["busy"] = True
    active = None
    try:
        item = _pipeline["item"]
        if not item:                                    # Aldric opens a new pipeline
            seed = await _pick_collab_seed()
            if not seed:
                return
            _kind, title, text = seed
            _pipeline["item"] = {"title": title, "seed": text,
                                 "sources": await _brain_research(title),
                                 "stage": 0, "artifact": [], "by": []}
            broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                       "text": f"opened a pipeline → {title[:42]}"})
            return
        stage = item["stage"]
        eid, label, task = _PIPELINE_STAGES[stage]
        _in_conv.add(eid)
        active = eid                                    # so the finally can release it on error
        hold[eid] = 12                                  # pause this agent so you see it work
        prior = "  ".join(item["artifact"]) or "(you are first — start it)"
        line = await _llm_say(
            f"You are {_persona(eid)} You are the '{label}' stage of a research assembly line.",
            f"Topic: {item['seed']}\nReal sources: {item['sources'][:450]}\n"
            f"Work so far: {prior}\nYour task: {task} Reply in ONE line (max 20 words).",
            f"{label}: {item['title']}")
        engine.set_entity_thought(eid, line)
        engine.set_entity_state(eid, "thinking")
        item["artifact"].append(f"{_AGENT_NAMES[eid]} ({label}): {line}")
        item["by"].append(_AGENT_NAMES[eid])
        broadcast({"type": "os_build", "kind": "collab", "who": _AGENT_NAMES[eid],
                   "text": f"{label} → {item['title'][:40]}"})
        if stage + 1 < len(_PIPELINE_STAGES):           # hand off to the next role (packet)
            broadcast({"type": "converse", "from": eid, "to": _PIPELINE_STAGES[stage + 1][0]})
        _in_conv.discard(eid)
        active = None
        item["stage"] += 1
        if item["stage"] >= len(_PIPELINE_STAGES):      # ship it
            stages = [s[0] for s in _PIPELINE_STAGES]
            chain = "\n".join(item["artifact"])
            final = await asyncio.to_thread(
                _llm_content_sync,
                "Distill this assembly line into ONE final finding (2-3 sentences) that a specific "
                "source below DIRECTLY supports — paraphrase that paper's actual result and name it "
                "(Author Year). Stay close to the evidence; do NOT over-reach. NEVER invent sources.",
                f"Topic: {item['seed']}\nChain:\n{chain}\n\nSources:\n{item['sources']}")
            if final and final.strip():
                src = ""
                if item["sources"] and "(no external" not in item["sources"]:
                    src = "\nSource: " + item["sources"].splitlines()[0].lstrip("- ").strip()[:140]
                # CREDIT THE WORK, NOT THE SEAT, fixed 2026-07-31. This byline was the literal string
                # "king" for every pipeline ever shipped, not because Aldric wrote the artifact but
                # because he owns the LAST stage of the list. Every stage contributes one line; the
                # ledger recorded all of them under one name and then read that as productivity —
                # King Aldric shows 4,321 discoveries in the brain's collective store against ~900
                # for everyone else, a 4.8x lead that is entirely this one hard-coded word. It is not
                # cosmetic: discoveries feed `_compute_standing`, standing feeds `_market_won`, so the
                # agent credited with other agents' output outbids them for the next discovery slot.
                # A pipeline artifact has N authors and the collective store takes one `npc`, so the
                # byline ROTATES along the chain — each agent carries ~1/N of the pipelines, which is
                # its true share of the work — and the full chain is named in the body, so no
                # contribution is anonymous whoever happens to hold the byline.
                # THE CHAIN IS THE GUARANTEE, so it gets its budget FIRST. Written the other way round
                # -- final[:400] then [:430] on the join -- it left 30 characters for a chain that is
                # 138 characters long for eight agents, so it truncated to "Chain: Shadow Kael -> High
                # Pr" and six of the eight contributors were anonymous after all. A comment promising a
                # guarantee the code does not deliver is worse than no comment: it stops the next
                # reader from checking. Reserve the chain and the source, give `final` the remainder,
                # and never cut a name in half.
                _chain = "\nChain: " + " -> ".join(item["by"])
                _room = _CONTRIB_CAP - len(_chain) - len(src)
                if _room < 120:                  # a chain this long leaves no room for the finding
                    _chain = "\nChain: %d agents, see the world log" % len(item["by"])
                    _room = _CONTRIB_CAP - len(_chain) - len(src)
                    logger.info("[pipeline] chain too long to name inline (%d agents)", len(item["by"]))
                # Persisted, so a restart does not hand the byline back to the first stage every time.
                # `_recent_intents` and the organ schedule are both persisted for exactly this reason;
                # leaving one counter in memory would have given `thief` a permanent share of the credit
                # on a process that the watchdog recycles.
                _pipeline["shipped"] = _pipeline_shipped_bump()
                _author = stages[(_pipeline["shipped"] - 1) % len(stages)]
                await _brain_contribute(_author, f"Pipeline: {item['title']}",
                                        final.strip()[:max(0, _room)] + _chain + src)
                broadcast({"type": "os_build", "kind": "collab", "who": " → ".join(item["by"]),
                           "text": f"shipped: {item['title'][:40]}"})
            for x in range(len(stages) - 1):            # consecutive handoffs build trust
                await record_trust(stages[x], stages[x + 1], "cooperate")
            for cid in stages:
                engine.set_entity_thought(cid, "")
            _pipeline["item"] = None
    except Exception as e:
        logger.debug(f"pipeline: {e}")
        _pipeline["item"] = None
    finally:
        if active:
            _in_conv.discard(active)                    # never leak a frozen agent
        _pipeline["busy"] = False


# ── ESS Trust Bridge ────────────────────────────────────────────
# The dungeon's social interactions feed the REAL server/agora TrustEngine
# (Axelrod TFT: cooperate +, defect −, forgiveness, decay). Conversation →
# cooperate; guards sparring → defect. Scores persist + stream to the client.
import importlib.util as _ilu

_TRUST_DB_PATH = str(HERE / "dungeon_trust.db")
_AGENT_NAMES = {
    "king": "King Aldric", "guard_l": "Sergeant Voss", "guard_r": "Dame Elara",
    "priest": "High Priest Orin", "thief": "Shadow Kael", "scholar": "Sage Mira",
    "artificer": "Artificer Rooke", "cartographer": "Cartographer Wren",
}
# Forecasting Tournament: ledger short name <-> dungeon eid; per-agent hit-rates cached here.
_FORECASTER_EID = {"Kael": "thief", "Mira": "scholar", "Orin": "priest",
                   "Aldric": "king", "Elara": "guard_r", "Voss": "guard_l",
                   "Rooke": "artificer", "Wren": "cartographer"}
_forecast_scores: dict = {}     # eid -> {"total", "correct", "hit_rate"} (refreshed by _run_predictions)
_mastery_scores: dict = {}      # eid -> verification rate (whose findings survive checking)
_bounty_scores: dict = {}       # eid -> kill-authority (whose challenges actually fell beliefs)
_standing_cache: dict = {}      # eid -> standing (refreshed by _broadcast_trust_graph)
_market_stats: dict = {"won": {}, "lost": {}}    # eid -> counts (the attention market's books)


def _market_won(eid: str) -> tuple[bool, float]:
    """ATTENTION MARKET: standing buys cognition. An agent's chance of winning a discovery
    slot (an LLM + research spend) scales with its standing RELATIVE to the others — the top
    agent always runs, the bottom one runs half the time. Differential reproduction, not
    starvation: everyone keeps sampling, the productive compound."""
    if not _standing_cache:
        return True, 1.0                     # market not open yet (no standing computed)
    s = _standing_cache.get(eid, 0.5)
    lo, hi = min(_standing_cache.values()), max(_standing_cache.values())
    p = 1.0 if hi - lo < 1e-9 else 0.5 + 0.5 * (s - lo) / (hi - lo)
    won = random.random() < p
    _market_stats["won" if won else "lost"][eid] = \
        _market_stats["won" if won else "lost"].get(eid, 0) + 1
    return won, p
_trust_engine = None
_trust_db = None


async def _init_trust() -> None:
    """Load the real TrustEngine from server/agora and back it with a local DB."""
    global _trust_engine, _trust_db
    if _trust_engine is not None:
        return
    try:
        import aiosqlite
        _trust_db = await aiosqlite.connect(_TRUST_DB_PATH)
        _trust_db.row_factory = aiosqlite.Row
        await _trust_db.executescript(
            """
            CREATE TABLE IF NOT EXISTS trust_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL, target_id TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0.3,
                interaction_count INTEGER NOT NULL DEFAULT 0,
                consecutive_cooperations INTEGER NOT NULL DEFAULT 0,
                consecutive_defections INTEGER NOT NULL DEFAULT 0,
                sliding_window TEXT NOT NULL DEFAULT '[]',
                last_updated TEXT,
                UNIQUE(source_id, target_id)
            );
            """
        )
        await _trust_db.commit()
        path = HERE.parent / "server" / "agora" / "coordination" / "ess_protocol.py"
        spec = _ilu.spec_from_file_location("ess_protocol_dungeon", str(path))
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _trust_engine = mod.TrustEngine(_trust_db)
        logger.info("ESS TrustEngine bridged (real server/agora code, db=%s)", _TRUST_DB_PATH)
    except Exception as e:
        logger.warning("Trust bridge unavailable (%s) — dungeon runs without trust", e)
        _trust_engine = None


async def _trust_matrix() -> list[dict]:
    """Current pairwise trust for every unordered agent pair."""
    if not _trust_engine:
        return []
    out = []
    eids = list(_AGENT_NAMES)
    for i, a in enumerate(eids):
        for b in eids[i + 1:]:
            try:
                out.append({"a": a, "b": b, "score": round(await _trust_engine.get_trust(a, b), 3)})
            except Exception:
                pass
    return out


async def record_trust(a: str, b: str, outcome: str) -> None:
    """Record a dungeon interaction into the ESS trust engine + broadcast it."""
    if not _trust_engine or a == b:
        return
    try:
        await _trust_engine.record_interaction(a, b, outcome)
        await _trust_engine.record_interaction(b, a, outcome)
        score = round(await _trust_engine.get_trust(a, b), 3)
        broadcast({
            "type": "trust_update", "a": a, "b": b,
            "a_name": _AGENT_NAMES.get(a, a), "b_name": _AGENT_NAMES.get(b, b),
            "outcome": outcome, "score": score,
        })
    except Exception as e:
        logger.debug("trust record failed: %s", e)


def _walkable(x: int, y: int) -> bool:
    s = engine.state
    if not (0 <= x < s.width and 0 <= y < s.height):
        return False
    t = s.tiles[y][x]
    return t.walkable and t.type in _WALKABLE_TYPES


def _astar(start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """4-directional A* over walkable tiles. Returns the path incl. start & goal, or None."""
    if start == goal:
        return [start]
    if not _walkable(*goal):
        return None
    came: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    g = {start: 0}
    openh = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), start)]
    while openh:
        _, cur = heapq.heappop(openh)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came[cur]
            return path[::-1]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (cur[0] + dx, cur[1] + dy)
            if not _walkable(*nb):
                continue
            ng = g[cur] + 1
            if nb not in g or ng < g[nb]:
                g[nb] = ng
                came[nb] = cur
                f = ng + abs(nb[0] - goal[0]) + abs(nb[1] - goal[1])
                heapq.heappush(openh, (f, nb))
    return None


# ── Brain bridge → server/agora (:8000): real memory, emotion, vault ──────────
# The dungeon is the BODY; each agent's MIND lives in server/agora. Best-effort:
# if :8000 is down, these no-op and the local goal engine still runs.
from urllib.parse import quote as _urlquote

_BRAIN_URL = os.environ.get("AGORA_BRAIN_URL", "http://127.0.0.1:8000").rstrip("/")
#: Router mount for every brain endpoint. `_brain_get_sync` takes a WHOLE path, so anything short of
#: this prefix 404s. Organ modules are handed `/brain/...` names in their contract and several wrote
#: exactly that, so `OrganCtx._api` normalises against this constant rather than each author guessing.
_API_PREFIX = "/api/v1/agent-os"
# CROSS-WIRED IDENTITY, fixed 2026-07-31. The last two rows were off by one against the authoritative
# table in server/agora/agent_os/agent_os.py:NPC_UUIDS, which reads ...006 = Artificer Rooke and
# ...008 = Cartographer Wren. There is no ...009 in that table at all. Consequences measured against
# the live brain: every `_brain_context("artificer", ...)` recalled WREN's memories and every
# `_brain_remember("artificer", ...)` wrote Rooke's lived experience into Wren's store, so Rooke's
# mind was Wren's; and every cartographer read/write addressed a UUID no agent owns, so Wren's writes
# 404'd into the bare `except` in _brain_post_sync and Wren has been running with an empty mind since
# the two agents were added. The names in the comments were right the whole time — only the digits
# were wrong, which is exactly why nobody read it.
_BRAIN_ID = {   # dungeon entity → server/agora NPC UUID (copied from NPC_UUIDS, do not hand-edit)
    "thief":   "00000000-0000-0000-0000-000000000001",  # Shadow Kael
    "scholar": "00000000-0000-0000-0000-000000000002",  # Sage Mira
    "priest":  "00000000-0000-0000-0000-000000000003",  # High Priest Orin
    "king":    "00000000-0000-0000-0000-000000000004",  # King Aldric
    "guard_r": "00000000-0000-0000-0000-000000000005",  # Dame Elara
    "artificer": "00000000-0000-0000-0000-000000000006",  # Artificer Rooke
    "guard_l": "00000000-0000-0000-0000-000000000007",  # Sergeant Voss
    "cartographer": "00000000-0000-0000-0000-000000000008",  # Cartographer Wren
}


def _brain_get_sync(path: str, timeout: int = 4):
    # default 4s for the fast endpoints; pass a longer timeout for slow LLM endpoints
    # (hypothesize, empirical-test) which otherwise always time out -> None.
    try:
        req = _urlreq.Request(_BRAIN_URL + path, headers={"Accept": "application/json"})
        with _urlreq.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


# Inbox tasks that are MACHINERY, not research themes — they carry no subject to gate on and must
# always get through (draining the queue, learning from what happened, owner-facing synthesis).
# `update canon` and `draft press` were here and should not have been: both carry a research subject
# and are exactly the kind of thing that must answer to the board.
_INBOX_ALWAYS = ("learn from outcomes", "forge ideas", "synthesize roadmap", "scout triage",
                 "scout outreach", "correspondence reply",
                 "cc:", "build:", "number-picks", "compose outreach",
                 # These two have no RESEARCH subject to gate on — their subject is Agora itself, the
                 # same reason "synthesize roadmap" and "learn from outcomes" are already here. Gating
                 # them against a 37-word research vocabulary was a category error, and it was eating
                 # them whole: measured 2026-07-25 over one log window, 54 drops, of which 17 were
                 # "attempt grand synthesis" and 12 were "forge analogy".
                 # The synthesis one is the worse loss. _run_synthesis_detector is Orin's flagship
                 # ability and deliberately rare — it fires ONLY when the canon's phase-transition
                 # precursors cross threshold, and its theme text ("the phase-transition precursors
                 # crossed threshold (bridge accel x2.0, 200 open falsifiers...)") can never contain a
                 # board keyword, so every single firing was discarded. That is why the panel reads
                 # "open falsifiers 200 · deepened 0 · synthesis pressure 35.33": the pressure kept
                 # climbing precisely because the attempts never arrived.
                 # NOT added: bridges and deepened insights (18 + 17 drops in the same window). Those
                 # DO name a research subject and are exactly the off-mission vault churn this gate
                 # was built to stop — they stay gated.
                 "attempt grand synthesis", "forge analogy")


# Subjects the board explicitly refuses, kept separate from what it asks for. Derived from the tail of
# the standing priorities ("ONLY test-beds, never the headline" + "Deprioritize ...") — these are the
# words a naive tokenizer turned into permissions.
def _light_stem(w: str) -> str:
    """Fold a simple English plural, and nothing else. MUST match `methods.light_stem` in the brain.

    This was `w.rstrip("s")`, which strips EVERY trailing s and therefore turned "inspeximus" into
    "inspeximu" -- the one term the board most needs to match, mangled by the matcher, while the
    brain published the term unstemmed. The two ends never met. Measured 2026-08-08.
    """
    # -ies -> -y, 2026-08-17, and it MUST land here in the same commit as `methods.light_stem`. The
    # docstring above records what a one-sided change costs: the two ends disagreed on every plural and
    # "agent" scored differently on the same text at the same moment. Rationale, measurements and the
    # rejected -ing variant are written out once, in the brain's copy; this is the mirror.
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


_BOARD_BANNED = {"physics", "finance", "health", "politics", "trivia", "cloud", "meta", "science",
                 "statistics", "neuroscience", "adhd", "longevity", "trading", "crypto", "fmri",
                 "psychology", "biology", "climate", "economics"}

# The SUBJECT has to be ours, not merely a word the board happens to contain. Matching any board token
# let "Specification curve correction tool" through on `correction` and "Build Vault Linter ... quality
# standards" through on `quality`, because the board prose contains those words in passing. A task that
# names none of these is not about our mission, whatever else it matches.
#
# TWO HALVES, ONE LITERAL. This set is the CURATED half: technical terms and competitor names that
# the owner's prose board cannot express as single words ("supersede", "provenance", "locomo",
# "graphiti"). The second group is the LIVE half, mirroring what `methods.board_priority_terms`
# derives from the board text he actually set. They were separate vocabularies and they disagreed on
# 41 terms: measured 2026-07-31, the curated half alone admitted 1 of Sergeant Voss's 8 challenge
# targets while the live half admitted 3 -- so his organ, which parses THIS literal with `ast`, was
# gating on the weaker of the two and refusing real work ("self-refinement plateaus at the critic's
# competence ceiling", "winner-take-all reinforcement becomes quality-blind").
#
# Kept as a literal rather than fetched, because `guard_l._board_vocabulary` reads it statically and
# must not execute this module (it is `__main__`; importing it would start a second server). The
# drift that costs is therefore guarded by a test, not by discipline.
_BOARD_CORE = {"memory", "memories", "inspeximus", "recall", "retrieval", "retrieve", "supersession",
               "supersede", "revert", "erasure", "erase", "forget", "poison", "provenance",
               "embedding", "embeddings", "rag", "vector", "mem0", "zep", "graphiti", "letta",
               "cognee", "memobase", "langmem", "benchmark", "locomo", "memops", "store", "context",
               "consolidation", "attestation", "tombstone", "receipt", "echo", "agent-memory",
               # the live half — see above
               "agent", "integrity", "moat", "quality", "correction", "product", "provable", "prove",
               "resistance", "roadmap", "multi", "compounds", "buyer", "competitor", "facing",
               # "operations" added 2026-08-08: the live board names it and this literal did not, so
               # `_inbox_theme_allowed` refused MemOps-shaped work -- the exact drift this list's
               # test exists to catch, sitting red and unread.
               "numero", "operations"}

#: The two literals above, folded through the SAME stem `_theme_words` applies, so the comparison in
#: `_inbox_theme_allowed` is stemmed-to-stemmed. Written out rather than stemming the literals in
#: place, because the source forms ("memories", "embeddings", "compounds") are what a human reading
#: the list expects to see.
_BOARD_CORE_STEM = {_light_stem(w) for w in _BOARD_CORE}
_BOARD_BANNED_STEM = {_light_stem(w) for w in _BOARD_BANNED}


def _inbox_theme_allowed(text: str) -> bool:
    """THE ONE CHOKE POINT for off-mission work.

    Thirty-one functions queue Claude-inbox tasks and only five of them called the board gate, which
    is why the churn kept coming back after each individual path was patched: 90 minutes after the
    inbox was cleared, a belief-challenge on conscientiousness-and-longevity and a replication of a
    deep-RL claim had already arrived, with the board locked to agent-memory integrity.

    Gating here instead covers every path at once, including ones added later. Uses the gate cache the
    async paths already refresh; when the cache is cold nothing is dropped, so a restart cannot
    silence the whole queue.
    """
    t = (text or "").strip().lower()
    if any(t.startswith(p) for p in _INBOX_ALWAYS):
        return True
    prio = _gate_cache.get("prio") or set()
    if not prio:
        return True                                  # no board priorities known yet -> do not block
    theme = t.split(" ||", 1)[0]
    theme = theme.split(":", 1)[1] if ":" in theme else theme
    words = _theme_words(theme)

    # REFUSED beats matched. The board names what it does NOT want in the same breath as what it
    # does ("Finance/health/physics are ONLY test-beds"; "Deprioritize generic meta-science,
    # politics, cloud/trivia"), and reading the text flat turned those into PASS tokens.
    # STEM BOTH SIDES. `words` comes from `_theme_words`, which stems; these two literals are
    # hand-written in whatever form read naturally ("compounds", "memories", "embeddings"). Comparing
    # a stemmed set against an unstemmed one drops every plural entry in the literal -- the same
    # mismatch that made the brain and the dungeon disagree about "agents", one layer over. Stemmed
    # once at module import, not per call.
    banned = words & _BOARD_BANNED_STEM
    if banned:
        logger.info("[gate] inbox task dropped, deprioritised subject %s: %s",
                    sorted(banned), theme.strip()[:80])
        return False
    if words & _BOARD_CORE_STEM:
        return True
    logger.info("[gate] inbox task dropped, names no subject of ours: %s", theme.strip()[:90])
    return False


def _brain_post_sync(path: str, body: dict, timeout: int = 4):
    # default 4s for the fast endpoints; pass a longer timeout for slow LLM endpoints.
    if path.endswith("/claude-inbox") and isinstance(body, dict) and "text" in body:
        if not _inbox_theme_allowed(body["text"]):
            return {"status": "skipped", "reason": "off-board"}
    try:
        req = _urlreq.Request(_BRAIN_URL + path, data=json.dumps(body).encode(),
                              headers={"Content-Type": "application/json"})
        with _urlreq.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


async def _brain_context(eid: str, situation: str) -> str:
    """Pull this agent's MIND from server/agora: emotion + relevant memories + a vault insight."""
    bid = _BRAIN_ID.get(eid)
    if not bid:
        return ""
    q = _urlquote(situation[:120])
    lines = []
    em = await asyncio.to_thread(_brain_get_sync, f"/api/v1/agent-os/{bid}/emotion")
    if em and em.get("current"):
        lines.append(f"Right now you feel {em['current']} (mood {float(em.get('mood', 0.7)):.2f}).")
    mq = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/agent-os/{bid}/memories/recall?q={q}&limit=4")
    if mq and mq.get("memories"):
        mems = "; ".join((m.get("content") or "")[:80] for m in mq["memories"][:3])
        if mems:
            lines.append(f"You remember: {mems}")
    vq = await asyncio.to_thread(_brain_get_sync, f"/api/v1/agent-os/brain/vault?q={q}&k=1")
    if vq and vq.get("results"):
        v = vq["results"][0]
        if v and v.get("text"):
            lines.append(f"From your studies ({v.get('title', '')}): {v['text'][:140]}")
    return "\n".join(lines)


async def _brain_remember(eid: str, content: str, tag: str = "neutral"):
    """Persist a lived experience back into the agent's server/agora memory."""
    bid = _BRAIN_ID.get(eid)
    if not bid:
        return
    await asyncio.to_thread(
        _brain_post_sync, f"/api/v1/agent-os/{bid}/memories",
        {"content": content[:200], "importance": 0.55, "emotional_tag": tag, "source": "dungeon"})


# `_brain_identity` (the agent's Vault-Company job description) was deleted 2026-07-31 with its only
# caller, the discarded LLM planner. Each organ carries its own role, so nothing needs to fetch it.


async def _brain_build_log() -> str:
    """Recent OS so far: collective discoveries + upgrade proposals (for recursion)."""
    bits = []
    ck = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=4")
    for k in (ck or {}).get("knowledge", [])[:3]:
        bits.append(f"knowledge: {k.get('title', '')}")
    up = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/upgrades?limit=4")
    for u in (up or {}).get("proposals", [])[:3]:
        bits.append(f"upgrade: {u.get('title', '')}")
    return " | ".join(bits) or "(nothing built yet)"


async def _brain_research(query: str) -> str:
    """Real frontier sources (arXiv) for grounding — formatted markdown, via the brain."""
    d = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/agent-os/brain/research?q={_urlquote(query[:120])}&n=4")
    return (d or {}).get("formatted", "")


async def _brain_vault_search(query: str) -> list:
    """The user's OWN semantically-relevant notes (titles + scores), via the brain."""
    d = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/agent-os/brain/vault-search?q={_urlquote(query[:120])}&k=5")
    return (d or {}).get("results", [])


_report_state = {"last": ""}


async def _send_morning_report() -> None:
    """Once per morning, ask the brain to build + Telegram a digest of overnight findings."""
    await asyncio.to_thread(_brain_post_sync,
                            "/api/v1/agent-os/brain/morning-report?send=true", {})


_GAP_CACHE = {"gaps": [], "ts": 0.0}


async def _brain_gaps() -> list:
    """The user's REAL knowledge gaps (isolated substantive notes), cached 5 min."""
    now = _time.monotonic()
    if _GAP_CACHE["gaps"] and now - _GAP_CACHE["ts"] < 300:
        return _GAP_CACHE["gaps"]
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/gaps?n=12")
    gaps = (d or {}).get("gaps", [])
    if gaps:
        _GAP_CACHE["gaps"], _GAP_CACHE["ts"] = gaps, now
    return _GAP_CACHE["gaps"]


_RECENT_INTENTS_FILE = Path(__file__).resolve().parent / ".recent_intents.json"
_RECENT_INTENTS_MAX = 50          # per agent


def _dedup_keep_last(seq) -> list:
    """Distinct values, keeping each at its MOST RECENT position.

    The budget is a RECENCY window, so a repeat must move an entry, never add one. Without this,
    `append` spends a slot per pick and the 50-entry history degenerates: measured 2026-08-08, all
    eight agents held 50 entries carrying 5-7 DISTINCT intents -- roughly eight copies apiece. The
    memory that exists to prevent repetition was being consumed by the repetition, so it remembered
    ~6 topics instead of 50 and every agent was permanently saturated.
    """
    return list(dict.fromkeys(list(seq)[::-1]))[::-1]


def _load_recent_intents() -> dict:
    """eid -> that agent's recently-issued intents. Accepts the legacy flat list on disk."""
    try:
        raw = json.loads(_RECENT_INTENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(raw, list):
        # MIGRATION from the single shared list: seed every agent with it, so the first cycle after
        # the upgrade dedups exactly as before and the per-agent histories diverge from there.
        return {e: _dedup_keep_last(raw)[-_RECENT_INTENTS_MAX:] for e in _AGENT_NAMES}
    if isinstance(raw, dict):
        # Dedup ON LOAD, so the saturated state already on disk heals at the next restart instead of
        # having to churn 50 picks per agent before the fix can take effect.
        return {k: _dedup_keep_last(v)[-_RECENT_INTENTS_MAX:]
                for k, v in raw.items() if isinstance(v, list)}
    return {}


# Recently-issued quest intents, to avoid repetition (self-upgrade #1). PERSISTED to disk so the dedup
# SURVIVES dungeon restarts — the watchdog's restart churn used to clear this every ~hour, so the swarm
# re-picked the same flywheel questions (the 8x-duplicate "Test Agora's claim" output monoculture, 2026-06-19).
#
# PER-AGENT since 2026-07-31. This was ONE 50-entry list shared by all eight agents, and the dedup that
# is meant to stop an agent repeating ITSELF was therefore stopping it from ever touching a topic a
# COLLEAGUE had touched. Two failures, both from the same line. First, the agents ate each other's
# work: the renewable pool is drawn from a handful of shared sources (flywheel questions, harvested
# directions, the library, the top-8 findings), so whoever planned first consumed the good candidates
# and the other seven were pushed onto the tail of the pool — the opposite of the intended per-agent
# variety, and the reason a single agent's plan could starve the rest of the keep of on-mission work.
# Second, and worse, the fallback INVERTS the guard: `chosen = (fresh or interleaved)`. Once the shared
# list had absorbed eight agents' picks, `fresh` came back empty for the next agent, the fallback
# handed it the unfiltered pool, and it drew the EXACT candidates the list was holding — a dedup that
# produces duplicates precisely when it is working hardest. A 50-entry budget spread over 8 agents is
# ~6 intents of real history each; per-agent it is the 50 the comment above always claimed.
_recent_intents: dict = _load_recent_intents()


def _save_recent_intents() -> None:
    try:
        _atomic_write(_RECENT_INTENTS_FILE,
            json.dumps({k: _dedup_keep_last(v)[-_RECENT_INTENTS_MAX:]
                        for k, v in _recent_intents.items()}),
            encoding="utf-8")
    except Exception:
        pass

_QUEST_PREFIX_RE = re.compile(
    r"^(?:Hypothesize on|Pursue direction|Deepen|Develop the gap|Connect|Frontier|Hypothesis|Pipeline"
    r"|Measured|Ground a finding from|Test Agora'?s claim|Hypothesize from findings|Replicate claim)"
    r"\s*:?\s*", re.I)


#: A finding is titled with the pair who produced it -- "King Aldric + Sage Mira: MemOps: ...". That
#: prefix is AUTHORSHIP, not subject, and leaving it on makes one topic look like as many distinct
#: topics as there are pairs who touched it. Measured 2026-08-08: the top-8 findings carried EIGHT
#: distinct strings over TWO real subjects (MemOps x6, QVal x2), and `b_find` sampled three of them
#: expecting three topics. Built from the live roster so it cannot over-match ordinary prose.
_ACTOR_PREFIX_RE = re.compile(
    r"^(?:(?:%s)(?:\s*\+\s*(?:%s))*)\s*:\s*" % ((("|".join(re.escape(n) for n in _AGENT_NAMES.values())),) * 2),
    re.I) if _AGENT_NAMES else None


def _strip_quest_prefix(title: str) -> str:
    """Peel any stacked quest/finding prefix so new intents don't nest into garbage like
    'Hypothesize on: Hypothesize on: Pursue direction: ...' (wastes LLM calls + pollutes titles).

    Also peels the AUTHOR pair prefix, for the same reason and with the same effect on supply.
    """
    t = (title or "").strip()
    for _ in range(4):
        new = _QUEST_PREFIX_RE.sub("", t).strip()
        if _ACTOR_PREFIX_RE is not None:
            new = _ACTOR_PREFIX_RE.sub("", new).strip()
        if new == t:
            break
        t = new
    return t


#: Why an agent ended a planning cycle with nothing — so the escalation tells the owner the truth.
#: "off_priority" (the board is narrower than the pool) is a DIFFERENT condition from an unreachable
#: brain, and reporting the first as the second sends "the brain may be down" while it is serving fine.
#: "exhausted" (every on-priority candidate has already been pursued by THIS agent) is a third: it
#: names a SUPPLY problem, and it is the honest reading of what the `(fresh or interleaved)` fallback
#: used to hide by re-serving work the brain then refused. Both are normal; neither is a blocker.
_plan_reason: dict = {}

# STARVATION MUST STAY VISIBLE -- AND HALF A MILLION IDENTICAL LINES A DAY IS NOT VISIBLE.
# The two "[plan] ... no research this cycle" / "0 grounded quest(s) from the renewable pool" lines
# below are deliberate, and the comments beside them are right: hiding a thin supply behind a fallback
# is what produced 1,435 guaranteed-reject writes, so the starvation gets logged rather than papered
# over. What was missed is that the logging itself has a legibility budget. Measured 2026-08-17: ONE
# dungeon process had written "no research this cycle" 1,505,267 times in three days -- ~500k/day, one
# per agent every 1.3 s -- and `_dungeon.err` had reached 409 MB. The dungeon had been research-starved
# continuously since it started, and that was invisible, because a line repeated half a million times
# is wallpaper. Grepping the log for the problem returns the problem 1.5 million times, which is the
# same as returning nothing.
#
# So these two now log every STATE CHANGE, plus one line per _IDLE_SUMMARY_EVERY repeats carrying the
# repeat count. Strictly louder than before: an operator sees "entered starvation at T" and
# "unchanged for 5,000 cycles" instead of a wall.
_IDLE_SUMMARY_EVERY = 500
_idle_state: dict = {}      # (eid, tag) -> [normalised message shape, consecutive repeats]
_DIGITS_RE = re.compile(r"\d+")


def _log_plan_state(eid: str, tag: str, msg: str, *args) -> None:
    """Log a per-agent planning state, collapsing repeats into counted summaries.

    The state is compared with DIGITS NORMALISED AWAY, and that is not tidiness -- it is the whole
    fix. The first version compared the rendered string verbatim, and measured over the 90 seconds
    after deployment it still wrote ~18 MB/day, because the supply count oscillates ("all 8 ..." then
    "all 9 ..." then "all 8 ..."), so every flip read as a new state. Starvation with a supply of 8 and
    starvation with a supply of 9 are the same operational condition; the count belongs in the message,
    not in the identity of the state.
    """
    rendered = msg % args if args else msg
    key = (eid, tag)
    shape = _DIGITS_RE.sub("N", rendered)
    prev = _idle_state.get(key)
    if prev is None or prev[0] != shape:
        _idle_state[key] = [shape, 1]
        logger.info("%s", rendered)
        return
    prev[1] += 1
    if prev[1] % _IDLE_SUMMARY_EVERY == 0:
        logger.info("%s  [unchanged for %d cycles]", rendered, prev[1])


async def _renewable_quests(eid: str, want: int = 3) -> list:
    """A GUARANTEED supply of REAL RESEARCH (no combinatorial filler): test Agora's own claims
    (flywheel), pursue harvested frontier directions, ground findings from FRESH papers, and form+test
    hypotheses that deepen existing findings. Bridges/gaps (combinatorial recombination of the
    saturated vault) were removed 2026-06-19 — they produced the low-substance 'gaming party' notes."""
    # One bucket per source. We INTERLEAVE them (round-robin) instead of concatenating flywheel-first,
    # so no single source can monopolize the top `want` slots — the flywheel's same ~3 questions used to
    # fill every slot, collapsing the swarm's output to one repeated theme (monoculture fix, 2026-06-19).
    b_fly, b_dir, b_paper, b_find = [], [], [], []
    try:
        # COMPOUNDING FLYWHEEL — the agents test the FALSIFIERS of Agora's own insights (its claims'
        # weak points), so the system's outputs become its next research + knowledge deepens.
        fw = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=3")
        for q in (fw or {}).get("open", []):
            # THE FALSIFIER IS THE CRITERION, NOT THE SUBJECT. `question` holds an insight's
            # falsifier by design ("test the weak point"), but a falsifier reads "SUPPORTED if the
            # fitted quadratic term is negative and statistically significant (p<0.05)..." — it names
            # a test, never what is being tested. Two costs, measured 2026-08-08: the quest title
            # told the agent nothing to research, and the board gate passed 0 of 3 because the
            # subject's vocabulary is not in the criterion. The SUBJECT is in `origin`.
            _crit = (q.get("question") or "").strip()
            _subj = re.sub(r"^(?:hypothesis|insight|contradiction)\s*:\s*", "",
                           (q.get("origin") or "").strip(), flags=re.I) or _crit
            b_fly.append((f"Test Agora's claim: {_subj[:55]}",
                          f"Test this claim with real evidence: {_subj}. "
                          f"It is decided against its PRE-REGISTERED criterion — {_crit}",
                          "hypothesize"))
        # HARVESTED DIRECTIONS — so research follows the synthesis and COMPOUNDS.
        dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
        for d in (dd or {}).get("directions", []):
            if d.get("kind") == "research":          # upgrade-directions go to the user, not agents
                b_dir.append((f"Pursue direction: {d['title']}",
                              f"Advance this with real evidence — {d.get('why', '')}"))
        # FRESH PAPERS (priority) — real, novel, frontier literature the vault does NOT yet cover, so
        # agents do GROUNDED research on new science instead of recombining the saturated vault. This
        # replaces the old "Connect A<->B" bridges and vague "Develop the gap" quests, which were
        # combinatorial filler (the "gaming party"): they recombined existing notes and produced
        # low-substance notes. Real research = grounded in a real paper, on the frontier.
        lib = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/library?n=60")
        # RANK, DO NOT SLICE. Papers are the swarm's ONLY external anchor -- everything else in this
        # function is our own canon fed back to us -- so taking the first six off a list is how the
        # frontier gets crowded out by whatever happens to sit at the front. Measured 2026-08-08: the
        # first six were nine-tenths of a stale off-mission block and the board gate passed 1 of 6,
        # while the same gate passed our own findings 8 of 8. A word-overlap gate CANNOT tell
        # "on-mission" from "written by us in the board's words", so it structurally prefers the
        # canon; ranking the external bucket on the same terms is what puts the frontier back on
        # equal footing instead of loosening the gate (the gate is correct -- see the dedup work).
        await _gate_refresh()
        _prio = _gate_cache.get("prio") or set()
        _papers = [p for p in (lib or {}).get("papers", []) if (p.get("title") or "").strip()]
        _papers.sort(key=lambda p: (-len(_theme_words(p.get("title") or "") & _prio),
                                    -float(p.get("ts") or 0)))
        for p in _papers[:6]:
            ttl = (p.get("title") or "").strip()
            b_paper.append((f"Ground a finding from: {ttl[:60]}",
                            f"State ONE research finding this paper directly supports, "
                            f"paraphrasing its actual result and naming it (Author Year): {ttl}",
                            "create"))
        fd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=8")
        finds = [k for k in (fd or {}).get("knowledge", []) if (k.get("content") or "")]
        # SAMPLE DISTINCT TOPICS, NOT DISTINCT ROWS. The top-8 is an author-pair cross-product of a
        # couple of subjects, so sampling rows returned three copies of one topic and called it three
        # quests. Measured 2026-08-08: 8 rows -> 2 real subjects. Dedup FIRST, then sample, so the
        # bucket's depth is the number of things to think about rather than the number of rows.
        # Key on a SHORT prefix, not the whole string: titles are stored already truncated, so a
        # longer author prefix leaves a shorter remainder and the same subject ends "...Operations in
        # Lon" under one pair and "...in L" under another. Measured: exact-string dedup left those as
        # two topics; a 40-char key merges them and still separates MemOps from QVal. Keep the LONGEST
        # variant, which carries the most subject.
        _topics: dict[str, str] = {}
        for k in finds:
            topic = _strip_quest_prefix(k.get("title") or "")[:55].strip()
            if topic:
                _key = topic.lower()[:40]
                if len(topic) > len(_topics.get(_key, "")):
                    _topics[_key] = topic
        for topic in random.sample(list(_topics.values()), min(3, len(_topics))):
            # findings → HYPOTHESIZE quests: form + test a new hypothesis that deepens the finding
            # (the self-deepening engine — each finding raises the next testable question).
            b_find.append((f"Hypothesize on: {topic}",
                           "Form + test a new hypothesis that deepens this finding", "hypothesize"))
    except Exception as e:
        logger.debug(f"renewable_quests {eid}: {e}")
    # INTERLEAVE the four sources round-robin, with a shuffled bucket order so the lead source varies
    # each cycle — this is the diversity fix: the top `want` picks now span sources instead of being
    # three flywheel questions every time.
    # THE 2026-06-19 FIX STOPPED ONE SOURCE MONOPOLISING THE SLOTS. IT DID NOT STOP THE EIGHT AGENTS
    # ALL TAKING THE SAME ITEMS. Every agent called this with the same four buckets and an independent
    # `random.shuffle`, which makes each agent's order random but does nothing to make them DIFFER --
    # the top of a 40-item pool is a small target and they crowd it.
    #
    # Measured 2026-07-31, once `_brain_contribute` stopped reporting rejections as landings: 71
    # rejected writes in ~20 minutes, all eight agents contributing, 45 of them "near-duplicate of a
    # recent finding" and 25 "vault already covers this". The same title was submitted THIRTEEN times
    # ("How should a memory system's write-acceptance conservatism scale..."), another twelve, another
    # ten. The swarm was not idle; it was eight agents grinding the same handful of themes and throwing
    # the results at a dedup gate, while every rejection logged as a success.
    #
    # So: deal the pool DETERMINISTICALLY BY AGENT. Each agent leads with a different bucket and starts
    # at a different depth, so eight simultaneous callers walk away with eight different top picks from
    # the same supply. Deterministic, not random: two agents drawing the same card by chance is exactly
    # what needs to stop, and a shuffle cannot promise it. The per-agent `_recent_intents` then keeps
    # each one off its OWN recent ground, which is a different guarantee and both are needed.
    buckets = [b_paper, b_find, b_fly, b_dir]
    for b in buckets:
        random.shuffle(b)
    _order = sorted(_AGENT_NAMES)                      # stable, restart-independent seat numbering
    _seat = _order.index(eid) if eid in _order else 0
    # ROTATE, do not slice. The first version of this started deep seats at index `_depth`, which SKIPS
    # that many items and starves an agent whose bucket is shallow -- measured immediately after
    # deploying it: Orin, Wren and Voss dropped from 3 quests to 1. Rotating each bucket instead means
    # every agent still walks EVERY item, just entering the ring at its own point, so differentiation
    # costs no supply.
    # COUNT THE BUCKETS THAT ACTUALLY HAVE STOCK. The first version divided by `len(buckets)` -- all
    # four, stocked or not -- so it assumed every source was supplying. When only ONE bucket is
    # non-empty, which is the ordinary live case (papers, findings and flywheel run dry while
    # `directions` refills), rotating the order of four buckets is a no-op and `_seat // 4` yields
    # just TWO distinct depths across eight agents. Measured 2026-07-31 after deploying it: eight
    # agents collapsed onto two distinct top picks, and the rejection ledger caught Artificer Rooke
    # and Dame Elara submitting one identical title in the SAME SECOND. My own fix, with the hole one
    # level down from where I tested it -- I checked the four-source case and shipped it.
    #
    # Dropping the empty buckets first makes the two dials measure what they are for: WHICH source
    # leads (seat % nz) and HOW DEEP the agent enters it (seat // nz). Empty buckets contribute
    # nothing to the interleave anyway, so removing them changes no supply, only the arithmetic.
    # Distinct top picks across the eight seats: 4 stocked sources 8/8, 1 stocked source with 7 items
    # 7/8 (the ceiling -- eight agents, seven items), a 3-item supply 3/8 (also the ceiling). Every
    # agent still walks EVERY item, so differentiation costs no supply.
    buckets = [b for b in buckets if b]
    if buckets:
        _nz = len(buckets)
        buckets = buckets[_seat % _nz:] + buckets[:_seat % _nz]
        _off = _seat // _nz
        if _off:
            buckets = [b[_off % len(b):] + b[:_off % len(b)] for b in buckets]
    interleaved, i = [], 0
    while any(len(b) > i for b in buckets):
        for b in buckets:
            if len(b) > i:
                interleaved.append(b[i])
        i += 1
    # BOARD-PRIORITY GATE (2026-07-20). Root cause of an all-night off-mission run: the `findings` bucket
    # re-seeds "Hypothesize on: <topic>" from the top-8 of collective knowledge, but nothing new displaces
    # that top-8 — so the same stale off-mission hypotheses (SCN neurons, CT scans, vertical transmission)
    # kept re-seeding themselves while the owner-locked inspeximus directions sat in a 1-of-4 bucket. That is a
    # self-reinforcing echo loop in our OWN swarm. Route the assembled pool through the SAME gatekeeper the
    # insight/predict generators already use: when ANY candidate matches the board priorities, only those
    # are eligible. Soft by design — if nothing matches, the full pool passes, so the swarm never starves.
    # Gate the PAYLOAD (the text after "<verb>: "), never the whole intent: the boilerplate prefixes
    # ("Ground a finding from", "Pursue direction", "Test Agora's claim") share generic words with the
    # board text itself ("every FINDING must answer...", "prioritize RESEARCH..."), so gating the raw
    # string matched on boilerplate and passed every off-domain paper. Measured: with the raw string the
    # first post-gate pick was still "Ground a finding from: GEAR ... Image Synthesis".
    # HONOUR AN EMPTY GATE. `_gate_filter` was made HARD on 2026-07-21 -- it returns [] when nothing in
    # the pool is on-priority, precisely because a soft fall-through passed off-mission batches whole.
    # This caller then threw that away: `if _on: interleaved = _on` left the FULL off-mission pool in
    # place on exactly the empty result the hard gate exists to produce. The fix landed in the gate and
    # the class went on living one function up. Measured cost while it did: the day's research ran on VR
    # episodic memory, sleep science, Earth-systems Markov chains, contract law and crypto trading with
    # the board locked to the inspeximus frontier, at a 9% land rate over ~15.5k LLM calls.
    #
    # Empty now means empty: no renewable quests this cycle. The agent falls through to a wander thought
    # (cheap, no cloud research), which is the correct cost for having nothing on-mission to do --
    # starvation is meant to be VISIBLE, not quietly filled with work nobody asked for.
    _off_priority = False
    try:
        _payload = {x[0]: (x[0].split(": ", 1)[1] if ": " in x[0] else x[0]) for x in interleaved}
        _keep = set(await _gate_filter(list(_payload.values())))
        _on = [x for x in interleaved if _payload[x[0]] in _keep]
        if interleaved and not _on:
            _off_priority = True
            logger.info("[plan] %s: %d candidate(s) ALL off-priority -> no research this cycle",
                        _AGENT_NAMES.get(eid, eid), len(interleaved))
        interleaved = _on
    except Exception as e:
        logger.debug(f"quest board-gate {eid}: {e}")
    _plan_reason[eid] = "off_priority" if _off_priority else ""
    # SELF-UPGRADE #1: don't re-pursue a topic THIS agent did recently — avoid the repetition the OS
    # fell into. Per-agent and PERSISTED, so the dedup survives dungeon restarts (kills the
    # cross-restart dups) without one agent's picks silencing the topic for the other seven.
    _seen = _recent_intents.setdefault(eid, [])
    fresh = [x for x in interleaved if x[0] not in _seen]
    # NO FALLBACK. This used to read `(fresh or interleaved)`, and the 2026-07-31 note above already
    # named what that does -- "the fallback INVERTS the guard ... a dedup that produces duplicates
    # precisely when it is working hardest" -- but only the per-agent half of that fix was applied.
    # This is the other half. Measured 2026-08-08 while it was still in place: 400 refusals in 17.9 h
    # (22.4/h) carrying just 28 distinct titles, one of them submitted 53 times by all eight agents,
    # every one refused by the brain as a near-duplicate. Exhausted now means exhausted: the agent
    # takes a wander thought instead, which is the correct cost of having nothing new to pursue.
    # STARVATION IS THE SIGNAL, not the bug -- it says the SUPPLY is thin, and hiding it behind a
    # fallback is what turned a supply problem into 1,435 guaranteed-reject writes.
    chosen = fresh[:want]
    if interleaved and not chosen:
        _plan_reason[eid] = "exhausted"
        _log_plan_state(eid, "exhausted",
                        "[plan] %s: all %d on-priority candidate(s) already pursued -> no research "
                        "this cycle (supply is %d deep)", _AGENT_NAMES.get(eid, eid),
                        len(interleaved), len(interleaved))
    for x in chosen:
        if x[0] in _seen:            # a repeat MOVES the entry, it never spends a second slot
            _seen.remove(x[0])
        _seen.append(x[0])
    del _seen[:-_RECENT_INTENTS_MAX]
    if chosen:
        _save_recent_intents()
    return [{"intent": x[0][:90], "kind": (x[2] if len(x) > 2 else "create"),
             "where": "wander", "action": x[1], "with": ""}
            for x in chosen]


# ── Trust Graph: ESS live trust + Vault-Company cross-agent learning, in the dungeon ──
_BRAIN_NAME2EID = {v: k for k, v in _AGENT_NAMES.items()}
_LEARN_GRAPH = {"edges": [], "ts": 0.0}


async def _brain_learning_graph() -> list[dict]:
    """Who-teaches-whom edges from the Vault Company, mapped to dungeon eids (cached 60s)."""
    now = _time.monotonic()
    if _LEARN_GRAPH["edges"] and now - _LEARN_GRAPH["ts"] < 60:
        return _LEARN_GRAPH["edges"]
    g = await asyncio.to_thread(_brain_get_sync, "/api/v1/vault-company/learning/graph")
    edges = []
    for e in (g or {}).get("edges", []):
        a = _BRAIN_NAME2EID.get(e.get("source"))
        b = _BRAIN_NAME2EID.get(e.get("target"))
        if a and b:
            edges.append({"from": a, "to": b, "skill": e.get("skill", "")})
    if edges:
        _LEARN_GRAPH["edges"], _LEARN_GRAPH["ts"] = edges, now
    return _LEARN_GRAPH["edges"]


def _compute_standing(trust: list[dict]) -> dict:
    """Each agent's reputation (0..1): average pairwise ESS trust, BLENDED with its forecasting
    hit-rate once it has resolved tournament calls (Forecasting Tournament — reputation follows
    truth, not just cooperation). This is the curation authority."""
    acc = {e: [] for e in _AGENT_NAMES}
    for p in trust:
        if p["a"] in acc:
            acc[p["a"]].append(p["score"])
        if p["b"] in acc:
            acc[p["b"]].append(p["score"])
    out = {}
    for e, v in acc.items():
        s = sum(v) / len(v) if v else 0.5
        fc = _forecast_scores.get(e) or {}
        if fc.get("hit_rate") is not None:
            s = 0.8 * s + 0.2 * fc["hit_rate"]
        ms = _mastery_scores.get(e)
        if ms is not None:                      # findings that survive verification → authority
            s = 0.85 * s + 0.15 * ms
        ka = _bounty_scores.get(e)
        if ka is not None:                      # challenges that fell beliefs → authority (kills pay)
            s = 0.9 * s + 0.1 * ka
        out[e] = round(s, 3)
    return out


# Absolute floor beneath the RELATIVE gate below — a keep whose trust has genuinely collapsed still
# must not write into the vault unreviewed. Same constant as tools/autolinker.py --standing-floor.
_STANDING_FLOOR = float(os.environ.get("DUNGEON_STANDING_FLOOR", "0.35"))


def _standing_ok(standing: float, roster: dict | None = None) -> tuple[bool, str]:
    """Is this agent trusted enough to write unreviewed? Judged RELATIVE to the live roster.

    THE DEFECT THIS REPLACES, and it is the same one tools/autolinker.py already had (fixed there
    2026-07-21): `_run_consolidation` and `_run_orchestration` both opened with `if standing < 0.55`,
    an absolute constant standing in front of a score that can never reach it. `_compute_standing`
    starts from the mean pairwise ESS trust and then blends in the forecast hit-rate, the mastery rate
    and the bounty rate — every blend is a weighted average with a term below the mean, so every blend
    pulls DOWNWARD, and reputation decay (`apply_decay(0.02)`, every ~40 ticks) pulls the whole roster
    toward baseline on top of that. The roster therefore drifts under the constant and STAYS there.
    Measured on the live agent_standing.json, 2026-07-31: the highest standing of all eight agents was
    0.477 (Voss) against the 0.55 gate. The consequence is not "rarely runs" but NEVER: Sage Mira's
    consolidation and King Aldric's doctrine+GitHub-push have not executed once.

    An absolute threshold on a drifting relative score is the bug, so lowering the constant would only
    move the date it re-closes. Gate on POSITION IN THE LIVE ROSTER instead, keeping an absolute floor
    so a genuinely collapsed keep still can't write.

    THE RELATIVE TEST IS ADVISORY, NOT A BLOCKER (2026-07-31, second pass). The first version of this
    fix gated on `standing < lo + 0.25 * (hi - lo)`, and that reintroduced the defect it replaced, one
    size smaller. ANY threshold expressed as a point inside [lo, hi] excludes the agent sitting AT lo,
    by construction, whenever hi > lo — moving the constant from 0.25 to 0.1 changes by how much, not
    whether. There is always a last agent and it always fails. Applied to the live roster it blocked
    Rooke (0.402), Wren (0.404) and Kael (0.410): the three this whole change exists to bring back.
    It was only latent because this function gates just two organs, Mira's and Aldric's, and both
    happen to pass today — one drift and it bites, and a ratchet closes behind it, because a blocked
    organ produces nothing and standing is fed by production.

    So: the FLOOR blocks, position is reported. That is the honest division. The floor is an absolute
    bar on a bounded score, which is a thing an absolute constant may legitimately do, and it answers
    the question the gate actually asks — has the keep collapsed. Being last in a band 0.10 wide is not
    a collapse; it is arithmetic. The relative standing still travels with the event so an operator can
    see who is trailing, and nothing silently kills an organ that has exactly one possible owner.

    The relative test here is also deliberately NOT autolinker's top-half median. There, several
    curators compete for one curation slot, so picking the better half is the point. Here each organ
    belongs to exactly ONE agent — nobody else can run Mira's consolidation — so a top-half rule would
    lock four of eight agents out of their own organ permanently. What the gate is actually for is
    holding back an agent that has fallen BEHIND the keep, and the floor is what measures that.
    """
    if standing < _STANDING_FLOOR:
        return False, f"trust {standing:.2f} below the {_STANDING_FLOOR:.2f} floor"
    peers = [float(v) for v in (roster or {}).values()]
    if len(peers) < 4:
        return True, ""            # no live roster to rank against → floor only (brain/trust down)
    lo, hi = min(peers), max(peers)
    rank = 1 + sum(1 for p in peers if p > standing)
    trailing = standing <= lo and hi > lo
    # ADVISORY. Reported so a trailing agent is visible, never returned as a block — see the docstring.
    return True, (f"trailing the keep at {standing:.2f} (rank {rank}/{len(peers)}, band {lo:.2f}-{hi:.2f})"
                  if trailing else "")


_plan_fails: dict = {}    # eid -> consecutive planning failures (for escalation)


async def _escalate(eid: str, problem: str) -> None:
    """Raise a SIGNIFICANT blocker to the user via Telegram (throttled brain-side)."""
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/escalate",
                            {"agent": _AGENT_NAMES.get(eid, eid), "problem": problem})


async def _consume_guidance(eid: str) -> str:
    """Pick up any guidance the user left for this agent via Telegram `fix` (once)."""
    d = await asyncio.to_thread(
        _brain_get_sync,
        f"/api/v1/agent-os/brain/guidance?agent={_urlquote(_AGENT_NAMES.get(eid, eid))}")
    return (d or {}).get("guidance") or ""


async def _run_verification() -> None:
    """Voss autonomously fact-checks recent findings and incorporates the VERIFIED ones into the
    vault — so the OS keeps only knowledge that holds up against real sources, hands-free."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/verify-findings?n=6", {})
    inc = (d or {}).get("incorporated", 0)
    if inc:
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": f"verified + incorporated {inc} finding(s) into the vault"})


async def _run_promotion() -> None:
    """Promote the best recent findings into the vault through the quality gate (~every 20 min) —
    the RELIABLE research→vault funnel so the Obsidian second-brain actually grows (verification
    incorporates ~0, so this is what keeps real notes flowing in)."""
    # local judge ~2.4s × up to 24 candidates + writes → needs a generous timeout (default 4s would
    # cut the funnel off mid-run, which is part of why so little was landing).
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/promote-findings?n=16", {}, 200)
    p = (d or {}).get("promoted", 0)
    if p:
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"promoted {p} grounded finding(s) into the vault"})


async def _run_harvest() -> None:
    """Aldric harvests recent findings into NEXT DIRECTIONS (research questions + system upgrades)
    so the work compounds — directions are surfaced to the user and seed the agents' next quests."""
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions?n=14")
    dirs = (d or {}).get("directions", [])
    if dirs:
        broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                   "text": f"charted {len(dirs)} next directions from recent findings"})


async def _run_self_reflection() -> None:
    """Recurring self-improvement: Agora reflects on its OWN mechanisms and Telegrams upgrade
    proposals for Claude (and the user) to implement — the OS critiquing + improving itself."""
    d = await asyncio.to_thread(
        _brain_get_sync, "/api/v1/agent-os/brain/self-upgrades?notify=true")
    ups = (d or {}).get("upgrades", [])
    if ups:
        broadcast({"type": "os_build", "kind": "collab", "who": "Agora",
                   "text": f"proposed {len(ups)} upgrades to itself"})


async def _run_pulse() -> None:
    """Push a plain-language Pulse to Telegram — regular, human-readable visibility into what the
    system is researching + why + what reached the vault (so the user isn't blind to the dungeon)."""
    await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/pulse?hours=3&notify=true")
    broadcast({"type": "os_build", "kind": "collab", "who": "Agora", "text": "sent a Pulse report"})


async def _run_reality_check() -> None:
    """REALITY BRIDGE in the loop — High Priest Orin tests a recent finding's claim against REAL-WORLD
    DATA (Hacker News / Wikipedia / World Bank), making the agents empirical scientists, not just
    literature synthesizers. Posts a 'Reality:' finding ONLY when real data actually bears on the claim
    (SUPPORTED/REFUTED/MIXED); skips INSUFFICIENT so it stays signal, not noise."""
    if not await _attn_ok("reality_check"):
        return
    fd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=12")
    finds = [k for k in (fd or {}).get("knowledge", [])
             if len(k.get("content") or "") > 120 and not (k.get("title") or "").startswith("Reality:")]
    if not finds:
        _attn_report("reality_check", False)
        return
    k = random.choice(finds)
    body = (k.get("content") or "").split("Source:")[0].strip()
    claim = re.split(r"(?<=[.!?])\s", body)[0][:160]     # the finding's first sentence = its claim
    if len(claim) < 25:
        _attn_report("reality_check", False)
        return
    d = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/agent-os/brain/empirical-test?q={_urlquote(claim)}", 90)
    verdict = (d or {}).get("verdict")
    if not verdict or verdict == "INSUFFICIENT":
        _attn_report("reality_check", False)
        return                                            # no signal at all → don't pollute
    # ZERO-BASELINE GUARD: a DORMANT traction verdict with literally no data ("0 stories ever,
    # 0 points") measures nothing — shipping it as a Reality note is noise in an empirical costume.
    if verdict == "DORMANT" and not ((d or {}).get("data") or {}).get("total_stories_ever"):
        _attn_report("reality_check", False)
        return
    _attn_report("reality_check", True)
    mode = "real-world traction" if (d or {}).get("mode") == "traction" else "empirical"
    content = (f"Reality check ({verdict}): {claim} — {d.get('evidence', '')} "
               f"[{mode}, via {d.get('source')}]")
    await _brain_contribute("priest", f"Reality: {claim[:60]}", content[:430])
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"reality-tested a finding: {verdict} (vs {d.get('source')})"})


_THEME_STOP = frozenset({
    "the", "and", "for", "with", "what", "when", "where", "from", "into", "under", "over",
    "this", "that", "your", "their", "does", "have", "between", "about", "toward", "towards",
    "agora", "vault", "research", "knowledge", "insight", "note", "notes",
})


def _theme_words(text: str) -> set[str]:
    """Significant, lightly-stemmed words of a theme (or note slug) for overlap matching."""
    return {_light_stem(w) for w in re.findall(r"[a-z]+", text.lower())
            if len(w) > 3 and w not in _THEME_STOP}


def _covered_note_themes(pattern: str = "insight*.md") -> list[set[str]]:
    """Word-sets of every matching Agora note already in the vault — the frontmatter title when
    readable (the slugified filename is truncated at ~60 chars), else the filename."""
    vault = os.environ.get("AGORA_VAULT_PATH", "C:/Users/Danculus/my-second-brain")
    notes = Path(vault) / "04 Resources" / "Concepts" / "Agora Agents"
    out = []
    try:
        for p in notes.rglob(pattern):
            text = p.stem.replace("-", " ")
            try:
                for line in p.read_text(encoding="utf-8", errors="ignore")[:600].splitlines():
                    if line.startswith("title:"):
                        text = line[6:]
                        break
            except Exception:
                pass
            out.append(_theme_words(text))
    except Exception:
        pass
    return out


def _theme_is_covered(theme: str, covered: list[set[str]]) -> bool:
    """A theme is covered when an existing item shares >=2 and >=half of its significant words.
    Single-word themes need only that word matched — the flat >=2 floor made them UNMATCHABLE,
    so a skipped 'Serotonin' re-queued forever past the gatekeeper."""
    tw = _theme_words(theme)
    floor = min(2, len(tw))
    return bool(tw) and any(len(tw & cw) >= floor and len(tw & cw) >= 0.5 * len(tw)
                            for cw in covered)


async def _pending_task_themes(prefix: str) -> list[set[str]]:
    """Word-sets of the pending Claude-inbox tasks of one kind (e.g. 'Predict:')."""
    inbox = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/claude-inbox")
    return [_theme_words(t["text"].split(":", 1)[1])
            for t in (inbox or {}).get("pending", [])
            if t.get("text", "").startswith(prefix)]


# ── THE WATCHDOG (dungeon side): keep the BRAIN alive — mirror of server watchdog.py ──
_wd_state = {"misses": 0, "restarts": [], "muted_until": 0.0}
_SERVER_DIR = str(Path(__file__).resolve().parent.parent / "server")


def _wd_should_restart(state: dict, now: float, window: int = 3600, max_restarts: int = 3) -> bool:
    state["restarts"] = [t for t in state["restarts"] if now - t < window]
    return len(state["restarts"]) < max_restarts


def _wd_kill_brain() -> int:
    killed = 0
    try:
        import psutil
        for p in psutil.process_iter(["cmdline", "name"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or [])
                if ("uvicorn" in cmd or "agora.main" in cmd) \
                        and "python" in (p.info.get("name") or "").lower() and " -c " not in cmd:
                    p.kill()
                    killed += 1
            except Exception:
                continue
    except Exception:
        pass
    return killed


def _wd_start_brain() -> bool:
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = "."
        env["PYTHONUNBUFFERED"] = "1"
        flags = 0x08000008          # DETACHED_PROCESS | CREATE_NO_WINDOW
        with open(Path(_SERVER_DIR) / "_brain.err", "ab") as err:
            subprocess.Popen([sys.executable, "-m", "uvicorn", "agora.main:app",
                              "--host", "127.0.0.1", "--port", "8000"],
                             cwd=_SERVER_DIR, env=env, creationflags=flags, stderr=err)
        return True
    except Exception:
        return False


def _wd_alert(text: str) -> None:
    """Telegram alert straight from the dungeon (the brain may be the thing that's down)."""
    try:
        tok = chat = ""
        for line in (Path(_SERVER_DIR) / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("HERMES_TELEGRAM_BOT_TOKEN="):
                tok = line.split("=", 1)[1].strip()
            elif line.startswith("HERMES_TELEGRAM_CHAT_ID="):
                chat = line.split("=", 1)[1].strip()
        if tok and chat:
            from urllib.parse import urlencode
            req = _urlreq.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                  data=urlencode({"chat_id": chat,
                                                  "text": "🐶 Watchdog: " + text}).encode())
            _urlreq.urlopen(req, timeout=15).read()
    except Exception:
        pass


async def _watch_brain() -> None:
    """One supervision beat (~5 min cadence): two consecutive misses → restart the brain;
    crash-loop guard (3/hour) → back off + alert the owner instead of thrashing."""
    up = bool(await asyncio.to_thread(
        _brain_get_sync, "/api/v1/vault-company/org-chart", 10))
    if up:
        _wd_state["misses"] = 0
        return
    _wd_state["misses"] += 1
    if _wd_state["misses"] < 2:
        return
    now = _time.time()
    if not _wd_should_restart(_wd_state, now):
        if now > _wd_state["muted_until"]:
            await asyncio.to_thread(_wd_alert,
                                    "brain is DOWN and in a crash loop — backing off, needs a human.")
            _wd_state["muted_until"] = now + 3600
        _wd_state["misses"] = 0
        return
    await asyncio.to_thread(_wd_kill_brain)
    ok = await asyncio.to_thread(_wd_start_brain)
    _wd_state["restarts"].append(now)
    _wd_state["misses"] = 0
    broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
               "text": "watchdog: the brain was down — restarted it"})
    await asyncio.to_thread(_wd_alert, f"brain was down — restarted it ({'ok' if ok else 'START FAILED'}).")


# ── THE GATEKEEPER: board priorities + skip ledger applied BEFORE queueing ──
_gate_cache: dict = {"skips": [], "prio": set(), "fetched": 0.0}
_PRIO_STOP = frozenset({"priority", "prioritie", "ship", "fewer", "deeper", "close", "closing",
                        "question", "theme", "standing", "week", "owner", "open", "opening"})


async def _gate_refresh() -> None:
    if _time.time() - _gate_cache["fetched"] < 3600:
        return
    s = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/gatekeeper/skips")
    b = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/board")
    _gate_cache["skips"] = [_theme_words(t) for t in (s or {}).get("themes", [])]
    # TAKE THE BRAIN'S TERMS. The board text has POLARITY: it ends "Finance/health/physics are ONLY
    # test-beds, never the headline. Deprioritize generic meta-science, politics, cloud/trivia".
    # Tokenizing it flat turns that refusal into the whitelist, and `_PRIO_STOP` below never learned
    # the negative clause the way the brain's `methods._BOARD_STOP` did. Measured 2026-07-31 against
    # the live board: politics, generic meta-science, cloud trivia, finance AND physics all passed
    # this gate, each matching on the very word the owner used to exclude it -- five for five. The
    # door built to hold the swarm on the inspeximus frontier was holding it open.
    terms = (b or {}).get("priority_terms")
    if isinstance(terms, list) and terms:
        _gate_cache["prio"] = {str(w).lower() for w in terms}
        _gate_cache["prio_src"] = "brain"
    else:
        # An older brain, or one that is down. Say so rather than silently reverting to the flat
        # read: this fallback is the buggy behaviour, and it must be visible while it is in use.
        pr = (b or {}).get("priorities", "") or ""
        _gate_cache["prio"] = {w for w in _theme_words(pr) if w not in _PRIO_STOP}
        _gate_cache["prio_src"] = "local-fallback"
        if _gate_cache["prio"]:
            logger.warning("[gate] brain served no priority_terms - falling back to the FLAT read of "
                           "the board, which admits the owner's own deprioritize words (%d terms)",
                           len(_gate_cache["prio"]))
    _gate_cache["fetched"] = _time.time()


async def _gate_filter(pool: list[str]) -> list[str]:
    """Drop editorially-refused themes; when board priorities exist, queue ONLY on-priority themes.

    HARD since 2026-07-21. It used to fall through to `return pool` when NOTHING in the pool matched
    the board — which is exactly the case that needed gating, so an off-mission batch passed whole.
    Measured cost of that one line: 17 of 22 pending inbox tasks were off-mission (eight
    `Hypothesize from findings` on vault themes like Landauer, orphan nodes, ADHD fMRI meta-analyses),
    while the board had been locked to the inspeximus frontier for days. The lab door was gated and the
    generator walked in through the window.

    Starvation is visible on purpose: returning [] logs the miss instead of quietly manufacturing work.
    An organ with nothing on-mission to do should say so, not fill the queue.
    """
    await _gate_refresh()
    pool = [t for t in pool if not _theme_is_covered(t, _gate_cache["skips"])]
    if _gate_cache["prio"]:
        on = [t for t in pool if _theme_words(t) & _gate_cache["prio"]]
        if not on and pool:
            logger.info("[gate] %d candidate(s) dropped: none on-priority (board=%s)",
                     len(pool), sorted(_gate_cache["prio"])[:6])
        return on
    return pool


_academy_cache: dict = {"lessons": {}, "fetched": 0.0}


async def _academy_lesson(eid: str) -> str:
    """The active mentor's rule for this agent (1h cache) — injected into discovery prompts."""
    if _time.time() - _academy_cache["fetched"] > 3600:
        _academy_cache["lessons"] = {}
        for e, full in _AGENT_NAMES.items():
            d = await asyncio.to_thread(
                _brain_get_sync, f"/api/v1/agent-os/brain/academy?agent={_urlquote(full)}")
            les = (d or {}).get("lesson") or ""
            if les:
                _academy_cache["lessons"][e] = les
        _academy_cache["fetched"] = _time.time()
    return _academy_cache["lessons"].get(eid, "")


# `_brain_graves` (epitaphs of dead ideas, shown to the planner so it would not re-dig them) was
# deleted 2026-07-31 with its only caller, the discarded LLM planner.


_attn_cache: dict = {"policy": {}, "fetched": 0.0}


async def _attn_ok(trigger: str) -> bool:
    """ATTENTION ECONOMY gate: run-probability follows the trigger's recent yield (the brain
    keeps the ledger; bounded [0.4, 1.0] so a cold trigger slows down but keeps sampling)."""
    if _time.time() - _attn_cache["fetched"] > 3600:
        d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/attention")
        if d and isinstance(d.get("policy"), dict):
            _attn_cache["policy"] = d["policy"]
        _attn_cache["fetched"] = _time.time()
    return random.random() < _attn_cache["policy"].get(trigger, 1.0)


def _attn_report(trigger: str, yielded: bool) -> None:
    """Fire-and-forget yield report back to the attention ledger."""
    try:
        asyncio.get_running_loop().run_in_executor(
            None, _brain_post_sync, "/api/v1/agent-os/brain/attention/report",
            {"trigger": trigger, "yielded": yielded})
    except Exception:
        pass


#: How long one unprocessed task may hold an organ shut before the guard stops honouring it.
#: A de-duplication guard with no expiry is an off-switch that anything can pull and nothing resets.
_PENDING_GUARD_MAX_H = 36.0


async def _task_already_pending(prefix: str) -> bool:
    """True when a task of this kind is already waiting in the Claude inbox (for the fixed-text
    daily tasks — a second copy adds nothing, Claude would just editorial-skip it).

    THE GUARD EXPIRES, because without an expiry it is the starvation mechanism. Every organ opens
    with this call, so ONE task that never gets processed shuts that organ down for as long as it
    sits there — silently, with the process healthy and every check green. Measured 2026-07-29:
    Rooke queued a 'Replicate claim' task on 07-25, it sat in the inbox for four days, and the
    Replication Unit — the most productive member of the organization by decisive repairs — returned
    at this line on every one of the ~200 sweeps in between. We have hit this exact class before and
    fixed it in one place: the Scout had the same wedge (see the scout-blocks-on-unprocessed-inbox
    memory). Fixing the instance and not the class is why it came back somewhere else.

    Past the deadline the organ is allowed to queue again. That risks a second copy of a task nobody
    is draining, which is a nuisance; the alternative is an organ that stays dead until a human
    notices, which is what actually happened for four days.
    """
    inbox = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/claude-inbox")
    now = _time.time()
    for t in (inbox or {}).get("pending", []):
        if not t.get("text", "").startswith(prefix):
            continue
        age_h = (now - float(t.get("ts", 0) or 0)) / 3600
        if age_h <= _PENDING_GUARD_MAX_H:
            return True
        logger.info("[guard] '%s' pending %.1fh (> %.0fh) — releasing the organ rather than "
                    "letting one stuck task keep it shut", prefix, age_h, _PENDING_GUARD_MAX_H)
    return False


async def _queue_insight_theme() -> None:
    if os.getenv("AGORA_QUIET_GENERATORS") == "1":
        return  # quieted: low-value 'synthesize insight' inbox churn (agent redesign; flag-reversible)
    """Insight Engine workflow: Agora GATHERS + QUEUES a rich theme; Claude Opus SYNTHESIZES it when
    active (the flash model is too weak for the synthesis). Picks a theme from the user's harvest
    directions / real gaps and drops it in the Claude inbox as 'Synthesize insight: <theme>'."""
    if not await _attn_ok("insight_queue"):
        return
    dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
    pool = [d["title"] for d in (dd or {}).get("directions", []) if d.get("title")]
    pool += [g["title"] for g in (await _brain_gaps())]
    if not pool:
        _attn_report("insight_queue", False)
        return
    # DEDUP: drop themes that already have a vault insight or a pending 'Synthesize insight:' task
    # (blind re-queueing produced duplicate backlogs Claude had to editorial-skip).
    covered = await asyncio.to_thread(_covered_note_themes, "insight*.md")
    covered += await _pending_task_themes("Synthesize insight:")
    pool = [t for t in pool if not _theme_is_covered(t, covered)]
    pool = await _gate_filter(pool)        # GATEKEEPER: skip ledger + board priorities upstream
    if not pool:
        broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
                   "text": "every candidate theme already has an insight — nothing new to queue"})
        _attn_report("insight_queue", False)
        return
    _attn_report("insight_queue", True)
    theme = random.choice(pool)
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Synthesize insight: {theme}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"queued a theme for Claude to synthesize: {theme[:40]}"})
    _mind_spark("#b89bff")        # violet — a new insight forms


async def _queue_deepening() -> None:
    if os.getenv("AGORA_QUIET_GENERATORS") == "1":
        return  # quieted: low-value 'deepen insight' inbox churn (agent redesign; flag-reversible)
    """Compounding Flywheel (second half): queue an insight's falsifier for Claude to RE-TEST against
    the fresh evidence and DEEPEN the insight — outputs come back as sharper outputs, knowledge deepens."""
    if not await _attn_ok("deepen_queue"):
        return
    fw = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=5")
    qs = (fw or {}).get("open", [])
    if not qs:
        _attn_report("deepen_queue", False)
        return
    # DEDUP: don't re-queue a falsifier that is already waiting in the Claude inbox (matched by qid).
    inbox = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/claude-inbox")
    pending_texts = [t.get("text", "") for t in (inbox or {}).get("pending", [])]
    qs = [q for q in qs if not any(f"[{q['id']}]" in txt for txt in pending_texts)]
    if not qs:
        _attn_report("deepen_queue", False)
        return
    _attn_report("deepen_queue", True)
    q = random.choice(qs)
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Deepen insight [{q['id']}]: {q.get('origin', '')} || falsifier: {q['question']}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"queued an insight to deepen (flywheel): {q.get('origin', '')[:30]}"})


async def _refresh_forecast_scores() -> None:
    """Pull each agent's tournament track record into the standing blend (+ trust-graph nodes)."""
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/agent-forecasts")
    for name, sc in ((d or {}).get("scores") or {}).items():
        eid = _FORECASTER_EID.get(name)
        if eid:
            _forecast_scores[eid] = sc
    # Agent Mastery: verification rate per contributor (full names) → standing blend
    m = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/agent-mastery")
    by_full = {v: k for k, v in _AGENT_NAMES.items()}
    for full, sc in ((m or {}).get("scores") or {}).items():
        eid = by_full.get(full)
        if eid and sc.get("rate") is not None:
            _mastery_scores[eid] = sc["rate"]
    # The Bounty Ledger: kill-authority per challenger → standing blend (rigor pays)
    bo = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/bounty")
    for full, ka in ((bo or {}).get("scores") or {}).items():
        eid = by_full.get(full)
        if eid:
            _bounty_scores[eid] = ka


async def _run_predictions() -> None:
    """The Accountable Mind: resolve any DUE predictions against current reality (score), then record
    a NEW falsifiable prediction on a current theme. Over time this builds Agora's track record."""
    res = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/resolve-predictions",
                                  {}, 120)
    n = (res or {}).get("resolved", 0)
    if n:
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": f"resolved {n} prediction(s) against reality"})
        # Tournament outcomes: who called reality right? Accuracy flows into standing.
        for rec in (res or {}).get("records", []):
            for c in rec.get("calls", []):
                ok = c.get("direction") == rec.get("actual")
                nm = _AGENT_NAMES.get(_FORECASTER_EID.get(c.get("agent"), ""), c.get("agent"))
                broadcast({"type": "os_build", "kind": "collab" if ok else "discovery", "who": nm,
                           "text": f"called {c.get('direction')} on '{rec.get('theme', '')[:30]}' — "
                                   f"{'CORRECT (+standing)' if ok else 'wrong (-standing)'}"})
        await _refresh_forecast_scores()
    # Queue a NEW prediction for CLAUDE to make (reasoned, high-quality — the flash forecast is weak).
    dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
    pool = [d["title"] for d in (dd or {}).get("directions", []) if d.get("title")]
    pool += [g["title"] for g in (await _brain_gaps())]
    if pool:
        # DEDUP: skip themes that already have an OPEN prediction or a pending 'Predict:' task —
        # a second forecast on the same theme adds no accountability, just ledger noise.
        led = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/predictions")
        covered = [_theme_words(p.get("theme", "")) for p in (led or {}).get("predictions", [])
                   if p.get("status") == "pending"]
        covered += await _pending_task_themes("Predict:")
        pool = [t for t in pool if not _theme_is_covered(_strip_quest_prefix(t), covered)]
        pool = await _gate_filter(pool)    # GATEKEEPER: skip ledger + board priorities upstream
    theme = ""
    if pool:
        # ZERO-BASELINE FILTER (forge 18c917): only queue themes with a non-zero real-world
        # metric — internal project/feature names score 0 everywhere and yield vacuous FLAT
        # predictions. Zero-baseline candidates go to the gatekeeper skip ledger instead.
        random.shuffle(pool)
        for cand in pool[:4]:
            cand = _strip_quest_prefix(cand)
            bd = await asyncio.to_thread(
                _brain_get_sync,
                f"/api/v1/agent-os/brain/predict-baseline?q={_urlquote(cand[:80])}", 90)
            if any((bd or {}).get("all_baselines", {}).values()):
                theme = cand
                break
            await asyncio.to_thread(
                _brain_post_sync, "/api/v1/agent-os/brain/gatekeeper/skip",
                {"theme": cand[:80],
                 "reason": "zero real-world baseline on every metric (internal/vacuous theme) "
                           "- filtered at queue time"})
    if theme:
        await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                                {"text": f"Predict: {theme[:80]}"})
        broadcast({"type": "os_build", "kind": "collab", "who": "Shadow Kael",
                   "text": f"queued a prediction for Claude: {theme[:35]}"})
        _mind_spark("#8fd3ff")        # cyan — a forecast cast forward
        # FORECASTING TOURNAMENT: all six agents call the same theme (their accuracy → standing).
        t = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/predict-tournament",
                                    {"theme": theme[:80]}, 120)
        if t and t.get("calls"):
            broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                       "text": f"forecasting tournament: 6 agents called '{theme[:28]}' "
                               f"(majority {t.get('direction')})"})


async def _queue_dialectic() -> None:
    if os.getenv("AGORA_QUIET_GENERATORS") == "1":
        return  # quieted: low-value 'dialectic' inbox churn (agent redesign; flag-reversible)
    """Queue a contentious claim for CLAUDE to run the dialectic on (quality thesis/antithesis/
    synthesis — the flash version is weak). Picks a flywheel falsifier or a harvest direction."""
    if not await _attn_ok("dialectic_queue"):
        return
    fw = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=4")
    claims = [q["question"] for q in (fw or {}).get("open", [])]
    if not claims:
        dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
        claims = [d["title"] for d in (dd or {}).get("directions", []) if d.get("title")]
    if not claims:
        _attn_report("dialectic_queue", False)
        return
    # DEDUP: skip claims already stress-tested (a vault dialectic note) or already queued.
    covered = await asyncio.to_thread(_covered_note_themes, "dialectic*.md")
    covered += await _pending_task_themes("Dialectic:")
    claims = [c for c in claims if not _theme_is_covered(c, covered)]
    if not claims:
        _attn_report("dialectic_queue", False)
        return
    _attn_report("dialectic_queue", True)
    claim = random.choice(claims)
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Dialectic: {claim[:120]}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
               "text": f"queued a claim for Claude to stress-test (dialectic): {claim[:30]}"})


async def _queue_mind_reflection() -> None:
    """THE AGORA MIND: queue a metacognitive reflection for Claude — synthesize the worldview from
    Agora's full cognitive state and decide what to think about next. The toolbox becomes a mind."""
    if await _task_already_pending("Reflect: state of mind"):
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Reflect: state of mind"})
    broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
               "text": "queued a metacognitive reflection for Claude (the Agora Mind)"})
    _mind_spark("#ffd27a", "explosion")        # gold — the mind reflects on itself


async def _queue_learning() -> None:
    """THE LEARNING LOOP: queue a review of Agora's own track record for Claude to derive applied
    lessons (what works, what to change) that feed back into future judgments. Agora improves itself."""
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/resolve-predictions", {})
    if await _task_already_pending("Learn from outcomes"):
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Learn from outcomes"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
               "text": "queued a track-record review for Claude (the Learning Loop)"})
    _mind_spark("#9affc0")        # green — a lesson learned


def _mind_spark(color: str = "#b89bff", kind: str = "explosion") -> None:
    """A burst of light at the throne — the Mind — when Agora has a cognitive moment. Visible thought.
    insight=violet · prediction=cyan · reflection=gold · learning=green · heartbeat=dim violet."""
    try:
        broadcast({"type": "effect_added", "data": {"type": kind, "x": 12, "y": 2, "color": color}})
    except Exception:
        pass


async def _run_exam() -> None:
    """THE EXAM: Agora sits a Socratic exam over the vault's core concepts; Claude grades it
    (inbox task queued by the brain). The graded scores become a capability time series."""
    if await _task_already_pending("Grade exam"):
        return
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/exam/generate",
                                {"n": 6}, 300)
    if d and d.get("id"):
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"Agora sat an exam — {len(d.get('questions', []))} questions answered, "
                           "awaiting Claude's grade"})
        _mind_spark("#ffd27a")        # gold — self-measurement


async def _run_memory_economy() -> None:
    """MEMORY ECONOMY: value-account the vault and PROPOSE archiving the dead weight as a gated
    curate action — Rasto approves from Telegram, notes move to quarantine (reversible)."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/memory-economy/propose",
                                {"n": 12}, 180)
    if d and d.get("status") == "proposed":
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"Memory Economy: proposed archiving {d.get('candidates')} dead-weight "
                           "notes (awaiting Rasto's approval)"})
        _mind_spark("#c9a14a")        # amber — the custodian governs


_night_state = {"last": ""}
_annals_state = {"last": ""}


async def _run_annals(sunday: bool = False) -> None:
    """THE ANNALS: write today's chronicle (idempotent vault note); Sundays also queue the
    weekly retrospective for Claude (loop kind A17)."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/annals/today", {}, 120)
    if d and d.get("day"):
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"chronicled the day: {len(d.get('commits', []))} commits, "
                           f"{len(d.get('artifacts', []))} artifacts"})
    if sunday and not await _task_already_pending("Write weekly retrospective"):
        await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                                {"text": "Write weekly retrospective"})


async def _run_night_shift() -> None:
    """THE NIGHT SHIFT: nightly memory consolidation — fresh semantic index by morning."""
    broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
               "text": "night shift: consolidating memory (re-embedding the vault)…"})
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/night-shift", {}, 900)
    if d and d.get("date"):
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"night shift done: {d.get('indexed', '?')} notes re-embedded, "
                           f"{d.get('bridges_applied', 0)} bridges applied ({d.get('minutes')} min)"})
        _mind_spark("#6a5a98", "spark")


async def _run_salon() -> None:
    """THE SALON: sense the followed minds; at most one contestable external claim a day goes
    into the dialectic — named disagreement beats self-generated challenge."""
    if await _task_already_pending("Dialectic:"):
        return
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/salon/sense", {}, 180)
    c = (d or {}).get("claim")
    if c:
        broadcast({"type": "os_build", "kind": "discovery", "who": "High Priest Orin",
                   "text": f"salon: challenging {c['author']} — {c['claim'][:42]}"})
        _mind_spark("#ff9ad1")
    elif d:
        broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
                   "text": f"salon: read {d.get('new_items', 0)} new pieces, no claim worth contesting"})


async def _run_desk() -> None:
    """THE DESK: lay out the owner's working context for whatever he touched most recently —
    his notes, fresh papers, the open questions that touch it (Telegram + a Desk vault note)."""
    d = await asyncio.to_thread(_brain_get_sync,
                                "/api/v1/agent-os/brain/desk?notify=true&note=true", 120)
    if d and d.get("topic"):
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"laid out the owner's desk: {d['topic'][:42]}"})


async def _run_atlas() -> None:
    """THE ATLAS: refresh the per-domain Maps of Content — the owner's navigation front doors."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/atlas/build", {}, 300)
    if d and d.get("domains"):
        broadcast({"type": "os_build", "kind": "collab", "who": "Dame Elara",
                   "text": f"atlas refreshed: {len(d['domains'])} domain maps of content"})


async def _run_board() -> None:
    """THE BOARD MEETING: weekly agenda to the owner — his reply becomes standing priorities."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/board/agenda", {}, 60)
    if d and d.get("agenda"):
        broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                   "text": "board meeting: agenda sent to the owner"})


async def _run_forge() -> None:
    """CAPABILITY FORGE: scan the system's failure traces for capability gaps, then queue the
    oldest open gap for Claude to close with the smallest new organ (tested, like any upgrade)."""
    if await _task_already_pending("Forge capability:"):
        return
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/forge/scan", {}, 60)
    top = (d or {}).get("top_open")
    if not top:
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Forge capability: {top['description'][:140]} || id: {top['id']}"})
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/forge/status",
                            {"id": top["id"], "status": "queued"})
    broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
               "text": f"forge: queued a capability build — {top['description'][:46]}"})
    _mind_spark("#c9a14a")        # amber — the forge lights


async def _run_tutor() -> None:
    """THE TUTOR: send the owner today's spaced-repetition micro-quiz (SM-2 over his own
    evergreen notes; retention feeds the vitals)."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/tutor/daily", {}, 120)
    if d and d.get("n"):
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"sent the owner {d['n']} recall card(s) (spaced repetition)"})


async def _queue_canon_update() -> None:
    """THE CANON: when >=2 artifacts landed since the last canon update, queue the merge —
    Claude rewrites the living book (merge, never append)."""
    if await _task_already_pending("Update canon"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/canon-inputs", 60)
    if len((d or {}).get("new_artifacts", [])) < 2:
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Update canon"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
               "text": f"{len(d['new_artifacts'])} new artifacts since the canon — queued the merge"})
    _mind_spark("#ffd27a")        # gold — the book rewrites itself


async def _queue_outreach() -> None:
    """CORRESPONDENT: weekly, have Claude compose a public outreach from the strongest belief
    (the post is GATED — nothing leaves until the owner approves)."""
    if await _task_already_pending("Compose outreach"):
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Compose outreach"})
    broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
               "text": "correspondent: queued the weekly public letter (gated on the owner)"})


async def _run_reply_harvest() -> None:
    """CORRESPONDENT: pull new replies on posted letters — external challenge coming home."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/correspondent/harvest",
                                {}, 60)
    if d and d.get("new_replies"):
        broadcast({"type": "os_build", "kind": "discovery", "who": "Shadow Kael",
                   "text": f"correspondent: {d['new_replies']} new repl(ies) from outside — challenge inbound"})
        _mind_spark("#ff9ad1", "explosion")


async def _queue_theory_run() -> None:
    """THEORY ENGINE: queue the next mechanistic belief for Claude to build + run as a formal
    model — beliefs stop being prose and start being executables."""
    if await _task_already_pending("Model belief:"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/theory/target", 30)
    t = (d or {}).get("target")
    if not t:
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Model belief: {t['title'][:100]} || path: {t['path']}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"theory engine: queued a belief to RUN as a model — {t['title'][:38]}"})
    _mind_spark("#b89bff", "explosion")


async def _queue_counterfactual_review() -> None:
    """COUNTERFACTUAL SELF: weekly, have Claude interpret the policy replays and turn deltas
    into design lessons (causal inference pointed at the system's own history)."""
    if await _task_already_pending("Counterfactual review"):
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Counterfactual review"})
    broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
               "text": "queued the weekly counterfactual review — what would other policies have done?"})


async def _run_oracle_scan() -> None:
    """THE ORACLE: pick the most liquid unjudged in-domain market and queue it for Claude's
    independent probability call (skin in the game — scored against hard reality)."""
    if await _task_already_pending("Oracle call:"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/oracle/scan", 60)
    cands = (d or {}).get("candidates", [])
    if not cands:
        return
    c = cands[0]
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Oracle call: {c['question'][:140]} || market_id: {c['market_id']} "
                 f"|| market_prob: {c['market_prob']} || ends: {c['ends']}"})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Shadow Kael",
               "text": f"oracle: queued a market for an independent call — {c['question'][:40]}"})
    _mind_spark("#8fd3ff")


async def _run_oracle_resolve() -> None:
    """THE ORACLE: score open positions whose markets resolved — Brier vs hard reality."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/oracle/resolve", {}, 120)
    for p in (d or {}).get("resolved", []):
        won = "BEAT the market" if p.get("beat_market") else "lost to the market"
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": f"oracle resolved: {p['question'][:36]} — {won} "
                           f"(Brier {p['brier_agora']} vs {p['brier_market']})"})
        _mind_spark("#9affc0" if p.get("beat_market") else "#ff9a9a", "explosion")


async def _run_coherence() -> None:
    """COHERENCE AUDIT: check one new belief against its closest siblings; tensions queue an
    internal dialectic — Agora's belief set stays a system, not a pile."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/coherence/audit",
                                {}, 180)
    if d and d.get("status") == "ok":
        msg = (f"coherence: audited '{(d.get('audited') or '')[:38]}' — "
               + (f"{d['tensions_found']} internal tension(s) → dialectic"
                  if d.get("tensions_found") else "consistent with the belief set"))
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss", "text": msg})
        if d.get("tensions_found"):
            _mind_spark("#ff9a9a")


async def _run_contradiction_sweep() -> None:
    """CONTRADICTION SWEEP: judge close note pairs for incompatibility, then feed the top open
    contradiction into the dialectic pipeline (thesis/antithesis/synthesis resolves it)."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/contradictions/scan",
                                {}, 240)
    if d and d.get("found"):
        broadcast({"type": "os_build", "kind": "discovery", "who": "Sergeant Voss",
                   "text": f"contradiction sweep: found {d['found']} place(s) where the vault "
                           "disagrees with itself"})
        _mind_spark("#ff9a9a")
    od = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/contradictions", 30)
    for c in (od or {}).get("open", [])[:1]:
        if c.get("claim") and not await _task_already_pending("Dialectic:"):
            await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                                    {"text": f"Dialectic: {c['claim'][:120]}"})
            await asyncio.to_thread(_brain_post_sync,
                                    "/api/v1/agent-os/brain/contradictions/status",
                                    {"id": c["id"], "status": "queued"})
            broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                       "text": f"queued the contradiction for dialectic resolution: {c['claim'][:38]}"})


async def _queue_belief_challenge() -> None:
    """BELIEF REVISION: the challenge sweep — pick the belief longest without a test and have
    Claude actively try to kill it. Survived beliefs harden; failed ones get revised or buried."""
    if await _task_already_pending("Challenge belief:"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/belief-challenge-target", 30)
    targets = (d or {}).get("targets") or ([(d or {}).get("target")] if (d or {}).get("target") else [])
    if not targets:
        return
    # BOARD GATE. This path never called it, so it kept queueing off-mission work straight past the
    # hardened filter — 90 minutes after the inbox was cleared it had filed a challenge on a
    # conscientiousness/longevity belief while the board was locked to agent-memory integrity.
    #
    # WALK the list; do not judge only the head. The brain ranks by loose token overlap with the board
    # and this gate is hard, so the two disagree — and when they did, taking only the head meant the
    # sweep returned nothing AND the refused belief stayed the stalest, so it was re-proposed and
    # re-refused forever. Bounty/Court and the Graveyard both starved to death behind it (1005h/1002h
    # idle) while 30 never-challenged on-mission beliefs waited. A rejection must advance the cursor.
    t = None
    for cand in targets:
        if cand and await _gate_filter([cand["title"]]):
            t = cand
            break
    if not t:
        print(f"[Challenge] all {len(targets)} candidates refused by the board gate — nothing queued")
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Challenge belief: {t['title'][:90]} || path: {t['path']}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
               "text": f"challenge sweep: trying to kill '{t['title'][:38]}'"})
    _mind_spark("#ff9a9a")        # red — a belief under fire


async def _tick_campaign() -> None:
    """CAMPAIGNS: advance EVERY running campaign one harvest; when a campaign's sub-questions
    are covered (or its horizon passes), queue its dossier for Claude to synthesize."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/campaign/tick", {}, 90)
    if not d or d.get("status") != "ok":
        return
    for r in d.get("results") or [d]:
        cid, cov = r.get("id"), r.get("coverage", {})
        if not cid:
            continue
        done = sum(1 for v in cov.values() if v >= 3)
        broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                   "text": f"campaign harvest: {done}/{len(cov)} sub-questions covered "
                           f"(harvest {r.get('ticks')})"})
        if r.get("ready") and not await _task_already_pending(f"Synthesize campaign dossier [{cid}]"):
            await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                                    {"text": f"Synthesize campaign dossier [{cid}]"})
            broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                       "text": f"campaign {cid} ready — queued the dossier for Claude"})
            _mind_spark("#ffd27a", "explosion")        # gold — a campaign concludes


async def _queue_library_read() -> None:
    """THE LIBRARY: find one unread full-text paper and queue it for Claude to read deeply
    (a structured paper note — the system's grounding goes from abstract-deep to read-deep)."""
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/library-inputs", 60)
    aid = (d or {}).get("arxiv_id", "")
    if not aid:
        return
    if await _task_already_pending("Read paper"):
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Read paper [{aid}]: {(d.get('title') or '')[:80]}"})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Sage Mira",
               "text": f"pulled a full paper to read deeply: {(d.get('title') or '')[:40]}"})
    _mind_spark("#8fd3ff")        # cyan — deep reading


async def _run_interview() -> None:
    """THE INTERVIEW: once a day, ask the owner the single most valuable question (Telegram).
    The brain skips it when an unanswered question is still fresh."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/interview/ask",
                                {}, 120)
    if d and d.get("status") == "asked":
        broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                   "text": f"asked the owner: {d['question']['question'][:48]}"})
        _mind_spark("#ff9ad1")        # pink — reaching toward the owner


async def _run_vitals() -> None:
    """THE OBSERVATORY: take a vital-signs snapshot — the longitudinal ledger Agora's own
    falsifiers (dead-weight trend, closure latency, bridge signals) need to ever resolve."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/vitals/snapshot",
                                {}, 240)
    s = (d or {}).get("snapshot")
    if s:
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": f"vital signs recorded: {s['vault_notes']} notes, "
                           f"dead-weight {s['dead_weight_frac']:.1%}, "
                           f"flywheel {s['flywheel_open']} open"})
        _mind_spark("#9affc0", "spark")        # green — self-measurement heartbeat


async def _queue_hypothesis_induction() -> None:
    """HYPOTHESIS INDUCTION: when a coherent cross-agent finding cluster exists, queue it for
    Claude to unify into ONE falsifiable hypothesis (the falsifier auto-registers in the
    flywheel, so the agents then go test the conjecture — findings become science)."""
    # PENDING CAP. Every other generator has one; this one did not, and it is the single largest
    # producer of off-mission work: its pool is a RANDOM sample of the whole 8k-finding corpus, so
    # each firing yields a brand-new theme that sails past the theme-dedup below. Eight of them
    # accumulated in one day. Capping it costs nothing — an unread hypothesis is not worth a ninth.
    if await _task_already_pending("Hypothesize from findings"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/hypothesis-inputs", 60)
    theme = (d or {}).get("theme", "")
    if not theme or len((d or {}).get("cluster", [])) < 3:
        return
    if not await _gate_filter([theme]):        # the pool is vault-wide; the board decides what leaves
        return
    covered = await asyncio.to_thread(_covered_note_themes, "hypothesis*.md")
    covered += await _pending_task_themes("Hypothesize from findings:")
    if _theme_is_covered(theme, covered):
        return
    # METHODS LIBRARY: try to pre-measure the baseline autonomously — the brain maps the theme
    # onto a vetted experiment template (agents supply parameters, never code) and runs it.
    # The hypothesis task then arrives WITH a measured number; Claude judges instead of building.
    baseline = ""
    md = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/methods/match",
                                 {"theme": theme[:300], "requester": "Artificer Rooke"}, 180)
    if (md or {}).get("status") == "ok" and md.get("measured"):
        baseline = (f" || AUTO-MEASURED BASELINE [{md.get('template')}/lab {md.get('lab_id')}]: "
                    f"{md.get('measured')} {md.get('verdict', '')}")[:420]
        broadcast({"type": "os_build", "kind": "collab", "who": "Artificer Rooke",
                   "text": f"ran a Methods-Library experiment for the conjecture: "
                           f"{md.get('measured', '')[:60]}"})
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Hypothesize from findings: {theme[:90]} || SEVERE-TEST RULE: "
                                     f"the hypothesis must ship WITH a runnable Lab test - run the "
                                     f"baseline via /brain/lab/run in this same task and put the "
                                     f"measured number in the note; no runnable test, no hypothesis"
                                     + baseline})
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"found a cross-agent finding cluster — queued a hypothesis: {theme[:34]}"})
    _mind_spark("#b89bff")        # violet — a conjecture forms


async def _run_academy() -> None:
    """THE ACADEMY: pair the weakest verifier with the strongest mentor; the mentee's discovery
    prompts carry the mentor's rule until the verification rate MEASURABLY improves. The firm
    trains its own people — and checks whether the training worked."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/academy/tick", {}, 30)
    st = (d or {}).get("status")
    if st == "enrolled":
        _academy_cache["fetched"] = 0.0          # refresh lessons immediately
        broadcast({"type": "os_build", "kind": "collab", "who": d.get("mentor", "?"),
                   "text": f"the academy opens: mentoring {d.get('mentee', '?')} "
                           f"(verification rate {d.get('rate', 0):.0%})"})
    elif st == "graduated":
        _academy_cache["fetched"] = 0.0
        broadcast({"type": "os_build", "kind": "collab", "who": d.get("mentee", "?"),
                   "text": f"graduated the academy: +{d.get('gain', 0):.0%} verification rate "
                           f"(taught by {d.get('mentor', '?')})"})
        _mind_spark("#7dffa0")        # green — a colleague measurably improved
    elif st == "rotated":
        _academy_cache["fetched"] = 0.0
        broadcast({"type": "os_build", "kind": "collab", "who": d.get("mentor", "?"),
                   "text": f"lesson didn't take ({d.get('gain', 0):+.0%}) — rotating the curriculum"})


async def _run_portfolio() -> None:
    """THE PORTFOLIO: Voss keeps the public scientific track record (forecasts, replications,
    self-challenges) current, and proposes the GATED publish ONLY when the record is thick
    enough to be credible — a thin 100%-at-n=2 record is a liability, so the self-gate IS the
    credibility. Deterministic from the ledgers; the owner approves the publish."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/portfolio/propose", {}, 30)
    st = (d or {}).get("status")
    if st == "proposed":
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": "track record is credible — proposed publishing the public receipts"})
    elif st == "too_thin":
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": f"track record held back ({d.get('resolved_total')} resolved) — "
                           f"not yet honest to publish"})


def loop_n_is_even_cycle() -> bool:
    """True on every other scout cycle — read from the heartbeat file, which is where loop_n actually
    persists (it survives restarts; it was at 2.2M when this was written, not reset by a relaunch).
    Used to alternate what the Scout hunts: an issue we can answer, then a PR we can learn from."""
    try:
        _, ln = _HEARTBEAT_FILE.read_text(encoding="utf-8").split()
        return (int(ln) // 10000) % 2 == 0
    except Exception:
        return False


async def _queue_scout() -> None:
    """THE OPPORTUNITY SCOUT: Shadow Kael hunts an open GitHub issue Agora can answer with
    evidence and queues Claude to judge + draft a GATED outreach reply. Systematizes the
    first public win (answer someone else's open problem with running architecture + numbers).
    Owner-facing trust surface, so ~6h and strictly gated."""
    # COLLECT FIRST, ALWAYS. This used to open with `if await _task_already_pending("Scout outreach"):
    # return`, so a single untriaged task stopped every later scan — the status read "last scan 23h ago"
    # while the loop fired on schedule and did nothing. Discovery is cheap and perishable (a thread older
    # than ~45 days is already cold); triage is the scarce part. So every firing files into the capped
    # box, and only the promotion into the inbox is rate-limited. The outreach gate itself is unchanged.
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/scout/box/add",
                            {"kind": "contribute"})
    if loop_n_is_even_cycle():                      # alternate: half the firings hunt something to LEARN
        await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/scout/box/add",
                                {"kind": "learn"})

    # PROMOTE A BATCH, NOT A LEAD. Judging "does our vault actually answer this?" takes seconds per
    # lead and the answer is usually no, so one lead per ~2.3h cycle capped the whole pipeline at
    # ~10/day and made a 30-slot box pointless. Five leads in ONE task is the shape that matches the
    # work: one pass, five verdicts, and the inbox still holds a single Scout item.
    if await _task_already_pending("Scout triage"):
        return                                      # collected above; the batch just isn't drained yet
    d = await asyncio.to_thread(_brain_get_sync,
                                "/api/v1/agent-os/brain/scout/box/take?kind=contribute&n=5", 30)
    leads = (d or {}).get("leads") or []
    dl = await asyncio.to_thread(_brain_get_sync,
                                 "/api/v1/agent-os/brain/scout/box/take?kind=learn&n=2", 30)
    learn = (dl or {}).get("leads") or []
    if not leads and not learn:
        return

    # The lead's IDENTITY (repo, issue, score, url) is ours and stays in the instruction. Its TITLE
    # and BODY are written by a stranger on the public web, so they travel in `untrusted` and are
    # sanitized + enveloped inside add_task. Before this they were interpolated straight into a task
    # whose very next line tells the reader to draft outward content with a free repo/issue_number.
    def _ident(x, i):
        return f"[{i}] {x['repo']}#{x['issue_number']} (fit {x.get('score')}) {x['url']}"

    def _content(x, i):
        return f"[{i}] TITLE: {x.get('title','')} || BODY: {(x.get('body') or '')[:320]}"

    body = " ||| ".join(_ident(x, i + 1) for i, x in enumerate(leads))
    learn_body = " ||| ".join(_ident(x, i + 1) for i, x in enumerate(learn))
    lead_text = " ||| ".join(_content(x, i + 1) for i, x in enumerate(leads + learn))
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Scout triage: {len(leads)} leads to answer + {len(learn)} to learn from. "
                 f"TO ANSWER: {body} || TO LEARN FROM (merged PRs in our problem space — read, "
                 f"extract what we did not know, do NOT pitch): {learn_body} || "
                 f"For each lead judge HONESTLY whether Agora/inspeximus answers it with EVIDENCE (a real "
                 f"mechanism + a measured number from our notes/Lab). Where yes, draft a gated reply: "
                 f"POST /brain/correspondent/draft {{title, body, repo, issue_number}} — helpful, "
                 f"specific, no overselling. Where no, say so and move on; reputation dies on a bad "
                 f"pitch. CLOSE EVERY LEAD either way: POST /brain/scout/box/mark {{url, status: "
                 f"'done'|'no_fit'}}, and POST /brain/scout-record {{url, repo, issue, outcome}} for "
                 f"the ones you judged. An unclosed lead is the only thing that holds a box slot.",
         "untrusted": lead_text,
         "source": "GitHub issue authors (strangers on the public web)"})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Shadow Kael",
               "text": f"filed {len(leads)} leads + {len(learn)} to learn from"})
    _mind_spark("#8fd3ff")        # cyan — a lead spotted outside the walls


async def _queue_press() -> None:
    """THE PRESS: Mira (editor-in-chief) picks the strongest unpublished artifact and queues
    Claude to draft a polished standalone public post — gated, the owner approves from
    Telegram. Results that die in the vault build no reputation; the Press is the storefront."""
    if await _task_already_pending("Draft press piece"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/press-target", 30)
    t = (d or {}).get("target") or {}
    if not t.get("title") or t.get("score", 0) < 4:
        return                                # nothing measured enough to be worth publishing
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Draft press piece: {t['title'][:120]} || source: {t['path']} || Rewrite the "
                 f"note as a polished STANDALONE public post (a stranger must understand it "
                 f"without our vault): the claim, the measured numbers, the method in two "
                 f"sentences, the falsifier, what would change our mind. No internal jargon or "
                 f"agent names in the body. Then POST /brain/press/draft {{title, body, source}} "
                 f"- gated, owner approves."})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
               "text": f"editor's desk: '{t['title'][:40]}' goes to press"})
    _mind_spark("#f39c12")        # amber — a piece heads for the storefront


async def _queue_roadmap() -> None:
    """KING ALDRIC — THE ROADMAP (his second ability): read the whole organism's instrument
    panel (organ yields, bottleneck, synthesis pressure, open gaps) and queue Claude to
    synthesize ONE concrete, data-backed next move FOR THE OWNER. Owner-facing, so it runs
    ~daily, not on the science cadence — direction, not noise."""
    if await _task_already_pending("Synthesize roadmap"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/roadmap-inputs", 30)
    if not d or d.get("status") != "ok":
        return
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Synthesize roadmap: read /brain/roadmap-inputs (panel: {d.get('report', '')[:400]}) "
                 f"and write ONE concrete, DATA-BACKED next move for the owner - what to build or "
                 f"prioritize next and WHY, citing the specific metric (idle organ, bottleneck, "
                 f"synthesis pressure, failed replications worth publishing, open forge gaps). "
                 f"Telegram it as a short numbered recommendation (<=4 lines). Direction, not a "
                 f"status dump - say what you would do next and the number that justifies it."})
    broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
               "text": f"reads the instrument panel — drafting the next move (bottleneck: "
                       f"{d.get('bottleneck', '?')[:30]})"})
    _mind_spark("#c0392b")        # crimson — the king sets direction


async def _run_coherence_audit() -> None:
    """DAME ELARA — COHERENCE AUDIT (her second ability): the bridge-builder runs the inverse of
    bridging. She scans the load-bearing BELIEF set for the pair that should cohere but actually
    CONFLICT, and sends that head-to-head to the Court — Claude judges which survives and revises
    the loser via belief-revise (→ Bounty + Graveyard). A belief system that never checks itself
    for internal conflict is a pile; this keeps it a system."""
    if await _task_already_pending("Resolve belief conflict"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/beliefs")
    beliefs = [b for b in (d or {}).get("beliefs", [])
               if b.get("belief_status") in ("active", "survived") and b.get("path")]
    if len(beliefs) < 4:
        return
    titles = [b.get("title", "") for b in beliefs[:14]]
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(titles))
    pick = await _llm_say(
        f"You are {_persona('guard_r')} You audit the belief set for INTERNAL CONFLICT — two "
        f"beliefs that cannot both be fully true, or that pull in opposite directions.",
        f"The beliefs:\n{numbered}\n\nName the ONE pair in the sharpest tension and why, in this "
        f"exact form: 'i vs j: <the conflict in <=18 words>'. If none genuinely conflict, reply "
        f"'none'.",
        "Where does the belief set contradict itself?")
    m = re.match(r"\s*(\d+)\s*(?:vs|VS|x|×|,)\s*(\d+)\s*:?\s*(.*)", pick or "")
    if not m:
        broadcast({"type": "os_build", "kind": "collab", "who": "Dame Elara",
                   "text": "coherence audit: the belief set holds together — no sharp conflict"})
        return
    i, j = int(m.group(1)), int(m.group(2))
    if not (0 <= i < len(beliefs) and 0 <= j < len(beliefs) and i != j):
        return
    ba, bb, why = beliefs[i], beliefs[j], (m.group(3) or "")[:160]
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Resolve belief conflict: '{ba.get('title', '')[:60]}' VS "
                 f"'{bb.get('title', '')[:60]}' || Elara's read: {why} || pathA: {ba.get('path')} "
                 f"|| pathB: {bb.get('path')} || Judge the head-to-head with your own knowledge: "
                 f"do they truly conflict? If yes, which is better-grounded - revise/retire the "
                 f"WEAKER via POST /brain/belief-revise {{path, verdict, reason, challenger: "
                 f"'Dame Elara', resurrect_when}} (pays Bounty, auto-buries); if they reconcile "
                 f"under a distinction, write a short note stating it. A false-alarm is fine - "
                 f"record it as 'beliefs cohere'."})
    broadcast({"type": "os_build", "kind": "challenge", "who": "Dame Elara",
               "text": f"coherence conflict → Court: '{ba.get('title', '')[:26]}' vs "
                       f"'{bb.get('title', '')[:26]}'"})
    _mind_spark("#ffae66")        # amber — a fault line in the belief set


async def _run_synthesis_detector() -> None:
    """HIGH PRIEST ORIN — SYNTHESIS DETECTOR (his second ability): instrument the canon's own
    phase-transition precursors (bridge-rate acceleration, falsifier-closure slowing) and, only
    when they cross threshold, queue Claude to attempt ONE new unifying principle subsuming >=3
    insights. Orin doesn't synthesize on a timer — he waits for the system to be ABOUT to."""
    if await _task_already_pending("Attempt grand synthesis"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/synthesis-signals", 30)
    if not d or not d.get("due"):
        return                                        # not poised — stay silent
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Attempt grand synthesis: the phase-transition precursors crossed threshold "
                 f"(bridge accel x{d.get('bridge_accel')}, {d.get('open_falsifiers')} open "
                 f"falsifiers, pressure {d.get('pressure')}). Look across the active insights/"
                 f"beliefs (GET /brain/beliefs + /brain/canon-inputs) and attempt ONE NEW unifying "
                 f"principle that genuinely SUBSUMES >=3 of them (not a restatement). If a real "
                 f"synthesis exists: write it, merge into Canon (/brain/canon-write), push. If the "
                 f"precursors fired but no honest unification exists, record that the signal was a "
                 f"false alarm (a vault note 'synthesis not yet') - a measured non-event TESTS our "
                 f"own phase-transition belief, which is the point."})
    broadcast({"type": "os_build", "kind": "discovery", "who": "High Priest Orin",
               "text": f"the precursors are aligning — a grand synthesis may be near "
                       f"(pressure {d.get('pressure')})"})
    _mind_spark("#ffd27a", "explosion")        # gold — a phase transition impends


async def _run_red_team() -> None:
    """SHADOW KAEL — RED TEAM (his second ability): the scout turns saboteur and attacks the
    system's STRONGEST belief, not its weakest. Most-survived = most load-bearing = most
    dangerous if wrong; Kael constructs the sharpest disconfirming case (a counterexample or a
    Lab-runnable refutation) and Claude adjudicates via belief-revise (→ Court/Bounty/Graveyard).
    Complacency is the failure mode of a belief that keeps winning; this is the cure."""
    if await _task_already_pending("Red-team belief"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/beliefs")
    beliefs = [b for b in (d or {}).get("beliefs", [])
               if b.get("belief_status") in ("active", "survived") and b.get("path")]
    if not beliefs:
        return
    # the MOST load-bearing belief faces the red team (most survived, then most recently affirmed)
    beliefs.sort(key=lambda b: (b.get("survived", 0), b.get("last_challenged") or ""), reverse=True)
    b = beliefs[0]
    claim, path = b.get("title", ""), b.get("path", "")
    _in_conv.add("thief")
    try:
        broadcast({"type": "os_build", "kind": "challenge", "who": "Shadow Kael",
                   "text": f"red-teams the keep's strongest belief: '{claim[:38]}'"})
        fallback = f"Even '{claim[:36]}' has a crack."
        attack = await _llm_say(
            f"You are {_persona('thief')} You are RED-TEAMING the system's strongest, most-relied-on "
            f"belief — the more it has survived, the more dangerous it is if wrong.",
            f"The belief: '{claim}'. In ONE line (max 22 words), construct the single sharpest "
            f"disconfirming case: a concrete counterexample, a hidden confound, or a measurable "
            f"prediction where it should FAIL. Be specific and adversarial.",
            fallback)
        if attack.strip() == fallback:
            return                                # the LLM failed — a canned line is not a case
        engine.set_entity_thought("thief", attack)
        _mind_spark("#ff6a6a", "explosion")
        await asyncio.to_thread(
            _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
            {"text": f"Red-team belief [{path}]: {claim[:80]} || KAEL'S ATTACK: {attack[:240]} || "
                     f"This is the system's STRONGEST belief under deliberate adversarial pressure. "
                     f"Evaluate Kael's disconfirming case with your own knowledge; if it has teeth, "
                     f"run a Lab refutation to MEASURE it, then rule via POST /brain/belief-revise "
                     f"{{path, verdict: survived|revised|retired, reason, challenger: 'Shadow Kael', "
                     f"resurrect_when}} - survival here strengthens the canon, a kill reshapes it."})
        broadcast({"type": "os_build", "kind": "discovery", "who": "Shadow Kael",
                   "text": f"red-team dossier sent to the judge: {claim[:34]}"})
    finally:
        _in_conv.discard("thief")
        engine.set_entity_state("thief", "idle")


async def _queue_cartography() -> None:
    """THE CARTOGRAPHER, remapped onto the outside world.

    Wren used to hunt the two vault domains with the FEWEST bridges. That objective guarantees an
    off-mission answer: in a vault holding physics, ADHD and category theory, the widest hole is always
    between two things unrelated to agent memory — and it was injected at the FRONT of the hypothesis
    queue, so it steered the whole swarm.

    Same instinct, honest map. He now charts the EXTERNAL library (GitHub issues/PRs + Reddit threads):
    which needs recur across how many UNRELATED projects, and which of them nobody answers. A hole in
    that map is a market gap; a hole in the vault map was a gap in our reading.
    """
    if await _task_already_pending("Chart the external map"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/library/external/map", 90)
    needs = (d or {}).get("map") or []
    if not needs:
        return
    top = needs[0]
    ours = [n for n in needs if n["need"] in ("revert/undo", "forget/erasure", "provenance/trust")]
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Chart the external map: loudest need '{top['need']}' raised in "
                 f"{top['distinct_projects']} unrelated projects ({top['mentions']} mentions). "
                 f"OUR axis right now: "
                 f"{'; '.join(str(n['need']) + ': ' + str(n['distinct_projects']) + ' projects' for n in ours)}. "
                 f"Loudest threads: {'; '.join((x.get('title') or '')[:60] + ' ' + (x.get('url') or '') for x in (top.get('loudest') or [])[:3])} "
                 f"|| Read the actual threads via GET /brain/library/external/search?q=<need>. Then "
                 f"answer ONE question in a note: where does external demand and what we have built "
                 f"actually MEET, and where are we building for a need nobody in the corpus is voicing? "
                 f"Name the gap in both directions - a need with many projects and no implementation is "
                 f"a market; a feature of ours that appears nowhere in the corpus is either early or "
                 f"imaginary, and say which you think it is and why. Tags ['agora','external-map']."})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Cartographer Wren",
               "text": f"charted external demand: {top['need']} in {top['distinct_projects']} projects"})
    _mind_spark("#5dade2")        # blue — a hole appears on the map


async def _queue_bridge_test() -> None:
    """THE BRIDGE BENCH: take one of Cartographer Wren's charted bridges and make someone rule on it.

    Wren produced 80 charts and 68 ended at 'hypothesized' — a proposal with no consumer obliged to
    act on it, so his organ looked like pure volume. It was not: the 9 charts he DID close read
    'no honest bridge', which is a finding. What was missing was anything that made a hypothesis
    into a claim awaiting a verdict.

    A structural hole between two domains is a claim ("these two clusters SHOULD connect and do
    not"), and it is falsifiable: either a mechanism transfers or it does not. The honest verdicts
    are `forged` (a real mapping, named), `no honest bridge` (the domains share surface vocabulary
    and nothing else — the outcome to expect most of the time), or `already bridged`.
    """
    if await _task_already_pending("Test bridge"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/cartography/untested", 30)
    cands = (d or {}).get("targets") or ([(d or {}).get("target")] if (d or {}).get("target") else [])
    cands = [c for c in cands if c and c.get("id")]
    if not cands:
        return
    # WALK. Judging only the head is the dead end that left Bounty/Court and the Graveyard silent for
    # 42 days; I fixed it in the belief sweep this morning and wrote it again here the same day.
    t = None
    for c in cands:
        if await _gate_filter([f"{c.get('a', '')} {c.get('b', '')} {c.get('note', '')}"]):
            t = c
            break
    if not t:
        print(f"[BridgeBench] all {len(cands)} bridges refused by the board gate — nothing queued")
        return
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Test bridge [{t['id']}]: does a real mechanism connect '{t.get('a')}' and "
                 f"'{t.get('b')}'? || charted note: {str(t.get('note'))[:150]} || "
                 f"Name the candidate mechanism, then try to KILL it: does it transfer structurally "
                 f"(same skeleton, not the same words), or do the two domains merely share "
                 f"vocabulary? Prefer a runnable check via /brain/lab/run where the mapping makes a "
                 f"numeric prediction. Then POST /brain/cartography/resolve "
                 f"{{id,outcome,note}} with outcome 'forged' | 'no honest bridge' | 'already "
                 f"bridged'. 'no honest bridge' is the expected answer and is a RESULT — record it "
                 f"without hesitation rather than manufacturing a mapping."})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Cartographer Wren",
               "text": f"put a bridge on the bench: {t.get('a', '')} x {t.get('b', '')}"})
    _mind_spark("#9b59b6")


async def _queue_replication() -> None:
    """THE REPLICATION UNIT: Artificer Rooke picks a sourced claim from the collective
    knowledge and queues it for Claude to re-run as a MINIMAL computational model in the Lab.
    REPRODUCED hardens the claim, FAILED is a publishable result (science's rarest export),
    NOT_COMPUTABLE is an honest pass — every outcome lands in Rooke's track record."""
    if await _task_already_pending("Replicate claim"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/replication-target", 30)
    t = (d or {}).get("target") or {}
    if not t.get("claim"):
        return
    if not await _gate_filter([t["claim"]]):      # same missing gate as the belief-challenge path
        return
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Replicate claim: {t['claim'][:180]} || Source: {t['source'][:140]} || "
                 f"Build the SMALLEST computational model of the claim's mechanism via "
                 f"/brain/lab/run (cite 'simulation'); judge REPRODUCED | FAILED | "
                 f"NOT_COMPUTABLE -> POST /brain/replication-record {{claim,source,outcome,"
                 f"lab_id,note}}. A FAILED replication with a clean model is publishable - "
                 f"consider a gated outreach draft. If the claim has no computable core, "
                 f"record NOT_COMPUTABLE and move on."})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Artificer Rooke",
               "text": f"took a claim to the bench: {t['claim'][:42]}"})
    _mind_spark("#16a085")        # teal — a claim under re-computation


async def _run_debate() -> None:
    """STRUCTURED DEBATE: thesis → attack → defense over a live belief, then Claude judges.
    One-shot dialectics were a single text; this is an actual adversarial exchange with skin
    in the game — the verdict (via belief-revise) changes the belief's status, pays Voss's
    bounty on a kill, and auto-buries the loser. Flash models can attack and defend when the
    format is this narrow; Claude is the judge, not the whole court."""
    if await _task_already_pending("Judge debate"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/beliefs")
    beliefs = [b for b in (d or {}).get("beliefs", [])
               if b.get("belief_status") in ("active", "survived") and b.get("path")]
    if not beliefs:
        return
    # the least-tested beliefs face the court first
    beliefs.sort(key=lambda b: (b.get("survived", 0), b.get("last_challenged") or ""))
    b = random.choice(beliefs[:5])
    claim, path = b.get("title", ""), b.get("path", "")
    mira, voss = "scholar", "guard_l"
    _in_conv.add(mira)
    _in_conv.add(voss)
    try:
        broadcast({"type": "os_build", "kind": "challenge", "who": "Sergeant Voss",
                   "text": f"summons '{claim[:40]}' before the court"})
        thesis = await _llm_say(
            f"You are {_persona(mira)} You DEFEND a belief before the court.",
            f"The belief: '{claim}'. In ONE line (max 22 words), state its strongest, most "
            f"specific case — the evidence or mechanism that carries it.",
            f"The belief '{claim[:40]}' stands on its evidence.")
        engine.set_entity_thought(mira, thesis)
        broadcast({"type": "converse", "from": mira, "to": voss})
        await asyncio.sleep(2.0)
        atk_fallback = f"The weakest assumption in '{claim[:40]}' is untested."
        attack = await _llm_say(
            f"You are {_persona(voss)} You PROSECUTE weak beliefs; your standing grows on kills.",
            f"The belief: '{claim}'. The defense said: '{thesis}'. In ONE line (max 22 words), "
            f"state the single sharpest objection — a confound, a counterexample, or a missing "
            f"control. Attack the argument, not the speaker.",
            atk_fallback)
        if attack.strip() == atk_fallback:
            return                                # no real prosecution today — adjourn, don't fake it
        engine.set_entity_thought(voss, attack)
        broadcast({"type": "converse", "from": voss, "to": mira})
        await asyncio.sleep(2.0)
        defense = await _llm_say(
            f"You are {_persona(mira)} You answer the prosecution directly.",
            f"The belief: '{claim}'. The objection: '{attack}'. In ONE line (max 22 words), "
            f"answer THAT objection specifically — concede what is true, save what survives.",
            f"The objection misses the core mechanism.")
        engine.set_entity_thought(mira, defense)
        broadcast({"type": "converse", "from": mira, "to": voss})
        await asyncio.to_thread(
            _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
            {"text": f"Judge debate [{path}]: {claim[:80]} || THESIS (Mira): {thesis[:200]} || "
                     f"ATTACK (Voss): {attack[:200]} || DEFENSE (Mira): {defense[:200]} || "
                     f"Rule via POST /brain/belief-revise {{path, verdict: survived|revised|retired, "
                     f"reason, challenger: 'Sergeant Voss', resurrect_when (when killing)}} - the "
                     f"verdict changes belief status, pays the Bounty, auto-buries kills. Judge the "
                     f"ARGUMENTS as presented + your own knowledge; if the attack surfaced a "
                     f"genuinely new line, also write a short dialectic vault note."})
        broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                   "text": f"debate transcript sent to the judge: {claim[:36]}"})
        _mind_spark("#ff9a9a")        # red — a belief on trial
    finally:
        for cid in (mira, voss):
            _in_conv.discard(cid)
            engine.set_entity_state(cid, "idle")


async def _queue_analogy_forge() -> None:
    """ANALOGY FORGE: pair the vault's most mechanism-dense concept note with a board-priority
    domain and demand a STRUCTURAL mapping (same skeleton, different flesh) — the move that
    produced the system's best idea (phase transitions → knowledge dynamics), made routine."""
    if await _task_already_pending("Forge analogy"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/analogy-inputs", 60)
    mech = (d or {}).get("mechanism") or {}
    if not mech.get("title"):
        return

    # THE SKIP LIST WAS NEVER ON THIS PATH, so skipping a forged analogy is what RELEASES the next
    # one: `_task_already_pending` asks only whether a copy is WAITING. Measured 2026-08-22 -- four
    # 'Phase Transitions' analogies were gatekeeper-skipped at 23:50 and a fifth was queued at
    # 03:35, onto a YouTube transcript id like the three before it. `_lead_saturated` does consult
    # the skip list, but it is only called on the Scout's lead path in agent_worker.py, so this
    # organ has been re-offering a mechanism Claude already refused, with nothing able to see it.
    #
    # Match on the MECHANISM, not the whole line: the domain varies every emission, so a
    # whole-string check can never fire on a template that only repeats its head.
    #
    # HONEST LIMIT, measured before shipping this: the head-match fires on the live case
    # ('Phase Transitions', repeats=4) and stays silent on an unskipped mechanism, but a REWORDED
    # title slips through -- 'Phase transitions in knowledge dynamics' reads repeats=0 against the
    # same four records. The forge takes its title from the vault note, so a reword means a
    # different note, and the alternative (token overlap, as _lead_saturated does) risks blocking
    # unrelated mechanisms that share a common word. Narrow and visible beats wide and silent.
    skips = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/gatekeeper/skips", 30)
    themes = [t for t in ((skips or {}).get("themes") or []) if isinstance(t, str)]
    mech_head = str(mech["title"])[:40].lower()
    repeats = sum(1 for t in themes if mech_head and mech_head in t.lower())
    if repeats >= 2:
        broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
                   "text": f"the forge stays cold: '{mech['title'][:32]}' was refused "
                           f"{repeats}x already"})
        return

    targets = [g["title"] for g in (await _brain_gaps())]
    bd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/board")
    m = re.search(r"Priority:\s*([^;]+)", (bd or {}).get("priorities") or "")
    if m:
        targets += [t.strip() for t in re.split(r"[+,]", m.group(1)) if len(t.strip()) > 3]
    if not targets:
        return
    target = random.choice(targets)
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Forge analogy: mechanism '{mech['title'][:60]}' -> domain '{target[:60]}' || "
                 f"path: {mech.get('path', '')} || STRUCTURAL mapping (same skeleton, different "
                 f"flesh), not surface similarity; ship the mapped hypothesis + falsifier + "
                 f"Lab-run baseline (severe-test rule) as a vault note tags "
                 f"['agora','analogy','claude-synthesis'], then POST /brain/analogy-record "
                 f"{{mechanism,target,note,outcome}}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sage Mira",
               "text": f"the forge is lit: '{mech['title'][:32]}' hammered toward {target[:28]}"})
    _mind_spark("#ffb3e6")        # pink — a cross-domain spark


async def _run_research_exchange() -> None:
    """RESEARCH EXCHANGE: compose the public digest and PROPOSE publishing it (gated —
    Rasto approves from Telegram; only then does it leave the machine)."""
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/exchange/propose",
                                {}, 120)
    if d and d.get("status") == "proposed":
        broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
                   "text": f"Research Exchange: digest of {d.get('insights')} insights composed "
                           "— publication awaits Rasto's approval"})
        _mind_spark("#7ad7ff")        # ice blue — reaching outward


async def _broadcast_mind_state() -> None:
    """Make Agora's cognition VISIBLE in the dungeon — broadcast its live mind state to the HUD: the
    worldview headline, prediction track-record, lessons learned, and open questions."""
    mi = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/mind-inputs", 30)
    if not mi:
        return
    cal = mi.get("calibration", {}) or {}
    wv = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/worldview")
    headline = ""
    if wv and wv.get("worldview"):
        # prefer the principle stated in the blockquote (> **...**); else the first bold claim
        m = re.search(r">\s*\*\*(.+?)\*\*", wv["worldview"]) or re.search(r"\*\*(.+?)\*\*", wv["worldview"])
        if m:
            headline = re.sub(r"\s+", " ", re.sub(r"[*>#]", "", m.group(1))).strip()[:160]
    lessons_lines = [ln for ln in (mi.get("lessons", "") or "").splitlines() if ln.strip()]
    # Prediction board: the open forecasts first (newest), recent resolved fill the rest.
    preds = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/predictions")
    plist = (preds or {}).get("predictions", [])
    ordered = ([p for p in reversed(plist) if p.get("status") == "pending"]
               + [p for p in reversed(plist) if p.get("status") != "pending"])
    board = [{"theme": p.get("theme", "")[:44], "dir": p.get("direction", "?"),
              "conf": round(100 * float(p.get("confidence", 0))), "status": p.get("status", "pending"),
              "days_left": max(0, round((p.get("resolve_ts", 0) - time.time()) / 86400))}
             for p in ordered[:4]]
    ex = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/exams")
    graded = [s for s in (ex or {}).get("series", []) if s.get("score") is not None]
    # THE MIND CHAMBER — the worldview as a living place above the throne (3D view of the same data)
    broadcast({"type": "mind_chamber",
               "beliefs": len(mi.get("beliefs", [])),
               "questions": (mi.get("flywheel", {}) or {}).get("open", 0),
               "outcomes": [p.get("status") for p in plist
                            if p.get("status") in ("correct", "incorrect")][-12:]})
    broadcast({"type": "mind_state",
               "board": board,
               "exam": (f"{graded[-1]['score']}/{graded[-1]['max']}" if graded else "—"),
               "worldview": headline or "synthesizing a worldview…",
               "beliefs": len(mi.get("beliefs", [])),
               "predictions": cal.get("total", 0),
               "hit_rate": (f"{cal['hit_rate']:.0%}" if cal.get("hit_rate") is not None else "—"),
               "lessons": len(lessons_lines),
               "flywheel_open": (mi.get("flywheel", {}) or {}).get("open", 0),
               "lesson": (lessons_lines[0].lstrip("- ")[:80] if lessons_lines else "")})
    _mind_spark("#6a5a98", "spark")        # a soft heartbeat — the mind is alive


async def _sense_and_queue() -> None:
    """Agora's Senses feed cognition: perceive what's hottest in the user's world NOW and queue an
    insight on it — so Agora thinks about the live present, not only the archived vault."""
    now = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/now", 45)
    topic = (now or {}).get("hottest", "")
    if not topic:
        return
    # DEDUP: a topic can stay hottest for days — don't re-queue it once an insight exists or waits.
    covered = await asyncio.to_thread(_covered_note_themes, "insight*.md")
    covered += await _pending_task_themes("Synthesize insight:")
    if _theme_is_covered(topic, covered):
        return
    if not await _gate_filter([topic]):    # GATEKEEPER: refused or off-priority while on-priority work exists
        return
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Synthesize insight: {topic[:90]} (what is live in the world right now)"})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Shadow Kael",
               "text": f"sensed a live topic + queued it: {topic[:34]}"})
    _mind_spark("#ff9ad1")        # pink — a perception from the outside world


async def _broadcast_trust_graph():
    """One unified graph for the dungeon: ESS pairwise trust + learning (teach) edges +
    each agent's standing — persisted so the trust-weighted curator (AutoLinker) can read it."""
    trust = await _trust_matrix()                       # [{a,b,score}]  ESS, live
    learn = await _brain_learning_graph()               # [{from,to,skill}]  who teaches whom
    standing = _compute_standing(trust)                 # eid -> 0..1
    _standing_cache.update(standing)                    # the attention market reads this
    nodes = [{"eid": e, "name": _AGENT_NAMES.get(e, e), "standing": standing.get(e, 0.5),
              "forecast": (_forecast_scores.get(e) or {}).get("hit_rate")}
             for e in _AGENT_NAMES]
    broadcast({"type": "trust_graph", "nodes": nodes, "trust": trust, "learn": learn})
    try:
        import json as _json
        by_name = {_AGENT_NAMES[e]: standing.get(e, 0.5) for e in _AGENT_NAMES}
        _atomic_write(Path(__file__).parent / "agent_standing.json",
            _json.dumps({"standing": by_name, "updated": _time.time()}))
    except Exception:
        pass


_REFUSAL_RE = re.compile(
    r"^\s*(?:i|we)\s+(?:cannot|can't|am\s+unable|are\s+unable|apologi[sz]e|am\s+sorry|notice\s+your)"
    r"|^\s*(?:i'm|we're)\s+(?:sorry|unable)\b"
    r"|^\s*as\s+an\s+ai\b"
    r"|\byour\s+request\s+asks\b"
    r"|\bthe\s+required\s+source\s+is\s+missing\b"
    r"|\bno\s+(?:paper|source)s?\s+(?:fits|matches|(?:was|were)\s+provided)\b"
    r"|^\s*(?:none|neither)\s+of\s+the\s+provided\b"
    r"|^\s*neither\s+(?:paper|source)s?\b"
    r"|^\s*the\s+provided\s+(?:real\s+)?(?:paper|source|literature)s?[^.\n]{0,40}\b"
    r"(?:do(?:es)?\s+not|don't|doesn't|are\s+unrelated|is\s+unrelated)"
    r"|^\s*(?:i|we)\s+need\s+a\b[^.\n]{0,30}\bsource"
    r"|^\s*you\s+did\s+not\s+provide"
    r"|\bno\s+(?:real\s+|specific\s+)?sources?[^.\n]{0,40}\b(?:is|was|were)\s+provided\b"
    r"|\bto\s+distill\s+(?:a\s+)?final\s+finding\b"
    r"|\bi\s+need\s+the\s+actual\s+(?:paper|source)"
    r"|\bplease\s+(?:provide|supply)\b[^.\n]{0,40}\bsource",
    re.IGNORECASE)


_ENVELOPE_RE = re.compile(r'^(?:[^\{\n]{0,80}?)\{\s*"?\w+"?\s*:\s*"?(.*)$', re.DOTALL)


def _unwrap(text: str) -> str:
    """Strip a JSON-ish envelope so the guards see the SENTENCE, not the wrapper around it.

    Every pattern in `_REFUSAL_RE` that matters here is anchored to the start of the string, and the
    agents' pipeline output arrives wrapped:

        Reality: {    "answer": "The provided sources do not support the claim about deltaG..."

    So `^\\s*the\\s+provided\\s+sources?\\s+...\\s+do(es)?\\s+not` — a pattern written for exactly this
    sentence — never fired, because the envelope stood in front of the anchor. MEASURED on the last 400
    discoveries: 18 are that non-finding, the shipped guard caught **0 of 18 (0.0% recall)**, and
    unwrapping first catches 15 (83.3%) with **0 false alarms across the other 382**.

    The class, again: the guard existed, was correct, and could not reach its input.
    """
    t = (text or "").strip()
    m = _ENVELOPE_RE.match(t)
    if m:
        t = m.group(1)
    return t.lstrip('"\' \n\t{[')


def _is_refusal(text: str) -> bool:
    """True when the LLM output is a refusal / no-fit meta-statement, not a finding. Shipping
    these as discoveries polluted the vault and the morning report ('I cannot complete this
    task' as a grounded finding) — a non-answer is a wasted slot, never knowledge."""
    raw = (text or "")[:300]
    return bool(_REFUSAL_RE.search(raw) or _REFUSAL_RE.search(_unwrap(text)[:300]))


# Quest-INTENT guard: the agents were logging quest PLANS as "discoveries" — "Extend King Aldric's
# result — Explore X", "Collaborate with Y on Z", "build on Mira's finding: ..." — which inflated the
# count with chatter (~74% of discovery rows carried no finding). A plan is not knowledge. We drop a
# contribution whose text is a bare quest-intent UNLESS it actually carries grounding (a source /
# citation / measured result), in which case it's a real finding that merely mentions prior work.
_INTENT_RE = re.compile(
    r"^\s*(extend\s+\w+|collaborate with\b|co-develop\b|review and validate\b|let'?s\s+(explore|build)"
    r"|build on\s+\w+'?s?\s+(finding|result|work)|pipeline:\s*(build on|collaborate|explore)"
    r"|test agora'?s\s+claim\b|explore\s+\w+|investigate\s+\w+)", re.I)
_GROUNDED_RE = re.compile(r"Source:|et al|\([A-Z][a-z]+,?\s+\d{4}\)|arXiv|\bdoi\b|measured|p_c|"
                          r"=\s*-?\d|\d+%|coverage|reproduced", re.I)


def _is_intent(text: str) -> bool:
    return bool(_INTENT_RE.search((text or "")[:120]))


def _credit_agent_mem(eid: str, subject: str, good: bool, k: int = 4, min_rel: float = 0.30) -> None:
    """Agent-side accuracy loop (stage 3, dungeon edition). When an agent's contribution LANDS
    (grounded) or is REJECTED (refusal / quest-intent), credit/debit the agent's OWN memories most
    relevant to the subject it was contributing on — so each agent's recall sharpens by WAS-IT-RIGHT,
    not just by use. Strong-relevance only; gentle (bounded Beta), so one miss can't erase a memory.

    DELIBERATELY UNWARRANTED — do not "fix" this by passing a warrant. The verdict here is OUR OWN
    quality gate (_is_refusal / _is_intent / _GROUNDED_RE) judging the agent's own output: a
    self-graded outcome with no external ground truth, which is precisely the MINJA loop
    `credit_requires_warrant` exists to block. So this path raises `good` and must never raise
    `good_warranted`. The brain's credit_outcome() DOES warrant, because a resolved forecast and a Lab
    run are artifacts outside the memory being credited. The 0% here is the guard working, not a gap
    in it — an audit that reads coverage alone cannot tell those apart, so it is written down."""
    try:
        m = _agent_store(eid)
        if m is None or not hasattr(m, "credit"):
            return
        ids = [h["id"] for h in m.recall(subject or "", k=k) if h.get("relevance", 0) >= min_rel]
        if ids:
            m.credit(ids, "good" if good else "bad")
    except Exception:
        pass


#: A finding that names a Lab run is a DISCOVERY and must satisfy the severe-test rule at the vault
#: door. A finding grounded in cited literature is an OBSERVATION -- still grounded, still gated by
#: the quality filters, but not a claim the Lab is supposed to have measured.
_LAB_REF_RE = re.compile(r"\blab(?:_id)?[\s:=_`]*([0-9a-f]{6})\b", re.I)


async def _brain_contribute(eid: str, title: str, content: str) -> bool:
    _subject = f"{title or ''} {content or ''}".strip()
    if _is_refusal(content) or _is_refusal(title):
        broadcast({"type": "os_build", "kind": "collab", "who": _AGENT_NAMES.get(eid, eid),
                   "text": "discarded a non-finding (refusal/no-fit) — the slot yielded nothing"})
        _credit_agent_mem(eid, _subject, False)   # the memory it leaned on didn't ground a finding
        return False
    if (_is_intent(content) or _is_intent(title)) and not _GROUNDED_RE.search(content or ""):
        broadcast({"type": "os_build", "kind": "collab", "who": _AGENT_NAMES.get(eid, eid),
                   "text": "discarded a quest-INTENT (a plan, not a finding) — only grounded results count"})
        _credit_agent_mem(eid, _subject, False)
        return False
    r = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/collective",
        {"npc": _AGENT_NAMES.get(eid, eid), "title": title[:90],
         # Was a bare 600 while the brain stored 500 and `_CONTRIB_CAP` said 500 -- three numbers
         # for one limit, and the smallest silently won. One constant now, on both sides.
         "content": content[:_CONTRIB_CAP],
         # TYPE IT BY WHAT IT ACTUALLY IS, rather than calling everything a discovery. This was
         # hardcoded to "discovery" for every path, and the vault's LAB-FIRST gate fires ONLY on that
         # type (agent_os_api.py:251, default "observation"). So a collaboration synthesis grounded in
         # a cited paper -- which runs no Lab and has no id to offer -- was submitted as the one type
         # the severe-test rule governs, and refused. Measured 2026-08-01: 231 contributions, 0
         # accepted, 168 of them refused for LAB-FIRST, while the Lab itself ran 171 times with 171 ok.
         # The policy is untouched: a discovery still needs a Lab. The label was the error.
         "knowledge_type": "discovery" if _LAB_REF_RE.search(content or "") else "observation"})
    # A REJECTION IS NOT A LANDING. `bool(r)` treated EVERY response as success, and the brain answers
    # a refusal with an ordinary body -- {"status": "rejected", "reason": ...} -- from six separate
    # gates (garbage, LAB-FIRST, vault dedup, stream dedup, non-finding, quality). bool() of that dict
    # is True. So every agent and every organ has been reporting "landed" for work the brain threw
    # away, for as long as those gates have existed. Measured 2026-07-31: Sergeant Voss's organ logged
    # "ok DECISIVE -> landed lab=c9dbc6", the Lab record c9dbc6 is real and passing, and NOTHING was
    # written -- his newest row in collective_knowledge was from the previous day. This also poisoned
    # the credit ledger below, which paid out on the same false signal.
    _status = str((r or {}).get("status") or "").lower() if isinstance(r, dict) else ""
    landed = _status == "added"
    if not landed:
        logger.info("[contribute] %s REJECTED by the brain (%s): %s",
                    _AGENT_NAMES.get(eid, eid),
                    (r or {}).get("reason", "no response") if isinstance(r, dict) else "no response",
                    title[:60])
    _credit_agent_mem(eid, _subject, landed)       # a grounded contribution rewards its grounding
    return landed


# Novelty-at-generation gate: ~71% of grounded findings were TRUE restatements of notes the vault
# already has (caught at write-time by dedup, but only after wasting the generation). Calibrated:
# well-covered topics score ~0.74-0.80 on vault-search, genuinely novel ones ~0.50-0.58 — 0.72 splits
# them cleanly. Above it, skip the discovery (the vault already knows this) and free the slot for new
# ground. The write-time dedup stays as the backstop.
_NOVELTY_GATE = float(os.environ.get("DUNGEON_NOVELTY_GATE", "0.88"))   # 2026-06-19: vault grew to ~6000 notes, so even FRESH papers score 0.76-0.85; 0.72 blocked everything. 0.88 blocks only near-dups (write-time dedup backstops).


# LAB-FIRST research (2026-06-19): make a MEASURED Lab result the only output. Routes a claim through
# the Methods Library (cheap agent supplies only the THEME; a Claude-vetted TEMPLATE runs in the Lab and
# returns MEASURED:/VERDICT: lines). Writes a finding ONLY if it carries a same-cycle lab_id + real
# measured number — no paraphrase, no "UNCERTAIN" markers. Flag-gated for a clean A/B + revert.
_LAB_FIRST = os.environ.get("DUNGEON_LAB_FIRST", "0").strip() == "1"


async def _experiment_discovery(eid: str, intent: str) -> None:
    """Reduce the claim to a runnable experiment via /brain/methods/match and record the MEASURED result."""
    who = _AGENT_NAMES.get(eid, eid)
    theme = _strip_quest_prefix(intent)
    # DEDUP: skip if this exact theme was already measured recently. The frontier directions are a fixed
    # list quested by several agents + findings get re-fed as seeds, so without this the SAME result gets
    # re-run and re-recorded 4-5x (real research that looks like churn). Checking first also saves the
    # expensive match+Lab run. (Prefix-normalized via _strip_quest_prefix, which now also peels 'Measured:'.)
    try:
        recent = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=30")
        norm = theme.lower()[:50]
        if norm and any(_strip_quest_prefix(k.get("title") or "").lower()[:50] == norm
                        for k in (recent or {}).get("knowledge", [])):
            broadcast({"type": "os_build", "kind": "collab", "who": who,
                       "text": f"'{theme[:32]}' already measured - skipping duplicate"})
            return
    except Exception:
        pass
    # VAULT-SATURATION GATE (2026-07-02): the check above only looks at the last 30 discoveries by exact
    # title prefix, so an experiment whose result the VAULT already holds (from an earlier week) still ran
    # the expensive match+Lab, then got dropped downstream as a vault duplicate (src_deduped). Measured
    # waste: ~95 of ~100 daily lab runs re-measured covered ground while ~5 genuinely-new results landed.
    # Mirror the vault-novelty gate _grounded_discovery already uses: if the theme is already densely covered
    # in the vault, SKIP before the costly run and steer the agent to new ground (fresh papers / uncovered
    # themes) instead of burning the slot. Reversible: raise/lower via DUNGEON_NOVELTY_GATE.
    try:
        related = await _brain_vault_search(theme)
        top_sim = (related[0].get("score", 0.0) if related else 0.0)
        if top_sim >= _NOVELTY_GATE:
            broadcast({"type": "os_build", "kind": "collab", "who": who,
                       "text": f"'{theme[:30]}' already covered in the vault (sim {top_sim:.2f}) - seeking new ground"})
            return
    except Exception:
        pass
    res = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/methods/match",
        {"theme": theme[:300], "requester": who}, 120)            # 120s: the match + Lab run is slow
    if res and res.get("status") == "ok" and res.get("ok") and (res.get("measured") or "").strip():
        tpl = res.get("template", ""); lab_id = res.get("lab_id", "")
        measured = (res.get("measured") or "").strip(); verdict = (res.get("verdict") or "").strip()
        content = f"{measured}\n{verdict}\nExperiment: {tpl} (Lab {lab_id}); params {res.get('params', {})}."
        broadcast({"type": "os_build", "kind": "collab", "who": who,
                   "text": f"ran experiment {tpl}: {measured[:56]}"})
        await _brain_contribute(eid, f"Measured: {theme[:66]}", content[:560])
    else:
        # No template fits -> KILL (never paraphrase). The compounding fix is a NEW template (authored by Claude).
        broadcast({"type": "os_build", "kind": "collab", "who": who,
                   "text": f"no experiment fits '{theme[:32]}' — killed (no paraphrase); needs a new Lab template"})


async def _grounded_discovery(eid: str, intent: str) -> None:
    """Turn a 'create' goal into a REAL finding grounded in arXiv AND connected to the user's
    own notes (or flagging a real gap) — a concrete claim, not a vague plan."""
    sources = await _brain_research(intent)
    if not sources or "(no external" in sources:
        # no literature, no finding — the LLM would only refuse (it may NEVER invent sources)
        broadcast({"type": "os_build", "kind": "collab", "who": _AGENT_NAMES.get(eid, eid),
                   "text": f"no real source found for '{intent[:36]}' — discovery slot skipped"})
        return
    related = await _brain_vault_search(intent)
    top_sim = (related[0].get("score", 0.0) if related else 0.0)
    # FRESH-PAPER EXEMPTION (2026-06-19): a quest to ground a specific NEW paper is novel by
    # definition — its finding isn't in the vault even if the TOPIC is vault-heavy. The topic-
    # similarity gate wrongly blocked these (e.g. "Ground a finding from: Lee & Spekkens" scored
    # 0.88 because causal inference is well-covered), starving the grounded-paper engine. Exempt them.
    _fresh_paper = intent.startswith("Ground a finding from:")
    if top_sim >= _NOVELTY_GATE and not _fresh_paper:  # the vault already covers this — would just dup it
        logger.info(f"[novelty-gate] {_AGENT_NAMES.get(eid, eid)} skipped '{intent[:40]}' "
                    f"(vault sim {top_sim:.2f} >= {_NOVELTY_GATE}) — steering to novel ground")
        broadcast({"type": "os_build", "kind": "collab", "who": _AGENT_NAMES.get(eid, eid),
                   "text": f"'{intent[:32]}' already in the vault (sim {top_sim:.2f}) — seeking new ground"})
        return
    rel = "; ".join(f"[[{r['title']}]]" for r in related[:3] if r.get("score", 0) > 0.45) \
        or "(the user's vault is thin on this — a real gap)"
    lesson = await _academy_lesson(eid)
    finding = await asyncio.to_thread(
        _llm_content_sync,
        f"You are {_persona(eid)} State ONE research FINDING that a specific paper below DIRECTLY "
        f"supports: paraphrase that paper's actual result and name it (Author Year). Stay close to "
        f"what the source literally shows — do NOT extrapolate or synthesize beyond it. Then, if apt, "
        f"link the user's notes. If no paper fits, say so plainly. Max 2 sentences. NEVER invent sources."
        + (f" {lesson}" if lesson else ""),
        f"Topic: {intent}\n\nReal papers:\n{sources or '(none found)'}\n\n"
        f"User's relevant existing notes: {rel}") or intent
    src = ""
    if sources and "(no external" not in sources and "(none" not in sources:
        first = sources.splitlines()[0].lstrip("- ").strip()
        src = f"\nSource: {first[:140]}"
    await _brain_contribute(eid, intent, finding.strip()[:420] + src)


async def _hypothesis_discovery(eid: str, topic: str) -> None:
    """AGORA 2.0 Pillar 2 in the dungeon loop — the self-deepening engine: form a NEW testable
    hypothesis from the topic and TEST it against real literature, yielding a finding WITH a verdict,
    evidence and a falsifier. Each tested hypothesis raises the next question → research deepens itself."""
    # strip any stacked quest/finding prefix down to the real topic (shared, loop-peeling stripper)
    t = _strip_quest_prefix(topic)
    d = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/agent-os/brain/hypothesize?q={_urlquote(t[:100])}", 75)
    if not d or not d.get("hypothesis"):
        await _grounded_discovery(eid, topic)            # fall back to a grounded finding
        return
    # SELF-UPGRADE #3: a hypothesis the literature can't settle is NOT a weak claim — it's a
    # DISCOVERED FRONTIER (a documented known-unknown marking where real research is needed). So the
    # engine is value-positive either way: SUPPORTED → a verified claim; else → a research frontier.
    verdict = str(d.get("verdict", "UNCERTAIN")).upper()
    conf = float(d.get("confidence", 0.5)) if isinstance(d.get("confidence", 0.5), (int, float)) else 0.5
    src = f"\nSource: {d.get('source', '')}" if d.get("source") else ""
    if verdict == "SUPPORTED":
        content = (f"Hypothesis (SUPPORTED, {conf:.0%}): {d['hypothesis']} {d.get('evidence', '')} "
                   f"Falsifier: {d.get('falsifier', '')}")
        await _brain_contribute(eid, f"Hypothesis: {t[:70]}", content[:430] + src)
    else:
        content = (f"Open frontier ({verdict}): {d['hypothesis']} The literature does not yet settle "
                   f"this. {d.get('evidence', '')} What would resolve it: {d.get('falsifier', '')}")
        await _brain_contribute(eid, f"Frontier: {t[:70]}", content[:430] + src)


async def _brain_propose_upgrade(eid: str, title: str, desc: str) -> bool:
    r = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/upgrade",
        {"npc": _AGENT_NAMES.get(eid, eid), "title": title[:90], "description": desc[:400]})
    return bool(r)


# ══ THE RESEARCH ORGANS ═══════════════════════════════════════════════════════════════════════
#
# WHY THIS EXISTS. Until now all eight agents ran byte-identical code: the same renewable quest pool,
# the same `_grounded_discovery`, the same prompt with a different persona string pasted at the front.
# A persona is not a capability, so "eight researchers" was one researcher sampled eight times, and
# three of the eight produced literally nothing. Each agent now owns a MODULE — its organ — that does
# work only that agent can do (`organs/<eid>.py`, one per dungeon entity id).
#
# THE CONTRACT. Each module exposes:
#     ORGAN = {"eid", "agent", "name", "ledger", "decisive": (...), "period_hours": 6.0}
#     async def cycle(ctx) -> {"status": "ok"|"idle"|"error", "decisive": bool, "title": str,
#                              "content": str, "lab_id": str|None, "why": str}
# `status="idle"` is a LEGITIMATE outcome and is never turned into a contribution — an organ with
# nothing to say must be allowed to say nothing. Fabricated work is the failure mode this whole file
# has been fighting (`_is_refusal`, `_is_intent`, the novelty gate), so it is not reintroduced here.
#
# The organ modules land in a SIBLING unit, so every import is defensive: a missing `organs/` package,
# a syntax error, a module without `cycle`, or an organ that raises mid-cycle must all degrade to one
# log line and a skipped turn. `ambient_life` must survive all four.
_ORGANS_DIR = HERE / "organs"
_ORGAN_STATE_FILE = HERE / ".organ_state.json"
_ORGAN_DEFAULT_PERIOD_H = 6.0            # ~4 cycles/day/agent
_ORGAN_IMPORT_RETRY = 3600.0             # re-try a missing/broken organ hourly, not every beat
_organ_mods: dict = {}                   # eid -> {"mod": module|None, "ts": float}
_organ_running: set = set()              # organs in flight (one cycle per agent at a time)


class _Ready:
    """A value that is ALREADY computed but also satisfies `await`.

    The organ modules are written in a sibling unit against a written contract, and that contract does
    not say whether `ctx.brain_get(...)` is awaited. Both spellings are plausible for an author looking
    at `async def cycle(ctx)`, and picking one silently breaks the other: a bare call to an async ctx
    returns a coroutine that fails on `.get(...)`, and an awaited sync ctx raises "object dict can't be
    used in 'await' expression". Both land as a caught error and a silent organ, which is exactly the
    starvation this unit exists to end. So the ctx returns plain values that are ALSO awaitable — the
    generator below never yields, so `await` resolves immediately without touching the event loop.
    Blocking is contained because the whole cycle runs on its own worker thread (`_organ_cycle_sync`).
    """

    def __await__(self):
        yield from ()
        return self


class _ReadyDict(_Ready, dict):
    pass


class _ReadyStr(_Ready, str):
    pass


class _ReadyList(_Ready, list):
    pass


def _ready(value):
    """Wrap a helper's return value so it works awaited or not. None -> empty dict: every caller in
    this file already spells the failure case `(d or {}).get(...)`, and an empty dict is falsy."""
    if value is None:
        return _ReadyDict()
    if isinstance(value, dict):
        return _ReadyDict(value)
    if isinstance(value, str):
        return _ReadyStr(value)
    if isinstance(value, list):
        return _ReadyList(value)
    return value


class _OrganCtx:
    """Everything an organ may touch — and nothing else. Built from the helpers already in this file
    so an organ inherits the brain bridge's timeouts, the inbox board gate in `_brain_post_sync`, and
    the agent's own inspeximus store."""

    def __init__(self, eid: str, mind: str = ""):
        self.eid = eid
        self.agent = _AGENT_NAMES.get(eid, eid)
        self.logger = logger
        #: this agent's brain-side mind (emotion + recalled memories + a vault insight). The planner
        #: used to rebuild this ~370x/hour and throw it away; it is fetched once per organ cycle now.
        self.mind = mind or ""

    async def llm(self, system: str, user: str, max_tokens: int = 0):
        """PROSE composition for an organ that needs to write, not to classify.

        The contract listed brain_get / brain_post / lab_run / recall / logger / agent and never a
        composer, so this was simply absent -- and Sage Mira's press arm, which correctly refuses to
        assemble a post out of note fragments without one, therefore refused on every target forever.
        Returns None when the LLM is off, so an organ that cannot compose still idles honestly rather
        than shipping something mechanical.
        """
        return await asyncio.to_thread(_llm_prose_sync, system, user, max_tokens)

    @staticmethod
    def _api(path: str) -> str:
        """Accept both spellings of a brain path. THE ORGAN CONTRACT NEVER SAID WHICH.

        `_brain_get_sync` builds `http://127.0.0.1:8000` + path, so a caller must supply the whole
        `/api/v1/agent-os/brain/...`. The contract handed to the organ authors said "drive endpoints
        that already exist" and named them the way the docs do -- `/brain/gaps`, `/brain/canon-inputs`
        -- so half of them wrote the short form and got a 404 on every read.

        Measured 2026-07-31 across the shipped organs: artificer and cartographer prefix correctly;
        king and thief probe for the prefix at runtime; guard_l is mixed; and guard_r (8 paths),
        priest (8) and scholar (5) use the bare form exclusively. Those three are Dame Elara, High
        Priest Orin and Sage Mira -- three of the four agents the acceptance gate scored at zero.
        Mira's cycle reported "no canon to curate (0 chars)" while `/brain/canon-inputs` was serving
        6,788 characters; the endpoint was fine and the request never reached it.

        Normalising here rather than in 27 call sites fixes the class, makes both spellings correct
        for every future organ, and removes the reason king and thief probe at all.
        """
        p = path or ""
        return _API_PREFIX + p if p.startswith("/brain/") or p == "/brain" else p

    def brain_get(self, path: str, timeout: int = 8):
        return _ready(_brain_get_sync(self._api(path), timeout))

    def brain_post(self, path: str, body: dict | None = None, timeout: int = 8):
        return _ready(_brain_post_sync(self._api(path), body or {}, timeout))

    def lab_run(self, name: str, code: str):
        """Run a computational falsifier in the brain's Lab. The severe-test rule: a claim ships only
        with a runnable baseline measured in the SAME cycle, so the record is returned whole (it
        carries `id`, `ok` and the captured `output`) rather than reduced to a boolean."""
        return _ready(_brain_post_sync("/api/v1/agent-os/brain/lab/run",
                                       {"name": (name or "")[:120], "code": code or ""}, 180))

    def recall(self, query: str, k: int = 4):
        """This agent's OWN inspeximus store — the per-agent memory the keep has been writing for
        weeks and reading into nothing."""
        return _ready(_recall_mem(self.eid, query or "", k))


def _organ_state() -> dict:
    try:
        d = json.loads(_ORGAN_STATE_FILE.read_text(encoding="utf-8"))
        return {k: float(v) for k, v in d.items()} if isinstance(d, dict) else {}
    except Exception:
        return {}


def _organ_state_save(state: dict) -> None:
    try:
        _atomic_write(_ORGAN_STATE_FILE, json.dumps(state))
    except Exception:
        pass


def _organ_module(eid: str):
    """Import `organs.<eid>`, or None. NEVER raises: the package is created by a sibling unit and the
    dungeon has to run with it absent, half-written, or broken."""
    import importlib
    cached = _organ_mods.get(eid)
    now = _time.time()
    if cached and (cached["mod"] is not None or now - cached["ts"] < _ORGAN_IMPORT_RETRY):
        return cached["mod"]
    who = _AGENT_NAMES.get(eid, eid)
    mod = None
    try:
        if not _ORGANS_DIR.is_dir():
            logger.info("[organ] no organs/ package yet - %s has no organ this cycle", who)
        else:
            mod = importlib.import_module(f"organs.{eid}")
            if not callable(getattr(mod, "cycle", None)):
                logger.warning("[organ] organs.%s has no cycle() - %s skipped", eid, who)
                mod = None
    except Exception as e:
        logger.warning("[organ] organs.%s failed to load (%s: %s) - %s skipped",
                       eid, type(e).__name__, str(e)[:120], who)
        mod = None
    _organ_mods[eid] = {"mod": mod, "ts": now}
    return mod


def _organ_period_h(mod) -> float:
    try:
        p = float((getattr(mod, "ORGAN", None) or {}).get("period_hours") or _ORGAN_DEFAULT_PERIOD_H)
        return p if p > 0 else _ORGAN_DEFAULT_PERIOD_H
    except Exception:
        return _ORGAN_DEFAULT_PERIOD_H


def _organ_name(mod, eid: str) -> str:
    try:
        return str((getattr(mod, "ORGAN", None) or {}).get("name") or eid)[:40]
    except Exception:
        return eid


def _organ_cycle_sync(mod, ctx) -> dict:
    """Run one organ cycle to completion on THIS thread (reached via asyncio.to_thread, so the game
    loop is never blocked by an organ's network or Lab time). Accepts an async or a plain `cycle`."""
    res = mod.cycle(ctx)
    if hasattr(res, "__await__"):
        async def _drive():
            return await res
        res = asyncio.run(_drive())
    return res if isinstance(res, dict) else {}


async def _run_organ(eid: str, mod) -> None:
    """One organ cycle: give the agent its mind, run its organ, route any result through the SAME
    `_brain_contribute` chokepoint every other producer uses, and log the verdict either way."""
    who = _AGENT_NAMES.get(eid, eid)
    organ = _organ_name(mod, eid)
    _organ_running.add(eid)
    try:
        mind = await _brain_context(eid, f"{organ} {_ROLE_HINT.get(eid, '')}")
        ctx = _OrganCtx(eid, mind)
        try:
            res = await asyncio.to_thread(_organ_cycle_sync, mod, ctx)
        except Exception as e:
            logger.warning("[organ] %s / %s: ERROR %s: %s | mind=%s", who, organ,
                           type(e).__name__, str(e)[:160], "yes" if mind else "EMPTY")
            return
        status = str(res.get("status") or "error").lower()
        decisive = bool(res.get("decisive"))
        title = str(res.get("title") or "").strip()
        content = str(res.get("content") or "").strip()
        lab_id = res.get("lab_id")
        why = str(res.get("why") or "")[:120]
        landed = False
        if status == "ok" and title and content:
            if lab_id:
                content = f"{content}\nLab: {lab_id}"
            # THE SAME CHOKEPOINT, deliberately. `_brain_contribute` carries the refusal guard, the
            # quest-intent guard and the memory credit/debit; an organ writing straight to the brain
            # would re-open every hole those guards were built to close.
            landed = await _brain_contribute(eid, title, content)
            if landed:
                await _brain_remember(eid, f"{organ}: {title}", "curious")
                broadcast({"type": "os_build", "kind": "discovery", "who": who,
                           "text": f"{organ}: {title[:60]}"})
        elif status == "ok":
            status = "error"          # ok with nothing in it is not ok
            why = why or "status ok but no title/content"
        # ONE LINE PER CYCLE, so starvation is visible from outside the process. Three of the eight
        # agents produced nothing for weeks and nothing in any log said so. ASCII only (cp1250 console).
        logger.info("[organ] %s / %s: %s%s%s%s%s", who, organ, status,
                    " DECISIVE" if decisive else "",
                    " -> landed" if landed else (" -> dropped at the gate" if status == "ok" else ""),
                    f" lab={lab_id}" if lab_id else "",
                    f" | {why}" if why else "")
    finally:
        _organ_running.discard(eid)


async def _organ_tick() -> None:
    """One beat of the organ scheduler: fire the MOST OVERDUE due organ, at most one per beat.

    One at a time on purpose. Eight organs firing together would put eight cloud calls and possibly
    eight Lab runs on the wire at once, against a measured cloud concurrency cap of 3 (`_LLM_SEM`) —
    the 429 storm the LLM planner used to cause. At ~4 cycles/day/agent the whole roster needs 32
    fires a day, so a beat every few minutes is far more headroom than the schedule can consume.
    """
    try:
        state = _organ_state()
        now = _time.time()
        due = []
        for eid in _AGENT_NAMES:
            if eid in _organ_running:
                continue
            mod = _organ_module(eid)
            if mod is None:
                continue
            last = state.get(eid, 0.0)
            overdue = now - last - _organ_period_h(mod) * 3600.0
            if overdue >= 0:
                due.append((overdue, eid, mod))
        if not due:
            return
        due.sort(key=lambda d: -d[0])           # most overdue first -> no agent can be starved out
        _overdue, eid, mod = due[0]
        # Stamp BEFORE running (and persist), so a crash or a restart mid-cycle cannot make this organ
        # re-fire on every beat, and so a restart does not re-fire the whole roster at once.
        state[eid] = now
        _organ_state_save(state)
        await _run_organ(eid, mod)
    except Exception as e:
        logger.debug("organ tick: %s", e)


_ROLE_HINT = {  # each thinker owns a real research domain
    "king":    "synthesis & governance — turn the group's findings into doctrine and decide what the OS should become",
    "guard_l": "resilience & antifragility — stress-test ideas, find failure modes, harden the system",
    "guard_r": "systems & feedback loops — formalize and structure what others discover",
    "priest":  "meaning, emergence & strange loops — seek the deep 'why' behind a finding",
    "thief":   "incentives, risk & game theory — find the edge or exploit others miss",
    "scholar": "knowledge itself — cross-reference the library and connect distant concepts",
    "artificer": "replication & computational verification — re-run claimed results as minimal models; trust only what computes",
    "cartographer": "the shape of the knowledge graph — find structural holes between domains and point research across them",
}

# Named destinations the LLM can send an agent to (tile = standing spot).
_LOCATIONS = {k: v["tile"] for k, v in _POSTS.items()}  # throne, treasury, library, ...


# REASSIGNMENT, NOT REDUNDANCY.
#
# These organs were briefly switched off because their selectors are anti-correlated with a
# single-product frontier — cartography hunts the vault domain pair with the FEWEST bridges, which in
# a vault of physics and category theory is guaranteed to be off-mission. The owner's correction was
# the right one: the instinct is fine, the map was wrong. So each is being repointed at the OUTSIDE
# world (the external library of GitHub issues/PRs and Reddit threads) rather than at our own notes.
#
#   cartography   -> /brain/library/external/map      DONE — which needs recur across unrelated
#                                                     projects, and which nobody answers
#   red_team      -> our public claims vs competitor docs and benchmarks        (next)
#   contradiction -> what we assert vs what the external corpus says            (next)
#   debate        -> the strongest external counter-position, sourced           (next)
#   analogy_forge -> how another project solved a problem we still have         (next)
#   coherence     -> our own public artifacts (README, benchmarks, posts)       (next)
#   counterfactual-> the design decisions we already shipped                    (next)
#   oracle        -> checkable forecasts about our own space, Brier-scored      (next)
#
# Until a role is rewritten, the choke point in _brain_post_sync keeps its output off the board, so a
# not-yet-reassigned organ costs a cycle but cannot fill the queue with noise.
async def ambient_life():
    """LLM-driven emergent simulation. Each agent decides its OWN goal via the LLM
    based on its persona, recent memory, who's nearby and the latest keep news — then
    pursues it (A*), narrates it, and remembers it so it never repeats itself. Guards
    still spar; agents who meet converse; everything feeds the ESS trust engine.
    Disable with DUNGEON_AMBIENT=0.
    """
    if os.environ.get("DUNGEON_AMBIENT", "1") == "0":
        return
    await asyncio.sleep(2.0)  # let the first browser connect

    paths: dict[str, list] = {}        # remaining A* tiles per agent
    hold: dict[str, int] = {}          # ticks to stand still
    cooldown: dict[str, int] = {}      # spar cooldown
    dead: dict[str, int] = {}          # knockout countdown
    goals: dict[str, dict] = {}        # eid -> the ACTIVE quest {intent, tile, action, where}
    quests: dict[str, list] = {}       # eid -> backlog of upcoming quests (the quest log)
    quest_log: dict[str, list] = {}    # eid -> recently COMPLETED quest titles (for the board)
    quest_done: dict[str, int] = {}    # eid -> total quests completed
    memory: dict[str, list] = {}       # eid -> last things this agent did/saw
    next_decide: dict[str, float] = {} # eid -> monotonic time of next decision
    deciding: set[str] = set()         # decisions in flight (quest replenishment)
    idle_bub: dict[str, float] = {}    # eid -> throttle for the "mulling…" idle bubble
    stuck: dict[str, int] = {}         # eid -> consecutive loops blocked from moving (anti-jam)
    world_events: list[str] = []       # recent keep news (shared, for reactivity)
    locations: dict = dict(_LOCATIONS)  # navigable spots — GROWS as agents build modules
    os_modules: list[dict] = []        # real structures agents have built into the OS
    # PERSIST the loop counter across restarts. The inbox task-generators fire on loop_n % N == offset
    # schedules (dialectic@400, insight@1100, deepening@1500, ...); with loop_n=0 on every restart, the
    # watchdog's restart churn kept resetting the countdown so the dungeon rarely ran the ~400-1500
    # uninterrupted loops needed to queue a task -> the Claude inbox starved (empty for hours). Loading
    # the last loop_n from the heartbeat makes the schedule accumulate across restarts. 2026-06-19.
    # Warm the board cache BEFORE any organ fires. `_inbox_theme_allowed` lets everything through
    # while the cache is cold (so a brain outage cannot silence the queue), and the cache was only
    # filled by `_gate_filter` — which just five of thirty-one organs call. On a fresh start that left
    # a window where every path was ungated.
    await _gate_refresh()

    loop_n = 0
    try:
        _hb = _HEARTBEAT_FILE.read_text(encoding="utf-8").split()
        if len(_hb) >= 2 and _hb[1].isdigit():
            loop_n = int(_hb[1])
    except Exception:
        loop_n = 0
    await _init_trust()
    await _refresh_forecast_scores()        # tournament hit-rates feed the standing blend
    _start_vec_worker()                     # background semantic-vec backfill (off the hot path)
    logger.info("LLM-driven life loop started")

    def remember(eid, text, mtype=None, value=None):
        memory.setdefault(eid, []).append(text)
        memory[eid] = memory[eid][-8:]
        m = _agent_store(eid)                       # dogfood: persist into the agent's inspeximus store
        if m is not None:
            try:
                s = str(text)
                # Findings/discoveries are durable knowledge -> semantic + higher value (long
                # half-life so they persist); plain quest chatter stays episodic and fades fast.
                # Engages inspeximus's per-type decay + value-ranking on our own agents.
                if value is None:
                    value = 2.5 if re.search(r"Source:|Hypothesis|Finding|Falsifier|"
                                             r"\([A-Z][a-z]+ \d{4}\)", s) else 1.0
                if mtype is None and value >= 2.0:
                    mtype = "semantic"
                # Keep the write fast: don't inline-embed (a live embed is ~2s under GPU contention).
                # Vectors are filled off the hot path by _vec_backfill_worker and live in RAM (inspeximus._save
                # strips vec on disk by design — the 2026-06-20 frozen-world fix — so recall is semantic
                # in-session and re-embeds lazily after a reload).
                _saved_embed = getattr(m, "embed", None)
                m.embed = None
                try:
                    # NAME THE WRITER. Measured 2026-07-31 across all eight stores: 261,673 records,
                    # `source` coverage 0.000%. slash(scope='source') -- the default, and the lever the
                    # whole accountability story rests on -- resolves on exactly this field, so on our own
                    # dogfood deployment it matched nothing and forfeited nothing, silently, every time.
                    # We were running the library with its main mechanism switched off by omission.
                    # Width by VALUE, not one flat cut. 300 chars is fine for quest chatter and far too
                    # narrow for a finding: it severs `Source:` lines and falsifiers, which is the same
                    # defect found today in agent_os (500), the contribution POST (500) and the seminar
                    # bridge (500). Chatter decays out anyway, so widening only the durable half costs
                    # almost nothing on a 261k-record store.
                    _cap = _AGENT_MEM_FINDING_CHARS if (value or 0) >= 2.0 else _AGENT_MEM_CHATTER_CHARS
                    m.remember(s[:_cap], tags=[eid], value=value, mtype=mtype,
                               source={"doc": "agent:%s" % eid})
                finally:
                    m.embed = _saved_embed
            except Exception:
                pass

    def note_event(text):
        world_events.append(text)
        del world_events[:-6]

    os_log: list[dict] = []   # the emerging Agentic OS: discoveries / upgrades / collabs

    def _os_build(kind, who, text):
        item = {"kind": kind, "who": who, "text": text}
        os_log.append(item)
        del os_log[:-30]
        broadcast({"type": "os_build", **item})

    _OS_COLORS = {"upgrade": "#ffcf5a", "discovery": "#7fd0ff", "collab": "#9affc0"}

    def _apply_module(name: str, tile, builder: str, kind: str = "upgrade"):
        """REALLY apply an upgrade: build a structure, light it, unlock it as a new
        navigable location, and register it as an OS capability others can extend."""
        slug = name.lower().strip()[:40] or f"module-{len(os_modules)}"
        if slug in locations and slug not in (m["slug"] for m in os_modules):
            slug = f"{slug}-{len(os_modules)}"  # don't shadow a base post
        color = _OS_COLORS.get(kind, "#ffcf5a")
        try:
            engine.add_light(f"os_{slug}", tile[0], tile[1], color, 1.3, 4.5, True)
        except Exception:
            pass
        engine.add_effect("glow", tile[0], tile[1], color, 1.2)
        locations[slug] = (int(tile[0]), int(tile[1]))   # now navigable by everyone
        mod = {"slug": slug, "name": name[:60], "tile": [int(tile[0]), int(tile[1])],
               "builder": builder, "kind": kind, "color": color}
        os_modules.append(mod)
        # CAP: keep only the newest 24 module lights. Faster (telepathic) quest completion meant
        # upgrade quests built modules quickly; without removing the OLD light + location they piled
        # up forever (the sudden swarm of named lights). Now old ones are reclaimed so it stays bounded.
        while len(os_modules) > 24:
            old = os_modules.pop(0)
            try:
                engine.remove_light(f"os_{old['slug']}")
                broadcast({"type": "os_module_removed", "slug": old["slug"]})
                if old["slug"] not in _LOCATIONS:
                    locations.pop(old["slug"], None)
            except Exception:
                pass
        broadcast({"type": "os_module", **mod})

    # ── Autonomous vault curation: a trusted curator runs AutoLinker over the vault ──
    _VAULT = os.environ.get("AGORA_VAULT_PATH", "C:/Users/Danculus/my-second-brain")
    _AUTOLINKER = str(Path(__file__).resolve().parent.parent / "tools" / "autolinker.py")
    _SAFEPUSH = str(Path(__file__).resolve().parent.parent / "tools" / "safe_vault_push.py")
    _AUTOPUSH = os.environ.get("DUNGEON_AUTOPUSH", "1") != "0"   # King Aldric commits to GitHub
    curation = {"running": False}

    async def _run_curation(eid, standing, mode="links"):
        """A high-standing curator autonomously runs AutoLinker (background subprocess).
        mode 'links' = Elara connects orphans; 'duplicates' = Voss QA-flags near-duplicates.
        Trust gates it inside the tool: enough standing → applies; else held to pending."""
        if curation["running"] or not Path(_VAULT).exists() or not Path(_AUTOLINKER).exists():
            return
        curation["running"] = True
        curator = _AGENT_NAMES.get(eid, eid)
        logger.info(f"[curation] starting {mode} for {curator}…")
        try:
            engine.set_entity_state(eid, "casting")
            engine.set_entity_thought(eid, "» auditing the vault…" if mode == "duplicates"
                                      else "» curating the vault graph…")
            out_dir = str(Path(_VAULT) / "04 Resources" / "Concepts" / "Agora Agents")
            extra = ["--duplicates"] if mode == "duplicates" else ["--orphans-only"]

            def _runit():
                return subprocess.run(
                    [sys.executable, _AUTOLINKER, "--vault", _VAULT, "--out", out_dir,
                     "--trust-weighted", "--curator", curator, *extra],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120)
            res = await asyncio.to_thread(_runit)
            text = (res.stdout or "") + (res.stderr or "")

            def _num(after, before):
                """First integer after the marker. The old version split on `before` and int()'d the
                remainder, which worked for "APPLIED 92 links" but silently returned 0 for
                "FLAGGED 33 true-duplicate groups" — the word it split on appeared INSIDE the token
                after the number. Voss's real result (33 groups, 89 redundant copies) was therefore
                reported to the world as "no duplicates found" every run."""
                try:
                    m = re.search(r"(\d+)", text.split(after, 1)[1])
                    return int(m.group(1)) if m else 0
                except Exception:
                    return 0

            gated = ("held in pending" in text.lower()) or ("held to pending" in text.lower())
            if gated:                                    # trust too low → queued for review
                note_event(f"{curator}'s {'audit' if mode=='duplicates' else 'curation'} "
                           f"held for review (trust {standing:.2f})")
                logger.info(f"[curation] {curator} held to pending (standing {standing:.2f})")
            elif mode == "duplicates":
                n = _num("FLAGGED", "duplicate")
                if n > 0:
                    note_event(f"{curator} flagged {n} duplicate notes for review")
                    _os_build("curation", curator,
                              f"flagged {n} duplicate notes (trust {standing:.2f})")
                    logger.info(f"[curation] {curator} flagged {n} duplicates")
                else:
                    logger.info(f"[curation] {curator} — no duplicates found")
            else:
                n = _num("APPLIED", "links")
                if n > 0:
                    note_event(f"{curator} curated {n} links into the vault")
                    e2 = engine.state.entities.get(eid)
                    if e2:
                        engine.add_effect("glow", int(round(e2.x)), int(round(e2.y)), "#9fe0ff", 1.3)
                    logger.info(f"[curation] {curator} applied {n} links (standing {standing:.2f})")
                    # Only headline SUBSTANTIAL curation in the OS build feed — routine 1-3 link
                    # gardening every cycle was drowning out the (rarer) research discoveries.
                    if n >= 4:
                        _os_build("curation", curator, f"connected {n} vault notes (trust {standing:.2f})")
                else:
                    logger.info(f"[curation] {curator} — vault graph already well-connected")
        except Exception as e:
            logger.warning(f"[curation] {eid} failed: {e!r}")
        finally:
            curation["running"] = False
            engine.set_entity_state(eid, "idle")
            engine.set_entity_thought(eid, "")

    consolidation = {"running": False, "seen": set()}
    agent_activity = {"seen": set()}     # ts of brain events already shown in the build log

    async def _surface_agent_activity() -> None:
        """Pull every agent's REAL recent work from the brain (replications, analogies, bridges,
        belief rulings, theory runs, outreach) and show it in the build log — so the keep displays
        ALL its agents working, not just the vault-graph curator on her minute loop."""
        d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/agent-activity?n=6")
        events = (d or {}).get("events", [])
        if not events:
            return
        seen = agent_activity["seen"]
        fresh = [e for e in events if e.get("ts") and e["ts"] not in seen]
        for e in reversed(fresh[:3]):                     # oldest-first, at most 3 per poll
            seen.add(e["ts"])
            name = e.get("agent", "Agora")
            _os_build("collab", name, e.get("text", ""))
            eid2 = next((k for k, v in _AGENT_NAMES.items() if v == name), None)  # avatar, if any
            if eid2:
                ent = engine.state.entities.get(eid2)
                if ent:
                    engine.add_effect("glow", int(round(ent.x)), int(round(ent.y)), "#9affc0", 1.2)
        if len(seen) > 500:                               # keep only the most recent timestamps
            agent_activity["seen"] = set(sorted(seen)[-200:])

    async def _run_consolidation(eid, standing, roster=None):
        """Sage Mira consolidates the agents' live discoveries into a real vault note —
        so live research reaches the vault (then Elara links it). Gated by her standing."""
        if consolidation["running"]:
            return
        consolidation["running"] = True
        curator = _AGENT_NAMES.get(eid, eid)
        try:
            _ok, _why = _standing_ok(standing, roster)
            if not _ok:
                note_event(f"{curator}'s consolidation held for review ({_why})")
                return
            if _why:      # advisory: the organ RUNS, but the operator sees who is trailing
                logger.info("[consolidation] %s is %s", curator, _why)
            ck = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=8")
            disc = [k for k in (ck or {}).get("knowledge", []) if k.get("title")]
            new = [k for k in disc if k["title"] not in consolidation["seen"]]
            if len(new) < 2:                              # wait for enough fresh material
                return
            engine.set_entity_state(eid, "casting")
            engine.set_entity_thought(eid, "» consolidating discoveries…")
            bullets = "\n".join(f"- **{k['title']}** — {(k.get('content') or '')[:140]}"
                                for k in new[:6])
            # Ground the digest in REAL frontier papers (arXiv) — no invented citations.
            theme = " ".join((new[0].get("title") or "").split()[:8])
            sources = await _brain_research(theme) if theme else ""
            synth = await asyncio.to_thread(
                _llm_content_sync,
                "You are Sage Mira, Knowledge Curator. Synthesize these discoveries into 2-3 "
                "sentences GROUNDED in the real papers provided: the emerging theme + what to "
                "pursue next. Reference a real paper where relevant. NEVER invent sources.",
                f"Discoveries:\n{bullets}\n\nReal papers (cite these, do not invent):\n{sources}") or ""
            content = (f"## Recent discoveries\n{bullets}\n\n"
                       f"## Synthesis — Sage Mira\n{synth.strip()}"
                       + (f"\n\n## Sources (arXiv)\n{sources}" if sources else ""))
            title = f"Vault Digest {_time.strftime('%Y-%m-%d %H%M')}"
            resp = await asyncio.to_thread(
                _brain_post_sync, "/api/v1/agent-os/brain/vault-note",
                {"title": title, "content": content, "agent": curator,
                 "tags": ["digest", "consolidation"]})
            for k in new[:6]:
                consolidation["seen"].add(k["title"])   # don't re-process this material either way
            # Bounded like its sibling forty lines up (agent_activity["seen"]), which applies the
            # identical idiom to the identical kind of dedup set. This one had no trim, so in a
            # process designed to run for days it grew for the lifetime of the process — and
            # "recently consolidated" quietly came to mean "ever consolidated", so material that
            # became relevant again could never be re-consolidated. The growth rate is small
            # (~40 distinct titles/day in real production); this is hygiene, not an incident.
            if len(consolidation["seen"]) > 500:
                consolidation["seen"] = set(sorted(consolidation["seen"])[-200:])
            if resp and resp.get("status") == "written":
                note_event(f"{curator} consolidated {len(new[:6])} discoveries into a vault note")
                _os_build("curation", curator,
                          f"consolidated {len(new[:6])} discoveries (quality {resp.get('score')}/10)")
                logger.info(f"[consolidation] {curator} wrote a digest (quality {resp.get('score')}/10)")
            elif resp and resp.get("status") == "rejected":
                note_event(f"{curator}'s digest rejected as shallow: {resp.get('reason', '')}")
                logger.info(f"[consolidation] {curator} digest REJECTED ({resp.get('score')}/10): "
                            f"{resp.get('reason')}")
        except Exception as e:
            logger.warning(f"[consolidation] {eid} failed: {e!r}")
        finally:
            consolidation["running"] = False
            engine.set_entity_state(eid, "idle")
            engine.set_entity_thought(eid, "")

    orchestration = {"running": False}

    async def _run_orchestration(eid, standing, roster=None):
        """King Aldric (Orchestrator) sets the 'State of the OS' doctrine and commits the
        agents' accumulated vault work to GitHub (durability). Gated by his standing."""
        if orchestration["running"]:
            return
        orchestration["running"] = True
        king = _AGENT_NAMES.get(eid, eid)
        logger.info(f"[orchestration] starting for {king} (standing {standing:.2f})…")
        try:
            _ok, _why = _standing_ok(standing, roster)
            if not _ok:
                note_event(f"{king}'s governance held ({_why})")
                return
            if _why:      # advisory: the organ RUNS, but the operator sees who is trailing
                logger.info("[orchestration] %s is %s", king, _why)
            engine.set_entity_state(eid, "casting")
            engine.set_entity_thought(eid, "» governing the OS…")
            build = await _brain_build_log()
            synth = await asyncio.to_thread(
                _llm_content_sync,
                "You are King Aldric, Engineering Lead and steward of the Vault Company's Agentic "
                "OS. Write a brief 'State of the OS': what the collective has built, the emerging "
                "direction, and the ONE priority to pursue next. Decisive, concrete, 3-4 sentences.",
                f"The OS so far: {build}") or ""
            if synth.strip():
                resp = await asyncio.to_thread(
                    _brain_post_sync, "/api/v1/agent-os/brain/vault-note",
                    {"title": f"State of the OS {_time.strftime('%Y-%m-%d %H%M')}",
                     "content": f"## State of the OS — King Aldric\n{synth.strip()}",
                     "agent": king, "tags": ["doctrine", "governance"]})
                if resp and resp.get("status") == "written":
                    note_event(f"{king} set the OS doctrine")
                    _os_build("upgrade", king, f"set OS doctrine: {synth.strip()[:50]}")
                elif resp and resp.get("status") == "rejected":
                    note_event(f"{king}'s doctrine rejected as shallow: {resp.get('reason', '')}")
                    logger.info(f"[orchestration] doctrine REJECTED: {resp.get('reason')}")
            # Commit the agents' accumulated vault work to GitHub (safe: refuses on deletions).
            if _AUTOPUSH and Path(_SAFEPUSH).exists():
                def _push():
                    subprocess.run(["git", "-C", _VAULT, "fetch", "origin", "main", "-q"],
                                   capture_output=True, timeout=60)
                    return subprocess.run(
                        [sys.executable, _SAFEPUSH,
                         f"Agora agents: autonomous vault update ({_time.strftime('%Y-%m-%d %H%M')})"],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=300)
                res = await asyncio.to_thread(_push)
                out = (res.stdout or "") + (res.stderr or "")
                if "main -> main" in out:
                    note_event(f"{king} committed the OS to GitHub")
                    _os_build("curation", king, "committed the agents' work to GitHub")
                    logger.info(f"[orchestration] {king} pushed vault to GitHub")
                elif "ABORT" in out:
                    logger.warning(f"[orchestration] push aborted: {out[-200:]}")
                else:
                    logger.info(f"[orchestration] push: {out[-160:]}")
        except Exception as e:
            logger.warning(f"[orchestration] {eid} failed: {e!r}")
        finally:
            orchestration["running"] = False
            engine.set_entity_state(eid, "idle")
            engine.set_entity_thought(eid, "")

    def publish_goals():
        """Quest board: each agent's ACTIVE quest + its queued backlog + done count."""
        rows = []
        i = 0
        for eid in _AGENT_NAMES:
            who = _AGENT_NAMES.get(eid, eid)
            done = quest_done.get(eid, 0)
            tag = f"{who} ✓{done}" if done else who
            g = goals.get(eid)
            if g:
                # REAL progress: how far through its WORK INTERVAL the quest is (time-based, since
                # work is telepathic now — not tied to walking to a tile). Fills smoothly to 100%.
                da = g.get("do_at")
                if da:
                    total = max(1.0, _WORK_DUR[1])
                    remaining = max(0.0, da - _time.monotonic())
                    prog = int(max(8, min(99, 100 * (1 - remaining / total))))
                else:
                    prog = 30
                # If this is a collaboration, surface the partner too so you SEE everyone on it.
                partners = [who]
                ally = (g.get("with") or "").strip()
                if ally:
                    partners.append(ally)
                rows.append({"id": i, "key": f"{eid}:{g['intent'][:24]}", "title": g["intent"],
                             "agent": tag, "agents": partners, "status": "in_progress", "progress": prog})
                i += 1
            for q in quests.get(eid, [])[:2]:        # show up to 2 upcoming quests
                rows.append({"id": i, "key": f"{eid}:q:{q['intent'][:24]}", "title": q["intent"],
                             "agent": who, "status": "open", "progress": 6})
                i += 1
        engine.set_tasks(rows)

    def _resolve_tile(eid, where):
        """A quest's location string → a walkable tile (named spot, ally, or wander)."""
        tile = locations.get(where)
        if tile is None:                              # maybe an ally's name
            for oid, nm in _AGENT_NAMES.items():
                if oid != eid and nm.split()[-1].lower() in where:
                    o = engine.state.entities.get(oid)
                    if o:
                        tile = (int(round(o.x)), int(round(o.y)))
                    break
        if tile is None or not _walkable(*tile):
            tile = random.choice(list(locations.values()))
        return tile

    def activate_next_quest(eid):
        """Pop the next quest into the active slot. Work is TELEPATHIC + time-based: the quest
        completes after a short work interval regardless of where the agent stands (no need to
        walk to a tile or be near a partner). Movement is decoupled, purely ambient wandering —
        so a traffic jam or unreachable tile can NEVER block real work again."""
        q = quests.get(eid)
        if not q:
            return False
        nxt = q.pop(0)
        goals[eid] = {**nxt, "tile": _resolve_tile(eid, nxt.get("where", "wander")),
                      "do_at": _time.monotonic() + random.uniform(*_WORK_DUR)}
        paths.pop(eid, None)
        engine.set_entity_thought(eid, "» " + nxt["intent"][:90])
        engine.set_entity_state(eid, "walking")
        publish_goals()
        return True

    async def replenish_quests(eid):
        """Fill the agent's backlog from the GROUNDED renewable pool (fresh papers, findings,
        flywheel questions, harvested directions) → the agent's backlog."""
        try:
            if eid not in engine.state.entities:
                return
            # User guidance (Telegram `fix`) takes priority — it becomes the next quest.
            guide = await _consume_guidance(eid)
            if guide:
                quests.setdefault(eid, []).insert(0, {
                    "intent": guide[:90], "kind": "create", "where": "wander",
                    "action": f"Act on the user's directive: {guide}", "with": ""})
                note_event(f"{_AGENT_NAMES.get(eid, eid)} got direction from Rasto: {guide[:48]}")
                publish_goals()
                return
            # THE LLM PLANNER IS GONE, deleted 2026-07-31 — and with it the context it was fed.
            #
            # `_LLM_PLANNER_ON` has been 0 by design since 2026-06-19 (it produced the "gaming party"
            # filler and was the dominant 429 source), but the flag was checked on the LAST line of a
            # ~90-line block that built its input first: a `_recall_mem` over a 15 MB inspeximus store,
            # a `_collective_recall` across all eight stores, `_brain_context` (3 HTTP), plus
            # `_brain_build_log` (2 HTTP), `_brain_gaps`, `_brain_identity`, `_brain_graves`, and a
            # ~2 KB prompt — and then threw all of it away with `... if _LLM_PLANNER_ON else {}`.
            # Measured 2026-07-31 in _dungeon.log: 2,234 planning cycles in six hours, every one of
            # them logging `LLM_quests=0`. That is ~370 cycles/hour of store deserialisation and brain
            # HTTP whose only consumer was an `else {}`. The prompt is not preserved anywhere: it is
            # the known-bad one, and the per-agent research organs below are its replacement.
            #
            # `_brain_context` survives the deletion and is now called ONCE PER ORGAN CYCLE (~4x/day
            # per agent) instead of ~370 times an hour — the same per-agent mind, moved to where it can
            # actually reach an output.
            for q in await _renewable_quests(eid, 3):
                quests.setdefault(eid, []).append(q)
            _log_plan_state(eid, "renewable",
                            "[plan] %s: %d grounded quest(s) from the renewable pool",
                            _AGENT_NAMES.get(eid, eid), len(quests.get(eid, [])))
            if quests.get(eid):
                _plan_fails[eid] = 0
            elif _plan_reason.get(eid) in ("off_priority", "exhausted"):
                # NOT a blocker: the sources delivered, the BOARD is narrower than what they delivered.
                # Counting this as a plan failure escalated "the brain may be down" while the brain was
                # serving perfectly — an alarm that names the wrong system trains everyone to ignore it.
                # "exhausted" joins it 2026-08-08 with the no-fallback fix: an agent that has already
                # pursued every on-priority candidate legitimately plans nothing, and routing that into
                # the escalation below would fire "the brain may be down" at the owner three cycles
                # later — the SAME false alarm this branch exists to prevent, re-created by the fix.
                _plan_fails[eid] = 0
            else:
                # even gaps/bridges/findings were empty → the brain is likely unreachable: a REAL blocker
                _plan_fails[eid] = _plan_fails.get(eid, 0) + 1
                if _plan_fails[eid] >= 3:
                    _plan_fails[eid] = 0
                    asyncio.create_task(_escalate(
                        eid, "I have no work AND the vault's gap/bridge/finding sources are all empty "
                        "or unreachable — the brain may be down. Reply `fix <topic>` to point me at something."))
                quests.setdefault(eid, []).append(
                    {"intent": random.choice(_THOUGHTS.get(eid, ["study the vault"])),
                     "kind": "explore", "where": "wander", "action": "...", "with": ""})
            publish_goals()
        except Exception as e:
            logger.debug(f"replenish_quests {eid}: {e}")
        finally:
            deciding.discard(eid)

    _loop_started = _time.time()          # wall-clock origin for the cadence heartbeat below
    _loop_n0 = loop_n                     # tick count at process start; loop_n is a LIFETIME total
    while True:
        await asyncio.sleep(0.85)
        # HEARTBEAT: stamp the loop counter + wall-clock to a file each iteration so an external
        # supervisor (dungeon_supervisor.py) can detect a wedged loop (the failure mode that froze
        # the QuestBoard) and restart us. Cheap, throttled to ~once/4s, never raises into the loop.
        if loop_n % 5 == 0:
            try:
                _atomic_write(_HEARTBEAT_FILE, f"{int(_time.time())} {loop_n}")
            except Exception:
                pass
        ents = engine.state.entities
        occupied = {(int(round(e.x)), int(round(e.y))): eid for eid, e in ents.items()}
        now = _time.monotonic()
        # Watchdog: a real conversation/pipeline stage lasts < ~20s. If an agent has been stuck in
        # _in_conv longer, it leaked (an exception skipped cleanup) — release it so it never freezes.
        for _e in list(_in_conv):
            _in_conv_seen.setdefault(_e, now)
            if now - _in_conv_seen[_e] > 75:
                _in_conv.discard(_e)
                _in_conv_seen.pop(_e, None)
        for _e in [k for k in _in_conv_seen if k not in _in_conv]:
            _in_conv_seen.pop(_e, None)
        for eid in list(ents.keys()):
            hold[eid] = max(0, hold.get(eid, 0) - 1)
            cooldown[eid] = max(0, cooldown.get(eid, 0) - 1)

        # Agents that wander near each other occasionally talk shop — now RARE (chatter was the #1
        # token sink at ROI 0.04). Grounded collaboration below is the dominant activity instead.
        if loop_n % 25 == 13:
            _maybe_start_conversation(ents, dead, hold, memory)

        loop_n += 1
        # CADENCE HEARTBEAT. Every organ below fires on `loop_n % N == M`, and every one of those
        # moduli was chosen against an ASSUMED 0.85s tick — the sleep at the top of this loop. Nobody
        # ever measured the real period, which is the loop body plus that sleep, and the body awaits
        # LLM calls. So the documented cadences ("~28 min", "~47 min") are unverified arithmetic, and
        # an organ whose trigger sits past the mean uptime between restarts can never fire at all:
        # loop_n resets to 0 on every restart. Cartography sits at tick 1700.
        #
        # This prints the ACTUAL elapsed time per tick so the cadence is observable rather than
        # assumed. It was not observable before: the dungeon exposed no loop counter anywhere, so the
        # question "how often does Rooke actually get a turn" had no answer from outside the process.
        if loop_n % 200 == 0:
            # Divide by ticks SINCE THIS PROCESS STARTED, not by loop_n. loop_n is restored from the
            # heartbeat file so the schedule accumulates across restarts (2026-06-19) — it is a
            # lifetime total in the millions, and dividing this process's uptime by it reports 0.00s
            # and reads like a spinning loop. I shipped that division and it was wrong within five
            # minutes of writing it, which is the same shape as everything else this file guards
            # against: a number that looks like a measurement and is an artefact of its denominator.
            _ticks = loop_n - _loop_n0
            _per = (_time.time() - _loop_started) / max(_ticks, 1)
            logger.info("[cadence] +%d ticks this process, %.2fs/tick (code assumes 0.85) | "
                        "lifetime loop_n=%d | period: replication(2000)=%.0fmin "
                        "belief(3300)=%.0fmin carto(3000)=%.0fmin",
                        _ticks, _per, loop_n, 2000 * _per / 60, 3300 * _per / 60, 3000 * _per / 60)
        # Meaningful collaboration: a varied pair co-produces a real grounded finding from a rotating
        # seed (recent finding / gap / bridge) — the OS actually doing research. Fired often now (it
        # feeds verify-findings, the one organ at ROI 0.92), so grounded output is the default, not chatter.
        if loop_n % 18 == 7:
            asyncio.create_task(_maybe_collaborate(hold))
        # Orchestrated pipeline: advance one stage of Aldric's assembly line (one role at a time).
        if loop_n % 9 == 4:
            asyncio.create_task(_pipeline_tick(hold))
        # These trust/DB/cross-agent-learning awaits can touch a slow brain/embedder; bound them so a
        # contended call caps the loop stall at a few seconds instead of FREEZING the visible world
        # (2026-06-20). The loop's progression must never hinge on a slow downstream call.
        if loop_n % 10 == 1:
            try:
                _m = await asyncio.wait_for(_trust_matrix(), timeout=3)
                if _m:
                    broadcast({"type": "trust_snapshot", "matrix": _m, "names": _AGENT_NAMES})
                await asyncio.wait_for(_broadcast_trust_graph(), timeout=3)   # ESS + cross-agent learning
                broadcast({"type": "os_snapshot", "log": os_log[-12:]})
                if os_modules:
                    broadcast({"type": "os_modules_snapshot", "modules": os_modules})
            except Exception:
                pass

        # Reputation decay: nudge all trust toward baseline so standing stays DYNAMIC —
        # bonds you don't reinforce fade, so curation authority genuinely shifts over time.
        if loop_n % 40 == 20 and _trust_engine:
            try:
                await asyncio.wait_for(_trust_engine.apply_decay(0.02), timeout=3)
            except Exception:
                pass

        # Autonomous curation: Dame Elara (Bridge Builder) tends the vault's links and
        # Sage Mira (Curator) consolidates live discoveries into vault notes — each gated
        # by their OWN standing, on offset cadences.
        if (loop_n % 850 == 7 or loop_n % 110 == 50 or loop_n % 1200 == 90
                or loop_n % 17000 == 300):
            try:
                _stm = _compute_standing(await asyncio.wait_for(_trust_matrix(), timeout=3))
            except Exception:
                _stm = {}
            if loop_n % 850 == 7 and not curation["running"]:       # Elara: connect links (~12 min)
                asyncio.create_task(_run_curation("guard_r", _stm.get("guard_r", 0.5)))
            if loop_n % 1200 == 90 and not curation["running"]:     # Voss: QA flag duplicates (~17 min)
                asyncio.create_task(_run_curation("guard_l", _stm.get("guard_l", 0.5), "duplicates"))
            if loop_n % 110 == 50 and not consolidation["running"]:  # Mira: consolidate digest
                asyncio.create_task(_run_consolidation("scholar", _stm.get("scholar", 0.5), _stm))
            if loop_n % 17000 == 300 and not orchestration["running"]:  # Aldric: doctrine + GitHub (~4 h)
                asyncio.create_task(_run_orchestration("king", _stm.get("king", 0.5), _stm))

        # Dogfood: run inspeximus's consolidation "dream pass" over each agent's memory (~every 28 min) —
        # value-rank under a keep-budget + link near-duplicates. Agora's product, on Agora's agents.
        if loop_n % 2000 == 123 and _Store is not None:
            def _consolidate_agent_mem():
                for _eid in list(_AGENT_NAMES):
                    mm = _agent_store(_eid)
                    if mm is not None:
                        try:
                            # keep>300 holds the active pool above inspeximus's measured semantic
                            # crossover, so recall runs the embedder (below it, lexical is as good).
                            mm.consolidate(keep=400)              # hubs + dedup + state-toggle + keep
                            mm.consolidate_clusters(threshold=15)  # cluster-triggered consolidation
                        except Exception:
                            pass
                return _keep_memory_signal()
            async def _reflect():
                sig = await asyncio.to_thread(_consolidate_agent_mem)
                # Surface what the collective memory values most + any self-contradiction it flags.
                if sig.get("top_cohort"):
                    note_event(f"the keep's memory leans on '{sig['top_cohort']}' "
                               f"(value {sig['top_value']})"
                               + (f"; {sig['contradictions']} memory contradiction(s) flagged"
                                  if sig.get("contradictions") else ""))
                if sig.get("contradictions"):
                    _os_build("challenge", "the keep", f"inspeximus flagged {sig['contradictions']} "
                              f"contradictory memories for review")
            asyncio.create_task(_reflect())

        # SURFACE every agent's REAL brain work into the build log (~every 30 s, offset cadence),
        # so the keep shows Rooke replicating, Wren bridging, Orin theorising — not only the curator.
        if loop_n % 38 == 21:
            asyncio.create_task(_surface_agent_activity())

        # THE NIGHT SHIFT — consolidate memory while the owner sleeps (02:00-05:59, once/day).
        if loop_n % 400 == 250:
            _ns_now = _time.localtime()
            _ns_today = _time.strftime("%Y-%m-%d", _ns_now)
            if 2 <= _ns_now.tm_hour < 6 and _night_state["last"] != _ns_today:
                _night_state["last"] = _ns_today
                asyncio.create_task(_run_night_shift())
        # THE ANNALS — write today's chronicle late evening (22:00-23:59, once/day);
        # Sundays also queue the weekly retrospective for Claude.
        if loop_n % 400 == 320:
            _an_now = _time.localtime()
            _an_today = _time.strftime("%Y-%m-%d", _an_now)
            if _an_now.tm_hour >= 22 and _annals_state["last"] != _an_today:
                _annals_state["last"] = _an_today
                asyncio.create_task(_run_annals(_an_now.tm_wday == 6))
        # Morning report → Telegram, once per day after 07:00 local.
        if loop_n % 200 == 100:
            _now = _time.localtime()
            _today = _time.strftime("%Y-%m-%d", _now)
            if _now.tm_hour >= 7 and _report_state["last"] != _today:
                _report_state["last"] = _today
                asyncio.create_task(_send_morning_report())
        # Voss autonomously fact-checks recent findings and incorporates the VERIFIED ones (~6 min).
        if loop_n % 450 == 200:
            asyncio.create_task(_run_verification())
        # Mira promotes the best grounded findings into the vault via the quality gate (~20 min) —
        # the reliable research→vault funnel so the second-brain actually grows.
        if loop_n % 750 == 350:               # ~10 min: wider + more frequent funnel (more gems land)
            asyncio.create_task(_run_promotion())
        # Aldric harvests findings into next directions (~13 min) — work compounds toward them.
        if loop_n % 950 == 600:
            asyncio.create_task(_run_harvest())
        # Agora reflects on itself and Telegrams upgrade proposals (~3 h) — recurring self-improvement.
        if loop_n % 13000 == 800:
            asyncio.create_task(_run_self_reflection())
        # Pulse — a plain-language visibility report to Telegram (~every 3 h, offset from the rest).
        if loop_n % 11000 == 5000:
            asyncio.create_task(_run_pulse())
        # Reality Bridge — Orin empirically tests a recent finding vs real-world data (~12 min).
        if loop_n % 850 == 350:
            asyncio.create_task(_run_reality_check())
        # Insight Engine — Agora queues a rich theme for Claude to synthesize (BOOSTED 2026-06-19, ~34 min).
        if loop_n % 2400 == 1100:
            asyncio.create_task(_queue_insight_theme())
        # Flywheel — queue an insight's falsifier for Claude to re-test + deepen (BOOSTED 2026-06-19, ~31 min).
        if loop_n % 2200 == 1500:
            asyncio.create_task(_queue_deepening())
        # Prediction Ledger — resolve due predictions + queue a new one for Claude (~90 min).
        if loop_n % 6300 == 1500:
            asyncio.create_task(_run_predictions())
        # Dialectic — DOWN-WEIGHTED 2026-06-19 (was %2800): it dominated the inbox (22/100 tasks) at low
        # value; the high-value organs (Replicate/Synthesize/Hypothesize/Deepen) are boosted instead (~155 min).
        if loop_n % 11000 == 400:
            asyncio.create_task(_queue_dialectic())
        # The Agora Mind — metacognitive reflection: synthesize the worldview + self-direct (~daily).
        if loop_n % 64000 == 33000:
            asyncio.create_task(_queue_mind_reflection())
        # The Learning Loop — review the track record + derive applied lessons (~daily, offset).
        if loop_n % 64000 == 9000:
            asyncio.create_task(_queue_learning())
        # The Mind HUD — make Agora's live cognition visible in the dungeon (~every 4 min).
        if loop_n % 300 == 60:
            asyncio.create_task(_broadcast_mind_state())
        # Agora's Senses — perceive what's live in the user's world + queue an insight on it (~daily).
        if loop_n % 64000 == 21000:
            asyncio.create_task(_sense_and_queue())
        # THE EXAM — a measurable capability benchmark over the vault's core concepts (~weekly).
        if loop_n % 448000 == 31000:
            asyncio.create_task(_run_exam())
        # MEMORY ECONOMY — the Custodian proposes archiving dead weight (GATED, ~weekly offset).
        if loop_n % 448000 == 250000:
            asyncio.create_task(_run_memory_economy())
        # RESEARCH EXCHANGE — compose + propose the public digest (GATED, ~weekly offset).
        if loop_n % 448000 == 120000:
            asyncio.create_task(_run_research_exchange())
        # HYPOTHESIS INDUCTION — bridge a finding cluster into a testable conjecture (BOOSTED 2026-06-19, ~57 min).
        if loop_n % 4000 == 2000:
            asyncio.create_task(_queue_hypothesis_induction())
        # THE OBSERVATORY — one vital-signs reading of the whole organism (~weekly offset).
        if loop_n % 448000 == 350000:
            asyncio.create_task(_run_vitals())
        # THE INTERVIEW — ask the owner the one question Agora most needs answered (~daily).
        if loop_n % 64000 == 47000:
            asyncio.create_task(_run_interview())
        # THE ROADMAP — Aldric synthesizes a data-backed next move for the owner (~daily, offset).
        if loop_n % 64000 == 12000:
            asyncio.create_task(_queue_roadmap())
        # THE PRESS — Mira sends the strongest unpublished artifact to the editor's desk (~2h).
        # Distribution stream: propose a fresh publish-ready post often; the one-pending-approval
        # gate (in /brain/press/draft) keeps it from flooding — the next is drafted once the owner
        # clears the last. Publishing stays gated until the owner sets an auto-post policy.
        if loop_n % 8000 == 2000:
            asyncio.create_task(_queue_press())
        # THE OPPORTUNITY SCOUT — Kael actively hunts an answerable open GitHub issue in the frontier
        # domains (~2.4h, offset). Gated: drafts a reply only where the vault answers with evidence;
        # the owner approves before anything posts. Active outreach = the reputation/name engine.
        if loop_n % 10000 == 4000:
            asyncio.create_task(_queue_scout())
        # THE PORTFOLIO — Voss keeps the public track record current, proposes publish if credible (~12h).
        if loop_n % 50000 == 30000:
            asyncio.create_task(_run_portfolio())
        # THE ACADEMY — enroll/measure the mentor-mentee pair (~12h, offset).
        if loop_n % 50000 == 10000:
            asyncio.create_task(_run_academy())
        # THE LIBRARY — read ONE full paper and queue it for Claude to digest (~daily, offset).
        if loop_n % 64000 == 55000:
            asyncio.create_task(_queue_library_read())
        # CAMPAIGNS — advance ALL running campaigns one harvest; a campaign closes as soon as
        # its coverage is enough, so check often (~3h), not daily.
        if loop_n % 8000 == 5000:
            asyncio.create_task(_tick_campaign())
        # ── THE SCIENCE ORGANS ─────────────────────────────────────────────
        # These only QUEUE a task for Claude and each is capped by _task_already_pending
        # (at most one of its kind pending). Cadence is matched to Claude's realistic drain
        # rate (~1 wake/15 min, a few tasks each) so the bench stays stocked WITHOUT a
        # perpetual backlog that starves low-priority work. ~0.85s/tick → ~75-110 min, staggered.
        if loop_n % 3500 == 900:                       # Analogy Forge  (~50 min)
            asyncio.create_task(_queue_analogy_forge())
        if loop_n % 3300 == 1200:                      # Belief revision  (~47 min)
            asyncio.create_task(_queue_belief_challenge())
        if loop_n % 5500 == 2100:                      # The Court — structured debate  (~78 min)
            asyncio.create_task(_run_debate())
        if loop_n % 2000 == 600:                       # Replication Unit (Rooke) - BOOSTED 2026-06-19 (Crucible=moat, ~28 min)
            asyncio.create_task(_queue_replication())
        if loop_n % 3000 == 1700:                      # Cartographer (Wren)  (~43 min)
            asyncio.create_task(_queue_cartography())
        # The bench that CONSUMES what Wren charts. Offset from the chartering fire so a fresh chart
        # is not tested in the same breath it is drawn; 2600 ticks ~ 45 min at the measured 1.05s.
        if loop_n % 2600 == 900:
            asyncio.create_task(_queue_bridge_test())
        if loop_n % 6000 == 1100:                      # Kael's Red Team  (~85 min)
            asyncio.create_task(_run_red_team())
        if loop_n % 2500 == 1200:                      # Orin's Synthesis Detector  (~35 min; fires only when due)
            asyncio.create_task(_run_synthesis_detector())
        if loop_n % 6500 == 800:                       # Elara's Coherence Audit  (~92 min, offset)
            asyncio.create_task(_run_coherence_audit())
        # CONTRADICTION SWEEP — find where the vault disagrees with itself (~95 min, offset).
        if loop_n % 6700 == 2400:
            asyncio.create_task(_run_contradiction_sweep())
        # COHERENCE AUDIT — does AGORA contradict itself? one new belief per day (~daily offset).
        if loop_n % 64000 == 50000:
            asyncio.create_task(_run_coherence())
        # THE COUNTERFACTUAL SELF — weekly review of history replayed under other policies.
        if loop_n % 448000 == 330000:
            asyncio.create_task(_queue_counterfactual_review())
        # THE THEORY ENGINE — run one mechanistic belief as a formal model (~95 min, offset).
        if loop_n % 6700 == 3000:
            asyncio.create_task(_queue_theory_run())
        # THE CORRESPONDENT — compose outreach ~2x/week (gated); harvest replies every ~6h
        # (a public conversation deserves a same-day answer, not a tomorrow one).
        if loop_n % 224000 == 100000:
            asyncio.create_task(_queue_outreach())
        if loop_n % 16000 == 3000:
            asyncio.create_task(_run_reply_harvest())
        # THE ORACLE — pick one live market for an independent call (~daily) + resolve (~daily).
        if loop_n % 64000 == 7000:
            asyncio.create_task(_run_oracle_scan())
        if loop_n % 64000 == 33000:
            asyncio.create_task(_run_oracle_resolve())
        # THE CANON — when enough new artifacts landed, queue the living-book merge (~2 days).
        if loop_n % 128000 == 30000:
            asyncio.create_task(_queue_canon_update())
        # THE TUTOR — the owner's daily spaced-repetition micro-quiz (~daily offset).
        if loop_n % 64000 == 26000:
            asyncio.create_task(_run_tutor())
        # CAPABILITY FORGE — scan failure traces for gaps + queue the top one (~weekly offset).
        if loop_n % 448000 == 180000:
            asyncio.create_task(_run_forge())
        # THE BOARD MEETING — weekly agenda to the owner; directives steer all synthesis.
        if loop_n % 448000 == 410000:
            asyncio.create_task(_run_board())
        # THE ATLAS — refresh the owner's per-domain maps of content (~weekly offset).
        if loop_n % 448000 == 90000:
            asyncio.create_task(_run_atlas())
        # THE DESK — lay out the owner's working context for today (~daily, morning-ish offset).
        if loop_n % 64000 == 36000:
            asyncio.create_task(_run_desk())
        # THE SALON — sense the followed external minds; one contestable claim a day (~daily).
        if loop_n % 64000 == 17000:
            asyncio.create_task(_run_salon())
        # THE RESEARCH ORGANS — one beat of the per-agent organ scheduler (~5 min). The beat is
        # cheap (a dict read + a mtime-free file read); the PERIOD is per organ (~4 cycles/day each)
        # and persisted, so this cadence only decides how finely the 32 daily fires are staggered.
        # It deliberately does NOT sit on a `% big-number` trigger: those are measured against an
        # assumed 0.85s tick and an organ whose trigger sits past the mean uptime between restarts
        # never fires at all (see the cadence heartbeat above — cartography sits at tick 1700).
        if loop_n % 350 == 175:
            asyncio.create_task(_organ_tick())
        # THE WATCHDOG — keep the brain alive (one supervision beat ~every 5 min).
        if loop_n % 220 == 117:
            asyncio.create_task(_watch_brain())

        if loop_n % 2 == 0:        # refresh the board ~every 1.7s so meters track real movement
            publish_goals()

        for eid, ent in list(ents.items()):
            cx, cy = int(round(ent.x)), int(round(ent.y))

            if dead.get(eid, 0) > 0:
                dead[eid] -= 1
                if dead[eid] == 0:
                    engine.set_entity_health(eid, 100)
                    engine.set_entity_state(eid, "idle")
                    engine.set_entity_thought(eid, "")
                    note_event(f"{_AGENT_NAMES.get(eid, eid)} rose again")
                continue
            if hold.get(eid, 0) > 0 or eid in _in_conv:
                continue

            # (Guards no longer auto-spar — everyone is a collaborator building the OS.)
            goal = goals.get(eid)

            # No active quest → take the next from the backlog, or have the LLM plan more.
            if goal is None:
                if now >= next_decide.get(eid, 0.0):
                    if quests.get(eid):
                        activate_next_quest(eid)
                    elif eid not in deciding:
                        deciding.add(eid)
                        asyncio.create_task(replenish_quests(eid))
                elif now >= idle_bub.get(eid, 0.0):
                    # Idle between quests → show what this agent is mulling (its REAL work),
                    # not a blank or stale bubble: the next queued quest, else its recent work.
                    idle_bub[eid] = now + 8.0
                    nxt_q = quests.get(eid) or []
                    focus = (nxt_q[0].get("intent") if nxt_q else None) \
                        or (memory.get(eid) or [None])[-1] \
                        or _ROLE_HINT.get(eid, "the next question")
                    engine.set_entity_thought(eid, "⋯ " + str(focus)[:84])
                continue

            # TELEPATHIC, TIME-BASED COMPLETION: the quest does its real work after a short work
            # interval, WHEREVER the agent stands — no walking to a tile, no being near a partner.
            # This removes the entire class of "agents jammed / can't reach the spot" stalls that
            # froze the QuestBoard. Movement below is now purely ambient.
            if "do_at" not in goal:
                goal["do_at"] = now + random.uniform(*_WORK_DUR)
            if now >= goal["do_at"]:
                kind = goal.get("kind", "explore")
                intent, action = goal["intent"], goal["action"]
                who = _AGENT_NAMES.get(eid, eid)
                engine.set_entity_state(eid, "casting" if kind in ("create", "upgrade") else "interact")
                engine.set_entity_thought(eid, action[:100])
                engine.add_effect("glow", cx, cy,
                                  "#7fd0ff" if kind == "create" else
                                  "#ffcf5a" if kind == "upgrade" else
                                  "#ff6a6a" if kind == "challenge" else "#ffd27a", 0.9)
                remember(eid, intent)

                def _telepath_partner(prefer):
                    """A partner by NAME (the LLM may name one in goal['with']) else a random living
                    peer — telepathic, proximity no longer required."""
                    others = [oid for oid in ents if oid != eid and dead.get(oid, 0) == 0]
                    if prefer:
                        pl = str(prefer).lower()
                        for oid in others:
                            nm = _AGENT_NAMES.get(oid, "")
                            if nm and (nm.lower() in pl or nm.split()[-1].lower() in pl):
                                return oid
                    return random.choice(others) if others else None

                if kind in ("hypothesize", "create"):
                    won, p = _market_won(eid)
                    if not won:
                        engine.set_entity_thought(eid, "priced out this round — earn standing")
                        note_event(f"{who} was priced out of the discovery market (p={p:.2f})")
                    elif _LAB_FIRST:
                        # LAB-FIRST: both research intents must end in a MEASURED Lab result, not a paraphrase.
                        asyncio.create_task(_experiment_discovery(eid, intent))
                        note_event(f"{who} runs an experiment: {intent}")
                        _os_build("discovery", who, intent)
                    elif kind == "hypothesize":
                        asyncio.create_task(_hypothesis_discovery(eid, intent))
                        note_event(f"{who} forms a hypothesis: {intent}")
                        _os_build("discovery", who, intent)
                    else:
                        asyncio.create_task(_grounded_discovery(eid, intent))
                        note_event(f"{who} discovered: {intent}")
                        _os_build("discovery", who, intent)
                elif kind == "upgrade":
                    asyncio.create_task(_brain_propose_upgrade(eid, intent, action))
                    _apply_module(intent, (cx, cy), who, "upgrade")  # REALLY build it
                    note_event(f"{who} built: {intent}")
                    _os_build("upgrade", who, intent)
                elif kind == "collaborate":
                    pid = _telepath_partner(goal.get("with"))
                    if pid:
                        asyncio.create_task(record_trust(eid, pid, "cooperate"))   # ESS trust, fire-and-forget (never block the loop)
                        partner = _AGENT_NAMES.get(pid, pid)
                        # NO _brain_contribute: a collaborate quest is a social/trust act, not a finding.
                        # Logging the plan text ("Extend X's result — …") as a 'discovery' was the chatter
                        # source. Real joint knowledge comes from the Seminar (a grounded Contribution).
                        note_event(f"{who} & {partner}: {intent}")
                        _os_build("collab", f"{who} + {partner}", intent)
                    else:
                        note_event(f"{who}: {intent}")
                elif kind == "challenge":
                    pid = _telepath_partner(goal.get("with"))
                    if pid:
                        asyncio.create_task(record_trust(eid, pid, "defect"))   # standing shifts; fire-and-forget
                        rival = _AGENT_NAMES.get(pid, pid)
                        note_event(f"{who} challenged {rival}: {intent}")
                        _os_build("challenge", f"{who} ⟂ {rival}", intent)
                    else:
                        note_event(f"{who}: {intent}")
                else:
                    note_event(f"{who}: {intent}")

                asyncio.create_task(_brain_remember(eid, f"{intent} — {action}"))
                quest_log.setdefault(eid, []).append(intent)
                del quest_log[eid][:-6]
                quest_done[eid] = quest_done.get(eid, 0) + 1
                broadcast({"type": "quest_done", "agent": who, "title": intent[:90],
                           "kind": kind, "total": quest_done[eid]})
                hold[eid] = 3
                goals.pop(eid, None)
                paths.pop(eid, None)
                next_decide[eid] = now + (random.uniform(_BACKLOG_MIN, _BACKLOG_MAX)
                                          if quests.get(eid) else random.uniform(_DECIDE_MIN, _DECIDE_MAX))
                publish_goals()
                continue

            # AMBIENT WANDER (cosmetic only — never gates work): drift toward a random spot; on
            # arrival or if boxed in, repick a fresh tile. A jam here can no longer stall anything.
            wt = goal.get("tile")
            if not wt or (cx, cy) == wt:
                goal["tile"] = wt = random.choice(list(locations.values()))
                paths.pop(eid, None)
            path = paths.get(eid) or []
            if not path:
                p = _astar((cx, cy), wt)
                if not p or len(p) < 2:
                    goal["tile"] = random.choice(list(locations.values()))   # repick, keep wandering
                    continue
                paths[eid] = path = p[1:]
            nx, ny = path[0]
            if (nx, ny) in occupied and occupied[(nx, ny)] != eid:
                step = next(((cx + dx, cy + dy) for dx, dy in random.sample([(1, 0), (-1, 0), (0, 1), (0, -1)], 4)
                             if _walkable(cx + dx, cy + dy)
                             and ((cx + dx, cy + dy) not in occupied or occupied[(cx + dx, cy + dy)] == eid)), None)
                if step:
                    engine.set_entity_state(eid, "walking"); engine.move_entity(eid, *step)
                    occupied.pop((cx, cy), None); occupied[step] = eid
                paths.pop(eid, None)
                continue
            engine.set_entity_state(eid, "walking")
            engine.move_entity(eid, nx, ny)
            occupied.pop((cx, cy), None)
            occupied[(nx, ny)] = eid
            path.pop(0)


# ── Main ────────────────────────────────────────────────────


def main():
    """Start MCP server + WebSocket + HTTP in the same process."""
    import sys

    if "--stdio" in sys.argv:
        # MCP stdio mode: run MCP in main thread
        logger.info("Starting in MCP stdio mode (for Hermes agent)...")

        # Start WS + HTTP in background threads
        def _run_async(loop_fn):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(loop_fn)

        ws_thread = threading.Thread(
            target=_run_async, args=(run_ws_server(),), daemon=True
        )
        ws_thread.start()
        http_thread = threading.Thread(
            target=_run_async, args=(run_http_server(),), daemon=True
        )
        http_thread.start()

        # Create default dungeon
        engine.create_default_dungeon()

        # Run MCP stdio transport
        mcp.run(transport="stdio")
    else:
        # Standalone mode. SERIOUS FIX (2026-06-19): the watchdog-checked HTTP server (:5174) used to run
        # on the SAME event loop as ambient_life(), so whenever the loop blocked (its LLM/heavy work
        # starving the event loop) the health endpoint couldn't answer -> the brain watchdog logged
        # "dungeon was down" and restarted it. That false-restart churn reset loop_n every time, which
        # starved the Claude inbox + the GitHub scout. http_handler is a PURE STATIC-FILE server (no
        # shared mutable state), so we now run it in its OWN thread+loop -> the health endpoint stays
        # responsive no matter what ambient_life is doing. WS (:5175, live state) stays on the main loop
        # (it already coexisted with ambient there; only the watchdog-checked HTTP needed decoupling).
        def _run_async(loop_fn):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(loop_fn)

        http_thread = threading.Thread(target=_run_async, args=(run_http_server(),),
                                       daemon=True, name="dungeon-http")
        http_thread.start()

        engine.create_default_dungeon()
        print(f"Dungeon Game Server starting...")
        print(f"  HTTP:     http://localhost:{HTTP_PORT}  (own thread - watchdog-safe)")
        print(f"  WebSocket: ws://localhost:{WS_PORT}")
        print(f"  Open http://localhost:{HTTP_PORT} in your browser")
        print()

        async def run_main():
            import concurrent.futures
            # FREEZE FIX (2026-06-20): the ambient loop fires many background LLM/brain calls via
            # asyncio.to_thread (collaborate, pipeline, curation, per-agent decisions). The DEFAULT
            # thread pool is only ~min(32, cpu+4); under cloud contention each call holds a thread for up
            # to 45s, so the pool EXHAUSTS and the loop's OWN to_thread awaits (trust matrix, decisions)
            # queue behind it -> the loop crawls to ~20s/tick and the world looks frozen (esp. when an
            # agent publishes -> an LLM burst). These calls are I/O-bound (threads just wait on network),
            # so a large pool is cheap and keeps the loop responsive even when the LLM is slow.
            loop = asyncio.get_running_loop()
            loop.set_default_executor(
                concurrent.futures.ThreadPoolExecutor(max_workers=64, thread_name_prefix="dungeon-io"))
            await asyncio.gather(run_ws_server(), ambient_life())

        asyncio.run(run_main())


if __name__ == "__main__":
    main()
