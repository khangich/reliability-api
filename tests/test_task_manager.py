from __future__ import annotations

import pytest

from core.models import LlmUsage, LoopGuardState, Policy, StepPayload, TaskCreateRequest
from core.runtime.task_manager import TaskManager


@pytest.fixture()
def task_manager() -> TaskManager:
    return TaskManager()


@pytest.fixture()
def base_policy() -> Policy:
    return Policy(
        id="test-policy",
        name="test",
        slo_ms=1000,
        budget_usd=1.0,
        max_retries=1,
        loop_guard=LoopGuardState(max_state_repeats=1),
    )


def test_create_task_and_record_step(task_manager: TaskManager, base_policy: Policy) -> None:
    request = TaskCreateRequest(task_id="task-1", policy_inline=base_policy)
    task = task_manager.create_task(request)

    response = task_manager.record_step(
        task.id, StepPayload(llm_usage=LlmUsage(cost_usd=0.4))
    )

    assert response.message == "accepted"
    assert response.task.cost_so_far.usd == pytest.approx(0.4)
    assert response.task.status.value == "running"


def test_budget_exceeded(task_manager: TaskManager, base_policy: Policy) -> None:
    request = TaskCreateRequest(task_id="task-budget", policy_inline=base_policy)
    task = task_manager.create_task(request)

    response = task_manager.record_step(
        task.id, StepPayload(llm_usage=LlmUsage(cost_usd=2.0))
    )

    assert response.message == "budget_exceeded"
    assert response.task.status.value == "failed"
    assert response.task.error == {
        "code": "BUDGET_EXCEEDED",
        "message": "Budget exceeded",
    }


def test_loop_detection_escalates(task_manager: TaskManager, base_policy: Policy) -> None:
    request = TaskCreateRequest(task_id="task-loop", policy_inline=base_policy)
    task = task_manager.create_task(request)

    payload = StepPayload(observation={"step": 1})
    assert task_manager.record_step(task.id, payload).message == "accepted"
    response = task_manager.record_step(task.id, payload)

    assert response.message == "loop_detected"
    assert response.task.status.value == "escalated"
    assert response.task.error == {
        "code": "LOOP_DETECTED",
        "message": "Loop detected",
    }
