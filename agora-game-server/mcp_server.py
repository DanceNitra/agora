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
_DECIDE_MIN, _DECIDE_MAX = (20.0, 45.0) if _STUDY else (3.0, 7.0)   # gap before PLANNING new goals
_BACKLOG_MIN, _BACKLOG_MAX = (4.0, 9.0)                             # gap to pull the NEXT queued quest
_CONV_COOLDOWN = 120.0 if _STUDY else 30.0                          # gap between an agent's talks

_PERSONA = {
    "king":    "King Aldric — the keep's engineer-king who builds the tools and turns findings into doctrine. Commanding, decisive.",
    "guard_l": "Sergeant Voss — the keep's quality gate. Blunt, rigorous; stress-tests every claim before it ships.",
    "guard_r": "Dame Elara — the keep's bridge-builder. Sharp, dry-witted; finds the links between ideas others miss.",
    "priest":  "High Priest Orin — the idea alchemist. Solemn, cryptic; fuses distant concepts into new ones.",
    "thief":   "Shadow Kael — the frontier scout. Sly, quick, curious; hunts the gaps in the vault no one else sees.",
    "scholar": "Sage Mira — the obsessive archivist. Precise; structures raw research into evergreen knowledge.",
}

# Per-agent throttles (monotonic timestamps) + in-conversation guard.
_speech_cd: dict[str, float] = {}
_conv_cd: dict[str, float] = {}
_in_conv: set[str] = set()
_in_conv_seen: dict[str, float] = {}   # eid -> when it entered _in_conv (watchdog against leaks)


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
            broadcast({"type": "converse", "from": sid, "to": oid})
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
_COLLAB_COOLDOWN = 80

# what each role best CONTRIBUTES when joining another agent's work
_ROLE_CONTRIB = {
    "thief":   "scout sharper evidence and adjacent frontier work",
    "scholar": "curate it into one crisp, structured claim",
    "priest":  "connect it across domains into a novel idea",
    "king":    "turn it into something buildable — an experiment or a tool",
    "guard_r": "find what in the vault it should link to",
    "guard_l": "stress-test it — name the weakest assumption or the hole",
}


async def _pick_collab_seed():
    """Rotate the seed across the real research surface (findings / gaps / bridges) so topics vary."""
    i = _collab_rot["i"] % 3
    _collab_rot["i"] += 1
    try:
        if i == 0:
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=8")
            ks = [k for k in (d or {}).get("knowledge", []) if (k.get("content") or "")]
            if ks:
                k = random.choice(ks)
                title = (k.get("title") or "a recent finding").replace("Pipeline: ", "").strip()
                return ("finding", title[:80], (k.get("content") or "")[:240])
        elif i == 1:
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/gaps?n=8")
            gs = (d or {}).get("gaps", [])
            if gs:
                g = random.choice(gs)
                return ("gap", g["title"][:80], f"The vault is thin on: {g['title']}")
        else:
            d = await asyncio.to_thread(
                _brain_get_sync, "/api/v1/agent-os/brain/bridges?n=4&rationale=false")
            bs = (d or {}).get("bridges", [])
            if bs:
                b = random.choice(bs)
                return ("bridge", f"{b['a']} ↔ {b['b']}"[:80],
                        f"Two related but unlinked ideas to fuse: {b['a']} and {b['b']}")
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
        a_line = await _llm_say(
            f"You are {_persona(a_id)} You and your colleague {bn} are co-working a {seed_kind}.",
            f"The {seed_kind}: '{seed_text}'. In ONE line (max 18 words), tell {bn} what it is "
            f"and exactly what you need from them.",
            f"{bn}, let's develop {seed_title} together.")
        engine.set_entity_thought(a_id, a_line)
        broadcast({"type": "converse", "from": a_id, "to": b_id})
        await asyncio.sleep(2.4)
        contrib = _ROLE_CONTRIB.get(b_id, "add your angle")
        b_line = await _llm_say(
            f"You are {_persona(b_id)} Your colleague {an} brought you a {seed_kind} to work on.",
            f"It is: '{seed_text}'. Your job: {contrib}. Real sources: {sources[:400]}. "
            f"In ONE line (max 20 words), give your concrete contribution.",
            f"Here is my angle on {seed_title}.")
        engine.set_entity_thought(b_id, b_line)
        broadcast({"type": "converse", "from": b_id, "to": a_id})
        await asyncio.sleep(2.4)
        joint = await asyncio.to_thread(
            _llm_content_sync,
            f"Combine {an} and {bn}'s exchange into ONE joint FINDING (2 sentences) that a specific "
            f"source below DIRECTLY supports — paraphrase that paper's actual result and name it "
            f"(Author Year). Stay close to the evidence; do NOT over-generalize. NEVER invent sources.",
            f"Seed ({seed_kind}): {seed_text}\n{an}: {a_line}\n{bn}: {b_line}\n\nReal sources:\n{sources}")
        if joint and joint.strip():
            src = ""
            if sources and "(no external" not in sources:
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
_PIPELINE_STAGES = [
    ("thief",   "scout",    "Scout the frontier and state the core claim, citing a real source."),
    ("priest",  "connect",  "Add ONE novel cross-domain connection or reframing."),
    ("scholar", "curate",   "Curate it into one crisp, well-structured claim."),
    ("guard_r", "link",     "Name which of the user's vault ideas this should connect to."),
    ("guard_l", "validate", "Stress-test it: name the weakest assumption, or say it holds and why."),
    ("king",    "commit",   "Synthesize the whole chain into the final, concrete finding."),
]
_pipeline = {"item": None, "busy": False}


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
                await _brain_contribute("king", f"Pipeline: {item['title']}",
                                        final.strip()[:430] + src)
                broadcast({"type": "os_build", "kind": "collab", "who": " → ".join(item["by"]),
                           "text": f"shipped: {item['title'][:40]}"})
            stages = [s[0] for s in _PIPELINE_STAGES]   # consecutive handoffs build trust
            for x in range(len(stages) - 1):
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


