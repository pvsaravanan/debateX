# Development Guide

## Tech Stack & Requirements

- **Backend**: Python 3.10+, FastAPI, Uvicorn, httpx, pydantic, python-dotenv
- **Frontend**: React 19, Vite 7, react-markdown + remark-gfm, vanilla CSS (dark theme via CSS variables)
- **System**: Node.js >= 20 LTS, npm >= 10, uv (Python package manager)

## Setup for Development

### Backend
Run from the **project root** — the backend package uses relative imports:
```bash
uv sync
uv run python -m backend.main
# or with auto-reload:
uv run uvicorn backend.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

## Architecture Orientation

- **`backend/debate.py` → `run_debate_stream()`** is the single orchestrator: an async generator yielding one event per phase (`routing_*`, `round1_*`…`round5_*`, `complete`/`error`). Both API endpoints consume it — change round logic here, once.
- **`backend/router.py`** classifies the query and assembles the council + cost estimate; **`backend/roles.py` → `allocate_personas()`** assigns the adversarial personas (the older `allocate_roles()` is test-pinned legacy — don't change its semantics).
- The frontend's SSE switch lives in `frontend/src/App.jsx` and must stay in lockstep with the event names emitted by `run_debate_stream()`.

## Common Workflows

### Adding a New Provider
The LLM integration is modular:
1. Create `backend/new_provider.py` (mirror `groq.py`: use `http_client.get_client()`, return `{'content', 'reasoning_details'}`, raise `ValueError` with the API's message on HTTP errors).
2. Update `backend/llm.py` to route a prefix (e.g., `new_provider/`) to it.
3. Register the API key in `.env` and `backend/config.py`.

### Adding a New Model
1. Append it to `debate_MODELS` in `backend/config.py` (prefix decides the provider).
2. Add a matching substring to the category `preferences` in `backend/router.py` so the router can council it.
3. Add pricing to `PRICING_TABLE` (skip for `:free` models — they're always $0).

### Testing
```bash
# Unit tests (no network needed — LLM classification falls back to the local regex classifier)
uv run python -m unittest tests.test_roles tests.test_router
```
- `tests/` also contains ad-hoc live-provider scripts (`test_or.py`, `test_groq.py`, `test_stream_5rounds.py`, …).
- To test pipeline changes without API spend: monkeypatch `backend.llm.query_openrouter` / `backend.llm.query_groq` with canned responses and drain `run_debate_stream()` — this exercises the entire event protocol. Note the chairman/challenger prompts embed earlier rounds' text, so order canned-response matching from most-specific prompt marker to least.

### Troubleshooting
- **Backend won't start (`ModuleNotFoundError`)**: run it from the project root as `python -m backend.main` — never from inside `backend/`.
- **Frontend CORS errors**: backend must be on port `8001`; the allowed origins list is in `backend/main.py`.
- **Models timing out**: check OpenRouter/Groq load, or raise the `timeout` argument in `backend/llm.py::query_model`.
- **"Event loop is closed" in scripts**: fixed at the client level (`http_client.py` re-creates the pooled client per event loop) — if you see it, you're likely caching your own client across `asyncio.run()` calls.
- **Empty councils / weird routing**: your model names don't match any category preference substrings in `router.py`; the router then falls back to the first 3 configured models.
