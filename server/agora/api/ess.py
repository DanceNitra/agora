"""
ESS REST API — Endpoints for the multi-agent trust protocol.

Endpoints:
  POST /api/ess/commit       — Agent commits to a goal (records commitment)
  POST /api/ess/interact     — Record an interaction (cooperate/defect)
  GET  /api/ess/trust/{agent_id}    — Get trust scores for an agent
  GET  /api/ess/evaluate/{agent_id} — Get TFT compliance + provokability
  GET  /api/ess/aggregates         — List all ESS aggregate types and counts

All endpoints accept and return JSON.

NOTE: Ed25519 message signing (task 1.5) is not wired in yet. `/commit` records the
commitment to the event store and returns the current trust state; once 1.5 lands, the
commitment can carry a real `trust_sig`. Nothing here depends on 1.5 being present.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from agora.coordination.ess_protocol import TrustEngine
from agora.coordination.tft_verifier import TFTVerifier
from agora.coordination.event_store import EventStore

router = APIRouter(prefix="/api/ess", tags=["ess"])


# ── Dependency helpers ─────────────────────────

def get_trust_engine(request: Request) -> TrustEngine:
    engine = getattr(request.app.state, "trust", None)
    if not engine:
        raise HTTPException(503, "Trust engine not initialised")
    return engine


def get_tft_verifier(request: Request) -> TFTVerifier:
    verifier = getattr(request.app.state, "tft_verifier", None)
    if not verifier:
        raise HTTPException(503, "TFT verifier not initialised")
    return verifier


def get_event_store(request: Request) -> EventStore:
    store = getattr(request.app.state, "event_store", None)
    if not store:
        raise HTTPException(503, "Event store not initialised")
    return store


def parse_body(body: dict, fields: list[str]) -> dict:
    """Validate required fields in request body."""
    for f in fields:
        if f not in body or body[f] in (None, ""):
            raise HTTPException(400, f"Missing required field: {f}")
    return body


# ── Endpoints ──────────────────────────────────


@router.post("/commit")
async def commit(request: Request):
    """Agent commits to a goal. Records the commitment and returns trust state.

    Request body:
      agent_id: str  (required)
      goal: str      (required)
      target_id: str (optional — if omitted, public commitment)
    """
    body = await request.json()
    parse_body(body, ["agent_id", "goal"])

    agent_id = body["agent_id"]
    goal = body["goal"]
    target_id = body.get("target_id")

    engine = get_trust_engine(request)

    # Record the commitment in the event store (best-effort).
    store = getattr(request.app.state, "event_store", None)
    if store:
        try:
            await store.append(
                aggregate_type="commitment",
                aggregate_id=agent_id,
                event_type="commitment_created",
                payload={"goal": goal, "target_id": target_id or "public"},
                metadata={"caller": "REST API /api/ess/commit"},
            )
        except Exception:
            pass  # event store failure must not break the commitment

    # Get current trust state toward the target (if any).
    trust_state = None
    if target_id:
        trust_score = await engine.get_trust(agent_id, target_id)
        trust_state = {
            "agent_id": agent_id,
            "target_id": target_id,
            "trust_score": trust_score,
        }

    return {
        "status": "committed",
        "commitment": {
            "agent_id": agent_id,
            "target_id": target_id or "public",
            "goal": goal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "trust_state": trust_state,
    }


@router.post("/interact")
async def interact(request: Request):
    """Record an interaction between two agents.

    Request body:
      agent_id:  str   (required — who initiated)
      target_id: str   (required — who was interacted with)
      outcome:   str   (required — "cooperate" or "defect")
      context:   dict  (optional — additional metadata)
    """
    body = await request.json()
    parse_body(body, ["agent_id", "target_id", "outcome"])

    agent_id = body["agent_id"]
    target_id = body["target_id"]
    outcome = body["outcome"]
    context = body.get("context", {})

    if outcome not in ("cooperate", "defect"):
        raise HTTPException(400, "outcome must be 'cooperate' or 'defect'")

    engine = get_trust_engine(request)
    verifier = get_tft_verifier(request)
    get_event_store(request)  # ensure event sourcing is available (503 otherwise)

    trust_before = await engine.get_trust(agent_id, target_id)

    # Record in the trust engine (this also appends to the event store).
    trust_result = await engine.record_interaction(agent_id, target_id, outcome)

    # Record the TFT interaction (own event-store stream).
    tft_result = await verifier.record_interaction(
        source_id=agent_id,
        target_id=target_id,
        outcome=outcome,
        trust_before=trust_before,
        trust_after=trust_result.get("score"),
        context=context,
    )

    # Provokability (ESS-stability) for this pair.
    provokability = await engine.compute_provokability(agent_id, target_id)

    return {
        "status": "recorded",
        "interaction": {
            "source_id": agent_id,
            "target_id": target_id,
            "outcome": outcome,
        },
        "trust": {
            "score": trust_result.get("score", 0.5),
            "interactions": trust_result.get("interactions", 0),
        },
        "tft": {
            "id": tft_result.get("id", ""),
            "round_num": tft_result.get("round_num", 0),
        },
        "provokability": {
            "score": provokability.get("provokability_score", 0.5),
            "is_stable": provokability.get("is_stable", False),
        },
    }


@router.get("/trust/{agent_id}")
async def get_trust(request: Request, agent_id: str, target_id: str | None = None):
    """Get trust scores for an agent.

    If target_id is provided, returns pairwise trust. Otherwise returns all of the
    agent's outgoing trust relationships.
    """
    engine = get_trust_engine(request)
    db = request.app.state.db

    if target_id:
        score = await engine.get_trust(agent_id, target_id)
        return {
            "agent_id": agent_id,
            "target_id": target_id,
            "trust_score": score,
            "pairwise": True,
        }

    cursor = await db.execute(
        "SELECT target_id, score, interaction_count FROM trust_scores "
        "WHERE source_id=? ORDER BY score DESC",
        (agent_id,),
    )
    rows = await cursor.fetchall()
    return {
        "agent_id": agent_id,
        "relationships": [
            {
                "target_id": r["target_id"],
                "trust_score": r["score"],
                "interactions": r["interaction_count"],
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/evaluate/{agent_id}")
async def evaluate(request: Request, agent_id: str):
    """Get TFT compliance + provokability for an agent.

    Returns TFT score, component breakdown, and provokability averaged across the
    agent's interaction partners.
    """
    verifier = get_tft_verifier(request)
    engine = get_trust_engine(request)

    tft_result = await verifier.evaluate(agent_id)

    # Collect unique partners from interaction history.
    partners = set()
    history = await verifier.load_history(agent_id)
    for h in history:
        partner = h["target_id"] if h.get("agent_is_source") else h.get("source_id", "")
        if partner and partner != agent_id:
            partners.add(partner)

    provokability_results = []
    for p in partners:
        prov = await engine.compute_provokability(agent_id, p)
        provokability_results.append({
            "partner_id": p[:8],
            "provokability_score": prov.get("provokability_score", 0.5),
            "is_stable": prov.get("is_stable", False),
        })

    avg_provokability = (
        sum(p["provokability_score"] for p in provokability_results)
        / max(len(provokability_results), 1)
    )

    return {
        "agent_id": tft_result.get("agent_id", agent_id[:8]),
        "tft_score": tft_result.get("tft_score", 0.5),
        "tft_components": tft_result.get("components", {}),
        "interaction_count": tft_result.get("interaction_count", 0),
        "provokability": {
            "average": round(avg_provokability, 4),
            "is_stable": all(p["is_stable"] for p in provokability_results) if provokability_results else False,
            "pair_count": len(provokability_results),
            "pairs": provokability_results[:10],  # Top 10
        },
    }


@router.get("/aggregates")
async def list_aggregates(request: Request):
    """List all ESS aggregate types with event counts."""
    store = get_event_store(request)
    db = request.app.state.db

    types_cursor = await db.execute(
        "SELECT aggregate_type, COUNT(*) as cnt FROM event_store "
        "GROUP BY aggregate_type ORDER BY cnt DESC"
    )
    rows = await types_cursor.fetchall()

    aggregates = []
    for r in rows:
        aggs = await store.list_aggregates(r["aggregate_type"])
        aggregates.append({
            "type": r["aggregate_type"],
            "event_count": r["cnt"],
            "stream_count": len(aggs),
        })

    return {
        "aggregates": aggregates,
        "total_types": len(aggregates),
    }
