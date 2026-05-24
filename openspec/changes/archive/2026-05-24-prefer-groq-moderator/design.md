## Context

DebateX dynamic models are loaded based on available keys. When both OpenRouter and Groq keys are configured, the debate models from both are appended concurrently into `debate_MODELS`. However, the moderator model is currently set to OpenRouter's free deepseek model since that block executes first. We will optimize the loading priorities so that the moderator defaults to Groq Llama 3.3 70B if `GROQ_API_KEY` is present.

## Goals / Non-Goals

**Goals:**
- Prioritize high-performance `groq/llama-3.3-70b-versatile` as the Chairman/Moderator when both Groq and OpenRouter keys are present.
- Ensure that the debate models from BOTH OpenRouter and Groq continue to be dynamically merged and concurrently utilized for the council.

**Non-Goals:**
- No change to individual provider wrapper clients (`groq.py` or `openrouter.py`).

## Decisions

### Decision: Update moderator selection logic in config.py
We will modify the model loading block in `backend/config.py` so that:
1. Both `OPENROUTER_API_KEY` and `GROQ_API_KEY` blocks concurrently extend `debate_MODELS` (already implemented).
2. If `GROQ_API_KEY` is present, it explicitly overrides `moderator_MODEL` to `groq/llama-3.3-70b-versatile` (rather than only setting it `if not moderator_MODEL`).
- *Rationale*: A high-performance Groq model is significantly faster and more capable of high-quality synthesis compared to OpenRouter free models, making it the superior choice for Moderator.

## Risks / Trade-offs

- **[Risk] Groq Key Missing** → *Mitigation*: The code is fully guarded; if only OpenRouter is present, it correctly defaults back to DeepSeek free model for the moderator.
