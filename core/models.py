"""Core data models for Reliability API runtime.

These Pydantic models are shared between the FastAPI application and
in-memory runtime components. They intentionally cover only the subset of
fields required for the v0 skeleton implementation; additional attributes can
be layered on without breaking the public API surface.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, root_validator


class TaskStatus(str, Enum):
    """Lifecycle states for a task tracked by the runtime."""

    PENDING = "pending"
    RUNNING = "running"
    ESCALATED = "escalated"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Budget(BaseModel):
    usd: float = Field(..., ge=0, description="Maximum USD budget for the task")
    tokens: Optional[int] = Field(
        None, ge=0, description="Optional token budget for LLM interactions"
    )
    seconds: Optional[int] = Field(
        None, ge=0, description="Optional wall-clock budget for tools"
    )


class CostSnapshot(BaseModel):
    usd: float = Field(0, ge=0, description="USD cost incurred so far")
    tokens: Optional[int] = Field(
        None, ge=0, description="Tokens consumed across all LLM calls"
    )
    seconds: Optional[int] = Field(
        None, ge=0, description="Wall-clock time spent in tools"
    )


class RetryState(BaseModel):
    max: int = Field(0, ge=0, description="Maximum retries permitted")
    attempted: int = Field(0, ge=0, description="Number of retries already used")


class LoopGuardState(BaseModel):
    max_state_repeats: int = Field(3, ge=0)
    min_novelty: float = Field(0.0, ge=0.0, le=1.0)
    repeats: int = Field(0, ge=0)


class HitlRoute(BaseModel):
    route: str
    on: List[str] = Field(default_factory=list)


class Policy(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    slo_ms: int = Field(..., ge=0)
    budget_usd: float = Field(..., ge=0)
    max_retries: int = Field(0, ge=0)
    loop_guard: Optional[LoopGuardState] = None
    hitl: Optional[HitlRoute] = None


class Task(BaseModel):
    id: str = Field(..., alias="task_id")
    tenant_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    policy_id: Optional[str] = None
    policy_inline: Optional[Policy] = None
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    budget: Budget
    cost_so_far: CostSnapshot = Field(default_factory=CostSnapshot)
    retries: RetryState = Field(default_factory=RetryState)
    loop_guard: LoopGuardState = Field(default_factory=LoopGuardState)
    hitl: Optional[HitlRoute] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    last_state_hash: Optional[str] = None
    result: Optional[Dict[str, str]] = None
    error: Optional[Dict[str, str]] = None

    @root_validator(pre=True)
    def populate_budget_from_policy(cls, values: Dict[str, object]) -> Dict[str, object]:
        policy: Optional[Policy] = values.get("policy_inline")
        budget = values.get("budget")
        if policy and not budget:
            values["budget"] = Budget(usd=policy.budget_usd)
        return values

    def apply_policy_defaults(self) -> None:
        """Populate policy-derived fields for runtime convenience."""

        policy = self.policy_inline
        if not policy:
            return

        if not self.deadline_at and policy.slo_ms:
            self.deadline_at = datetime.utcnow() + timedelta(milliseconds=policy.slo_ms)
        if not self.retries.max:
            self.retries.max = policy.max_retries
        if policy.loop_guard:
            self.loop_guard = policy.loop_guard.model_copy()
        elif not self.loop_guard:
            self.loop_guard = LoopGuardState()
        self.budget.usd = policy.budget_usd
        if policy.hitl:
            self.hitl = policy.hitl.model_copy()


class ToolAction(BaseModel):
    name: str
    schema: Optional[Dict[str, object]] = None
    payload: Dict[str, object]
    idempotency_key: Optional[str] = None
    timeout_ms: Optional[int] = Field(None, ge=0)


class LlmUsage(BaseModel):
    prompt_tokens: Optional[int] = Field(None, ge=0)
    completion_tokens: Optional[int] = Field(None, ge=0)
    cost_usd: Optional[float] = Field(None, ge=0)


class StepPayload(BaseModel):
    observation: Optional[Dict[str, object]] = None
    actions: List[ToolAction] = Field(default_factory=list)
    llm_usage: Optional[LlmUsage] = None


class PolicyUpsertRequest(Policy):
    tenant_id: Optional[str] = None


class TaskCreateRequest(BaseModel):
    task_id: str
    policy_id: Optional[str] = None
    policy_inline: Optional[Policy] = None
    metadata: Dict[str, str] = Field(default_factory=dict)

    def to_task(self, policy: Optional[Policy] = None) -> Task:
        policy_to_use = policy or self.policy_inline
        if not policy_to_use and not self.policy_id:
            raise ValueError("Either policy_id or policy_inline must be provided")
        if not policy_to_use:
            policy_to_use = Policy(
                id=self.policy_id,
                slo_ms=60000,
                budget_usd=0.1,
                max_retries=0,
            )
        return Task(
            task_id=self.task_id,
            policy_id=self.policy_id,
            policy_inline=policy_to_use,
            metadata=self.metadata,
            budget=Budget(usd=policy_to_use.budget_usd),
        )


class StepResponse(BaseModel):
    task: Task
    message: str = "accepted"
