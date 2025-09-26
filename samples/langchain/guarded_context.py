"""LangChain guard usage sample against the in-memory task manager."""
from __future__ import annotations

from typing import Any, Dict

try:
    from langchain.agents import AgentExecutor
    from langchain.llms.fake import FakeListLLM
    from langchain.tools import tool
except ModuleNotFoundError:  # pragma: no cover - samples are illustrative only
    AgentExecutor = FakeListLLM = None  # type: ignore

from core.models import LlmUsage, Policy, StepPayload, TaskCreateRequest
from core.runtime.task_manager import TaskManager


def build_demo_agent() -> AgentExecutor:
    """Create a trivial LangChain agent for the sample."""
    if AgentExecutor is None or FakeListLLM is None:
        raise RuntimeError("LangChain must be installed to run the sample")

    @tool
    def echo_tool(text: str) -> str:
        return text

    llm = FakeListLLM(responses=["echo_tool"])
    return AgentExecutor.from_agent_and_tools(agent=llm, tools=[echo_tool])


def run_guarded_agent(task_manager: TaskManager, *, task_id: str, flow: str) -> None:
    """Run the fake agent under a Reliability guard."""
    agent = build_demo_agent()
    task_request = TaskCreateRequest(
        task_id=task_id,
        policy_inline=Policy(
            id="samples.langchain.guard",
            name="LangChain Guard",
            slo_ms=60_000,
            budget_usd=0.05,
            max_retries=2,
        ),
        metadata={"flow": flow},
    )
    task = task_manager.create_task(task_request)

    try:
        agent_output: Dict[str, Any] = agent.invoke({"input": "hello"})
        payload = StepPayload(
            observation={"agent_output": agent_output},
            llm_usage=LlmUsage(prompt_tokens=10, completion_tokens=5, cost_usd=0.001),
        )
        task_manager.record_step(task.id, payload)
    finally:
        task_manager.cancel_task(task.id)


def main() -> None:
    manager = TaskManager()
    run_guarded_agent(manager, task_id="demo#1", flow="prior_auth")


if __name__ == "__main__":  # pragma: no cover - manual sample
    main()
