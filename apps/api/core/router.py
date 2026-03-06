from dataclasses import dataclass

from .schemas import GenerateRequest, Mode, ModelSource
from .settings import Settings


HIGH_RISK_MODES: set[Mode] = {"reviewer"}


@dataclass(frozen=True)
class RoutingDecision:
    source: ModelSource
    reason: str


def external_available(settings: Settings) -> bool:
    return bool(settings.external_api_key and settings.external_model_name)


def choose_model_source(req: GenerateRequest, settings: Settings) -> RoutingDecision:
    if req.data_classification == "restricted":
        return RoutingDecision(source="internal", reason="restricted_data_internal_only")
    if req.preferred_model_source:
        if req.preferred_model_source == "external" and not external_available(settings):
            return RoutingDecision(source="internal", reason="preferred_external_unavailable")
        return RoutingDecision(source=req.preferred_model_source, reason="preferred_model_source")
    total_input_size = len(req.user_input) + len(req.context or "")
    if (
        req.mode in HIGH_RISK_MODES
        and settings.reviewer_default_source == "external"
        and external_available(settings)
    ):
        return RoutingDecision(source="external", reason="reviewer_prefers_external")
    if total_input_size >= settings.long_input_external_threshold and external_available(settings):
        return RoutingDecision(source="external", reason="long_input_prefers_external")
    if settings.default_model_source == "external" and external_available(settings):
        return RoutingDecision(source="external", reason="default_model_source")
    return RoutingDecision(source="internal", reason="default_internal")


def should_fallback_to_external(
    req: GenerateRequest,
    settings: Settings,
    attempt_count: int,
    last_error: str | None,
) -> bool:
    if req.data_classification == "restricted":
        return False
    if not settings.external_fallback_enabled:
        return False
    if not external_available(settings):
        return False
    if attempt_count >= settings.max_attempts and last_error is not None:
        return True
    return False
