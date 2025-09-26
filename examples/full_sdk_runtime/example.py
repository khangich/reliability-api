"""Full SDK loop helper utilities."""
from __future__ import annotations

from typing import Callable, Optional

from adapters.sdk.py import ReliabilityClient
from core.models import StepPayload, StepResponse, Task, TaskCreateRequest
from core.runtime.task_manager import TaskManager


def run_full_sdk_loop(
    task_manager: TaskManager,
    task_request: TaskCreateRequest,
    planner: Callable[[Task], Optional[StepPayload]],
) -> StepResponse:
    """Mirror Option E by delegating the task loop to the SDK client."""

    client = ReliabilityClient(task_manager)
    return client.task_loop(task_request, planner)
