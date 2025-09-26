"""CrewAI metadata policy sample illustrating Reliability integration."""
from __future__ import annotations

try:
    from crewai import Agent, Crew, Process, Task
except ModuleNotFoundError:  # pragma: no cover - docs only
    Agent = Crew = Process = Task = None  # type: ignore

from core.models import Policy, TaskCreateRequest
from core.runtime.task_manager import TaskManager


def reliability_metadata(flow: str) -> dict:
    """Return policy metadata CrewAI can thread through to the runtime."""
    return {
        "reliability_policy": {
            "flow": flow,
            "slo_ms": 180_000,
            "budget_usd": 0.40,
            "max_retries": 2,
            "loop_guard": {"max_state_repeats": 3},
        }
    }


def kickoff_crewai_flow() -> None:
    if Agent is None or Crew is None or Task is None:
        raise RuntimeError("CrewAI must be installed to run the sample")

    collector = Agent(role="Collector", goal="Negotiate payment", backstory="Demo")
    task = Task(
        description="Call debtor and set plan",
        agent=collector,
        metadata=reliability_metadata("collections_call"),
    )
    Crew(agents=[collector], tasks=[task], process=Process.sequential).kickoff()


def register_task(task_manager: TaskManager, *, task_id: str) -> None:
    """Show how CrewAI metadata maps into a task create request."""
    task_manager.create_task(
        TaskCreateRequest(
            task_id=task_id,
            policy_inline=Policy(
                id="samples.crewai.flow",
                name="CrewAI Flow",
                slo_ms=180_000,
                budget_usd=0.40,
                max_retries=2,
            ),
            metadata=reliability_metadata("collections_call"),
        )
    )


if __name__ == "__main__":  # pragma: no cover - manual sample
    register_task(TaskManager(), task_id="crew#1")
