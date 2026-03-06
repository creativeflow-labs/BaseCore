from fastapi import FastAPI

from apps.api.core.errors import register_error_handlers
from apps.api.core.settings import get_settings
from apps.api.routes.generate import router as generate_router
from apps.api.routes.health import router as health_router

settings = get_settings()
app = FastAPI(title=settings.app_name)
register_error_handlers(app)
app.include_router(health_router)
app.include_router(generate_router)
