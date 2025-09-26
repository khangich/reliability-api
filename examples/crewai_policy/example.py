"""CrewAI integration helpers showcasing policy metadata usage."""
from __future__ import annotations

from typing import Any, Dict

from crewai import Crew

from core.models import StepPayload, StepResponse, TaskCreateRequest
from core.runtime.task_manager import TaskManager


def reliability_policy(*, flow: str, slo_ms: int, budget_usd: float) -> Dict[str, Any]:
    """Return metadata that mirrors the CrewAI adapter contract."""

    return {
        "flow": flow,
        "policy": {
            "slo_ms": slo_ms,
            "budget_usd": budget_usd,
        },
    }


def run_crewai_with_reliability(
    task_manager: TaskManager,
    task_request: TaskCreateRequest,
    crew: Crew,
    *,
    observation_key: str = "crew_output",
) -> StepResponse:
    """Execute a CrewAI flow and report the result to the runtime."""

    task = task_manager.create_task(task_request)
    result = crew.kickoff()
    payload = StepPayload(observation={observation_key: result})
    return task_manager.record_step(task.id, payload)
