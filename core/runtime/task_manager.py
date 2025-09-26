"""In-memory task manager used by the FastAPI application.

The implementation is intentionally lightweight but captures key behaviours of
an enforcement runtime: policy resolution, basic budget accounting, loop guard
tracking, and deadline evaluation. As the project matures this module can be
swapped with a persistent storage backed version without changing the API
layer.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Dict, Optional

from fastapi import HTTPException, status

from core.models import (
    Policy,
    PolicyUpsertRequest,
    StepPayload,
    StepResponse,
    Task,
    TaskCreateRequest,
    TaskStatus,
)


class TaskManager:
    """Manage task lifecycles and policy definitions."""

    def __init__(self) -> None:
        self._policies: Dict[str, Policy] = {}
        self._tasks: Dict[str, Task] = {}

    # ------------------------------------------------------------------
    # Policy operations
    # ------------------------------------------------------------------
    def upsert_policy(self, request: PolicyUpsertRequest) -> Policy:
        policy_id = request.id or request.name
        if not policy_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Policy id or name is required",
            )
        policy = Policy(**request.dict(exclude_unset=True))
        policy.id = policy_id
        self._policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self._policies.get(policy_id)

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------
    def create_task(self, request: TaskCreateRequest) -> Task:
        if request.task_id in self._tasks:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task already exists",
            )
        policy = request.policy_inline
        if not policy and request.policy_id:
            policy = self.get_policy(request.policy_id)
            if not policy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Policy not found",
                )
        task = request.to_task(policy)
        task.policy_inline = policy or task.policy_inline
        task.started_at = datetime.utcnow()
        task.updated_at = task.started_at
        task.status = TaskStatus.RUNNING
        task.apply_policy_defaults()
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return task

    def record_step(self, task_id: str, payload: StepPayload) -> StepResponse:
        task = self.get_task(task_id)
        if task.status not in {TaskStatus.RUNNING, TaskStatus.PENDING}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task is {task.status}, additional steps not permitted",
            )
        now = datetime.utcnow()
        task.updated_at = now

        # Deadline enforcement
        if task.deadline_at and now > task.deadline_at:
            task.status = TaskStatus.FAILED
            task.error = {"code": "DEADLINE_MISS", "message": "Deadline exceeded"}
            return StepResponse(task=task, message="deadline_missed")

        # Budget enforcement (basic USD only for the stub)
        if payload.llm_usage and payload.llm_usage.cost_usd:
            projected_cost = task.cost_so_far.usd + payload.llm_usage.cost_usd
            if projected_cost > task.budget.usd:
                task.status = TaskStatus.FAILED
                task.error = {"code": "BUDGET_EXCEEDED", "message": "Budget exceeded"}
                return StepResponse(task=task, message="budget_exceeded")
            task.cost_so_far.usd = projected_cost

        # Loop detection heuristics (state hash only for now)
        new_hash = self._compute_step_hash(payload)
        if task.last_state_hash == new_hash:
            task.loop_guard.repeats += 1
        else:
            task.loop_guard.repeats = 0
        task.last_state_hash = new_hash
        if task.loop_guard.max_state_repeats and task.loop_guard.repeats >= task.loop_guard.max_state_repeats:
            task.status = TaskStatus.ESCALATED
            task.error = {"code": "LOOP_DETECTED", "message": "Loop detected"}
            return StepResponse(task=task, message="loop_detected")

        return StepResponse(task=task)

    def escalate_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        task.status = TaskStatus.ESCALATED
        task.updated_at = datetime.utcnow()
        return task

    def cancel_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        task.status = TaskStatus.CANCELED
        task.updated_at = datetime.utcnow()
        return task

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _compute_step_hash(self, payload: StepPayload) -> str:
        digest = hashlib.sha256()
        digest.update(json.dumps(payload.dict(), sort_keys=True).encode("utf-8"))
        return digest.hexdigest()


# Global singleton used by FastAPI dependency injection
manager = TaskManager()
