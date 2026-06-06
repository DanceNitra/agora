"""Graph API router for Agora server."""

import json
from fastapi import APIRouter, Depends, Request

router = APIRouter(tags=["graph"])


async def get_db(request: Request):
    return request.app.state.db


@router.get("/graph")
async def get_graph_data(db=Depends(get_db)):
    """Return nodes + links for the D3 force graph."""
    cursor = await db.execute(
        "SELECT agent_id, role, trust_score, energy_balance, genome FROM agent_identities WHERE status='active'"
    )
    agents = await cursor.fetchall()

    nodes = []
    for a in agents:
        try:
            genome = json.loads(a["genome"])
        except (json.JSONDecodeError, TypeError):
            genome = {}
        name = genome.get("role", a["role"])
        nodes.append({
            "id": a["agent_id"],
            "name": name,
            "role": a["role"],
            "trustScore": a["trust_score"],
        })

    # Build links from trust_scores
    cursor2 = await db.execute(
        "SELECT source_id, target_id, score FROM trust_scores"
    )
    links_raw = await cursor2.fetchall()
    links = [
        {"source": r["source_id"], "target": r["target_id"],
         "type": "trust", "weight": r["score"]}
        for r in links_raw
    ]

    return {"nodes": nodes, "links": links}
