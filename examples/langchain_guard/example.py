"""LangChain integration helpers for the Reliability API skeleton."""
from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Dict, Optional

from langchain.agents import AgentExecutor

from core.models import LlmUsage, StepPayload, StepResponse, TaskCreateRequest
from core.runtime.task_manager import TaskManager


class LangChainReliabilityGuard(AbstractContextManager["LangChainReliabilityGuard"]):
    """Minimal context manager mirroring the ergonomic guard helper."""

    def __init__(self, task_manager: TaskManager, task_request: TaskCreateRequest) -> None:
        self._task_manager = task_manager
        self._task_request = task_request
        self._task_id: Optional[str] = None

    def __enter__(self) -> "LangChainReliabilityGuard":
        task = self._task_manager.create_task(self._task_request)
        self._task_id = task.id
        return self

    def __exit__(self, exc_type, exc, tb) -> Optional[bool]:  # type: ignore[override]
        if exc_type and self._task_id:
            self._task_manager.cancel_task(self._task_id)
        return None

    def invoke_agent(
        self,
        agent: AgentExecutor,
        agent_input: Dict[str, Any],
        *,
        llm_usage: Optional[LlmUsage] = None,
    ) -> StepResponse:
        if not self._task_id:
            raise RuntimeError("Guard must be entered before invoking the agent")
        agent_output = agent.invoke(agent_input)
        payload = StepPayload(
            observation={"agent_output": agent_output, "agent_input": agent_input},
            llm_usage=llm_usage,
        )
        return self._task_manager.record_step(self._task_id, payload)


def run_guarded_langchain_flow(
    task_manager: TaskManager,
    task_request: TaskCreateRequest,
    agent: AgentExecutor,
    agent_input: Dict[str, Any],
    *,
    llm_usage: Optional[LlmUsage] = None,
) -> StepResponse:
    """Utility that mirrors the SDK guard usage pattern."""

    with LangChainReliabilityGuard(task_manager, task_request) as guard:
        return guard.invoke_agent(agent, agent_input, llm_usage=llm_usage)
