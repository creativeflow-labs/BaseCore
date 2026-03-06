import json

from pydantic import ValidationError

from .schemas import BuilderOutput, ReviewerOutput, WriterOutput


def parse_json(text: str) -> dict:
    return json.loads(text.strip())


def validate_output(mode: str, data: dict):
    if mode == "builder":
        return BuilderOutput.model_validate(data)
    if mode == "writer":
        return WriterOutput.model_validate(data)
    if mode == "reviewer":
        return ReviewerOutput.model_validate(data)
    raise ValueError(f"Unknown mode: {mode}")


def semantic_checks(mode: str, obj) -> str | None:
    if mode == "builder":
        if len(obj.primary_user_segment.split()) > 12:
            return "BUILDER_PRIMARY_USER_SEGMENT_TOO_BROAD"
        if any("이상" in metric.name for metric in obj.operational_metrics):
            return "BUILDER_METRIC_NAME_CONTAINS_TARGET_TEXT"
    if mode == "writer":
        if any(not variant.text.strip() for variant in obj.variants):
            return "WRITER_VARIANT_TEXT_EMPTY"
    if mode == "reviewer":
        if obj.confidence > 0.95 and not obj.issues:
            return "REVIEWER_CONFIDENCE_TOO_HIGH_WITHOUT_ISSUES"
    return None


def validate_text_is_json_and_schema(mode: str, text: str):
    try:
        data = parse_json(text)
    except Exception as exc:
        return False, f"JSON_PARSE_ERROR: {exc}", None

    try:
        obj = validate_output(mode, data)
    except ValidationError as exc:
        return False, f"SCHEMA_ERROR: {exc.errors()[:3]}", None

    semantic_error = semantic_checks(mode, obj)
    if semantic_error:
        return False, semantic_error, None
    return True, "OK", obj