def _brain_get_sync(path: str, timeout: int = 4):
    # default 4s for the fast endpoints; pass a longer timeout for slow LLM endpoints
    # (hypothesize, empirical-test) which otherwise always time out -> None.
    try:
        req = _urlreq.Request(_BRAIN_URL + path, headers={"Accept": "application/json"})
        with _urlreq.urlopen(req, timeout=timeout) as r:
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


_recent_intents: list = []   # recently-issued quest intents, to avoid repetition (self-upgrade #1)

_QUEST_PREFIX_RE = re.compile(
    r"^(?:Hypothesize on|Pursue direction|Deepen|Develop the gap|Connect|Frontier|Hypothesis|Pipeline)"
    r"\s*:?\s*", re.I)


def _strip_quest_prefix(title: str) -> str:
    """Peel any stacked quest/finding prefix so new intents don't nest into garbage like
    'Hypothesize on: Hypothesize on: Pursue direction: ...' (wastes LLM calls + pollutes titles)."""
    t = (title or "").strip()
    for _ in range(4):
        new = _QUEST_PREFIX_RE.sub("", t).strip()
        if new == t:
            break
        t = new
    return t


async def _renewable_quests(eid: str, want: int = 3) -> list:
    """A GUARANTEED, inexhaustible supply of real work drawn from the vault's surface — gaps to
    develop, bridges to connect, findings to deepen. The vault always has these, so agents NEVER
    run out of meaningful tasks (the flaky LLM planner becomes just a bonus, not a dependency)."""
    pool, priority = [], []
    try:
        # COMPOUNDING FLYWHEEL first — the agents test the FALSIFIERS of Agora's own insights (its
        # claims' weak points), so the system's outputs become its next research + knowledge deepens.
        fw = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=3")
        for q in (fw or {}).get("open", []):
            priority.append((f"Test Agora's claim: {q['question'][:55]}",
                             f"Find real evidence on whether this holds: {q['question']}", "hypothesize"))
        # HARVESTED DIRECTIONS next (priority) — so research follows the synthesis and COMPOUNDS.
        dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
        for d in (dd or {}).get("directions", []):
            if d.get("kind") == "research":          # upgrade-directions go to the user, not agents
                priority.append((f"Pursue direction: {d['title']}",
                                 f"Advance this with real evidence — {d.get('why', '')}"))
        gaps = await _brain_gaps()
        for g in random.sample(gaps, min(3, len(gaps))):
            pool.append((f"Develop the gap: {g['title']}",
                         f"Find real evidence to develop '{g['title']}'"))
        bd = await asyncio.to_thread(
            _brain_get_sync, "/api/v1/agent-os/brain/bridges?n=5&rationale=false")
        for b in (bd or {}).get("bridges", [])[:3]:
            pool.append((f"Connect {b['a']} <-> {b['b']}",
                         f"Ground how {b['a']} relates to {b['b']}, citing a real paper"))
        fd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=8")
        finds = [k for k in (fd or {}).get("knowledge", []) if (k.get("content") or "")]
        for k in random.sample(finds, min(3, len(finds))):
            # findings → HYPOTHESIZE quests: form + test a new hypothesis that deepens the finding
            # (the self-deepening engine — each finding raises the next testable question).
            topic = _strip_quest_prefix(k.get("title") or "")[:55]
            if not topic:
                continue
            pool.append((f"Hypothesize on: {topic}",
                         "Form + test a new hypothesis that deepens this finding", "hypothesize"))
    except Exception as e:
        logger.debug(f"renewable_quests {eid}: {e}")
    random.shuffle(pool)
    combined = priority + pool                        # directions first, then the renewable surface
    # SELF-UPGRADE #1: don't re-pursue a topic done recently — avoid the repetition the OS fell into.
    fresh = [x for x in combined if x[0] not in _recent_intents]
    chosen = (fresh or combined)[:want]
    for x in chosen:
        _recent_intents.append(x[0])
        del _recent_intents[:-50]
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
    """Each agent's reputation (0..1) = average pairwise ESS trust. This is the curation
    authority: high standing → that agent's curation auto-applies to the vault."""
    acc = {e: [] for e in _AGENT_NAMES}
    for p in trust:
        if p["a"] in acc:
            acc[p["a"]].append(p["score"])
        if p["b"] in acc:
            acc[p["b"]].append(p["score"])
    return {e: round(sum(v) / len(v), 3) if v else 0.5 for e, v in acc.items()}


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
    d = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/promote-findings?n=3", {})
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
    fd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=12")
    finds = [k for k in (fd or {}).get("knowledge", [])
             if len(k.get("content") or "") > 120 and not (k.get("title") or "").startswith("Reality:")]
    if not finds:
        return
    k = random.choice(finds)
    body = (k.get("content") or "").split("Source:")[0].strip()
    claim = re.split(r"(?<=[.!?])\s", body)[0][:160]     # the finding's first sentence = its claim
    if len(claim) < 25:
        return
    d = await asyncio.to_thread(
        _brain_get_sync, f"/api/v1/agent-os/brain/empirical-test?q={_urlquote(claim)}", 90)
    verdict = (d or {}).get("verdict")
    if not verdict or verdict == "INSUFFICIENT":
        return                                            # no signal at all → don't pollute
    mode = "real-world traction" if (d or {}).get("mode") == "traction" else "empirical"
    content = (f"Reality check ({verdict}): {claim} — {d.get('evidence', '')} "
               f"[{mode}, via {d.get('source')}]")
    await _brain_contribute("priest", f"Reality: {claim[:60]}", content[:430])
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"reality-tested a finding: {verdict} (vs {d.get('source')})"})


