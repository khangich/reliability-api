"""LangChain reliable tool decorator illustration."""
from __future__ import annotations

from typing import Callable

try:
    from langchain.agents import AgentExecutor
    from langchain.llms.fake import FakeListLLM
    from langchain.tools import Tool
except ModuleNotFoundError:  # pragma: no cover - docs only
    AgentExecutor = FakeListLLM = Tool = None  # type: ignore

from core.models import Policy, TaskCreateRequest
from core.runtime.task_manager import TaskManager


def reliable_tool(tool_func: Callable[..., str]) -> Callable[..., str]:
    """Toy decorator mirroring the SDK reliable tool helper."""

    def wrapper(*args, **kwargs) -> str:
        result = tool_func(*args, **kwargs)
        # Production decorator would report the action and enforce retries.
        return result

    return wrapper


@reliable_tool
def submit_prior_auth(payload: dict) -> str:
    return "submitted"


def build_agent() -> AgentExecutor:
    if AgentExecutor is None or FakeListLLM is None or Tool is None:
        raise RuntimeError("LangChain must be installed to run the sample")
    llm = FakeListLLM(responses=["submit_prior_auth"])
    return AgentExecutor.from_agent_and_tools(
        agent=llm,
        tools=[Tool.from_function(name="submit_prior_auth", func=submit_prior_auth)],
    )


def run_with_tool(task_manager: TaskManager) -> None:
    agent = build_agent()
    task = task_manager.create_task(
        TaskCreateRequest(
            task_id="decorator#1",
            policy_inline=Policy(
                id="samples.langchain.decorator",
                name="LangChain Reliable Tool",
                slo_ms=120_000,
                budget_usd=0.25,
                max_retries=3,
            ),
            metadata={"flow": "prior_auth"},
        )
    )
    agent.invoke({"input": "Submit prior auth"})
    task_manager.cancel_task(task.id)


if __name__ == "__main__":  # pragma: no cover - manual sample
    run_with_tool(TaskManager())
