from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


Mode = Literal["builder", "writer", "reviewer"]
ModelSource = Literal["internal", "external"]
DataClassification = Literal["public", "internal", "restricted"]


class GenerateRequest(BaseModel):
    mode: Mode
    user_input: str = Field(min_length=1)
    context: str | None = None
    goal: str | None = None
    tone: str | None = None
    length: str | None = None
    data_classification: DataClassification = "internal"
    preferred_model_source: ModelSource | None = None
    prompt_version: str = "v0.2"
    schema_version: str = "v0.2"

class BuilderFlowStep(BaseModel):
    step: str
    user_action: str
    system_response: str


class BuilderScreen(BaseModel):
    name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]

    @field_validator("inputs", "outputs")
    @classmethod
    def require_non_empty_screen_fields(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("field must not be empty")
        return value


class BuilderSystemAction(BaseModel):
    trigger: str
    action: str
    output: str


class BuilderMetric(BaseModel):
    name: str
    measurement_method: str
    signal: str


class BuilderAcceptanceCriterion(BaseModel):
    scenario: str
    expected_result: str


class BuilderOutput(BaseModel):
    product_one_liner: str
    primary_user_segment: str
    user_pain_points: list[str]
    user_flow_steps: list[BuilderFlowStep]
    screens: list[BuilderScreen]
    system_actions: list[BuilderSystemAction]
    mvp_in_scope: list[str]
    mvp_out_scope: list[str]
    operational_metrics: list[BuilderMetric]
    acceptance_criteria: list[BuilderAcceptanceCriterion]
    risks: list[str]

    @field_validator(
        "user_pain_points",
        "user_flow_steps",
        "screens",
        "system_actions",
        "mvp_in_scope",
        "operational_metrics",
        "acceptance_criteria",
        "risks",
    )
    @classmethod
    def require_non_empty_lists(cls, value: list) -> list:
        if not value:
            raise ValueError("field must not be empty")
        return value


class WriterVariant(BaseModel):
    tone: str
    length: str
    text: str


class WriterOutput(BaseModel):
    variants: list[WriterVariant]
    constraints_applied: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("variants")
    @classmethod
    def require_variants(cls, value: list[WriterVariant]) -> list[WriterVariant]:
        if not value:
            raise ValueError("variants must not be empty")
        return value


class ReviewIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    evidence: str
    fix: str


class ReviewerOutput(BaseModel):
    summary: str
    issues: list[ReviewIssue]
    confidence: float = Field(ge=0.0, le=1.0)
    recheck_steps: list[str] = Field(default_factory=list)


class GenerationEnvelope(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    mode: Mode
    model_source: ModelSource
    model_name: str
    routing_reason: str
    prompt_version: str
    schema_version: str
    attempts: int
    latency_ms: int
    validation_status: Literal["passed", "failed"]
    fallback_used: bool = False
    result: dict[str, Any] | None = None
    error: str | None = None
    raw: str | None = None
