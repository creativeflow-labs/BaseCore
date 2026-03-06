# Internal Model Notes

Recommended starting point for v0.1:

- Small open-weight distilled reasoning/chat model
- 7B to 14B class for predictable serving cost

Operational rules:

- Pin model id explicitly
- Do not use public unauthenticated exposure
- Keep vLLM reachable only through BaseCore API or private network
- Record model version in every generation log
