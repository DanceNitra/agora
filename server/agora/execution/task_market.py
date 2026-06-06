"""Decentralized task market with exploration/exploitation assignment."""

import random
import time
import uuid
from collections import deque
from typing import Any, Optional


class TaskStatus:
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskMarket:
    """Agent task market with 30% exploration rate for fair task distribution.

    Tasks are posted by the system or agents, then assigned to agents via
    a weighted strategy that balances exploitation (skill match) with
    exploration (random assignment).
    """

    def __init__(self, exploration_rate: float = 0.30):
        if not 0.0 <= exploration_rate <= 1.0:
            raise ValueError("exploration_rate must be between 0.0 and 1.0")
        self._exploration_rate = exploration_rate
        self._tasks: dict[str, dict] = {}
        self._pending_queue: deque[str] = deque()
        self._agent_skills: dict[str, set[str]] = {}

    def register_agent(self, agent_id: str, skills: Optional[list[str]] = None) -> None:
        """Register an agent and its skills for task matching."""
        self._agent_skills[agent_id] = set(skills or [])

    def post_task(
        self,
        task_type: str,
        payload: Any,
        required_skills: Optional[list[str]] = None,
        priority: int = 0,
        meta: Optional[dict] = None,
    ) -> str:
        """Post a new task to the market.

        Args:
            task_type: Category of the task.
            payload: Arbitrary task data.
            required_skills: Skills needed to complete the task.
            priority: Higher values = more urgent.
            meta: Optional metadata.

        Returns:
            Task ID.
        """
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "required_skills": set(required_skills or []),
            "priority": priority,
            "status": TaskStatus.PENDING,
            "assigned_to": None,
            "created_at": time.time(),
            "assigned_at": None,
            "completed_at": None,
            "result": None,
            "meta": meta or {},
        }
        self._tasks[task_id] = task
        self._pending_queue.append(task_id)
        return task_id

    def get_next_task(self, agent_id: str) -> Optional[dict]:
        """Assign the next suitable task to an agent.

        Assignment strategy (30% exploration):
          - 70% exploitation: try to find a task whose required_skills
            intersect with the agent's registered skills.
          - 30% exploration: pick from the front of the queue regardless
            of skill match.

        Args:
            agent_id: The agent requesting a task.

        Returns:
            The assigned task dict (with assignment fields filled) or None
            if no tasks are available.
        """
        if not self._pending_queue:
            return None

        # --- Exploration pick (30%) ---
        if random.random() < self._exploration_rate:
            # Pick the oldest pending task
            candidate_id = self._pending_queue[0]
            candidate = self._tasks.get(candidate_id)
            if candidate and candidate["status"] == TaskStatus.PENDING:
                return self._assign(candidate_id, agent_id)

        # --- Exploitation pick (70%) ---
        agent_skills = self._agent_skills.get(agent_id, set())
        # Scan pending queue for best skill match
        for candidate_id in list(self._pending_queue):
            candidate = self._tasks.get(candidate_id)
            if candidate and candidate["status"] == TaskStatus.PENDING:
                required = candidate["required_skills"]
                if required and required.intersection(agent_skills):
                    return self._assign(candidate_id, agent_id)

        # Fallback: if no skill match found, assign the oldest pending task
        if self._pending_queue:
            candidate_id = self._pending_queue[0]
            candidate = self._tasks.get(candidate_id)
            if candidate and candidate["status"] == TaskStatus.PENDING:
                return self._assign(candidate_id, agent_id)

        return None

    def complete_task(
        self, task_id: str, result: Any = None, failed: bool = False
    ) -> bool:
        """Mark a task as completed or failed.

        Args:
            task_id: The task identifier.
            result: The result payload.
            failed: If True marks as FAILED instead of COMPLETED.

        Returns:
            True if the task was updated, False if not found.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task["status"] = TaskStatus.FAILED if failed else TaskStatus.COMPLETED
        task["result"] = result
        task["completed_at"] = time.time()
        return True

    def _assign(self, task_id: str, agent_id: str) -> dict:
        """Internal assignment — removes task from queue and sets fields.

        Returns a copy of the task dict safe for external consumption.
        """
        task = self._tasks[task_id]
        task["status"] = TaskStatus.ASSIGNED
        task["assigned_to"] = agent_id
        task["assigned_at"] = time.time()
        # Remove from queue
        if task_id in self._pending_queue:
            self._pending_queue.remove(task_id)
        return {
            "id": task["id"],
            "type": task["type"],
            "payload": task["payload"],
            "required_skills": list(task["required_skills"]),
            "priority": task["priority"],
            "status": task["status"],
            "assigned_to": agent_id,
            "created_at": task["created_at"],
            "assigned_at": task["assigned_at"],
        }

    def get_pending_count(self) -> int:
        """Return the number of pending tasks."""
        return len(self._pending_queue)

    def get_task(self, task_id: str) -> Optional[dict]:
        """Retrieve a task by ID."""
        return self._tasks.get(task_id)
