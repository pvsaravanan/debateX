# DebateX Codebase Analysis

DebateX is a self-hosted cognitive consensus engine that runs a **routed, persona-driven 5-round council debate** to produce a single high-confidence answer: query classification → dynamic persona allocation → anonymized peer review → revise/defend → challenger critique → chairman synthesis, streamed over SSE with per-query cost estimation.

*(This document reflects the rebuilt pipeline: router.py and roles.py are now live parts of the flow, and both API endpoints share a single orchestrator.)*

---

## Directory Structure

```
debateX/
├── backend/
│   ├── config.py          # API keys, model lists, moderator selection, data dir
│   ├── llm.py              # Facade: routes a model name to the Groq or OpenRouter client
│   ├── openrouter.py        # OpenRouter HTTP client
│   ├── groq.py              # Groq HTTP client
│   ├── http_client.py       # Shared pooled httpx.AsyncClient (singleton)
│   ├── debate.py            # Core 5-round orchestration + ranking parser
│   ├── disagreement.py      # Chairman JSON-block parsing + heuristic fallback (DisagreementMap)
│   ├── metacognition.py     # Self-consistency probing engine (currently NOT wired into the live flow)
│   ├── roles.py             # Role allocation (Chairman/Devil's Advocate/etc.) — DEFINED BUT UNUSED
│   ├── router.py            # Query classifier + council/cost routing — DEFINED BUT UNUSED
│   ├── storage.py           # JSON file persistence (data/conversations/*.json), not thread-safe
│   ├── main.py               # FastAPI app, REST + SSE streaming endpoint
│   └── __init__.py
├── frontend/src/
│   ├── App.jsx                       # State root; consumes SSE events, builds message objects
│   ├── api.js                         # fetch + SSE reader client (hits localhost:8001)
│   ├── components/
│   │   ├── ChatInterface.jsx          # Message list, per-round loading indicators, error panel
│   │   ├── Sidebar.jsx                # Conversation list, rename/delete
│   │   ├── Stage1.jsx                 # Round 1 tabs: initial answers
│   │   ├── Stage2.jsx                 # Round 2 tabs: peer rankings + de-anonymized display + aggregate table
│   │   ├── Round3.jsx                 # Round 3 tabs: REVISE/DEFEND decisions
│   │   ├── Round4.jsx                 # Round 4: Challenger critique + collapsible target answer
│   │   ├── Stage3.jsx                 # Round 5: final chairman answer
│   │   ├── DisagreementPanel.jsx      # Consensus/disagreement zones + confidence bars
│   │   └── ConfidenceHeatmap.jsx      # Renders metacognition scores (currently always empty — see below)
├── tests/                 # Ad-hoc scripts (test_or.py, test_groq.py, test_stream_5rounds.py, test_roles.py, test_router.py, …)
├── run.bat / start.sh      # One-click startup scripts
└── data/conversations/     # JSON conversation store (gitignored)
```

---

## The Deliberation Pipeline

```
User Query
    │
Routing: route_query()                    → LLM classifier (local regex fallback) buckets the
    │                                        query into technical/code, creative, factual/research,
    │                                        ethical/philosophical, or math/logic; assembles a
    │                                        preference-ordered optimal council (capped at 4);
    │                                        estimates full-debate cost from PRICING_TABLE
    │
Personas: allocate_personas()             → council members receive rotated adversarial personas
    │                                        (Reasoner, Devil's Advocate, Fact-Checker, Steelmanner)
    │                                        as query-type-specific system prompts; the chairman
    │                                        (moderator_MODEL) gets a chairman persona for Round 5
    │
    ├─ (optional, concurrent) metacognition probe — behind ENABLE_METACOGNITION in config.py
    │
Round 1: stage1_collect_responses()      → council answers independently in parallel, each
    │                                        through the lens of its persona
    │
Round 2: stage2_collect_rankings()        → responses anonymized as "Response A/B/C…", every
    │                                        council member ranks + critiques all responses;
    │                                        parse_ranking_from_text() (deduplicating) +
    │                                        calculate_aggregate_rankings()
    │
Round 3: stage3_revise_or_defend()        → each model sees peer critiques + aggregate standings,
    │                                        must open with "DECISION: REVISE" or "DECISION: DEFEND";
    │                                        degrades to Round-1 answers as implicit defenses if all fail
    │
Round 4: stage4_challenger_critique()     → the council's Devil's Advocate (else the worst-ranked
    │                                        model) attacks the top-ranked model's Round-3 answer
    │
Round 5: stage5_chairman_synthesis()      → the chairman (with its persona system prompt) sees the
    │                                        full deliberation_history JSON + narrative summary,
    │                                        produces the definitive answer AND a fenced JSON
    │                                        DisagreementMap, parsed by disagreement.py
    │
Return: {stage1, stage2, stage3(=Round5), metadata: {routing, label_to_model,
         aggregate_rankings, rounds[], disagreement_map, metacognition}}
```

