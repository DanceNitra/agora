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

# Pace: "study" = slow & deliberate (default; real research, light on the quota),
# "fast" = lively banter. Override with DUNGEON_PACE.
_PACE = os.environ.get("DUNGEON_PACE", "study").strip().lower()
_STUDY = _PACE != "fast"
_DECIDE_MIN, _DECIDE_MAX = (35.0, 90.0) if _STUDY else (3.0, 7.0)   # gap between an agent's goals
_CONV_COOLDOWN = 120.0 if _STUDY else 30.0                          # gap between an agent's talks

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


def _llm_content_sync(system: str, user: str) -> str | None:
    """Blocking OpenRouter call → raw assistant message content, or None on failure."""
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
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug(f"LLM call failed: {e}")
        return None


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


def _llm_json_sync(system: str, user: str) -> dict | None:
    """OpenRouter call expecting a JSON object → the parsed dict, or None."""
    content = _llm_content_sync(system, user)
    if not content:
        return None
    try:
        obj = json.loads(content)
        return obj if isinstance(obj, dict) else None
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


# ── ESS Trust Bridge ────────────────────────────────────────────
# The dungeon's social interactions feed the REAL server/agora TrustEngine
# (Axelrod TFT: cooperate +, defect −, forgiveness, decay). Conversation →
# cooperate; guards sparring → defect. Scores persist + stream to the client.
import importlib.util as _ilu

_TRUST_DB_PATH = str(HERE / "dungeon_trust.db")
_AGENT_NAMES = {
    "king": "King Aldric", "guard_l": "Sergeant Voss", "guard_r": "Dame Elara",
    "priest": "High Priest Orin", "thief": "Shadow Kael", "scholar": "Sage Mira",
}
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

_BRAIN_URL = os.environ.get("AGORA_BRAIN_URL", "http://localhost:8000").rstrip("/")
_BRAIN_ID = {   # dungeon entity → server/agora NPC UUID (names already aligned)
    "thief":   "00000000-0000-0000-0000-000000000001",  # Shadow Kael
    "scholar": "00000000-0000-0000-0000-000000000002",  # Sage Mira
    "priest":  "00000000-0000-0000-0000-000000000003",  # High Priest Orin
    "king":    "00000000-0000-0000-0000-000000000004",  # King Aldric
    "guard_r": "00000000-0000-0000-0000-000000000005",  # Dame Elara
    "guard_l": "00000000-0000-0000-0000-000000000007",  # Sergeant Voss
}


def _brain_get_sync(path: str):
    try:
        req = _urlreq.Request(_BRAIN_URL + path, headers={"Accept": "application/json"})
        with _urlreq.urlopen(req, timeout=4) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _brain_post_sync(path: str, body: dict):
    try:
        req = _urlreq.Request(_BRAIN_URL + path, data=json.dumps(body).encode(),
                              headers={"Content-Type": "application/json"})
        with _urlreq.urlopen(req, timeout=4) as r:
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


# Each agent's Vault-Company JOB (their purpose). Static → fetched once and cached.
_BRAIN_IDENTITY: dict[str, str] = {}


async def _brain_identity(eid: str) -> str:
    """The agent's real role at the Vault Company — so it knows WHY it's here."""
    if eid in _BRAIN_IDENTITY:
        return _BRAIN_IDENTITY[eid]
    name = _AGENT_NAMES.get(eid, eid)
    d = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/vault-company/agent/{_urlquote(name)}/definition")
    text = ""
    try:
        role = (d or {}).get("definition", {}).get("role", {})
        soul = (d or {}).get("definition", {}).get("soul", {})
        title = role.get("title", "")
        dept = role.get("department", "")
        desc = role.get("description", "")
        motiv = soul.get("motivation", "")
        if title:
            text = (f"Your job at the Vault Company: {title} in {dept}. {desc} "
                    f"Your drive: {motiv}").strip()
    except Exception:
        pass
    if text:  # cache only a real hit (retry next time if the brain was down)
        _BRAIN_IDENTITY[eid] = text
    return text


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


async def _broadcast_trust_graph():
    """One unified graph for the dungeon: ESS pairwise trust + learning (teach) edges."""
    trust = await _trust_matrix()                       # [{a,b,score}]  ESS, live
    learn = await _brain_learning_graph()               # [{from,to,skill}]  who teaches whom
    nodes = [{"eid": e, "name": _AGENT_NAMES.get(e, e)} for e in _AGENT_NAMES]
    broadcast({"type": "trust_graph", "nodes": nodes, "trust": trust, "learn": learn})


async def _brain_contribute(eid: str, title: str, content: str) -> bool:
    r = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/collective",
        {"npc": _AGENT_NAMES.get(eid, eid), "title": title[:90],
         "content": content[:400], "knowledge_type": "discovery"})
    return bool(r)


async def _brain_propose_upgrade(eid: str, title: str, desc: str) -> bool:
    r = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/upgrade",
        {"npc": _AGENT_NAMES.get(eid, eid), "title": title[:90], "description": desc[:400]})
    return bool(r)


