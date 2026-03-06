from fastapi import HTTPException, status

from .schemas import GenerateRequest
from .settings import Settings


def enforce_request_policy(req: GenerateRequest, settings: Settings) -> None:
    if len(req.user_input) > settings.max_input_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"user_input exceeds {settings.max_input_chars} characters",
        )
    if req.context and len(req.context) > settings.max_context_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"context exceeds {settings.max_context_chars} characters",
        )
