"""Tasks API router for Agora server."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ---------- Schemas ----------

class TaskPost(BaseModel):
    title: str
    description: str
    priority: int = 0
    assigned_to: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: int
    status: str  # open, assigned, completed, failed
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int


# ---------- Dependency: database session ----------

def get_db():
    """Placeholder: yields a database session."""
    yield None


# ---------- Helpers ----------

def _task_to_response(task_row) -> TaskResponse:
    """Convert a database task row to a TaskResponse."""
    return TaskResponse(
        id=task_row.id,
        title=task_row.title,
        description=task_row.description,
        priority=task_row.priority,
        status=task_row.status,
        assigned_to=getattr(task_row, "assigned_to", None),
        created_at=task_row.created_at,
        updated_at=task_row.updated_at,
        completed_at=getattr(task_row, "completed_at", None),
    )


# ---------- Routes ----------

@router.get("/", response_model=TaskListResponse)
async def list_open_tasks(db=Depends(get_db)):
    """List all open (non-completed, non-failed) tasks."""
    # tasks = (
    #     db.query(TaskModel)
    #     .filter(TaskModel.status.in_(["open", "assigned"]))
    #     .order_by(TaskModel.priority.desc(), TaskModel.created_at.asc())
    #     .all()
    # )
    tasks = []  # placeholder
    return TaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=len(tasks),
    )


@router.post("/", response_model=TaskResponse, status_code=201)
async def post_task(body: TaskPost, db=Depends(get_db)):
    """Create (post) a new task."""
    # task = TaskModel(
    #     title=body.title,
    #     description=body.description,
    #     priority=body.priority,
    #     status="open",
    #     assigned_to=body.assigned_to,
    # )
    # db.add(task)
    # db.commit()
    # db.refresh(task)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str, db=Depends(get_db)):
    """Get a single task's status by ID."""
    # task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    # if not task:
    #     raise HTTPException(status_code=404, detail="Task not found")
    # return _task_to_response(task)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.post("/{task_id}/assign/{agent_id}", response_model=TaskResponse)
async def assign_task(task_id: str, agent_id: str, db=Depends(get_db)):
    """Assign an open task to an agent."""
    # task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    # if not task:
    #     raise HTTPException(status_code=404, detail="Task not found")
    # if task.status != "open":
    #     raise HTTPException(status_code=400, detail=f"Task is {task.status}, cannot assign")
    # task.status = "assigned"
    # task.assigned_to = agent_id
    # task.updated_at = datetime.utcnow()
    # db.commit()
    # db.refresh(task)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: str, db=Depends(get_db)):
    """Mark a task as completed."""
    # task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    # if not task:
    #     raise HTTPException(status_code=404, detail="Task not found")
    # if task.status not in ("open", "assigned"):
    #     raise HTTPException(status_code=400, detail=f"Task is {task.status}, cannot complete")
    # task.status = "completed"
    # task.completed_at = datetime.utcnow()
    # task.updated_at = datetime.utcnow()
    # db.commit()
    # db.refresh(task)
    raise HTTPException(status_code=501, detail="Not implemented — database integration pending")
