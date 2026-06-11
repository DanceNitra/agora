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
    "artificer": "say what a MINIMAL computational model of it would be and what number it must show",
    "cartographer": "name which DISTANT vault domain this should bridge to, and why the hole matters",
}


async def _pick_collab_seed():
    """Rotate the seed across the real research surface. The FRONTIER (under-explored thin
    domains + structural holes) gets 2 of every 4 slots so research is pushed to the EDGE, not
    the dense centre the agents churn on; findings/gaps/bridges fill the other two."""
    i = _collab_rot["i"] % 4
    _collab_rot["i"] += 1
    try:
        if i in (0, 2):                                   # FRONTIER — priority, novelty by default
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/frontier-seed", 75)
            t = (d or {}).get("target") or {}
            if t.get("target"):
                kind = "frontier-hole" if t.get("kind") == "hole" else "frontier-thin"
                return (kind, t["target"][:80], t.get("prompt", "")[:300])
            # frontier exhausted (everything bridged/developed) → fall through to a finding
        if i == 1:
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/gaps?n=8")
            gs = (d or {}).get("gaps", [])
            if gs:
                g = random.choice(gs)
                return ("gap", g["title"][:80], f"The vault is thin on: {g['title']}")
        if i == 3:
            d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/collective?limit=8")
            ks = [k for k in (d or {}).get("knowledge", []) if (k.get("content") or "")]
            if ks:
                k = random.choice(ks)
                title = (k.get("title") or "a recent finding").replace("Pipeline: ", "").strip()
                return ("finding", title[:80], (k.get("content") or "")[:240])
        # any slot can fall back to a bridge seed if its own source came up empty
        if True:
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
        if not sources or "(no external" in sources:
            sources = await _brain_research(seed_text[:90])    # second angle: the seed text itself
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

