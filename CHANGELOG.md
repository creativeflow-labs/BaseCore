# Changelog

## v0.2.0

- Builder mode redesigned for execution-ready product specs
- Added structured builder fields for user flow, screens, system actions, operational metrics, and acceptance criteria
- Strengthened builder prompts and semantic validation rules
- Updated local mock provider to emit v0.2 builder output
- Expanded regression coverage around builder quality and fallback behavior

## v0.1.0

- Initial BaseCore scaffold released
- FastAPI API with builder, writer, reviewer modes
- Internal and external provider routing with fallback
- JSON schema validation and rewrite loop
- Redacted logging, API key auth, and rate limiting baseline
- Provider health endpoints and structured error handling
- Eval runner with internal and external comparison support
- Local Apple Silicon development path via mock internal provider
