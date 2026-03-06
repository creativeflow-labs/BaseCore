import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


EMAIL_PATTERN = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d[\d -]{7,}\d)\b")


def redact_text(value: str | None) -> str | None:
    if value is None:
        return None
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    return redacted


def build_log_payload(
    *,
    req_payload: dict[str, Any],
    result_payload: dict[str, Any],
    store_raw_outputs: bool,
) -> dict[str, Any]:
    payload = {
        **result_payload,
        "request": {
            "mode": req_payload.get("mode"),
            "goal": redact_text(req_payload.get("goal")),
            "tone": redact_text(req_payload.get("tone")),
            "length": redact_text(req_payload.get("length")),
            "data_classification": req_payload.get("data_classification"),
            "user_input": redact_text(req_payload.get("user_input")),
            "context": redact_text(req_payload.get("context")),
        },
    }
    if not store_raw_outputs:
        payload.pop("raw", None)
    elif payload.get("raw"):
        payload["raw"] = redact_text(payload["raw"])
    return payload


def write_log(log_dir: Path, payload: dict[str, Any]) -> None:
    timestamp = datetime.now(UTC).strftime("%Y%m%d")
    output_path = log_dir / f"{timestamp}.jsonl"
    line = json.dumps(payload, ensure_ascii=False)
    with output_path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")
