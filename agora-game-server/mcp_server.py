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
import sys
import threading
import time
from pathlib import Path
from typing import Any

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

        # Stream events
        try:
            while True:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                frame = _make_ws_frame(msg)
                writer.write(frame)
                await writer.drain()
        except asyncio.TimeoutError:
            # Ping / keepalive
            try:
                frame = _make_ws_frame("", opcode=0x9)  # ping
                writer.write(frame)
                await writer.drain()
                # Wait for pong
                await asyncio.wait_for(reader.readexactly(2), timeout=5)
            except Exception:
                pass

    except (asyncio.IncompleteReadError, ConnectionError, ConnectionResetError):
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
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
    server = await asyncio.start_server(ws_handler, "0.0.0.0", WS_PORT)
    logger.info(f"WebSocket server on ws://0.0.0.0:{WS_PORT}")
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
    server = await asyncio.start_server(http_handler, "0.0.0.0", HTTP_PORT)
    logger.info(f"HTTP server on http://0.0.0.0:{HTTP_PORT}")
    async with server:
        await server.serve_forever()


# ── Ambient Life (autonomous entity behaviour for the standalone demo) ──

import random

_WALKABLE_TYPES = {"floor", "floor_vip", "throne", "arch", "door", "grass"}

_THOUGHTS = {
    "king": ["The realm is restless tonight.", "Bring me the treasury ledger.",
             "Who dares approach my throne?"],
    "guard_l": ["All quiet at the gate.", "Halt — state your business.",
                "Another long watch ahead."],
    "guard_r": ["Steel at the ready.", "Something stirs in the hall.", "For the crown!"],
    "priest": ["The old gods are listening.", "A blessing upon this hall.",
               "Dark omens gather..."],
    "thief": ["So much gold, so little time.", "Nobody's watching the chests...",
              "The shadows are my ally."],
    "scholar": ["Fascinating runes on that wall.", "Knowledge is the true treasure.",
                "I must record this at once."],
}


import heapq

_GUARDS = {"guard_l", "guard_r"}

# Posts around the keep that tasks send agents to. Each tile is a walkable standing
# spot; `role` is the agent who prefers it (others take it only if nothing else fits).
_POSTS = {
    "throne":   {"tile": (11, 4),  "title": "Attend the throne",    "role": "king",    "act": "interact", "fx": "#ff66cc"},
    "treasury": {"tile": (19, 4),  "title": "Inspect the treasury", "role": "thief",   "act": "interact", "fx": "#ffd24d"},
    "library":  {"tile": (3, 3),   "title": "Study the archives",   "role": "scholar", "act": "interact", "fx": "#88aaff"},
    "shrine":   {"tile": (11, 8),  "title": "Bless the nave",       "role": "priest",  "act": "casting",  "fx": "#a98bff"},
    "gate":     {"tile": (11, 17), "title": "Hold the gate",        "role": "guard_l", "act": "guard",    "fx": "#aaccff"},
    "hall":     {"tile": (6, 11),  "title": "Patrol the great hall","role": "guard_r", "act": "guard",    "fx": "#ffae66"},
    "barracks": {"tile": (4, 16),  "title": "Sweep the barracks",   "role": None,      "act": "guard",    "fx": "#cfcfcf"},
    "armory":   {"tile": (19, 16), "title": "Secure the armory",    "role": None,      "act": "interact", "fx": "#d4a35a"},
}

_ACT_LINES = {
    "interact": ["Done.", "All in order.", "As commanded."],
    "casting":  ["Blessings bestowed.", "The rite is complete.", "Spirits, hear me."],
    "guard":    ["Post secured.", "Nothing to report.", "All quiet here."],
}
_TALK = {
    "king": ["You may approach.", "Speak, then."],
    "guard_l": ["On guard!", "Spar with me!"],
    "guard_r": ["Have at thee!", "For the crown!"],
    "priest": ["Blessings upon you.", "Peace, friend."],
    "thief": ["...didn't see me.", "Move along."],
    "scholar": ["A word, colleague?", "Most curious!"],
}


