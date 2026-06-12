"""Tasks API router for Agora server."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(tags=["tasks"])


# ---------- Schemas ----------

class TaskPost(BaseModel):
    title: str
    description: str
    priority: int = 0
    assigned_to: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: int
    status: str
    assignee_id: Optional[str] = None
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int


# ---------- Dependency ----------

async def get_db(request: Request):
    return request.app.state.db


# ---------- Routes ----------

@router.get("/", response_model=TaskListResponse)
async def list_open_tasks(db=Depends(get_db)):
    """List all open tasks."""
    cursor = await db.execute(
        "SELECT id, title, description, priority, status, assignee_id, created_at, updated_at "
        "FROM tasks WHERE status NOT IN ('completed', 'failed', 'cancelled') "
        "ORDER BY priority DESC, created_at ASC"
    )
    rows = await cursor.fetchall()
    tasks = [TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        assignee_id=row["assignee_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    ) for row in rows]
    return TaskListResponse(tasks=tasks, total=len(tasks))


@router.post("/", response_model=TaskResponse, status_code=201)
async def post_task(body: TaskPost, db=Depends(get_db)):
    """Create a new task."""
    task_id = uuid.uuid4().hex
    cursor = await db.execute(
        "INSERT INTO tasks (id, title, description, priority, status, assignee_id, metadata) "
        "VALUES (?, ?, ?, ?, 'pending', ?, '{}')",
        (task_id, body.title, body.description, body.priority, body.assigned_to),
    )
    await db.commit()
    cursor2 = await db.execute(
        "SELECT id, title, description, priority, status, assignee_id, created_at, updated_at "
        "FROM tasks WHERE id=?",
        (task_id,),
    )
    row = await cursor2.fetchone()
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        assignee_id=row["assignee_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: int, db=Depends(get_db)):
    """Get a single task by ID."""
    cursor = await db.execute(
        "SELECT id, title, description, priority, status, assignee_id, created_at, updated_at "
        "FROM tasks WHERE id=?",
        (task_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        assignee_id=row["assignee_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{task_id}/assign/{agent_id}", response_model=TaskResponse)
async def assign_task(task_id: int, agent_id: str, db=Depends(get_db)):
    """Assign an open task to an agent."""
    cursor = await db.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Task is {row['status']}, cannot assign")
    # Verify agent exists
    cursor2 = await db.execute(
        "SELECT agent_id FROM agent_identities WHERE agent_id=?", (agent_id,)
    )
    if not await cursor2.fetchone():
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.execute(
        "UPDATE tasks SET status='assigned', assignee_id=?, updated_at=datetime('now') WHERE id=?",
        (agent_id, task_id),
    )
    await db.commit()
    cursor3 = await db.execute(
        "SELECT id, title, description, priority, status, assignee_id, created_at, updated_at "
        "FROM tasks WHERE id=?", (task_id,),
    )
    row = await cursor3.fetchone()
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        assignee_id=row["assignee_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, db=Depends(get_db)):
    """Mark a task as completed."""
    cursor = await db.execute("SELECT status FROM tasks WHERE id=?", (task_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] not in ("pending", "assigned", "in_progress"):
        raise HTTPException(status_code=400, detail=f"Task is {row['status']}, cannot complete")
    await db.execute(
        "UPDATE tasks SET status='completed', updated_at=datetime('now') WHERE id=?",
        (task_id,),
    )
    await db.commit()
    cursor2 = await db.execute(
        "SELECT id, title, description, priority, status, assignee_id, created_at, updated_at "
        "FROM tasks WHERE id=?", (task_id,),
    )
    row = await cursor2.fetchone()
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        assignee_id=row["assignee_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