async def _queue_insight_theme() -> None:
    """Insight Engine workflow: Agora GATHERS + QUEUES a rich theme; Claude Opus SYNTHESIZES it when
    active (the flash model is too weak for the synthesis). Picks a theme from the user's harvest
    directions / real gaps and drops it in the Claude inbox as 'Synthesize insight: <theme>'."""
    dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
    pool = [d["title"] for d in (dd or {}).get("directions", []) if d.get("title")]
    pool += [g["title"] for g in (await _brain_gaps())]
    if not pool:
        return
    theme = random.choice(pool)
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Synthesize insight: {theme}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"queued a theme for Claude to synthesize: {theme[:40]}"})


async def _queue_deepening() -> None:
    """Compounding Flywheel (second half): queue an insight's falsifier for Claude to RE-TEST against
    the fresh evidence and DEEPEN the insight — outputs come back as sharper outputs, knowledge deepens."""
    fw = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=5")
    qs = (fw or {}).get("open", [])
    if not qs:
        return
    q = random.choice(qs)
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Deepen insight [{q['id']}]: {q.get('origin', '')} || falsifier: {q['question']}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "High Priest Orin",
               "text": f"queued an insight to deepen (flywheel): {q.get('origin', '')[:30]}"})


async def _run_predictions() -> None:
    """The Accountable Mind: resolve any DUE predictions against current reality (score), then record
    a NEW falsifiable prediction on a current theme. Over time this builds Agora's track record."""
    res = await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/resolve-predictions", {})
    n = (res or {}).get("resolved", 0)
    if n:
        broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
                   "text": f"resolved {n} prediction(s) against reality"})
    # Queue a NEW prediction for CLAUDE to make (reasoned, high-quality — the flash forecast is weak).
    dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
    pool = [d["title"] for d in (dd or {}).get("directions", []) if d.get("title")]
    pool += [g["title"] for g in (await _brain_gaps())]
    if pool:
        theme = _strip_quest_prefix(random.choice(pool))
        await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                                {"text": f"Predict: {theme[:80]}"})
        broadcast({"type": "os_build", "kind": "collab", "who": "Shadow Kael",
                   "text": f"queued a prediction for Claude: {theme[:35]}"})