**Single orchestrator**: `run_debate_stream()` in `backend/debate.py` is an async generator yielding one event dict per phase (`routing_start/complete`, `round1_start/complete` … `round5_start/complete`, `complete`, `error`). Both endpoints consume it — `POST /message/stream` serializes each event as SSE; `POST /message` (batch) runs it to completion via `run_full_debate()`. Round logic exists exactly once.

### Round-by-round mechanics

- **Round 1**: `query_models_parallel(debate_MODELS, messages)` — pure `asyncio.gather`, graceful degradation (a model returning `None` is dropped, not fatal).
- **Round 2**: Builds an anonymization map `{"Response A": model_name, ...}`, and a strict prompt requiring a `FINAL RANKING:` header followed by a numbered list (`1. Response C`). `parse_ranking_from_text()` regex-extracts the ranking; falls back to scanning for any `Response [A-Z]` occurrences if the strict header is missing. `calculate_aggregate_rankings()` averages each model's rank position across all peer evaluations and sorts ascending (lower = better).
- **Round 3**: Each model is shown the anonymized Round-1 responses, all Round-2 peer evaluations verbatim, and the aggregate standings, then must self-identify (`model_label`) and either revise or defend. Decision is parsed by scanning the first line(s) for `DECISION: DEFEND` / `DECISION: REVISE`; that line is stripped from the displayed response but preserved in `raw_response`.
- **Round 4**: Challenger = `aggregate_rankings[-1]` (worst model), unless that's also the leader (only possible with ≥2 models), in which case the second-worst is used. Targets `aggregate_rankings[0]` (best model)'s Round-3 answer.
- **Round 5**: Chairman prompt embeds the full `deliberation_history` as a JSON block plus a narrative recap of all 4 rounds, and — if provided — a `metacognition_block` of per-model confidence weights. It requests a JSON-fenced `DisagreementMap` per the `CHAIRMAN_DISAGREEMENT_SCHEMA` in `disagreement.py`. If the chairman's output has no parseable JSON block, `build_disagreement_map_heuristic()` derives one from Jaccard token-similarity across Round-1/Round-3 claims (bullet/sentence extraction, capped at 5 zones). The JSON fence is stripped from the text shown to the user via regex before returning.
- **Fallback chain**: Both Round 3 exceptions and Round 5 (chairman) failures are handled per-model with `asyncio.gather(..., return_exceptions=True)` / try-except, and Round 5 additionally falls back through `debate_MODELS` in order, and finally to the raw Round-3 leading answer if every model fails.

---

## Backend Modules in Detail

### `config.py`
- Loads `.env` via `python-dotenv`.
- `debate_MODELS` and `moderator_MODEL` are built **additively and conditionally** based on which of `OPENROUTER_API_KEY` / `GROQ_API_KEY` are set. If both keys are present, both providers' models are appended to `debate_MODELS`, and `moderator_MODEL` ends up being whichever branch ran last — currently **Groq's `llama-3.3-70b-versatile` wins** if `GROQ_API_KEY` is set, since that block runs after OpenRouter's and unconditionally overwrites `moderator_MODEL`.
- Model IDs currently configured: 4 OpenRouter free-tier models (`nvidia/nemotron-3-ultra-550b-a55b:free`, `poolside/laguna-m.1:free`, `google/gemma-4-31b-it:free`, `poolside/laguna-xs-2.1:free`) and 3 Groq models (`llama-3.1-8b-instant`, `openai/gpt-oss-20b`, `llama-3.3-70b-versatile`).
- Backend port is **8001** (documented reason: avoid conflict with another local app on 8000).

