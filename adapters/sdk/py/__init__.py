"""Minimal Python SDK surface mirroring the Reliability client ergonomics."""
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable, Optional

from core.models import StepPayload, StepResponse, Task, TaskCreateRequest, TaskStatus
from core.runtime.task_manager import TaskManager


class _GuardedTask(AbstractContextManager["_GuardedTask"]):
    """Context manager returned by :meth:`ReliabilityClient.guard`."""

    def __init__(self, client: "ReliabilityClient", request: TaskCreateRequest) -> None:
        self._client = client
        self._request = request
        self._task: Optional[Task] = None

    def __enter__(self) -> "_GuardedTask":  # type: ignore[override]
        self._task = self._client.create_task(self._request)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if exc_type and self._task:
            self._client.cancel_task(self._task.id)

    @property
    def task(self) -> Task:
        if not self._task:
            raise RuntimeError("Guard must be entered before accessing the task")
        return self._task

    def report(self, payload: StepPayload) -> StepResponse:
        if not self._task:
            raise RuntimeError("Guard must be entered before reporting steps")
        return self._client.report_step(self._task.id, payload)


class ReliabilityClient:
    """Thin wrapper around the in-memory :class:`TaskManager`."""

    def __init__(self, task_manager: TaskManager) -> None:
        self._task_manager = task_manager

    # ------------------------------------------------------------------
    # Task lifecycle helpers
    # ------------------------------------------------------------------
    def create_task(self, request: TaskCreateRequest) -> Task:
        return self._task_manager.create_task(request)

    def cancel_task(self, task_id: str) -> Task:
        return self._task_manager.cancel_task(task_id)

    def get_task(self, task_id: str) -> Task:
        return self._task_manager.get_task(task_id)

    def report_step(self, task_id: str, payload: StepPayload) -> StepResponse:
        return self._task_manager.record_step(task_id, payload)

    def guard(self, request: TaskCreateRequest) -> _GuardedTask:
        return _GuardedTask(self, request)

    # ------------------------------------------------------------------
    # Full task loop helper (Option E)
    # ------------------------------------------------------------------
    def task_loop(
        self,
        request: TaskCreateRequest,
        planner: Callable[[Task], Optional[StepPayload]],
    ) -> StepResponse:
        """Drive a task until the planner indicates completion."""

        task = self.create_task(request)
        current = task
        while current.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            payload = planner(current)
            if payload is None:
                current.status = TaskStatus.SUCCEEDED
                return StepResponse(task=current, message="completed")
            response = self.report_step(current.id, payload)
            current = response.task
            if current.status not in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                return response
        # Already terminal; fabricate a simple response for completeness.
        return StepResponse(task=current)


__all__ = ["ReliabilityClient"]