async def _queue_dialectic() -> None:
    """Queue a contentious claim for CLAUDE to run the dialectic on (quality thesis/antithesis/
    synthesis — the flash version is weak). Picks a flywheel falsifier or a harvest direction."""
    fw = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/flywheel/questions?n=4")
    claims = [q["question"] for q in (fw or {}).get("open", [])]
    if not claims:
        dd = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/directions/current")
        claims = [d["title"] for d in (dd or {}).get("directions", []) if d.get("title")]
    if not claims:
        return
    claim = random.choice(claims)
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Dialectic: {claim[:120]}"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
               "text": f"queued a claim for Claude to stress-test (dialectic): {claim[:30]}"})


async def _queue_mind_reflection() -> None:
    """THE AGORA MIND: queue a metacognitive reflection for Claude — synthesize the worldview from
    Agora's full cognitive state and decide what to think about next. The toolbox becomes a mind."""
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Reflect: state of mind"})
    broadcast({"type": "os_build", "kind": "collab", "who": "King Aldric",
               "text": "queued a metacognitive reflection for Claude (the Agora Mind)"})


async def _queue_learning() -> None:
    """THE LEARNING LOOP: queue a review of Agora's own track record for Claude to derive applied
    lessons (what works, what to change) that feed back into future judgments. Agora improves itself."""
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/resolve-predictions", {})
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": "Learn from outcomes"})
    broadcast({"type": "os_build", "kind": "collab", "who": "Sergeant Voss",
               "text": "queued a track-record review for Claude (the Learning Loop)"})


async def _broadcast_trust_graph():
    """One unified graph for the dungeon: ESS pairwise trust + learning (teach) edges +
    each agent's standing — persisted so the trust-weighted curator (AutoLinker) can read it."""
    trust = await _trust_matrix()                       # [{a,b,score}]  ESS, live
    learn = await _brain_learning_graph()               # [{from,to,skill}]  who teaches whom
    standing = _compute_standing(trust)                 # eid -> 0..1
    nodes = [{"eid": e, "name": _AGENT_NAMES.get(e, e), "standing": standing.get(e, 0.5)}
             for e in _AGENT_NAMES]
    broadcast({"type": "trust_graph", "nodes": nodes, "trust": trust, "learn": learn})
    try:
        import json as _json
        by_name = {_AGENT_NAMES[e]: standing.get(e, 0.5) for e in _AGENT_NAMES}
        (Path(__file__).parent / "agent_standing.json").write_text(
            _json.dumps({"standing": by_name, "updated": _time.time()}))
    except Exception:
        pass


async def _brain_contribute(eid: str, title: str, content: str) -> bool:
    r = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/collective",
        {"npc": _AGENT_NAMES.get(eid, eid), "title": title[:90],
         "content": content[:600], "knowledge_type": "discovery"})
    return bool(r)


