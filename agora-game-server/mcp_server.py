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
                # Health check server
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
