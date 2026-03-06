# BaseCore v0.1 Updated Architecture

## Positioning

BaseCore v0.1 is not a proprietary foundation model. It is an internal AI execution platform that reduces dependence on external APIs by combining:

- Internal open-weight inference
- External provider fallback
- Structured output enforcement
- Validation and rewrite loops
- Logging and eval for future data flywheel

The external path can use OpenAI-compatible APIs directly, with OpenAI as the default operational assumption.

## Product Goal

v0.1 focuses on operational discipline, not raw model quality.

1. Support `builder`, `writer`, `reviewer`
2. Return parseable JSON that matches strict schema
3. Route between internal and external providers with validation-driven fallback

## Architecture

```text
Client
  -> BaseCore API
      -> Policy Guard
      -> Router
          -> Internal Provider (vLLM)
          -> External Provider
      -> Prompt Builder
      -> Validator
      -> Rewrite Loop
      -> Telemetry / Eval Log
```

## Routing Rules

- Restricted data stays on the internal provider.
- Reviewer mode can default to an external provider for higher-quality critique.
- Long inputs can route to external if internal capacity is weaker.
- Internal validation failure can trigger external fallback when allowed.

## Why This Shape

- Internal model quality will be weaker than frontier APIs for some time.
- Routing prevents the product from being blocked by a single provider.
- Schema discipline creates reusable training and evaluation data.
- Logs and goldens are more valuable at this stage than premature fine-tuning.

## Security Baseline

- Do not expose vLLM directly to the public internet.
- Keep provider credentials only in server-side environment variables.
- Store redacted logs for analytics and separate raw logs if needed.
- Treat retrieved context as untrusted input.
- Add request limits, timeout limits, and audit metadata.
- Require service-level API key auth on BaseCore API outside local development.
- Apply rate limiting before model execution.

## Local Development Reality

- The original vLLM deployment path assumes CUDA-capable infrastructure.
- On this Apple Silicon Mac, the practical local options are:
- mock internal provider for API and schema development
- another local OpenAI-compatible server if installed later
- external OpenAI fallback for quality checks

## Data Flywheel

Do not train directly on raw production logs.

Use this sequence:

1. Collect outputs and validation results
2. Mark approved outputs
3. Redact sensitive content
4. Build goldens and regression cases
5. Fine-tune only on curated examples

## v0.2 Direction

- Coach mode
- RAG with source attribution
- Human approval workflow for dataset promotion
- LoRA or SFT experiments from curated approved sets