async def _grounded_discovery(eid: str, intent: str) -> None:
    """Turn a 'create' goal into a REAL finding grounded in arXiv AND connected to the user's
    own notes (or flagging a real gap) — a concrete claim, not a vague plan."""
    sources = await _brain_research(intent)
    related = await _brain_vault_search(intent)
    rel = "; ".join(f"[[{r['title']}]]" for r in related[:3] if r.get("score", 0) > 0.45) \
        or "(the user's vault is thin on this — a real gap)"
    finding = await asyncio.to_thread(
        _llm_content_sync,
        f"You are {_persona(eid)} State ONE research FINDING that a specific paper below DIRECTLY "
        f"supports: paraphrase that paper's actual result and name it (Author Year). Stay close to "
        f"what the source literally shows — do NOT extrapolate or synthesize beyond it. Then, if apt, "
        f"link the user's notes. If no paper fits, say so plainly. Max 2 sentences. NEVER invent sources.",
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
    goals: dict[str, dict] = {}        # eid -> the ACTIVE quest {intent, tile, action, where}
    quests: dict[str, list] = {}       # eid -> backlog of upcoming quests (the quest log)
    quest_log: dict[str, list] = {}    # eid -> recently COMPLETED quest titles (for the board)
    quest_done: dict[str, int] = {}    # eid -> total quests completed
    memory: dict[str, list] = {}       # eid -> last things this agent did/saw
    next_decide: dict[str, float] = {} # eid -> monotonic time of next decision
    deciding: set[str] = set()         # decisions in flight (quest replenishment)
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
                try:
                    return int(text.split(after, 1)[1].split(before)[0].strip())
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
                    _os_build("curation", curator, f"connected {n} vault notes (trust {standing:.2f})")
                    e2 = engine.state.entities.get(eid)
                    if e2:
                        engine.add_effect("glow", int(round(e2.x)), int(round(e2.y)), "#9fe0ff", 1.3)
                    logger.info(f"[curation] {curator} applied {n} links (standing {standing:.2f})")
                else:
                    logger.info(f"[curation] {curator} — vault graph already well-connected")
        except Exception as e:
            logger.warning(f"[curation] {eid} failed: {e!r}")
        finally:
            curation["running"] = False
            engine.set_entity_state(eid, "idle")
            engine.set_entity_thought(eid, "")

    consolidation = {"running": False, "seen": set()}

    async def _run_consolidation(eid, standing):
        """Sage Mira consolidates the agents' live discoveries into a real vault note —
        so live research reaches the vault (then Elara links it). Gated by her standing."""
        if consolidation["running"]:
            return
        consolidation["running"] = True
        curator = _AGENT_NAMES.get(eid, eid)
        try:
            if standing < 0.55:
                note_event(f"{curator}'s consolidation held for review (trust {standing:.2f})")
                return
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

    async def _run_orchestration(eid, standing):
        """King Aldric (Orchestrator) sets the 'State of the OS' doctrine and commits the
        agents' accumulated vault work to GitHub (durability). Gated by his standing."""
        if orchestration["running"]:
            return
        orchestration["running"] = True
        king = _AGENT_NAMES.get(eid, eid)
        logger.info(f"[orchestration] starting for {king} (standing {standing:.2f})…")
        try:
            if standing < 0.55:
                note_event(f"{king}'s governance held (trust {standing:.2f})")
                return
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
                rows.append({"id": i, "title": g["intent"], "agent": tag, "status": "in_progress"})
                i += 1
            for q in quests.get(eid, [])[:2]:        # show up to 2 upcoming quests
                rows.append({"id": i, "title": q["intent"], "agent": who, "status": "open"})
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
        """Pop the next quest from the backlog into the active slot and route to it."""
        q = quests.get(eid)
        if not q:
            return False
        nxt = q.pop(0)
        goals[eid] = {**nxt, "tile": _resolve_tile(eid, nxt.get("where", "wander"))}
        paths.pop(eid, None)
        engine.set_entity_thought(eid, "» " + nxt["intent"][:90])
        engine.set_entity_state(eid, "walking")
        publish_goals()
        return True

    async def replenish_quests(eid, cx, cy):
        """Ask the LLM for a BATCH of real, vault-grounded quests → the agent's backlog."""
        try:
            ent = engine.state.entities.get(eid)
            if not ent:
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
            nearby = [_AGENT_NAMES.get(o, o) for o, e in engine.state.entities.items()
                      if o != eid and abs(e.x - cx) + abs(e.y - cy) <= 8]
            locs = ", ".join(locations.keys())
            mem = " | ".join(memory.get(eid, [])[-4:]) or "(nothing yet)"
            done = " | ".join(quest_log.get(eid, [])[-6:]) or "(none yet)"
            news = " | ".join(world_events[-4:]) or "(quiet)"
            # Pull the agent's real mind (memory/emotion/vault) from server/agora.
            brain = await _brain_context(eid, f"{_ROLE_HINT.get(eid, '')} {mem}")
            build_log = await _brain_build_log()
            allies = ", ".join(_AGENT_NAMES[o] for o in _AGENT_NAMES if o != eid)
            mods = "; ".join(m["name"] for m in os_modules[-6:]) or "(none yet)"
            # The user's REAL knowledge gaps — aim research at what they actually lack.
            _gaps = await _brain_gaps()
            gap_txt = "; ".join(g["title"] for g in random.sample(_gaps, min(4, len(_gaps)))) \
                if _gaps else "(unknown)"
            ident = await _brain_identity(eid)
            role_line = ident or f"Your domain: {_ROLE_HINT.get(eid, 'open inquiry')}."
            sysmsg = (
                f"You are {_persona(eid)} {role_line} "
                f"You work at the Vault Company, building a living 'Agentic OS' of GENUINE knowledge "
                f"inside the vault. PLAN YOUR NEXT 3 RESEARCH MOVES as a quest list. Each must be a "
                f"SPECIFIC, substantive step that fits your role, draws on your memory + the library, "
                f"builds on the OS so far, and does NOT repeat what you've already done. Vary the kinds. "
                f"This is a RESEARCH keep, not a combat dungeon — NEVER invent traps, treasure, "
                f"prisoners, guards, gates, or defenses; only real knowledge work (concepts, notes, "
                f"connections, tools, experiments). A 'module' is a knowledge artifact, not a trap. "
                f"kind: create (a discovery) | upgrade (build a knowledge module) | collaborate (with an "
                f"ally, builds trust) | challenge (contest an ally's weak finding, costs trust) | explore. "
                f'Reply ONLY JSON: {{"quests":[{{"intent":"<specific, present tense, max 14 words>",'
                f'"kind":"<create|upgrade|collaborate|challenge|explore>",'
                f'"location":"<one of: {locs} | an ally name | wander>",'
                f'"with":"<ally name if collaborating/challenging, else empty>",'
                f'"action":"<the concrete output you will produce — one sentence>"}}]}}  (exactly 3 quests)'
            )
            usr = ((("What you know:\n" + brain + "\n\n") if brain else "") +
                   f"The OS so far (build on it, don't repeat): {build_log}\n"
                   f"Modules built (visit/extend them): {mods}\n"
                   f"Fellow thinkers: {allies}\n"
                   f"The user's REAL knowledge GAPS — isolated notes worth developing (AIM HERE): {gap_txt}\n"
                   f"Your recent work: {mem}\nAlready completed (do NOT repeat): {done}\n"
                   f"Nearby now: {', '.join(nearby) or 'no one'}\nLatest in the keep: {news}\n"
                   f"Your quest log (3 next moves — prefer ones that DEVELOP a real gap above):")
            data = await asyncio.to_thread(_llm_json_sync, sysmsg, usr) or {}
            added = 0
            for q in (data.get("quests") or [])[:4]:
                intent = (q.get("intent") or "").strip()
                if not intent:
                    continue
                kind = (q.get("kind") or "explore").strip().lower()
                if kind not in ("collaborate", "challenge", "create", "upgrade", "explore"):
                    kind = "explore"
                quests.setdefault(eid, []).append({
                    "intent": intent, "kind": kind,
                    "where": (q.get("location") or "wander").strip().lower(),
                    "action": (q.get("action") or "...").strip(),
                    "with": (q.get("with") or "").strip()})
                added += 1
            # GUARANTEE work: if the (flaky) LLM planner came up short, draw REAL quests from the
            # vault's inexhaustible surface — gaps, bridges, findings. Agents never run dry.
            if len(quests.get(eid, [])) < 2:
                for q in await _renewable_quests(eid, 3):
                    quests.setdefault(eid, []).append(q)
            if quests.get(eid):
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

    while True:
        await asyncio.sleep(0.85)
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

        # Agents that wander near each other talk shop about their research.
        _maybe_start_conversation(ents, dead, hold, memory)

        loop_n += 1
        # Meaningful collaboration: a varied pair co-produces a real grounded finding from a
        # rotating seed (recent finding / gap / bridge) — the OS actually doing work.
        if loop_n % 45 == 20:
            asyncio.create_task(_maybe_collaborate(hold))
        # Orchestrated pipeline: advance one stage of Aldric's assembly line (one role at a time).
        if loop_n % 9 == 4:
            asyncio.create_task(_pipeline_tick(hold))
        if loop_n % 10 == 1:
            _m = await _trust_matrix()
            if _m:
                broadcast({"type": "trust_snapshot", "matrix": _m, "names": _AGENT_NAMES})
            await _broadcast_trust_graph()          # ESS trust + cross-agent learning
            broadcast({"type": "os_snapshot", "log": os_log[-12:]})
            if os_modules:
                broadcast({"type": "os_modules_snapshot", "modules": os_modules})

        # Reputation decay: nudge all trust toward baseline so standing stays DYNAMIC —
        # bonds you don't reinforce fade, so curation authority genuinely shifts over time.
        if loop_n % 40 == 20 and _trust_engine:
            await _trust_engine.apply_decay(0.02)

        # Autonomous curation: Dame Elara (Bridge Builder) tends the vault's links and
        # Sage Mira (Curator) consolidates live discoveries into vault notes — each gated
        # by their OWN standing, on offset cadences.
        if (loop_n % 70 == 7 or loop_n % 110 == 50 or loop_n % 130 == 90
                or loop_n % 17000 == 300):
            _stm = _compute_standing(await _trust_matrix())
            if loop_n % 70 == 7 and not curation["running"]:        # Elara: connect links
                asyncio.create_task(_run_curation("guard_r", _stm.get("guard_r", 0.5)))
            if loop_n % 130 == 90 and not curation["running"]:      # Voss: QA flag duplicates
                asyncio.create_task(_run_curation("guard_l", _stm.get("guard_l", 0.5), "duplicates"))
            if loop_n % 110 == 50 and not consolidation["running"]:  # Mira: consolidate digest
                asyncio.create_task(_run_consolidation("scholar", _stm.get("scholar", 0.5)))
            if loop_n % 17000 == 300 and not orchestration["running"]:  # Aldric: doctrine + GitHub (~4 h)
                asyncio.create_task(_run_orchestration("king", _stm.get("king", 0.5)))

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
        if loop_n % 1500 == 700:
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
        # Insight Engine — Agora queues a rich theme for Claude Opus to synthesize (~3 h, premium).
        if loop_n % 13000 == 1100:
            asyncio.create_task(_queue_insight_theme())
        # Flywheel — queue an insight's falsifier for Claude to re-test + deepen (~4 h, offset).
        if loop_n % 17000 == 9000:
            asyncio.create_task(_queue_deepening())
        # Prediction Ledger — resolve due predictions vs reality + queue a new one for Claude (~2 h).
        if loop_n % 9000 == 2500:
            asyncio.create_task(_run_predictions())
        # Dialectic — queue a contentious claim for Claude to stress-test (~5 h, offset).
        if loop_n % 19000 == 7000:
            asyncio.create_task(_queue_dialectic())
        # The Agora Mind — metacognitive reflection: synthesize the worldview + self-direct (~daily).
        if loop_n % 64000 == 33000:
            asyncio.create_task(_queue_mind_reflection())
        # The Learning Loop — review the track record + derive applied lessons (~daily, offset).
        if loop_n % 64000 == 9000:
            asyncio.create_task(_queue_learning())

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
                        asyncio.create_task(replenish_quests(eid, cx, cy))
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
                                  "#ffcf5a" if kind == "upgrade" else
                                  "#ff6a6a" if kind == "challenge" else "#ffd27a", 0.9)
                remember(eid, intent)

                if kind == "hypothesize":
                    asyncio.create_task(_hypothesis_discovery(eid, intent))
                    note_event(f"{who} forms a hypothesis: {intent}")
                    _os_build("discovery", who, intent)
                elif kind == "create":
                    asyncio.create_task(_grounded_discovery(eid, intent))
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
                elif kind == "challenge":
                    # An intellectual dispute: contest a weak/contradictory finding → trust down.
                    pid = next((oid for oid, e2 in ents.items()
                                if oid != eid and abs(e2.x - cx) + abs(e2.y - cy) <= 2), None)
                    if pid:
                        await record_trust(eid, pid, "defect")   # standing of both can shift
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
                hold[eid] = 3
                goals.pop(eid, None)
                paths.pop(eid, None)
                # Work through the backlog promptly; only pause for the study gap before planning anew.
                next_decide[eid] = now + (random.uniform(_BACKLOG_MIN, _BACKLOG_MAX)
                                          if quests.get(eid) else random.uniform(_DECIDE_MIN, _DECIDE_MAX))
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
