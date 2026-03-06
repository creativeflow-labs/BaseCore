from dataclasses import dataclass
import json

import httpx
from openai import OpenAI

from .settings import Settings


@dataclass(frozen=True)
class ProviderConfig:
    source: str
    provider: str
    base_url: str | None
    api_key: str | None
    model_name: str


def build_provider_config(source: str, settings: Settings) -> ProviderConfig:
    if source == "internal":
        return ProviderConfig(
            source="internal",
            provider=settings.internal_provider,
            base_url=settings.internal_base_url,
            api_key=settings.internal_api_key,
            model_name=settings.internal_model_name,
        )
    if source == "external":
        if not settings.external_api_key or not settings.external_model_name:
            raise ValueError("External provider is not fully configured")
        base_url = settings.external_base_url or "https://api.openai.com/v1"
        return ProviderConfig(
            source="external",
            provider=settings.external_provider,
            base_url=base_url,
            api_key=settings.external_api_key,
            model_name=settings.external_model_name,
        )
    raise ValueError(f"Unknown provider source: {source}")


def chat_completion(
    provider: ProviderConfig,
    messages: list[dict[str, str]],
    timeout_seconds: int,
    temperature: float,
    max_tokens: int,
):
    if provider.provider == "mock":
        return _mock_chat_completion(messages=messages)
    client = OpenAI(base_url=provider.base_url, api_key=provider.api_key, timeout=timeout_seconds)
    return client.chat.completions.create(
        model=provider.model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def probe_provider(provider: ProviderConfig, timeout_seconds: int) -> dict[str, str]:
    if provider.provider == "mock":
        return {"status": "ok", "detail": "mock_provider"}
    try:
        response = httpx.get(
            f"{provider.base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {provider.api_key}"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return {"status": "ok", "detail": "reachable"}
    except Exception as exc:
        return {"status": "error", "detail": f"{type(exc).__name__}"}


class _MockMessage:
    def __init__(self, content: str):
        self.content = content


class _MockChoice:
    def __init__(self, content: str):
        self.message = _MockMessage(content)


class _MockResponse:
    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]


def _mock_chat_completion(messages: list[dict[str, str]]) -> _MockResponse:
    user_content = messages[-1]["content"] if messages else "{}"
    try:
        payload = json.loads(user_content)
        task = payload.get("task", {})
    except Exception:
        task = {}
    mode = _infer_mode(messages)
    user_input = task.get("user_input", "")
    tone = task.get("tone") or "neutral"
    length = task.get("length") or "medium"

    if mode == "builder":
        content = json.dumps(
            {
                "product_one_liner": f"Mock BaseCore plan for {user_input[:40] or 'task'}",
                "target_user": "Internal product operator",
                "core_loop_steps": ["receive request", "produce structured plan", "validate output"],
                "mvp_in_scope": ["structured JSON output", "basic validation", "logging"],
                "mvp_out_scope": ["fine-tuning pipeline", "advanced agent memory"],
                "risks": ["mock provider is not quality representative"],
                "success_metrics": ["schema pass rate", "fallback rate"],
                "test_cases": ["valid builder response", "non-empty scope fields"],
                "validators": ["JSON schema passes", "required arrays are populated"],
            },
            ensure_ascii=False,
        )
        return _MockResponse(content)

    if mode == "writer":
        content = json.dumps(
            {
                "variants": [
                    {
                        "tone": tone,
                        "length": length,
                        "text": f"Mock variant 1 for: {user_input[:80]}",
                    },
                    {
                        "tone": tone,
                        "length": length,
                        "text": f"Mock variant 2 for: {user_input[:80]}",
                    },
                ],
                "constraints_applied": [f"tone matched {tone}", f"length matched {length}"],
                "warnings": ["mock provider output is for local development only"],
            },
            ensure_ascii=False,
        )
        return _MockResponse(content)

    content = json.dumps(
        {
            "summary": f"Mock review for: {user_input[:60] or 'artifact'}",
            "issues": [
                {
                    "severity": "medium",
                    "evidence": "Mock provider cannot inspect real semantics deeply.",
                    "fix": "Run the same request through the external provider before shipping.",
                }
            ],
            "confidence": 0.42,
            "recheck_steps": ["rerun with external provider", "review evidence manually"],
        },
        ensure_ascii=False,
    )
    return _MockResponse(content)


def _infer_mode(messages: list[dict[str, str]]) -> str:
    text = " ".join(message.get("content", "") for message in messages)
    if "Mode: BUILDER" in text:
        return "builder"
    if "Mode: WRITER" in text:
        return "writer"
    return "reviewer"