_BRAIN_URL = os.environ.get("AGORA_BRAIN_URL", "http://localhost:8000").rstrip("/")
_BRAIN_ID = {   # dungeon entity → server/agora NPC UUID (names already aligned)
    "thief":   "00000000-0000-0000-0000-000000000001",  # Shadow Kael
    "scholar": "00000000-0000-0000-0000-000000000002",  # Sage Mira
    "priest":  "00000000-0000-0000-0000-000000000003",  # High Priest Orin
    "king":    "00000000-0000-0000-0000-000000000004",  # King Aldric
    "guard_r": "00000000-0000-0000-0000-000000000005",  # Dame Elara
    "guard_l": "00000000-0000-0000-0000-000000000007",  # Sergeant Voss
    "artificer": "00000000-0000-0000-0000-000000000008",  # Artificer Rooke
    "cartographer": "00000000-0000-0000-0000-000000000009",  # Cartographer Wren
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


def _brain_post_sync(path: str, body: dict, timeout: int = 4):
    # default 4s for the fast endpoints; pass a longer timeout for slow LLM endpoints.
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
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", text.lower())
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
    pr = (b or {}).get("priorities", "") or ""
    _gate_cache["prio"] = {w for w in _theme_words(pr) if w not in _PRIO_STOP}
    _gate_cache["fetched"] = _time.time()


async def _gate_filter(pool: list[str]) -> list[str]:
    """Drop editorially-refused themes; when board priorities exist and any candidate matches
    them, queue ONLY the on-priority ones (off-priority themes wait their turn)."""
    await _gate_refresh()
    pool = [t for t in pool if not _theme_is_covered(t, _gate_cache["skips"])]
    if _gate_cache["prio"]:
        on = [t for t in pool if _theme_words(t) & _gate_cache["prio"]]
        if on:
            return on
    return pool


_graves_cache: dict = {"epitaphs": [], "fetched": 0.0}
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


async def _brain_graves() -> list[str]:
    """Epitaphs of dead ideas (1h cache) — the planner shows agents where NOT to dig again."""
    if _time.time() - _graves_cache["fetched"] > 3600:
        d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/graveyard")
        _graves_cache["epitaphs"] = (d or {}).get("epitaphs") or []
        _graves_cache["fetched"] = _time.time()
    return _graves_cache["epitaphs"]


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


async def _task_already_pending(prefix: str) -> bool:
    """True when a task of this kind is already waiting in the Claude inbox (for the fixed-text
    daily tasks — a second copy adds nothing, Claude would just editorial-skip it)."""
    inbox = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/claude-inbox")
    return any(t.get("text", "").startswith(prefix) for t in (inbox or {}).get("pending", []))


async def _queue_insight_theme() -> None:
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
    t = (d or {}).get("target")
    if not t:
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
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/hypothesis-inputs", 60)
    theme = (d or {}).get("theme", "")
    if not theme or len((d or {}).get("cluster", [])) < 3:
        return
    covered = await asyncio.to_thread(_covered_note_themes, "hypothesis*.md")
    covered += await _pending_task_themes("Hypothesize from findings:")
    if _theme_is_covered(theme, covered):
        return
    await asyncio.to_thread(_brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
                            {"text": f"Hypothesize from findings: {theme[:90]} || SEVERE-TEST RULE: "
                                     f"the hypothesis must ship WITH a runnable Lab test - run the "
                                     f"baseline via /brain/lab/run in this same task and put the "
                                     f"measured number in the note; no runnable test, no hypothesis"})
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


async def _queue_scout() -> None:
    """THE OPPORTUNITY SCOUT: Shadow Kael hunts an open GitHub issue Agora can answer with
    evidence and queues Claude to judge + draft a GATED outreach reply. Systematizes the
    first public win (answer someone else's open problem with running architecture + numbers).
    Owner-facing trust surface, so ~6h and strictly gated."""
    if await _task_already_pending("Scout outreach"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/scout-target", 30)
    t = (d or {}).get("target") or {}
    if not t.get("url") or t.get("error"):
        return
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Scout outreach: {t['repo']}#{t['issue_number']} (fit {t.get('score')}) || "
                 f"TITLE: {t['title']} || BODY: {t['body'][:500]} || Judge HONESTLY: does Agora's "
                 f"vault genuinely answer this with EVIDENCE (real mechanism + a measured number "
                 f"from our notes/Lab)? If yes, draft a gated outreach comment via POST "
                 f"/brain/correspondent/draft {{title, body, repo: '{t['repo']}', issue_number: "
                 f"{t['issue_number']}}} - helpful, specific, no overselling, mapped to their pain. "
                 f"Then POST /brain/scout-record {{url: '{t['url']}', repo: '{t['repo']}', issue: "
                 f"{t['issue_number']}, outcome}}. If we cannot genuinely help, record outcome "
                 f"'no real fit' and DO NOT draft - reputation dies on a bad pitch."})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Shadow Kael",
               "text": f"scouted an opportunity: {t['repo']}#{t['issue_number']}"})
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
    """THE CARTOGRAPHER: Wren scans the whole knowledge graph for the widest structural hole
    (two substantial domains with the fewest bridges) and queues it for Claude to bridge with
    ONE honest mechanism note — brokerage across holes is where new ideas live. His yield is
    measured later: did bridges actually appear where he pointed?"""
    if await _task_already_pending("Chart structural hole"):
        return
    d = await asyncio.to_thread(_brain_get_sync, "/api/v1/agent-os/brain/cartography-hole", 90)
    h = (d or {}).get("hole") or {}
    if not h.get("a"):
        return
    await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/claude-inbox",
        {"text": f"Chart structural hole: {h['a']} x {h['b']} || bridges now: {h.get('bridges', 0)} "
                 f"|| {h['a']} notes: {', '.join(h.get('a_notes', [])[:3])} || {h['b']} notes: "
                 f"{', '.join(h.get('b_notes', [])[:3])} || Write ONE bridge note connecting the "
                 f"strongest pair via a REAL shared mechanism (not surface similarity), tags "
                 f"['agora','bridge','claude-synthesis'], push; then POST /brain/cartography-record "
                 f"{{a,b,bridges_then,note,outcome}}. If no honest bridge exists, record outcome "
                 f"'no honest bridge' without a note - a charted dead hole is also a map."})
    broadcast({"type": "os_build", "kind": "discovery", "who": "Cartographer Wren",
               "text": f"charted a hole in the map: {h['a'][:22]} × {h['b'][:22]} "
                       f"({h.get('bridges', 0)} bridges)"})
    _mind_spark("#5dade2")        # blue — a hole appears on the map


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
        (Path(__file__).parent / "agent_standing.json").write_text(
            _json.dumps({"standing": by_name, "updated": _time.time()}))
    except Exception:
        pass


_REFUSAL_RE = re.compile(
    r"^\s*(?:i|we)\s+(?:cannot|can't|am\s+unable|are\s+unable|apologi[sz]e|am\s+sorry|notice\s+your)"
    r"|^\s*(?:i'm|we're)\s+(?:sorry|unable)\b"
    r"|^\s*as\s+an\s+ai\b"
    r"|\byour\s+request\s+asks\b"
    r"|\bthe\s+required\s+source\s+is\s+missing\b"
    r"|\bno\s+(?:paper|source)\s+(?:fits|matches|was\s+provided)\b"
    r"|^\s*(?:none|neither)\s+of\s+the\s+provided\b"
    r"|^\s*neither\s+(?:paper|source)s?\b"
    r"|^\s*the\s+provided\s+(?:real\s+)?(?:paper|source|literature)s?[^.\n]{0,40}\b"
    r"(?:do(?:es)?\s+not|don't|doesn't|are\s+unrelated|is\s+unrelated)"
    r"|^\s*(?:i|we)\s+need\s+a\b[^.\n]{0,30}\bsource"
    r"|^\s*you\s+did\s+not\s+provide"
    r"|\bno\s+(?:real\s+|specific\s+)?source[^.\n]{0,40}\b(?:is|was)\s+provided\b"
    r"|\bplease\s+(?:provide|supply)\b[^.\n]{0,40}\bsource",
    re.IGNORECASE)


