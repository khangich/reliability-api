"""FastAPI application exposing the Reliability API surface.

The application uses the in-memory :mod:`TaskManager` for state management.
This keeps the example self-contained while leaving room for future expansion
(e.g. swapping to a database-backed implementation).
"""
from __future__ import annotations

from fastapi import Depends, FastAPI

from core.models import PolicyUpsertRequest, StepPayload, StepResponse, Task, TaskCreateRequest
from core.runtime.task_manager import TaskManager, manager

app = FastAPI(title="Reliability API", version="0.1.0")


def get_manager() -> TaskManager:
    return manager


@app.post("/policies", response_model=PolicyUpsertRequest)
def upsert_policy(request: PolicyUpsertRequest, task_manager: TaskManager = Depends(get_manager)):
    return task_manager.upsert_policy(request)


@app.post("/tasks", status_code=201, response_model=Task)
def create_task(request: TaskCreateRequest, task_manager: TaskManager = Depends(get_manager)):
    return task_manager.create_task(request)


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str, task_manager: TaskManager = Depends(get_manager)):
    return task_manager.get_task(task_id)


@app.post("/tasks/{task_id}/step", response_model=StepResponse)
def record_step(task_id: str, payload: StepPayload, task_manager: TaskManager = Depends(get_manager)):
    return task_manager.record_step(task_id, payload)


@app.post("/tasks/{task_id}:escalate", response_model=Task)
def escalate(task_id: str, task_manager: TaskManager = Depends(get_manager)):
    return task_manager.escalate_task(task_id)


@app.post("/tasks/{task_id}:cancel", response_model=Task)
def cancel(task_id: str, task_manager: TaskManager = Depends(get_manager)):
    return task_manager.cancel_task(task_id)
