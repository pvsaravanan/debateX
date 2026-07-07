# Deployment & Configuration

## Configuration

DebateX relies on environment variables set in a `.env` file at the root of the project (see `.env.example`).

### Environment Variables
| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | Optional* | API key for OpenRouter models (free-tier council members) |
| `GROQ_API_KEY` | Optional* | API key for Groq models (default Chairman) |
| `ENABLE_METACOGNITION` | Optional | `true` enables pre-flight self-consistency probing (3 temperature samples per model, max 3 models). Default `false` — it multiplies API call volume, which free-tier rate limits usually cannot absorb. |

*\*At least one API key must be provided. If both are set, models from both providers are registered and Groq's `llama-3.3-70b-versatile` becomes the Chairman.*

### Customizing Council Members
Edit `backend/config.py` to change which models are registered:

- Models prefixed with `groq/` are routed to the Groq API; all others go to OpenRouter.
- `moderator_MODEL` is the Chairman used for Round-5 synthesis and title generation.

When adding a model, also update `backend/router.py`:
- Add a substring for it to the relevant category `preferences` lists so the query router can select it into councils (unmatched models only join via the fallback path).
- Add it to `PRICING_TABLE` for accurate cost estimates. Models whose name ends in `:free` are always costed at $0.

### Query Routing & Cost Estimation
Every query is classified (technical/code, creative, factual/research, ethical/philosophical, math/logic) before Round 1. The router assembles a preference-ordered council of at most 4 models and projects the USD cost of the full deliberation, which is shown in the UI's Routing panel.

## Deployment

DebateX ships as two processes:

```bash
# Backend (from the project root — relative imports require it)
uv run python -m backend.main          # serves on http://0.0.0.0:8001

# Frontend
cd frontend && npm install && npm run build
npm run preview                         # or serve dist/ with any static server
```

On Windows, `run.bat` starts both with hot-reload; on macOS/Linux use `start.sh`.

### Production notes
- Storage is JSON-files-on-disk (`data/conversations/`), serialized behind a process-wide lock. **Run a single backend process**; multiple uvicorn workers sharing the data directory require replacing `backend/storage.py` with a database.
- If the frontend is served from a different origin, add it to the CORS `allow_origins` list in `backend/main.py` and update `API_BASE` in `frontend/src/api.js`.
- The pooled HTTP client is closed via FastAPI's lifespan hook — nothing extra needed for clean shutdown.

## Performance & Cost

### Latency Profile
For a 4-model council (all phases parallel within themselves, sequential across rounds):
- **Routing**: <1-2s (single small-model classification call, regex fallback on failure)
- **Round 1** (initial answers): 4-8s
- **Round 2** (peer review): 3-6s
- **Round 3** (revise/defend): 3-6s
- **Round 4** (challenger): 2-4s (single call)
- **Round 5** (chairman synthesis): 3-6s (single call, largest prompt)
- **Total**: ~15-30s; the SSE stream surfaces each phase as it completes.

### Cost Optimization
- The router already caps councils at 4 models and prefers category-appropriate ones.
- Keep free-tier OpenRouter models in the council and reserve the paid high-reasoning model (e.g. `groq/llama-3.3-70b-versatile`) for the Chairman (`moderator_MODEL`).
- Leave `ENABLE_METACOGNITION=false` unless you have paid-tier rate limits: it adds up to 9 extra calls per query.
- The pre-flight `estimated_cost_usd` in the routing metadata is the projection for the whole deliberation — use it to monitor spend per query.
