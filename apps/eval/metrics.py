from collections import Counter, defaultdict
from typing import Any


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    passed = [record for record in records if record.get("validation_status") == "passed"]
    failed = [record for record in records if record.get("validation_status") == "failed"]
    avg_attempts = round(sum(record.get("attempts", 0) for record in records) / total, 2) if total else 0.0
    avg_latency_ms = round(sum(record.get("latency_ms", 0) for record in records) / total, 2) if total else 0.0
    failure_reasons = Counter(record.get("error") for record in failed if record.get("error"))
    fallback_rate = round(
        sum(1 for record in records if record.get("fallback_used")) / total,
        4,
    ) if total else 0.0
    return {
        "total": total,
        "pass_rate": round(len(passed) / total, 4) if total else 0.0,
        "avg_attempts": avg_attempts,
        "avg_latency_ms": avg_latency_ms,
        "fallback_rate": fallback_rate,
        "failed": len(failed),
        "top_failure_reasons": failure_reasons.most_common(5),
    }


def summarize_by(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get(field, "unknown"))].append(record)
    return {key: summarize(value) for key, value in sorted(grouped.items())}