# ── LLM Brain (OpenRouter / Nemotron) ───────────────────────────
# Agents think and converse in-character via a small, fast Nemotron model.
# Falls back to the canned _THOUGHTS/_TALK/_ACT_LINES tables when no key is set
# or any call fails, so the dungeon always runs.
import urllib.request as _urlreq
import time as _time

_LLM_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
# nano-30b-a3b: newest Nemotron 3, MoE (3B active) → ~1.5s/line, ideal for live banter.
_LLM_MODEL = os.environ.get("DUNGEON_LLM_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free").strip()
_LLM_URL = "https://openrouter.ai/api/v1/chat/completions"
_LLM_ON = bool(_LLM_KEY)

_PERSONA = {
    "king":    "King Aldric — the proud, aging ruler of this keep. Regal, weary, commanding.",
    "guard_l": "Sergeant Voss — a gruff veteran gate guard. Blunt, loyal, watchful.",
    "guard_r": "Dame Elara — a sharp knight of the great hall. Disciplined, dry-witted.",
    "priest":  "High Priest Orin — keeper of the shrine. Solemn, cryptic, kindly.",
    "thief":   "Shadow Kael — a sly rogue eyeing the treasury. Sarcastic, quick, greedy.",
    "scholar": "Sage Mira — an obsessive archivist. Curious, precise, easily distracted.",
}

# Per-agent throttles (monotonic timestamps) + in-conversation guard.
_speech_cd: dict[str, float] = {}
_conv_cd: dict[str, float] = {}
_in_conv: set[str] = set()


def _persona(eid: str) -> str:
    return _PERSONA.get(eid, "a weary dungeon dweller")


def _llm_say_sync(system: str, user: str) -> str | None:
    """Blocking OpenRouter call → one short line, or None on any failure."""
    if not _LLM_ON:
        return None
    payload = json.dumps({
        "model": _LLM_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.95,
        "max_tokens": 350,
        "response_format": {"type": "json_object"},
    }).encode()
    req = _urlreq.Request(_LLM_URL, data=payload, headers={
        "Authorization": f"Bearer {_LLM_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/DanceNitra/agora",
        "X-Title": "Dungeon OS",
    })
    try:
        with _urlreq.urlopen(req, timeout=25) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"]["content"]
        line = (json.loads(content).get("line") or "").strip()
        return line[:120] or None
    except Exception as e:
        logger.debug(f"LLM say failed: {e}")
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
    _speech_cd[eid] = now + 14.0

    async def _run():
        sysmsg = (f"You are {_persona(eid)} You are in a torch-lit medieval dungeon keep. "
                  f'Reply ONLY with JSON {{"line":"<one short in-character line, max 12 words>"}}.')
        line = await _llm_say(sysmsg, situation + " Your line:", fallback)
        if eid not in _in_conv:  # don't stomp an active conversation
            engine.set_entity_thought(eid, line)

    asyncio.create_task(_run())


async def _converse(a_id: str, b_id: str, hold: dict[str, int]) -> None:
    """Two agents exchange a few in-character lines as sequential speech bubbles."""
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
            sysmsg = (f"You are {_persona(sid)} You are in a torch-lit dungeon keep, speaking "
                      f"with {oname}. Reply ONLY with JSON "
                      f'{{"line":"<one short spoken line, max 14 words>"}}.')
            convo = "  ".join(history) if history else "(you speak first)"
            fb = random.choice(_TALK.get(sid, ["Well met.", "..."]))
            line = await _llm_say(sysmsg, f"Dialogue so far: {convo}\nReply to {oname}.", fb)
            engine.set_entity_thought(sid, line)
            history.append(f"{sname}: {line}")
            await asyncio.sleep(2.4)
        await asyncio.sleep(1.0)
        for cid in (a_id, b_id):
            engine.set_entity_thought(cid, "")
            engine.set_entity_state(cid, "idle")
    finally:
        now = _time.monotonic()
        _conv_cd[a_id] = _conv_cd[b_id] = now + 30.0
        hold[a_id] = hold[b_id] = 0
        _in_conv.discard(a_id)
        _in_conv.discard(b_id)


def _maybe_start_conversation(ents, dead: dict[str, int], hold: dict[str, int]) -> None:
    """Find one eligible nearby pair and start a conversation (at most one per tick)."""
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
                asyncio.create_task(_converse(a, b, hold))
                return


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


