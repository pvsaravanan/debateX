# CLAUDE.md - Technical Notes for DebateX

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

DebateX is a self-hosted cognitive consensus engine: a routed, persona-driven 5-round deliberation across a council of diverse LLMs. Every query is classified and cost-estimated, the council receives adversarial personas, answers are peer-reviewed anonymously, the leading answer is attacked by a Challenger, and a Chairman synthesizes the final answer plus a structured disagreement map.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- `debate_MODELS` is built additively from whichever API keys exist in `.env` (`OPENROUTER_API_KEY`, `GROQ_API_KEY`). If both are set, both providers' models are registered and Groq's `llama-3.3-70b-versatile` wins `moderator_MODEL` (its block runs last).
- `ENABLE_METACOGNITION` (env flag, default false) gates the pre-flight self-consistency probe. Off by default because it triples per-model call volume — a problem on free-tier rate limits.
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000).

**`llm.py`** — provider facade
- `query_model()` dispatches on the `"groq/"` model-name prefix to `groq.py` (prefix stripped), otherwise to `openrouter.py`.
- `query_models_parallel()` accepts an optional `system_prompts: Dict[model, prompt]` — this is how personas are injected. Failures map to `None` per model (graceful degradation choke point); rate-limit/credit errors are logged distinctly.

**`http_client.py`**
- Singleton pooled `httpx.AsyncClient` shared by both providers. Re-created if the current event loop differs from the one it was created on (successive `asyncio.run()` calls in tests/scripts would otherwise hit "Event loop is closed"). Closed via FastAPI lifespan hook in `main.py`.

**`router.py`** — Query Classification & Cost Estimation
- `route_query()`: LLM classification (small/fast model preferred) with `classify_query_local()` regex fallback → one of `technical/code`, `creative`, `factual/research`, `ethical/philosophical`, `math/logic`.
- Council selection is **preference-ordered substring matching** per category (covers the configured models: nemotron, laguna, gemma, llama-3.3, llama-3.1, gpt-oss; plus forward-compat: qwen, deepseek, glm-4.5), capped at 4 models.
- `calculate_predicted_cost()` projects full-debate USD cost from `PRICING_TABLE` using per-round token assumptions. Models ending `:free` always cost $0.
- `CATEGORY_TO_ROLE_TYPE` bridges router categories to roles.py query types.