def _is_refusal(text: str) -> bool:
    """True when the LLM output is a refusal / no-fit meta-statement, not a finding. Shipping
    these as discoveries polluted the vault and the morning report ('I cannot complete this
    task' as a grounded finding) — a non-answer is a wasted slot, never knowledge."""
    return bool(_REFUSAL_RE.search((text or "")[:300]))


async def _brain_contribute(eid: str, title: str, content: str) -> bool:
    if _is_refusal(content) or _is_refusal(title):
        broadcast({"type": "os_build", "kind": "collab", "who": _AGENT_NAMES.get(eid, eid),
                   "text": "discarded a non-finding (refusal/no-fit) — the slot yielded nothing"})
        return False
    r = await asyncio.to_thread(
        _brain_post_sync, "/api/v1/agent-os/brain/collective",
        {"npc": _AGENT_NAMES.get(eid, eid), "title": title[:90],
         "content": content[:600], "knowledge_type": "discovery"})
    return bool(r)


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
    await _refresh_forecast_scores()        # tournament hit-rates feed the standing blend
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
            graves = await _brain_graves()
            grave_txt = ("\nDEAD ENDS (tried, killed — do NOT re-walk these): "
                         + "; ".join(graves[:4])) if graves else ""
            usr = ((("What you know:\n" + brain + "\n\n") if brain else "") +
                   f"The OS so far (build on it, don't repeat): {build_log}\n"
                   f"Modules built (visit/extend them): {mods}\n"
                   f"Fellow thinkers: {allies}\n"
                   f"The user's REAL knowledge GAPS — isolated notes worth developing (AIM HERE): {gap_txt}"
                   f"{grave_txt}\n"
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
        # Insight Engine — Agora queues a rich theme for Claude to synthesize (~95 min, premium).
        if loop_n % 6700 == 1100:
            asyncio.create_task(_queue_insight_theme())
        # Flywheel — queue an insight's falsifier for Claude to re-test + deepen (~80 min).
        if loop_n % 5600 == 1500:
            asyncio.create_task(_queue_deepening())
        # Prediction Ledger — resolve due predictions + queue a new one for Claude (~90 min).
        if loop_n % 6300 == 1500:
            asyncio.create_task(_run_predictions())
        # Dialectic — queue a contentious claim for Claude to stress-test (~80 min, offset).
        if loop_n % 5600 == 400:
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
        # HYPOTHESIS INDUCTION — bridge a finding cluster into a testable conjecture (~95 min).
        if loop_n % 6700 == 2000:
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
        # THE OPPORTUNITY SCOUT — Kael hunts an answerable open GitHub issue (~6h, offset, gated).
        if loop_n % 25000 == 18000:
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
        if loop_n % 7000 == 900:                       # Analogy Forge  (~100 min)
            asyncio.create_task(_queue_analogy_forge())
        if loop_n % 6500 == 1200:                      # Belief revision  (~92 min)
            asyncio.create_task(_queue_belief_challenge())
        if loop_n % 5500 == 2100:                      # The Court — structured debate  (~78 min)
            asyncio.create_task(_run_debate())
        if loop_n % 5500 == 600:                       # Replication Unit (Rooke)  (~78 min)
            asyncio.create_task(_queue_replication())
        if loop_n % 6000 == 1700:                      # Cartographer (Wren)  (~85 min)
            asyncio.create_task(_queue_cartography())
        if loop_n % 6000 == 1100:                      # Kael's Red Team  (~85 min)
            asyncio.create_task(_run_red_team())
        if loop_n % 5000 == 2600:                      # Orin's Synthesis Detector  (~70 min; fires only when due)
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
        # THE WATCHDOG — keep the brain alive (one supervision beat ~every 5 min).
        if loop_n % 220 == 117:
            asyncio.create_task(_watch_brain())

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

                if kind in ("hypothesize", "create"):
                    # ATTENTION MARKET: a discovery slot costs an LLM+research spend —
                    # standing decides who gets to spend (the productive compound).
                    won, p = _market_won(eid)
                    if not won:
                        engine.set_entity_thought(eid, "priced out this round — earn standing")
                        note_event(f"{who} was priced out of the discovery market (p={p:.2f})")
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
