"""Example flow showing how the OpenAI gateway proxy integrates with tasks."""
from __future__ import annotations

from typing import Callable, Dict, List

from adapters.gateway import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    GatewayForwardResult,
    OpenAIGatewayProxy,
)
from core.models import TaskCreateRequest
from core.runtime.task_manager import TaskManager


def run_gateway_proxy_flow(
    task_manager: TaskManager,
    task_request: TaskCreateRequest,
    messages: List[Dict[str, str]],
    upstream: Callable[[ChatCompletionRequest], ChatCompletionResponse],
) -> GatewayForwardResult:
    """Drive a single OpenAI chat call through the proxy."""

    proxy = OpenAIGatewayProxy(task_manager)
    request = ChatCompletionRequest(task=task_request, messages=messages)
    return proxy.forward_chat_completion(request, upstream)