### `llm.py` (provider facade)
- `query_model()` dispatches on a `"groq/"` prefix to `query_groq()` (stripping the prefix), otherwise defaults to `query_openrouter()`. This prefix convention is how `debate_MODELS` entries route to the correct provider.
- `query_models_parallel()` wraps `asyncio.gather(..., return_exceptions=True)`, logs rate-limit/credit-related exceptions distinctly, and maps every model to `None` on failure rather than raising — this is the single graceful-degradation choke point for Round 1 and Round 2.

### `openrouter.py` / `groq.py`
- Both are thin, near-identical `httpx` POST wrappers returning `{'content', 'reasoning_details'}`.
- Both raise `ValueError` with the parsed API error message on HTTP errors (rather than swallowing them) — the *caller* (`llm.py`/`debate.py`) is responsible for catching these.
- Both now route requests through `http_client.get_client()` instead of opening a new `httpx.AsyncClient` per call.

### `http_client.py`
- Module-level singleton `httpx.AsyncClient` (max 20 connections / 10 keepalive, 120s timeout, 10s connect timeout) shared across all OpenRouter/Groq calls for connection pooling. Recreated lazily if closed. `close_client()` exists for app shutdown but **is not currently called anywhere** (no FastAPI shutdown event registered in `main.py`).

