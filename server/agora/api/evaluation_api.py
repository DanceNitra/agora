"""Evaluation API — epoch metrics, agent scoring, and context inspection."""

from fastapi import APIRouter, Request
from agora.coordination.tft_verifier import TFTVerifier

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])


@router.get("/epoch/current")
async def get_current_epoch(request: Request):
    """Get current epoch state and live metrics."""
    epoch_engine = request.app.state.epoch_engine
    stats = await epoch_engine.get_stats()
    evaluator = request.app.state.epoch_evaluator
    if evaluator and stats.get("current_epoch", 0) > 0:
        report = await evaluator.get_epoch_report_from_db(stats["current_epoch"])
        if report:
            stats["report"] = report
    return stats


@router.get("/epoch/{epoch_number}")
async def get_epoch_report(request: Request, epoch_number: int):
    """Get full evaluation report for a specific epoch."""
    evaluator = request.app.state.epoch_evaluator
    report = await evaluator.get_epoch_report_from_db(epoch_number)
    if not report:
        return {"epoch": epoch_number, "error": "No data for this epoch"}
    return report


@router.get("/agent/{agent_id}")
async def get_agent_evaluation(request: Request, agent_id: str):
    """Get evaluation metrics and score for a single agent."""
    evaluator = request.app.state.epoch_evaluator
    metrics = await evaluator.compute_agent_metrics(agent_id)
    score = await evaluator.compute_agent_score(agent_id)
    return {"metrics": metrics, "score": score}


@router.get("/agents")
async def get_all_agent_scores(request: Request):
    """Get scores for all known agents, ranked."""
    evaluator = request.app.state.epoch_evaluator
    db = request.app.state.db

    try:
        cursor = await db.execute(
            "SELECT agent_id FROM agent_identities ORDER BY trust_score DESC"
        )
        results = []
        for row in await cursor.fetchall():
            metrics = await evaluator.compute_agent_metrics(row["agent_id"])
            score = await evaluator.compute_agent_score(row["agent_id"])
            results.append({
                "agent_id": metrics["agent_id"],
                "name": metrics["name"],
                "role": metrics["role"],
                "score": score["score"],
                "trust_delta": metrics["trust_delta"],
                "help_rate": metrics["help_success_rate"],
                "skill_growth": metrics["skill_growth"],
            })

        return {"count": len(results), "agents": results}
    except Exception as e:
        return {"error": str(e)}


@router.get("/context/{agent_id}")
async def get_agent_context(request: Request, agent_id: str):
    """Get the structured context for an agent (as sent to LLM)."""
    cm = request.app.state.context_manager
    if not cm:
        return {"error": "Context manager not initialized"}
    context = await cm.build_context(agent_id)
    return {"agent_id": agent_id[:8], "context": context}


@router.post("/compact/{agent_id}")
async def compact_agent_memory(request: Request, agent_id: str):
    """Trigger memory compaction for an agent."""
    cm = request.app.state.context_manager
    if not cm:
        return {"error": "Context manager not initialized"}
    compacted = await cm.check_and_compact(agent_id)
    return {"agent_id": agent_id[:8], "compacted": compacted}


@router.get("/actions/{agent_id}")
async def get_agent_actions(request: Request, agent_id: str):
    """Get recent action history for an agent."""
    ee = request.app.state.execution_engine
    if not ee:
        return {"error": "Execution engine not initialized"}
    history = ee.get_action_history(agent_id)
    return {"agent_id": agent_id[:8], "count": len(history), "actions": history}


# ═══════════════════════════════════════════════
# TFT VERIFIER ENDPOINTS
# ═══════════════════════════════════════════════

# IMPORTANT: /tft/all MUST come before /tft/{agent_id} to avoid
# FastAPI path param capture of "all" as an agent_id


@router.get("/tft/all")
async def get_all_tft_scores(request: Request):
    """Get TFT compliance scores for all agents that have interactions."""
    tft: TFTVerifier = request.app.state.tft_verifier
    if not tft:
        return {"error": "TFT Verifier not initialized"}
    results = await tft.evaluate_all()
    return {"count": len(results), "agents": results}


@router.get("/tft/pair/{agent_id}/{partner_id}")
async def get_tft_pair_score(request: Request, agent_id: str, partner_id: str):
    """Get TFT compliance score for interactions between two agents."""
    tft: TFTVerifier = request.app.state.tft_verifier
    if not tft:
        return {"error": "TFT Verifier not initialized"}
    result = await tft.evaluate_pair(agent_id, partner_id)
    return result


@router.get("/tft/{agent_id}")
async def get_tft_score(request: Request, agent_id: str):
    """Get TFT compliance score for a single agent."""
    tft: TFTVerifier = request.app.state.tft_verifier
    if not tft:
        return {"error": "TFT Verifier not initialized"}
    result = await tft.evaluate(agent_id)
    return result


@router.get("/tft/log/{agent_id}")
async def get_tft_log(request: Request, agent_id: str, limit: int = 50):
    """Get raw interaction log for an agent."""
    tft: TFTVerifier = request.app.state.tft_verifier
    if not tft:
        return {"error": "TFT Verifier not initialized"}
    history = await tft.load_history(agent_id, limit=limit)
    return {"agent_id": agent_id[:8], "count": len(history), "interactions": history}


# ═══════════════════════════════════════════════
# EIGENTRUST MATRIX ENDPOINT
# ═══════════════════════════════════════════════


@router.get("/trust/matrix")
async def get_trust_matrix(request: Request):
    """Get the full EigenTrust matrix + eigenvector scores for all agents."""
    eigen = getattr(request.app.state, "eigen_trust", None)
    if not eigen:
        return {"error": "EigenTrust not initialized"}
    result = await eigen.compute(damping=0.85)
    return result


@router.get("/trust/matrix/raw")
async def get_trust_matrix_raw(request: Request, min_interactions: int = 1):
    """Get the raw N×N trust matrix (JSON-safe lists)."""
    eigen = getattr(request.app.state, "eigen_trust", None)
    if not eigen:
        return {"error": "EigenTrust not initialized"}
    result = await eigen.get_raw_matrix(min_interactions=min_interactions)
    return result
