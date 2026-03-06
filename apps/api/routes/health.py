from fastapi import APIRouter, Depends

from apps.api.core.providers import build_provider_config, probe_provider
from apps.api.core.settings import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/health/providers")
def provider_health(settings: Settings = Depends(get_settings)) -> dict:
    providers: dict[str, dict[str, str | bool | None]] = {}

    providers["internal"] = {
        "configured": True,
        "model_name": settings.internal_model_name,
        **probe_provider(
            build_provider_config("internal", settings),
            timeout_seconds=min(settings.request_timeout_seconds, 5),
        ),
    }

    external_configured = bool(settings.external_api_key and settings.external_model_name)
    external_payload: dict[str, str | bool | None] = {
        "configured": external_configured,
        "model_name": settings.external_model_name,
        "provider": settings.external_provider,
    }
    if external_configured:
        external_payload.update(
            probe_provider(
                build_provider_config("external", settings),
                timeout_seconds=min(settings.request_timeout_seconds, 5),
            )
        )
    else:
        external_payload.update({"status": "not_configured", "detail": "missing_api_key_or_model"})
    providers["external"] = external_payload

    overall = "ok"
    if providers["internal"]["status"] != "ok" and providers["external"]["status"] != "ok":
        overall = "degraded"

    return {
        "status": overall,
        "providers": providers,
    }