### `debate.py`
- Houses all 5 round functions, `parse_ranking_from_text()`, `calculate_aggregate_rankings()`, `generate_conversation_title()`, and the two orchestration entry points (`run_full_debate()` for the non-streaming endpoint, and the inlined equivalent in `main.py`'s SSE generator).
- `generate_conversation_title()` tries the moderator model first (15s timeout), then falls back through every `debate_MODELS` entry (10s timeout each), then falls back to the first 4 words of the user's query, explicitly instructed to preserve the query's original language (unlike every other prompt in the system, which forces English output).

### `disagreement.py`
- Defines `ClaimScore`, `DisagreementZone`, `DisagreementMap` dataclasses.
- `parse_disagreement_map()` extracts a fenced/bare JSON block from the chairman's raw text via regex + `json.loads`, tolerating malformed input by returning `None` (triggering the heuristic fallback).
- `build_disagreement_map_heuristic()` is a **non-semantic, Jaccard-similarity based approximation** — it does not use an LLM. It extracts bullet/numbered lines (or first sentences >4 words) from each model's final answer, and buckets a claim as "consensus" only if every model's claim set contains something with >0.3 token overlap.
- `CHAIRMAN_DISAGREEMENT_SCHEMA` is injected as a suffix into the Round 5 prompt — it's the contract the model must fulfill for `parse_disagreement_map()` to succeed.

### `metacognition.py`
- Implements self-consistency probing: sample each model 3× at temperatures `[0.3, 0.7, 1.0]`, compute pairwise TF-IDF cosine similarity (hand-rolled, stdlib-only — no numpy/sklearn), and map average similarity → a confidence score/tier (`HIGH ≥0.70`, `MEDIUM 0.40–0.69`, `LOW <0.40`).
- Probes are capped at `MAX_PROBE_MODELS = 3` models to control API call volume; within a model, the 3 temperature calls are sequential with a 0.4s stagger (rate-limit avoidance), but different models are probed concurrently.
- Fully implemented and exercised by `run_full_debate()` (the non-streaming endpoint) and by `stage5_chairman_synthesis()`'s optional `metacognition_summary` parameter, which — when present — is injected into the chairman prompt as a `metacognition_block` instructing it to weight model contributions by confidence.
- **However, it is currently disconnected from the live user flow** — see Notable Inconsistencies.

### `roles.py` — defined but unused
- `allocate_roles()` builds a `RoleAssignment` (Chairman / Devil's Advocate / Fact-Checker / Steelmanner / Reasoners) with query-type-specific system prompts (`technical`, `creative`, `factual`, `ethical`, `math`), deterministically rotated by `query_index % n` so role assignment varies across conversations.
- Not imported by `debate.py` or `main.py`. Only referenced by `tests/test_roles.py`. Appears to be a scaffolded-but-not-yet-integrated feature for role-specialized debate.

### `router.py` — defined but unused
- `route_query()` classifies a query into one of 5 categories (technical/code, creative, factual/research, ethical/philosophical, math/logic) via a fast LLM call with a local regex-based fallback (`classify_query_local()`), then picks an "optimal council" subset of models by name-substring matching (e.g. `"llama-3.3" in m`) and flags (`disagreement_panel_mandatory`, `fact_checker_web_access`), plus a `PRICING_TABLE`-based cost estimate.
- Not imported anywhere in the live pipeline. Only referenced by `tests/test_router.py`.
- Note: its model-matching heuristics (`"qwen"`, `"deepseek"`, `"glm-4.5"`) don't match any of the models actually configured in `config.py` today, so if wired in as-is it would frequently fall through to the "first 3 available models" fallback.

### `storage.py`
- Flat JSON-per-conversation files in `data/conversations/{id}.json`. Explicitly documented in-file as **not thread-safe** (read-modify-write race condition under concurrent requests to the same conversation) — a deliberate known limitation, not an oversight.
- `list_conversations()` filters out conversations with zero messages (so abandoned "New Conversation" shells don't clutter the sidebar).
- Round/metadata data (`rounds`, `metadata`) is persisted per assistant message when provided — this is a change from the old 3-stage docs, which claimed metadata was never persisted. Metadata IS now saved via `add_assistant_message(..., metadata=metadata)`.

### `main.py`
- CORS restricted to `localhost:5173`/`localhost:3000`.
- Two message-send endpoints: `POST /message` (batch, calls `run_full_debate`) and `POST /message/stream` (SSE, calls the 5 round functions directly with a hand-rolled event generator). **These two code paths independently reimplement the same orchestration** — see below.
- SSE event types emitted: `stage1_start/complete`, `stage2_start/complete` (includes `label_to_model` + `aggregate_rankings`), `round3_start/complete`, `round4_start/complete`, `round5_start/complete` (includes `disagreement_map`), `title_complete`, `complete`, `error`. Note the naming inconsistency: rounds 1–2 use `stageN_*` while rounds 3–5 use `roundN_*`.
- Errors inside the generator are caught broadly and surfaced as an `error` SSE event with `str(e)` — the frontend's `ChatInterface.jsx` then sniffs the error string for `"groq"`/`"gsk_"` or `"free-models-per-day"` substrings to render provider-specific remediation instructions. This is a fragile string-matching contract between backend error messages and frontend display logic.

---

## Frontend

### `App.jsx`
- Holds `conversations` (sidebar list) and `currentConversation` (active thread) state; the assistant message object is progressively mutated in place as SSE events arrive (`stage1`, `stage2`, `round3`, `round4`, `stage3`, `disagreement_map`, `metacognition`, `metadata`, plus a `loading` flag map keyed by round name).
- Has a `metacognition_start`/`metacognition_complete` case in its switch statement — **dead code today**, since the backend's SSE generator never emits those event types (see Notable Inconsistencies).
- `handleNewConversation` is a no-op guard against redundantly clearing an already-empty draft.

### `ChatInterface.jsx`
- Renders one loading-state line per round while streaming, then the corresponding stage component once its data lands. Falls back to reading `msg.rounds` (the persisted/batch shape) via `.find(r => r.type === '...')` when `round3`/`round4` aren't present directly on the message — this is what allows previously-saved conversations (loaded via `GET /api/conversations/{id}`, which returns the batch-shaped stored JSON) to render correctly alongside freshly-streamed ones.
- Contains the provider-specific error remediation UI described above.

### `Stage1.jsx` / `Stage2.jsx` / `Round3.jsx` / `Round4.jsx` / `Stage3.jsx`
- Tabbed per-model views, consistent with the original transparency design: raw model output, model identity always inspectable.
- `Stage2.jsx` performs **client-side de-anonymization only for display** (`deAnonymizeText`, regex string replace of `Response X` → `**modelName**`), preserving the original anonymized-evaluation methodology while keeping the UI readable. Also renders the "Extracted Ranking" list and the aggregate rankings table.
- `Round3.jsx` shows a REVISE/DEFEND badge per model tab.
- `Round4.jsx` shows challenger vs. target with a collapsible accordion for the attacked answer.

### `DisagreementPanel.jsx`
- Renders `disagreement_map` (consensus points, expandable disagreement zones with per-model positions, divergence reasoning, and confidence-score bars with an AGREE/PARTIAL/DISAGREE stance badge). Returns `null` if both consensus and disagreement arrays are empty.

### `ConfidenceHeatmap.jsx`
- Renders per-model confidence tiers/bars and expandable raw temperature-probe text, driven by `metacognition.scores`. **Currently always receives `null`/never renders in the live streaming flow** (see below) — it only would populate if the batch (`/message`, non-streaming) endpoint were used, or if `metacognition` were re-wired into the SSE path.

### Styling
- Dark theme (`--bg-primary: #171717`, `--accent-blue: #67e8f9`, `--accent-cyan: #22d3ee`) — a change from the old light-mode design noted in stale prior docs/CLAUDE.md.
- React 19 + Vite 7, `react-markdown` + `remark-gfm` for GFM tables/strikethrough support in all markdown-rendered content.

---

## Resolved Issues (fixed in the consensus-engine rebuild)

All items previously listed as inconsistencies/dead code have been addressed:

1. **Metacognition** is now controlled by a single `ENABLE_METACOGNITION` flag in `config.py` (default off, per free-tier rate limits) and behaves identically on both endpoints via the shared orchestrator. When enabled, it runs concurrently with Rounds 1–2 and its summary is injected into the chairman prompt.
2. **`router.py` and `roles.py` are live**: every query is classified, routed to a preference-ordered council, persona-allocated (rotated deterministically per query via CRC32 of the query text), and cost-estimated before Round 1. The Devil's Advocate persona feeds Round 4's challenger selection.
3. **One orchestrator**: `run_debate_stream()` is the only implementation of the round pipeline; batch and SSE endpoints both consume it.
4. **SSE naming is consistent**: `routing_*`, `round1_*` … `round5_*`, `title_complete`, `complete`, `error`. The frontend was updated in lockstep; persisted conversations (which store `stage1/stage2/stage3` + `rounds`) still render via `ChatInterface`'s metadata fallbacks.
5. **`close_client()` is called** from a FastAPI lifespan hook; the pooled httpx client is also re-created if the running event loop changes (fixes "Event loop is closed" in scripts/tests using successive `asyncio.run()` calls).
6. **Router model-matching covers the configured models** (`nemotron`, `laguna`, `gemma`, `llama-3.3`, `llama-3.1`, `gpt-oss`) with preference ordering, plus forward-compat substrings (`qwen`, `deepseek`, `glm-4.5`). Free-tier (`:free`) models are always costed at $0.
7. **`storage.py` read-modify-write operations are serialized** behind a process-wide `threading.Lock` (multi-worker deployments still need a real database — documented in-file).
8. Additional fixes: the DELETE endpoint no longer converts its own 404 into a 500; `parse_ranking_from_text()` deduplicates labels so a model repeating "Response A" can't skew aggregates; Round 3 degrades to Round-1 answers as implicit defenses when every model fails; Round-5 fallbacks always attach a (heuristic) disagreement map; empty/whitespace model responses are filtered in Rounds 1 and 3; the router's classification call prefers small/fast models instead of the 550B Nemotron.

---

## Data Flow Summary (current, accurate)

```
POST /api/conversations/{id}/message/stream
    │
    ├─ storage.add_user_message()
    ├─ (if first message) generate_conversation_title() — background task, awaited before completion
    │
    ├─ SSE: routing_start → route_query() + allocate_personas() → routing_complete
    │        {category, optimal_council, chairman, role_map, estimated_cost_usd, ...}
    ├─ SSE: round1_start → stage1_collect_responses(council, personas) → round1_complete
    ├─ SSE: round2_start → stage2_collect_rankings() + calculate_aggregate_rankings() → round2_complete
    ├─ SSE: round3_start → stage3_revise_or_defend() → round3_complete
    ├─ SSE: round4_start → stage4_challenger_critique(devil's advocate preferred) → round4_complete
    ├─ SSE: round5_start → stage5_chairman_synthesis() (+ disagreement map parse/fallback) → round5_complete
    ├─ SSE: title_complete (if first message)
    ├─ storage.add_assistant_message(..., rounds=[...], metadata={routing, label_to_model,
    │        aggregate_rankings, rounds, disagreement_map, metacognition})
    └─ SSE: complete
```

The entire pipeline is async; parallelism happens *within* each round (all council models queried via `asyncio.gather`), but the rounds themselves run **sequentially** since each depends on the previous round's output. The frontend renders a `RoutingPanel` (category, council personas, chairman, estimated cost) above the round components.