**`roles.py`** — Dynamic Persona Allocation
- `allocate_personas(council, chairman_model, query_type, query_index)` is the live entry point: council members get rotated adversarial personas (always ≥1 Reasoner, then Devil's Advocate, Fact-Checker, Steelmanner; extras become Reasoners); the chairman persona goes into `chairman_prompt` for Round 5 and does NOT consume a council seat.
- Rotation is deterministic: `query_index = crc32(query)` (computed in debate.py), so the same query always gets the same allocation, but different queries rotate roles.
- `allocate_roles()` is the older allocator where the chairman IS a council member — kept because `tests/test_roles.py` pins its behavior. Don't change its semantics.
- `ROUND1_DIRECTIVE` is appended to council personas so every member still answers the question in Round 1 (a bare Devil's Advocate prompt would refuse to draft an answer).

**`debate.py`** — The Single Orchestrator
- `run_debate_stream(user_query)` is an **async generator** and the only implementation of the pipeline. Both endpoints consume it. Any round-logic change goes here, once.
- Event protocol: `routing_start/complete` → (`metacognition_start/complete` if enabled) → `round1_start/complete` … `round5_start/complete` → `complete` (carries the full assembled `result` for persistence — main.py strips it before sending SSE) or `error`.
- Round functions are parameterized (`council`, `system_prompts`, `chairman_model`, `preferred_challenger`) with `debate_MODELS`/`moderator_MODEL` defaults.
- Round 4 challenger = Devil's Advocate persona if present and not the leader, else worst-ranked model.
- Round 5 fallback chain: chairman → each config model → raw leading Round-3 answer; a disagreement map (parsed or heuristic) is always attached.
- `parse_ranking_from_text()`: extracts "FINAL RANKING:" section, handles numbered and plain formats, **deduplicates labels** (first occurrence wins) so repeated mentions can't skew aggregates.
- `run_full_debate()` just drains the generator (batch mode).

**`disagreement.py`**
- `CHAIRMAN_DISAGREEMENT_SCHEMA` is injected into the Round-5 prompt; `parse_disagreement_map()` extracts the fenced JSON block; `build_disagreement_map_heuristic()` (Jaccard token similarity over extracted claims, no LLM) is the fallback. The JSON fence is stripped from the narrative shown to users.

**`metacognition.py`**
- Samples each model 3× at temperatures 0.3/0.7/1.0, hand-rolled TF-IDF cosine similarity → confidence tier (HIGH ≥0.70 / MEDIUM ≥0.40 / LOW). Capped at 3 models, staggered within a model. Summary injected into the Chairman prompt as confidence weights. Only runs when `ENABLE_METACOGNITION=true`.

**`storage.py`**
- JSON-per-conversation files in `data/conversations/`. Read-modify-write operations are serialized behind a process-wide `threading.Lock` — safe for one process; multiple uvicorn workers still need a real DB.
- Assistant messages persist `{stage1, stage2, stage3, rounds[], metadata}`; metadata includes `routing`, `label_to_model`, `aggregate_rankings`, `disagreement_map`, `metacognition`.

**`main.py`**
- FastAPI with CORS for localhost:5173/3000; lifespan hook closes the pooled HTTP client.
- `POST /api/conversations/{id}/message` (batch) and `POST /api/conversations/{id}/message/stream` (SSE) both consume `run_debate_stream()`. Title generation runs as a concurrent task, emitted as `title_complete`.

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Consumes the SSE protocol; progressively fills the assistant message (`routing`, `stage1`, `stage2`, `round3`, `round4`, `stage3`, `disagreement_map`, `metacognition`) with per-phase `loading` flags.

**`components/RoutingPanel.jsx`**
- Renders classification category, council chips with persona badges, chairman, and estimated cost (green "FREE" for $0). Reads either the live `msg.routing` or persisted `msg.metadata.routing`.

**`components/Stage1.jsx` / `Stage2.jsx` / `Round3.jsx` / `Round4.jsx` / `Stage3.jsx`**
- Tabbed per-model views titled Round 1–5. Stage2 de-anonymizes **client-side for display only** (models never see identities) and shows the "Extracted Ranking" for parse validation. Round3 shows REVISE/DEFEND badges. Round4 credits the Devil's Advocate when it is the challenger. Stage3 is the Chairman synthesis.
- Component filenames (Stage1/Stage2/Stage3) predate the round renaming — the message state keys (`stage1/stage2/stage3`) match the persisted storage shape, so don't rename them casually.

**`components/DisagreementPanel.jsx` / `ConfidenceHeatmap.jsx`**
- Consensus/disagreement zones with confidence bars; metacognition heatmap (renders only when the flag is enabled server-side).

**Styling**
- Dark theme via CSS variables in `index.css` (`--bg-primary: #171717`, `--accent-blue: #67e8f9`). All ReactMarkdown output must be wrapped in `<div className="markdown-content">`.

## Key Design Decisions

### One orchestrator, two endpoints
The SSE and batch endpoints previously had divergent hand-rolled copies of the pipeline. `run_debate_stream()` is now the single source of truth; the `complete` event carries the assembled result so consumers never re-derive it.

### Backward-compatible persistence
Old conversations (pre-routing, pre-rounds) still render: `ChatInterface` falls back from top-level message fields to `msg.rounds[]` / `msg.metadata` lookups. Storage message shape (`stage1/stage2/stage3` keys) is intentionally unchanged.

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.; backend maps labels → models; frontend bolds real names for readability with an explanatory note. Prevents reputation bias while keeping transparency.

### Error Handling Philosophy
- Continue with successful responses if some models fail; never fail the request on a single model failure. Round 3 degrades to Round-1 answers as implicit defenses; Round 5 walks a fallback chain ending at the leading answer.
- Frontend error panel sniffs error strings for provider hints ("groq"/"gsk_", "free-models-per-day") to show remediation steps — a fragile string contract between backend error messages and UI; keep messages stable.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory (relative imports).
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware; ports are 8001 (backend) / 5173 (frontend), update `frontend/src/api.js` if changing.
3. **Ranking Parse Failures**: If models ignore the format, fallback regex extracts any "Response X" patterns in order (deduplicated).
4. **`allocate_roles` vs `allocate_personas`**: the former is test-pinned legacy; the live pipeline uses the latter. New persona work goes in `allocate_personas`.
5. **Router preferences are substring matches**: adding a model to `config.py` without a matching substring in `router.py` category preferences means it only joins councils via the fallback path. Add it to `PRICING_TABLE` too or cost estimates use the default rate (free-tier `:free` suffix is always $0).
6. **SSE event names**: `routing_*`, `round1_*`–`round5_*`. Frontend switch in `App.jsx` must stay in lockstep with `run_debate_stream()`.

## Testing Notes

- `python -m unittest tests.test_roles tests.test_router` — pinned unit tests for role allocation and routing/cost (14 tests, no network required: LLM classification falls back to the local regex classifier on failure).
- `tests/` also contains ad-hoc API scripts (`test_or.py`, `test_groq.py`, `test_stream_5rounds.py`, …) for live-provider smoke testing.
- For pipeline changes, mock `backend.llm.query_openrouter` / `backend.llm.query_groq` and drain `run_debate_stream()` — asserts the whole event protocol without API spend.

## Data Flow Summary

```
User Query
    ↓
Routing: route_query() → category, council (≤4), cost  +  allocate_personas() → role system prompts
    ↓
Round 1: council answers in parallel (persona lenses)
    ↓
Round 2: anonymize → parallel peer rankings → parse → aggregate rankings
    ↓
Round 3: each model REVISEs or DEFENDs under peer feedback
    ↓
Round 4: Devil's Advocate (or worst-ranked) attacks the leading answer
    ↓
Round 5: Chairman (moderator + chairman persona) synthesizes + disagreement map
    ↓
Return/persist: {stage1, stage2, stage3, rounds[], metadata{routing, rankings, disagreement_map, metacognition}}
    ↓
Frontend: RoutingPanel + Round 1–5 tabs + DisagreementPanel (+ ConfidenceHeatmap when enabled)
```

Parallelism is *within* rounds (asyncio.gather across the council); rounds themselves are sequential.
