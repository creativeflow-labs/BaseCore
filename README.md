# BaseCore

Version: `v0.1.0`

BaseCore is an internal AI execution layer for structured product work. v0.1 focuses on reliable JSON outputs for three modes:

- `builder`
- `writer`
- `reviewer`

The system is designed to run with two tracks:

- Internal open-weight model served through vLLM
- External provider fallback for tasks that need higher quality or fail internal validation

## v0.1 Scope

- Route requests between internal and external providers
- Enforce strict JSON schema outputs
- Validate and rewrite until output passes or attempts are exhausted
- Log execution metadata for evaluation and future dataset curation
- Run smoke/regression/adversarial eval cases

## Layout

```text
apps/
  api/
    core/
    routes/
  eval/
deployments/
data/
```

## Quick Start

1. Copy env values.

```bash
cp .env.example .env
```

2. Start the internal model server when available.

```bash
cd deployments/vllm
docker compose --env-file ../../.env up -d
```

Apple Silicon note:

- The current `deployments/vllm` path assumes NVIDIA CUDA and does not run natively on this Mac setup.
- For local development on this machine, use `INTERNAL_PROVIDER=mock` or point `INTERNAL_PROVIDER=openai-compatible` to a local OpenAI-compatible server such as LM Studio.

3. Start the API.

```bash
uvicorn apps.api.main:app --reload --port 9000
```

4. Test the API.

```bash
curl -X POST http://localhost:9000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "builder",
    "user_input": "영어회화앱 MVP를 4주 로드맵으로 설계해줘. 3탭 구조(스크립트/단어/문화).",
    "goal": "새 앱 기획",
    "tone": "professional",
    "length": "medium"
  }'
```

Provider status can be checked with:

```bash
curl http://localhost:9000/health/providers
```

If you want to use your OpenAI account as the external provider, set:

```bash
EXTERNAL_PROVIDER=openai
EXTERNAL_BASE_URL=https://api.openai.com/v1
EXTERNAL_API_KEY=your_openai_api_key
EXTERNAL_MODEL_NAME=your_selected_model
```

For local-only development without an internal model server, keep:

```bash
INTERNAL_PROVIDER=mock
```

## Minimal Security Defaults

- Keep `ENABLE_AUTH=true` outside local development
- Set `SERVICE_API_KEY` and send it as `X-API-Key`
- Keep `STORE_RAW_OUTPUTS=false` unless you explicitly need raw completion storage
- Use rate limiting for every public or semi-public deployment

## Routing Defaults

- `data_classification=restricted` forces internal-only execution
- `reviewer` requests prefer external when configured
- Long inputs can prefer external through `LONG_INPUT_EXTERNAL_THRESHOLD`
- Internal validation failure can fall back to external when enabled

## Run Tests

```bash
.venv/bin/pytest -q
```

## Run Eval

Internal only:

```bash
.venv/bin/python -m apps.eval.run_eval --sources internal
```

Internal and external comparison:

```bash
.venv/bin/python -m apps.eval.run_eval --sources internal external
```

## Recommended Milestones

1. Get internal vLLM inference stable.
2. Raise schema pass rate with validator and rewrite loop.
3. Add external fallback and policy routing.
4. Accumulate approved outputs and eval results.
5. Use curated data for later LoRA or SFT.
