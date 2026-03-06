from apps.eval.metrics import summarize, summarize_by


def test_summarize_includes_latency_and_fallback_rate() -> None:
    records = [
        {
            "validation_status": "passed",
            "attempts": 1,
            "latency_ms": 100,
            "fallback_used": False,
            "model_source": "internal",
            "_case_mode": "writer",
        },
        {
            "validation_status": "failed",
            "attempts": 2,
            "latency_ms": 300,
            "fallback_used": True,
            "error": "JSON_PARSE_ERROR",
            "model_source": "external",
            "_case_mode": "writer",
        },
    ]
    summary = summarize(records)
    assert summary["pass_rate"] == 0.5
    assert summary["avg_attempts"] == 1.5
    assert summary["avg_latency_ms"] == 200.0
    assert summary["fallback_rate"] == 0.5


def test_summarize_by_groups_records() -> None:
    records = [
        {"validation_status": "passed", "attempts": 1, "latency_ms": 100, "fallback_used": False, "model_source": "internal"},
        {"validation_status": "failed", "attempts": 1, "latency_ms": 200, "fallback_used": False, "model_source": "external"},
    ]
    grouped = summarize_by(records, "model_source")
    assert grouped["internal"]["total"] == 1
    assert grouped["external"]["failed"] == 1
