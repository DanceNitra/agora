"""
Artifacts API — list, view, and search agent-produced artifacts.

Artifacts are produced by agents completing tasks (task_executor) and
by agent thoughts in the tick loop. Each artifact has real content
generated based on task type and agent role.
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


async def get_db(request: Request):
    return request.app.state.db


@router.get("/")
async def list_artifacts(
    request: Request,
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    artifact_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List artifacts with optional filters."""
    db = request.app.state.db
    conditions = []
    params = []

    if agent_id:
        conditions.append("a.agent_id=?")
        params.append(agent_id)
    if artifact_type:
        conditions.append("a.artifact_type=?")
        params.append(artifact_type)

    where = " AND ".join(conditions) if conditions else "1=1"

    cursor = await db.execute(
        f"SELECT a.id, a.agent_id, a.title, a.artifact_type, a.storage_path, "
        f"a.mime_type, a.size_bytes, a.metadata, a.is_published, a.created_at, "
        f"ai.role "
        f"FROM artifacts a "
        f"LEFT JOIN agent_identities ai ON a.agent_id = ai.agent_id "
        f"WHERE {where} "
        f"ORDER BY a.id DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    )
    rows = await cursor.fetchall()

    # Count total
    cursor2 = await db.execute(
        f"SELECT COUNT(*) as c FROM artifacts WHERE {where}", params
    )
    total = (await cursor2.fetchone())["c"]

    artifacts = []
    for row in rows:
        meta = json.loads(row["metadata"] or "{}")
        artifacts.append({
            "id": row["id"],
            "agent_id": row["agent_id"][:12],
            "role": row["role"],
            "title": row["title"],
            "artifact_type": row["artifact_type"],
            "storage_path": row["storage_path"],
            "mime_type": row["mime_type"] or "text/plain",
            "size_bytes": row["size_bytes"] or 0,
            "is_published": bool(row["is_published"]),
            "created_at": row["created_at"],
            "difficulty": meta.get("difficulty"),
            "task_id": meta.get("task_id"),
            "summary": meta.get("summary", ""),
        })

    return {"artifacts": artifacts, "total": total, "limit": limit, "offset": offset}


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: int, request: Request):
    """Get a single artifact with its full content."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT a.id, a.agent_id, a.title, a.artifact_type, a.storage_path, "
        "a.mime_type, a.size_bytes, a.metadata, a.content, a.is_published, a.created_at, "
        "ai.role "
        "FROM artifacts a "
        "LEFT JOIN agent_identities ai ON a.agent_id = ai.agent_id "
        "WHERE a.id=?",
        (artifact_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")

    meta = json.loads(row["metadata"] or "{}")
    return {
        "id": row["id"],
        "agent_id": row["agent_id"][:12],
        "role": row["role"],
        "title": row["title"],
        "artifact_type": row["artifact_type"],
        "content": row["content"] or "(empty)",
        "mime_type": row["mime_type"] or "text/plain",
        "size_bytes": row["size_bytes"] or 0,
        "is_published": bool(row["is_published"]),
        "created_at": row["created_at"],
        "metadata": meta,
    }


@router.get("/stats/summary")
async def artifact_summary(request: Request):
    """Aggregated artifact statistics."""
    db = request.app.state.db
    cursor = await db.execute(
        "SELECT artifact_type, COUNT(*) as cnt FROM artifacts GROUP BY artifact_type ORDER BY cnt DESC"
    )
    by_type = [{"type": r["artifact_type"], "count": r["cnt"]} for r in await cursor.fetchall()]

    cursor = await db.execute(
        "SELECT ai.role, COUNT(*) as cnt FROM artifacts a "
        "JOIN agent_identities ai ON a.agent_id = ai.agent_id "
        "GROUP BY ai.role ORDER BY cnt DESC"
    )
    by_role = [{"role": r["role"], "count": r["cnt"]} for r in await cursor.fetchall()]

    cursor = await db.execute("SELECT COUNT(*) as c, SUM(size_bytes) as total_bytes FROM artifacts")
    totals = await cursor.fetchone()

    return {
        "total_artifacts": totals["c"] or 0,
        "total_bytes": totals["total_bytes"] or 0,
        "by_type": by_type,
        "by_role": by_role,
    }
