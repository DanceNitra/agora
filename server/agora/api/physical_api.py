"""Physical World API — NPC positions, movement, library queries."""
from fastapi import APIRouter, Request, HTTPException
from agora.agent_os.dungeon_map import get_room_at
from agora.api.dungeon import DUNGEON_AGENT_IDS

UUID_TO_NAME = {v: k for k, v in DUNGEON_AGENT_IDS.items()}

router = APIRouter(prefix="/api/v1/physical", tags=["physical"])


@router.get("/npcs")
async def get_npc_positions(request: Request):
    """Get all NPC positions and their current room."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT npc_id, npc_name, role, pos_x, pos_y, health, status FROM dungeon_npcs WHERE status='active' ORDER BY npc_name"
    )
    npcs = []
    for row in await cursor.fetchall():
        d = dict(row)
        d["room"] = get_room_at(d["pos_x"], d["pos_y"])
        npcs.append(d)
    return {"npcs": npcs, "total": len(npcs)}


@router.post("/move-to-npc")
async def move_to_npc(requester: str, target: str, request: Request):
    """Command an NPC to physically move to another NPC."""
    requester_id = DUNGEON_AGENT_IDS.get(requester)
    target_id = DUNGEON_AGENT_IDS.get(target)
    if not requester_id or not target_id:
        raise HTTPException(status_code=404, detail="NPC not found")

    pw = request.app.state.physical_world
    success = await pw.move_to_npc(requester_id, target_id)
    return {"status": "moving" if success else "blocked", "requester": requester, "target": target}


@router.post("/move-to-room")
async def move_to_room(npc_name: str, room: str, request: Request):
    """Command an NPC to move to a specific room."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name)
    if not npc_id:
        raise HTTPException(status_code=404, detail="NPC not found")
    if room not in ("main_hall", "library", "treasury", "crypt"):
        raise HTTPException(status_code=400, detail=f"Unknown room: {room}")

    pw = request.app.state.physical_world
    success = await pw.move_to_room(npc_id, room)
    return {"status": "moving" if success else "blocked", "npc": npc_name, "target_room": room}


@router.post("/library/query")
async def library_query(npc_name: str, question: str, request: Request):
    """NPC visits the library and asks the oracle a question."""
    npc_id = DUNGEON_AGENT_IDS.get(npc_name)
    if not npc_id:
        raise HTTPException(status_code=404, detail="NPC not found")

    pw = request.app.state.physical_world

    # Check if NPC is at the library
    cursor = await request.app.state.db.execute(
        "SELECT pos_x, pos_y FROM dungeon_npcs WHERE npc_id=?", (npc_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="NPC not found")

    if not pw.is_at_library(row["pos_x"], row["pos_y"]):
        return {
            "status": "too_far",
            "message": f"{npc_name} is not at the library. Current room: {get_room_at(row['pos_x'], row['pos_y'])}",
        }

    answer = await pw.query_library(npc_name, question)
    return {"status": "answered", "npc": npc_name, "question": question, "answer": answer}


@router.get("/library/position")
async def library_position():
    """Get the library's position on the map."""
    from agora.agent_os.physical_world import LIBRARY_POS
    return {
        "library": {
            "x": LIBRARY_POS[0],
            "y": LIBRARY_POS[1],
            "tile_x": LIBRARY_POS[0] // 32,
            "tile_y": LIBRARY_POS[1] // 32,
            "room": get_room_at(LIBRARY_POS[0], LIBRARY_POS[1]),
        }
    }