_ROLE_HINT = {  # each thinker owns a real research domain
    "king":    "synthesis & governance — turn the group's findings into doctrine and decide what the OS should become",
    "guard_l": "resilience & antifragility — stress-test ideas, find failure modes, harden the system",
    "guard_r": "systems & feedback loops — formalize and structure what others discover",
    "priest":  "meaning, emergence & strange loops — seek the deep 'why' behind a finding",
    "thief":   "incentives, risk & game theory — find the edge or exploit others miss",
    "scholar": "knowledge itself — cross-reference the library and connect distant concepts",
}

# Named destinations the LLM can send an agent to (tile = standing spot).
_LOCATIONS = {k: v["tile"] for k, v in _POSTS.items()}  # throne, treasury, library, ...


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
    goals: dict[str, dict] = {}        # eid -> {intent, tile, action, where}
    memory: dict[str, list] = {}       # eid -> last things this agent did/saw
    next_decide: dict[str, float] = {} # eid -> monotonic time of next decision
    deciding: set[str] = set()         # decisions in flight
    world_events: list[str] = []       # recent keep news (shared, for reactivity)
    locations: dict = dict(_LOCATIONS)  # navigable spots — GROWS as agents build modules
    os_modules: list[dict] = []        # real structures agents have built into the OS
    loop_n = 0
    await _init_trust()
    logger.info("LLM-driven life loop started")

    def remember(eid, text):
        memory.setdefault(eid, []).append(text)
        memory[eid] = memory[eid][-8:]

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
        del os_modules[:-24]
        broadcast({"type": "os_module", **mod})

    def publish_goals():
        engine.set_tasks([
            {"id": i, "title": g["intent"], "agent": _AGENT_NAMES.get(eid, eid),
             "status": "in_progress"}
            for i, (eid, g) in enumerate(goals.items())
        ])

    async def decide_goal(eid, cx, cy):
        """Ask the LLM for this agent's next goal (fire-and-forget)."""
        try:
            ent = engine.state.entities.get(eid)
            if not ent:
                return
            nearby = [_AGENT_NAMES.get(o, o) for o, e in engine.state.entities.items()
                      if o != eid and abs(e.x - cx) + abs(e.y - cy) <= 8]
            locs = ", ".join(locations.keys())
            mem = " | ".join(memory.get(eid, [])[-4:]) or "(nothing yet)"
            news = " | ".join(world_events[-4:]) or "(quiet)"
            # Pull the agent's real mind (memory/emotion/vault) from server/agora.
            brain = await _brain_context(eid, f"{_ROLE_HINT.get(eid, '')} {mem}")
            build_log = await _brain_build_log()
            allies = ", ".join(_AGENT_NAMES[o] for o in _AGENT_NAMES if o != eid)
            mods = "; ".join(m["name"] for m in os_modules[-6:]) or "(none yet)"
            ident = await _brain_identity(eid)
            role_line = ident or f"Your domain: {_ROLE_HINT.get(eid, 'open inquiry')}."
            sysmsg = (
                f"You are {_persona(eid)} {role_line} "
                f"With your colleagues you work at the Vault Company, building a living 'Agentic "
                f"OS' — a growing body of GENUINE knowledge and self-upgrades inside the vault. Do "
                f"REAL work THAT FITS YOUR ROLE: investigate, connect concepts, form hypotheses, "
                f"synthesize findings, or build tools — grounded in your memory and the library. Be "
                f"concrete and SUBSTANTIVE; never vague, never repeat yourself or others; each step "
                f"must ADVANCE the work and build on what's already known. "
                f"Pick: create (a real discovery/insight in your field), upgrade (build a concrete "
                f"module that encodes a finding), collaborate (combine your role with an ally's), or explore. "
                f'Reply ONLY JSON: {{"intent":"<a SPECIFIC goal that fits your role, present tense, max 14 words>",'
                f'"kind":"<collaborate|create|upgrade|explore>",'
                f'"location":"<one of: {locs} | an ally name | wander>",'
                f'"with":"<an ally name if collaborating, else empty>",'
                f'"action":"<the concrete finding or output you produce — one substantive sentence>"}}'
            )
            usr = ((("What you know:\n" + brain + "\n\n") if brain else "") +
                   f"The OS so far (build on it, don't repeat): {build_log}\n"
                   f"Modules built (visit/extend them): {mods}\n"
                   f"Fellow thinkers: {allies}\n"
                   f"Your recent work: {mem}\nNearby now: {', '.join(nearby) or 'no one'}\n"
                   f"Latest in the keep: {news}\nYour next research move:")
            data = await asyncio.to_thread(_llm_json_sync, sysmsg, usr) or {}
            intent = (data.get("intent") or "").strip() or random.choice(
                _THOUGHTS.get(eid, ["wander the keep"]))
            kind = (data.get("kind") or "explore").strip().lower()
            if kind not in ("collaborate", "create", "upgrade", "explore"):
                kind = "explore"
            where = (data.get("location") or "wander").strip().lower()
            action = (data.get("action") or "...").strip()
            with_name = (data.get("with") or "").strip()

            # Resolve destination → tile
            tile = None
            if where in locations:
                tile = locations[where]
            else:  # maybe an ally's name?
                for oid, nm in _AGENT_NAMES.items():
                    if oid != eid and nm.split()[-1].lower() in where:
                        o = engine.state.entities.get(oid)
                        if o:
                            tile = (int(round(o.x)), int(round(o.y)))
                        break
            if tile is None or not _walkable(*tile):  # wander → random reachable spot
                tile = random.choice(list(locations.values()))
            goals[eid] = {"intent": intent, "tile": tile, "action": action, "where": where,
                          "kind": kind, "with": with_name}
            paths.pop(eid, None)  # fresh goal → fresh path
            engine.set_entity_thought(eid, "» " + intent[:90])
            engine.set_entity_state(eid, "walking")
            publish_goals()
        except Exception as e:
            logger.debug(f"decide_goal {eid}: {e}")
            goals[eid] = {"intent": "wander the keep", "where": "wander", "action": "...",
                          "tile": random.choice(list(locations.values()))}
        finally:
            deciding.discard(eid)

    while True:
        await asyncio.sleep(0.85)
        ents = engine.state.entities
        occupied = {(int(round(e.x)), int(round(e.y))): eid for eid, e in ents.items()}
        now = _time.monotonic()
        for eid in list(ents.keys()):
            hold[eid] = max(0, hold.get(eid, 0) - 1)
            cooldown[eid] = max(0, cooldown.get(eid, 0) - 1)

        # Agents that wander near each other strike up a conversation.
        _maybe_start_conversation(ents, dead, hold)

        loop_n += 1
        if loop_n % 18 == 1:
            _m = await _trust_matrix()
            if _m:
                broadcast({"type": "trust_snapshot", "matrix": _m, "names": _AGENT_NAMES})
            await _broadcast_trust_graph()          # ESS trust + cross-agent learning
            broadcast({"type": "os_snapshot", "log": os_log[-12:]})
            if os_modules:
                broadcast({"type": "os_modules_snapshot", "modules": os_modules})

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

            # No goal → ask the LLM (throttled, one decision in flight per agent)
            if goal is None:
                if eid not in deciding and now >= next_decide.get(eid, 0.0):
                    deciding.add(eid)
                    asyncio.create_task(decide_goal(eid, cx, cy))
                continue

            # Arrived → act on the goal's KIND; create/upgrade/collaborate make real
            # artifacts in the shared brain. Everything is remembered.
            if (cx, cy) == goal["tile"]:
                kind = goal.get("kind", "explore")
                intent, action = goal["intent"], goal["action"]
                who = _AGENT_NAMES.get(eid, eid)
                engine.set_entity_state(eid, "casting" if kind in ("create", "upgrade") else "interact")
                engine.set_entity_thought(eid, action[:100])
                engine.add_effect("glow", cx, cy,
                                  "#7fd0ff" if kind == "create" else
                                  "#ffcf5a" if kind == "upgrade" else "#ffd27a", 0.9)
                remember(eid, intent)

                if kind == "create":
                    asyncio.create_task(_brain_contribute(eid, intent, action))
                    note_event(f"{who} discovered: {intent}")
                    _os_build("discovery", who, intent)
                elif kind == "upgrade":
                    asyncio.create_task(_brain_propose_upgrade(eid, intent, action))
                    _apply_module(intent, (cx, cy), who, "upgrade")  # REALLY build it
                    note_event(f"{who} built: {intent}")
                    _os_build("upgrade", who, intent)
                elif kind == "collaborate":
                    pid = next((oid for oid, e2 in ents.items()
                                if oid != eid and abs(e2.x - cx) + abs(e2.y - cy) <= 2), None)
                    if pid:
                        await record_trust(eid, pid, "cooperate")
                        partner = _AGENT_NAMES.get(pid, pid)
                        asyncio.create_task(
                            _brain_contribute(eid, f"{intent} (with {partner})", action))
                        note_event(f"{who} & {partner}: {intent}")
                        _os_build("collab", f"{who} + {partner}", intent)
                    else:
                        note_event(f"{who}: {intent}")
                else:
                    note_event(f"{who}: {intent}")

                asyncio.create_task(_brain_remember(eid, f"{intent} — {action}"))
                hold[eid] = 3
                goals.pop(eid, None)
                paths.pop(eid, None)
                next_decide[eid] = now + random.uniform(_DECIDE_MIN, _DECIDE_MAX)
                publish_goals()
                continue

            # Walk toward the goal (replan if blocked)
            path = paths.get(eid) or []
            if not path:
                p = _astar((cx, cy), goal["tile"])
                if p is None:
                    goals.pop(eid, None)        # unreachable → pick a new goal soon
                    next_decide[eid] = now + 1.0
                    continue
                paths[eid] = path = p[1:]
            if not path:
                goals.pop(eid, None)
                continue
            nx, ny = path[0]
            if (nx, ny) in occupied and occupied[(nx, ny)] != eid:
                p = _astar((cx, cy), goal["tile"])
                if p is None:
                    goals.pop(eid, None); paths.pop(eid, None)
                    continue
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
