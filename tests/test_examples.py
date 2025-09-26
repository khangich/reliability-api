from __future__ import annotations

import sys
import types
from typing import Any, Dict

import pytest

from adapters.gateway import ChatCompletionResponse
from core.models import (
    LlmUsage,
    LoopGuardState,
    Policy,
    StepPayload,
    Task,
    TaskCreateRequest,
)
from core.runtime.task_manager import TaskManager


@pytest.fixture(autouse=True)
def cleanup_modules():
    original_langchain = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith("langchain")
    }
    original_crewai = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith("crewai")
    }
    try:
        yield
    finally:
        for name in list(sys.modules.keys()):
            if name.startswith("langchain") or name.startswith("crewai"):
                sys.modules.pop(name, None)
        sys.modules.update(original_langchain)
        sys.modules.update(original_crewai)


def stub_langchain(result: Any) -> Any:
    module = types.ModuleType("langchain")
    agents_module = types.ModuleType("langchain.agents")

    class DummyAgentExecutor:
        def __init__(self) -> None:
            self.invocations: list[Dict[str, Any]] = []

        def invoke(self, payload: Dict[str, Any]) -> Any:
            self.invocations.append(payload)
            return result

    agents_module.AgentExecutor = DummyAgentExecutor
    module.agents = agents_module
    sys.modules["langchain"] = module
    sys.modules["langchain.agents"] = agents_module
    return DummyAgentExecutor


def stub_crewai(result: Any) -> Any:
    module = types.ModuleType("crewai")

    class DummyCrew:
        def __init__(self) -> None:
            self.kickoff_called = 0

        def kickoff(self) -> Any:
            self.kickoff_called += 1
            return result

    module.Crew = DummyCrew
    sys.modules["crewai"] = module
    return DummyCrew


def test_langchain_guard_flow() -> None:
    DummyAgentExecutor = stub_langchain({"answer": "ok"})

    from examples.langchain_guard import run_guarded_langchain_flow

    policy = Policy(
        id="langchain-policy",
        name="langchain",
        slo_ms=2000,
        budget_usd=2.0,
        max_retries=1,
        loop_guard=LoopGuardState(max_state_repeats=2),
    )
    request = TaskCreateRequest(task_id="langchain#1", policy_inline=policy)
    manager = TaskManager()
    agent = DummyAgentExecutor()

    response = run_guarded_langchain_flow(
        manager,
        request,
        agent,
        {"input": "hi"},
        llm_usage=LlmUsage(cost_usd=0.5),
    )

    assert response.message == "accepted"
    assert response.task.cost_so_far.usd == pytest.approx(0.5)
    assert agent.invocations == [{"input": "hi"}]


def test_crewai_policy_runner() -> None:
    DummyCrew = stub_crewai({"status": "completed"})

    from examples.crewai_policy import reliability_policy, run_crewai_with_reliability

    metadata = reliability_policy(flow="collections", slo_ms=1000, budget_usd=3.0)
    assert metadata == {
        "flow": "collections",
        "policy": {"slo_ms": 1000, "budget_usd": 3.0},
    }

    policy = Policy(
        id="crew-policy",
        name="crew",
        slo_ms=1000,
        budget_usd=3.0,
        max_retries=1,
        loop_guard=LoopGuardState(max_state_repeats=2),
    )
    request = TaskCreateRequest(task_id="crew#1", policy_inline=policy)
    manager = TaskManager()
    crew = DummyCrew()

    response = run_crewai_with_reliability(
        manager,
        request,
        crew,
    )

    assert response.message == "accepted"
    assert crew.kickoff_called == 1


def test_gateway_proxy_flow() -> None:
    from examples.gateway_proxy import run_gateway_proxy_flow

    manager = TaskManager()
    policy = Policy(
        id="gateway-policy",
        name="gateway",
        slo_ms=2000,
        budget_usd=1.5,
        max_retries=1,
        loop_guard=LoopGuardState(max_state_repeats=2),
    )
    request = TaskCreateRequest(task_id="gateway#1", policy_inline=policy)

    def upstream(call_request):
        assert call_request.messages == [{"role": "user", "content": "ping"}]
        return ChatCompletionResponse(
            message={"role": "assistant", "content": "pong"},
            usage=LlmUsage(cost_usd=0.3, prompt_tokens=5, completion_tokens=7),
        )

    result = run_gateway_proxy_flow(
        manager,
        request,
        messages=[{"role": "user", "content": "ping"}],
        upstream=upstream,
    )

    assert result.response.message["content"] == "pong"
    assert result.step.task.cost_so_far.usd == pytest.approx(0.3)


def test_full_sdk_loop() -> None:
    from examples.full_sdk_runtime import run_full_sdk_loop

    manager = TaskManager()
    policy = Policy(
        id="sdk-policy",
        name="sdk",
        slo_ms=5000,
        budget_usd=2.5,
        max_retries=1,
        loop_guard=LoopGuardState(max_state_repeats=2),
    )
    request = TaskCreateRequest(task_id="sdk#1", policy_inline=policy)

    def planner(task: Task):
        if task.cost_so_far.usd:
            return None
        return StepPayload(
            observation={"status": "step-recorded"},
            llm_usage=LlmUsage(cost_usd=0.4, prompt_tokens=2, completion_tokens=3),
        )

    response = run_full_sdk_loop(manager, request, planner)

    assert response.message in {"accepted", "completed"}
    assert response.task.cost_so_far.usd == pytest.approx(0.4)
