from __future__ import annotations

from fastapi.testclient import TestClient

from api.http import app as app_module
from api.http.app import app, get_manager
from core.runtime.task_manager import TaskManager


def reset_task_manager() -> TaskManager:
    new_manager = TaskManager()
    app_module.manager = new_manager
    app.dependency_overrides[get_manager] = lambda: new_manager
    return new_manager


def test_fastapi_smoke_flow() -> None:
    reset_task_manager()
    try:
        with TestClient(app) as client:
            policy = {
                "id": "policy-smoke",
                "slo_ms": 5000,
                "budget_usd": 5.0,
                "max_retries": 2,
            }

            response = client.post("/policies", json=policy)
            assert response.status_code == 200
            assert response.json()["id"] == "policy-smoke"

            task_request = {
                "task_id": "task-smoke",
                "policy_id": "policy-smoke",
            }

            response = client.post("/tasks", json=task_request)
            assert response.status_code == 201
            task_id = response.json()["task_id"]

            step_payload = {
                "llm_usage": {"cost_usd": 1.0},
                "observation": {"note": "first step"},
            }

            response = client.post(f"/tasks/{task_id}/step", json=step_payload)
            assert response.status_code == 200
            body = response.json()
            assert body["message"] == "accepted"
            assert body["task"]["cost_so_far"]["usd"] == 1.0
            assert body["task"]["status"] == "running"
    finally:
        app.dependency_overrides.clear()
