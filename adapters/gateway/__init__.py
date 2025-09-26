"""Lightweight OpenAI-style gateway proxy helpers.

The real product will expose an HTTP service that accepts OpenAI compatible
requests and forwards them to the upstream provider while enforcing Reliability
task guarantees.  For the skeleton repository we provide a minimal in-process
proxy that captures the important touch points so we can write unit tests and
samples covering **Option A** (zero/low-touch proxy).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from fastapi import HTTPException, status
from pydantic import BaseModel

from core.models import LlmUsage, StepPayload, StepResponse, TaskCreateRequest
from core.runtime.task_manager import TaskManager


class ChatCompletionRequest(BaseModel):
    """Subset of the OpenAI chat completion schema we need for tests."""

    task: TaskCreateRequest
    messages: List[Dict[str, str]]
    model: str = "gpt-4o-mini"


class ChatCompletionResponse(BaseModel):
    """Minimal chat completion response envelope."""

    message: Dict[str, str]
    usage: LlmUsage


@dataclass
class GatewayForwardResult:
    """Return type that surfaces both upstream and runtime outcomes."""

    response: ChatCompletionResponse
    step: StepResponse


class OpenAIGatewayProxy:
    """Forward OpenAI requests while recording enforcement telemetry."""

    def __init__(self, task_manager: TaskManager) -> None:
        self._task_manager = task_manager

    def forward_chat_completion(
        self,
        request: ChatCompletionRequest,
        upstream: Callable[[ChatCompletionRequest], ChatCompletionResponse],
    ) -> GatewayForwardResult:
        """Forward the request and emit a Reliability step event."""

        try:
            task = self._task_manager.create_task(request.task)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_409_CONFLICT:
                raise
            task = self._task_manager.get_task(request.task.task_id)

        response = upstream(request)
        payload = StepPayload(
            observation={
                "model": request.model,
                "messages": request.messages,
                "response": response.message,
            },
            llm_usage=response.usage,
        )
        step = self._task_manager.record_step(task.id, payload)
        return GatewayForwardResult(response=response, step=step)


__all__ = [
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "GatewayForwardResult",
    "OpenAIGatewayProxy",
]