async def ambient_life():
    """Task-driven simulation: a quest board hands out posts across the whole keep,
    agents A*-path to them, perform the action, and report done. Guards still spar
    when they cross paths (attack → hit → HP → knockout → revive). The board and all
    state stream to the client. Disable with DUNGEON_AMBIENT=0 (e.g. Hermes drives).
    """
    if os.environ.get("DUNGEON_AMBIENT", "1") == "0":
        return
    await asyncio.sleep(2.0)  # let the first browser connect

    tasks: list[dict] = []          # the live quest board
    next_id = 1
    paths: dict[str, list] = {}     # remaining path tiles per agent
    task_of: dict[str, int] = {}    # agent -> task id
    hold: dict[str, int] = {}       # ticks to stand still (action / combat anim)
    cooldown: dict[str, int] = {}   # spar cooldown
    dead: dict[str, int] = {}       # knockout countdown
    logger.info("Task simulation loop started")

    def publish():
        engine.set_tasks([
            {"id": t["id"], "title": t["title"], "agent": t["agent"], "status": t["status"]}
            for t in tasks
        ])

    while True:
        await asyncio.sleep(0.85)
        ents = engine.state.entities
        occupied = {(int(round(e.x)), int(round(e.y))): eid for eid, e in ents.items()}
        for eid in list(ents.keys()):
            hold[eid] = max(0, hold.get(eid, 0) - 1)
            cooldown[eid] = max(0, cooldown.get(eid, 0) - 1)

        # Keep the board topped up; retire old completed quests
        changed = False
        done = [t for t in tasks if t["status"] == "done"]
        if len(done) > 2:
            for t in done[:-2]:
                tasks.remove(t)
            changed = True
        # At most ONE active task per post → agents spread to distinct spots (no pile-ups)
        open_n = sum(1 for t in tasks if t["status"] == "open")
        active_posts = {t["post"] for t in tasks if t["status"] != "done"}
        avail = [k for k in _POSTS if k not in active_posts]
        random.shuffle(avail)
        while open_n < 3 and avail:
            key = avail.pop()
            p = _POSTS[key]
            tasks.append({"id": next_id, "post": key, "title": p["title"], "tile": p["tile"],
                          "role": p["role"], "act": p["act"], "fx": p["fx"],
                          "status": "open", "agent": None})
            next_id += 1
            open_n += 1
            changed = True
        if changed:
            publish()

        # Agents that wander near each other strike up a conversation.
        _maybe_start_conversation(ents, dead, hold)

        for eid, ent in list(ents.items()):
            cx, cy = int(round(ent.x)), int(round(ent.y))

            if dead.get(eid, 0) > 0:
                dead[eid] -= 1
                if dead[eid] == 0:
                    engine.set_entity_health(eid, 100)
                    engine.set_entity_state(eid, "idle")
                    engine.set_entity_thought(eid, "")
                continue
            if hold.get(eid, 0) > 0:
                continue
            if eid in _in_conv:
                continue  # busy in a conversation — handled by _converse

            # Guards spar if they end up next to each other (interrupts the patrol)
            if eid in _GUARDS and cooldown.get(eid, 0) == 0:
                sparred = False
                for oid in _GUARDS:
                    if oid == eid:
                        continue
                    o = ents.get(oid)
                    if not o or dead.get(oid, 0) > 0 or hold.get(oid, 0) > 0:
                        continue
                    ox, oy = int(round(o.x)), int(round(o.y))
                    if max(abs(ox - cx), abs(oy - cy)) == 1:
                        engine.face_entity(eid, ox, oy)
                        engine.face_entity(oid, cx, cy)
                        engine.set_entity_state(eid, "attack")
                        engine.set_entity_state(oid, "hit")
                        engine.add_effect("spark", ox, oy, "#ffd27a", 0.5)
                        hp = o.health - 18
                        if hp <= 24:
                            engine.set_entity_health(oid, 0)
                            engine.set_entity_state(oid, "dead")
                            engine.set_entity_thought(oid, "Aargh!")
                            engine.set_entity_thought(eid, "Yield!")
                            dead[oid] = 6
                        else:
                            engine.set_entity_health(oid, hp)
                        hold[eid] = hold[oid] = 2
                        cooldown[eid] = cooldown[oid] = 5
                        sparred = True
                        break
                if sparred:
                    continue

            # Claim a task if free
            tid = task_of.get(eid)
            task = next((t for t in tasks if t["id"] == tid), None)
            if task is None or task["status"] == "done":
                task_of.pop(eid, None)
                paths.pop(eid, None)
                cand = ([t for t in tasks if t["status"] == "open" and t["role"] == eid]
                        or [t for t in tasks if t["status"] == "open" and t["role"] is None]
                        or [t for t in tasks if t["status"] == "open"])
                # Take the nearest task we can actually reach
                chosen, chosen_path = None, None
                for c in sorted(cand, key=lambda t: abs(t["tile"][0] - cx) + abs(t["tile"][1] - cy)):
                    pp = _astar((cx, cy), c["tile"])
                    if pp is not None:
                        chosen, chosen_path = c, pp
                        break
                if chosen is None:
                    roll = random.random()
                    if roll < 0.25:
                        engine.set_entity_state(eid, "thinking")
                        _schedule_thought(
                            eid, "You stand idle in the keep with no task right now.",
                            random.choice(_THOUGHTS.get(eid, ["..."])))
                        hold[eid] = 2
                    elif roll < 0.7:
                        # Wander one walkable step so paths cross → conversations happen.
                        steps = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                        random.shuffle(steps)
                        for dx, dy in steps:
                            nx, ny = cx + dx, cy + dy
                            if _walkable(nx, ny) and (nx, ny) not in occupied:
                                engine.set_entity_state(eid, "walking")
                                engine.move_entity(eid, nx, ny)
                                occupied.pop((cx, cy), None)
                                occupied[(nx, ny)] = eid
                                break
                    continue
                chosen["status"] = "in_progress"
                chosen["agent"] = ent.name
                task_of[eid] = chosen["id"]
                paths[eid] = chosen_path[1:]
                engine.set_entity_state(eid, "walking")
                engine.set_entity_thought(eid, "» " + chosen["title"])
                publish()
                continue

            # Arrived → perform the action, then mark the quest done
            if (cx, cy) == task["tile"]:
                act = task["act"]
                state = "casting" if act == "casting" else ("thinking" if act == "guard" else "interact")
                engine.set_entity_state(eid, state)
                _schedule_thought(
                    eid, f"You just finished the task: '{task['title']}'. React briefly.",
                    random.choice(_ACT_LINES.get(act, ["Done."])))
                engine.add_effect("glow" if act != "guard" else "spark", cx, cy, task["fx"], 0.9)
                hold[eid] = 3
                task["status"] = "done"
                task["agent"] = ent.name
                task_of.pop(eid, None)
                paths.pop(eid, None)
                publish()
                continue

            # Walk the path (replanning if it ran out or the next step is blocked)
            def _abandon():
                task["status"] = "open"
                task["agent"] = None
                task_of.pop(eid, None)
                paths.pop(eid, None)
                publish()

            path = paths.get(eid) or []
            if not path:
                p = _astar((cx, cy), task["tile"])
                if p is None:
                    _abandon(); continue            # goal no longer reachable → release it
                paths[eid] = path = p[1:]
            if not path:
                continue
            nx, ny = path[0]
            if (nx, ny) in occupied and occupied[(nx, ny)] != eid:
                p = _astar((cx, cy), task["tile"])  # someone's in the way → reroute
                if p is None:
                    _abandon(); continue
                paths[eid] = p[1:]
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
        # Standalone mode: run all three in asyncio
        async def run_all():
            await asyncio.gather(
                run_ws_server(),
                run_http_server(),
                ambient_life(),
            )

        engine.create_default_dungeon()
        print(f"Dungeon Game Server starting...")
        print(f"  HTTP:     http://localhost:{HTTP_PORT}")
        print(f"  WebSocket: ws://localhost:{WS_PORT}")
        print(f"  Open http://localhost:{HTTP_PORT} in your browser")
        print()
        asyncio.run(run_all())


if __name__ == "__main__":
    main()
