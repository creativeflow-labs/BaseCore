import time

from .modes import build_messages
from .providers import build_provider_config, chat_completion
from .router import RoutingDecision, choose_model_source, should_fallback_to_external
from .schemas import GenerateRequest, GenerationEnvelope
from .settings import Settings
from .validator import validate_text_is_json_and_schema


def max_tokens_for_mode(mode: str) -> int:
    if mode == "writer":
        return 1600
    if mode == "builder":
        return 1400
    return 1200


def _run_attempts(
    source: str,
    routing_reason: str,
    req: GenerateRequest,
    settings: Settings,
    fallback_used: bool = False,
) -> tuple[GenerationEnvelope, str | None]:
    provider = build_provider_config(source, settings)
    last_error = None
    last_text = None
    started_at = time.perf_counter()

    for attempt in range(1, settings.max_attempts + 1):
        messages = build_messages(
            mode=req.mode,
            user_payload={
                "goal": req.goal,
                "tone": req.tone,
                "length": req.length,
                "context": req.context,
                "user_input": req.user_input,
            },
            validation_error=last_error,
        )
        try:
            response = chat_completion(
                provider=provider,
                messages=messages,
                timeout_seconds=settings.request_timeout_seconds,
                temperature=0.0,
                max_tokens=max_tokens_for_mode(req.mode),
            )
        except Exception as exc:
            last_error = f"PROVIDER_ERROR:{type(exc).__name__}"
            break
        text = response.choices[0].message.content or ""
        last_text = text
        ok, reason, obj = validate_text_is_json_and_schema(req.mode, text)
        if ok:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            envelope = GenerationEnvelope(
                mode=req.mode,
                model_source=source,
                model_name=provider.model_name,
                routing_reason=routing_reason,
                prompt_version=req.prompt_version,
                schema_version=req.schema_version,
                attempts=attempt,
                latency_ms=latency_ms,
                validation_status="passed",
                fallback_used=fallback_used,
                result=obj.model_dump(),
                raw=text,
            )
            return envelope, None
        last_error = reason

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    failed_envelope = GenerationEnvelope(
        mode=req.mode,
        model_source=source,
        model_name=provider.model_name,
        routing_reason=routing_reason,
        prompt_version=req.prompt_version,
        schema_version=req.schema_version,
        attempts=settings.max_attempts,
        latency_ms=latency_ms,
        validation_status="failed",
        fallback_used=fallback_used,
        error=last_error or "UNKNOWN_VALIDATION_ERROR",
        raw=last_text,
    )
    return failed_envelope, last_error


def generate_with_routing(req: GenerateRequest, settings: Settings) -> GenerationEnvelope:
    primary_decision: RoutingDecision = choose_model_source(req, settings)
    envelope, last_error = _run_attempts(
        primary_decision.source,
        primary_decision.reason,
        req,
        settings,
    )
    if envelope.validation_status == "passed":
        return envelope

    if (
        primary_decision.source == "internal"
        and should_fallback_to_external(req, settings, envelope.attempts, last_error)
    ):
        fallback_envelope, _ = _run_attempts(
            "external",
            f"fallback_after_internal_failure:{last_error}",
            req,
            settings,
            fallback_used=True,
        )
        return fallback_envelope
    return envelope
