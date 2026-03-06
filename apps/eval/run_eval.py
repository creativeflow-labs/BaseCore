import argparse
import json
import asyncio
from pathlib import Path
from typing import Any

import httpx

from apps.eval.metrics import summarize, summarize_by


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BaseCore eval cases against one or more model sources.")
    parser.add_argument(
        "--base-url",
        default="inprocess",
        help="BaseCore API base URL or 'inprocess' to run against the local FastAPI app",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["internal"],
        choices=["internal", "external"],
        help="Preferred model sources to evaluate",
    )
    parser.add_argument(
        "--cases-dir",
        default="apps/eval/cases",
        help="Directory containing JSONL eval case files",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional BaseCore API key for X-API-Key",
    )
    return parser.parse_args()


def load_cases(case_file: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in case_file.read_text(encoding="utf-8").splitlines() if line.strip()]


async def run_case(client: httpx.AsyncClient, case: dict[str, Any], source: str) -> dict[str, Any]:
    payload = {
        **case,
        "preferred_model_source": source,
    }
    response = await client.post("/generate", json=payload)
    response.raise_for_status()
    body = response.json()
    body["_requested_source"] = source
    body["_case_mode"] = case["mode"]
    return body


def print_summary(label: str, records: list[dict[str, Any]]) -> None:
    print(label, summarize(records))
    print(f"{label}:by_source", summarize_by(records, "model_source"))
    print(f"{label}:by_mode", summarize_by(records, "_case_mode"))


async def run_eval() -> None:
    args = parse_args()
    root = Path(args.cases_dir)
    files = sorted(root.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"No eval case files found in {root}")

    all_records: list[dict[str, Any]] = []
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    client_kwargs: dict[str, Any] = {
        "timeout": 60.0,
        "headers": headers,
    }
    if args.base_url == "inprocess":
        from apps.api.main import app

        client_kwargs["transport"] = httpx.ASGITransport(app=app)
        client_kwargs["base_url"] = "http://basecore.local"
    else:
        client_kwargs["base_url"] = args.base_url

    async with httpx.AsyncClient(**client_kwargs) as client:
        for source in args.sources:
            source_records: list[dict[str, Any]] = []
            for case_file in files:
                records = [await run_case(client, case, source) for case in load_cases(case_file)]
                source_records.extend(records)
                all_records.extend(records)
                print_summary(f"{case_file.name}:{source}", records)
            print_summary(f"overall:{source}", source_records)

    print_summary("overall:all", all_records)


if __name__ == "__main__":
    asyncio.run(run_eval())
