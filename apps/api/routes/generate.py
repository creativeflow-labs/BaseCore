from fastapi import APIRouter, Depends

from apps.api.core.policy import enforce_request_policy
from apps.api.core.rewrite_loop import generate_with_routing
from apps.api.core.security import enforce_rate_limit, require_api_key
from apps.api.core.schemas import GenerateRequest, GenerationEnvelope
from apps.api.core.settings import Settings, get_settings
from apps.api.core.telemetry import build_log_payload, write_log

router = APIRouter()


@router.post("/generate", response_model=GenerationEnvelope)
def generate(
    req: GenerateRequest,
    _: None = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
    settings: Settings = Depends(get_settings),
) -> GenerationEnvelope:
    enforce_request_policy(req, settings)
    result = generate_with_routing(req, settings)
    write_log(
        settings.log_dir,
        build_log_payload(
            req_payload=req.model_dump(),
            result_payload=result.model_dump(),
            store_raw_outputs=settings.store_raw_outputs,
        ),
    )
    return result
