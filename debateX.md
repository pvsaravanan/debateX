# DebateX Changes Log

This file records all changes made to the DebateX codebase starting from May 22, 2026.

## Change Log

### [2026-05-22 09:57] Initial Log Setup
- **File Created**: [debateX.md](file:///c:/proj/debateX/debateX.md)
- **Description**: Created this file to log all future modifications, files created, and updates made during the development session as requested by the user.

### [2026-05-22 14:18] Groq Integration & Premium Error Profiling
- **File Modified**: [backend/config.py](file:///c:/proj/debateX/backend/config.py)
  - Updated to active, high-performance Groq models (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `gemma2-9b-it`).
  - Added Llama 3.3 70B as default moderator fallback model when OpenRouter is inactive.
- **File Modified**: [backend/groq.py](file:///c:/proj/debateX/backend/groq.py)
  - Explicitly branded exception messages with "Groq:" prefixes so the frontend client can reliably identify Groq service exceptions.
  - Implemented dynamic string-fallback logic using `str(e) or type(e).__name__` to ensure network errors with empty string messages (e.g. `ReadTimeout`) are never rendered as blank messages in the user interface.
- **File Modified**: [frontend/src/components/ChatInterface.jsx](file:///c:/proj/debateX/frontend/src/components/ChatInterface.jsx)
  - Restored broken and unmatched JSX tags to re-enable Round 3, Round 4, and Stage 3 rendering correctly.
  - Implemented dynamic Groq error panel logic which guides users on API key configuration, rate limits (RPM/TPM), and developer console status.
- **File Modified**: [frontend/src/components/ChatInterface.css](file:///c:/proj/debateX/frontend/src/components/ChatInterface.css)
  - Added custom premium styling for the `.groq-error` badge with a sleek brand-themed layout.
- **File Created**: [tests/test_groq.py](file:///c:/proj/debateX/tests/test_groq.py)
  - Created a robust automated test script validating direct Groq completions and backend facade routing flow.
- **File Modified**: [.env](file:///c:/proj/debateX/.env)
  - Appended `# GROQ_API_KEY=gsk_...` as a commented setup template.

### [2026-05-24 10:15] OpenSpec Integration & Baseline Specifications
- **Files Created**: [.agent/skills/openspec-*](file:///c:/proj/debateX/.agent/skills)
  - Configured prompt interfaces and automated SDD (Spec-driven development) skills for Antigravity.
- **Files Created**: [openspec/specs/api.md](file:///c:/proj/debateX/openspec/specs/api.md), [openspec/specs/core_deliberation.md](file:///c:/proj/debateX/openspec/specs/core_deliberation.md), [openspec/specs/storage.md](file:///c:/proj/debateX/openspec/specs/storage.md)
  - Created baseline high-level technical specifications for the entire DebateX codebase.
- **Files Created**: [openspec/specs/api/spec.md](file:///c:/proj/debateX/openspec/specs/api/spec.md), [openspec/specs/core-deliberation/spec.md](file:///c:/proj/debateX/openspec/specs/core-deliberation/spec.md), [openspec/specs/storage/spec.md](file:///c:/proj/debateX/openspec/specs/storage/spec.md)
  - Generated formal OpenSpec requirements and scenarios detailing exact system behaviors, passing all CLI schema validation constraints.
- **File Created**: [openspec/changes/archive/2026-05-24-baseline-debate-specs/](file:///c:/proj/debateX/openspec/changes/archive)
  - Created and archived the initial baseline change proposal containing proposal.md, design.md, and tasks.md, permanently recording this spec transition in Git.

### [2026-05-24 10:20] Dynamic Roles Allocation & Customized Prompts
- **File Created**: [backend/roles.py](file:///c:/proj/debateX/backend/roles.py)
  - Created the role allocator and shift-based rotation module. Defines the `RoleAssignment` dataclass and maps custom system prompts per cognitive role (Reasoner, Fact-Checker, Devil's Advocate, Steelmanner, Chairman) to the five query types (technical, creative, factual, ethical, math).
- **File Created**: [tests/test_roles.py](file:///c:/proj/debateX/tests/test_roles.py)
  - Authored a comprehensive test suite validating all role properties, deterministic shift sequences, gracefully degraded lists (<5 models), and specialized query prompts.
- **File Created**: [openspec/specs/dynamic-roles/spec.md](file:///c:/proj/debateX/openspec/specs/dynamic-roles/spec.md)
  - Formulated formal requirements and test scenarios matching OpenSpec schemas.
- **File Created**: [openspec/changes/archive/2026-05-24-add-dynamic-roles/](file:///c:/proj/debateX/openspec/changes/archive)
  - Created and archived the dynamic-roles change proposal.

### [2026-05-24 10:55] Query Classifier Router & Cost Estimation
- **File Created**: [backend/router.py](file:///c:/proj/debateX/backend/router.py)
  - Created the query router and pricing mapping module. Defines the `QueryRouting` dataclass, implements double-path classification (queries OpenRouter free models via LLM facade, falling back gracefully to local regex keywords), resolves optimal model compositions, toggles Disagreement Panels and Fact-Checker Web Access, and predicts total query cost.
- **File Created**: [tests/test_router.py](file:///c:/proj/debateX/tests/test_router.py)
  - Authored a robust test suite validating all local classification categories, cost estimation arithmetic, and fallback route executions.
- **File Created**: [openspec/specs/query-routing/spec.md](file:///c:/proj/debateX/openspec/specs/query-routing/spec.md)
  - Formulated formal requirements and test scenarios matching OpenSpec schemas.
- **File Created**: [openspec/changes/archive/2026-05-24-add-query-router/](file:///c:/proj/debateX/openspec/changes/archive)
  - Created and archived the query-router change proposal.

### [2026-05-24 11:10] High-Performance Moderator Prioritization
- **File Modified**: [backend/config.py](file:///c:/proj/debateX/backend/config.py)
  - Updated model loading block to explicitly override and prioritize `groq/llama-3.3-70b-versatile` as the Chairman/Moderator when both Groq and OpenRouter keys are present in the environment, while concurrently retaining the dynamic merged council list across both providers.
- **File Modified**: [openspec/specs/core-deliberation/spec.md](file:///c:/proj/debateX/openspec/specs/core-deliberation/spec.md)
  - Added formal requirement and test scenario for high-performance moderator prioritization, passing all validation tests.
- **File Created**: [openspec/changes/archive/2026-05-24-prefer-groq-moderator/](file:///c:/proj/debateX/openspec/changes/archive)
  - Created and archived the prefer-groq-moderator change proposal.

### [2026-05-24 11:28] Groq Models Update & Pricing Calibration
- **File Modified**: [backend/config.py](file:///c:/proj/debateX/backend/config.py)
  - Updated Groq models list to: `llama-3.1-8b-instant`, `openai/gpt-oss-120b`, `qwen/qwen3-32b`, and `llama-3.3-70b-versatile` as requested by the user.
- **File Modified**: [backend/router.py](file:///c:/proj/debateX/backend/router.py)
  - Updated pricing metrics table to include `groq/openai/gpt-oss-120b` (input: $0.15/1M, output: $0.60/1M) and `groq/qwen/qwen3-32b` (input: $0.29/1M, output: $0.59/1M) using real-world GroqCloud parameters.
  - Refined cognitive category routing rules to map `gpt-oss` and `qwen` models as target council selectors for technical, creative, factual, ethical, and mathematical queries.
- **File Modified**: [tests/test_router.py](file:///c:/proj/debateX/tests/test_router.py)
  - Updated mock test model list to reflect the new set of models.

### [2026-05-24 13:08] Disagreement Detection Engine & DisagreementPanel UI
- **File Created**: [backend/disagreement.py](file:///c:/proj/debateX/backend/disagreement.py)
  - New module implementing `DisagreementMap`, `DisagreementZone`, and `ClaimScore` dataclasses.
  - `parse_disagreement_map()`: Parses the Chairman's structured JSON output (consensus points, divergence zones, per-model confidence scores) into a typed `DisagreementMap`.
  - `build_disagreement_map_heuristic()`: Fallback engine using Jaccard token similarity to build a `DisagreementMap` when the Chairman LLM omits the structured block.
  - `CHAIRMAN_DISAGREEMENT_SCHEMA`: Prompt fragment injected into the Chairman system prompt requesting structured JSON with `consensus_points`, `disagreement_zones`, `human_decision_needed`, and `confidence_scores[].score/stance`.
- **File Modified**: [backend/debate.py](file:///c:/proj/debateX/backend/debate.py)
  - Imports `disagreement` helpers.
  - `stage5_chairman_synthesis()` now injects `CHAIRMAN_DISAGREEMENT_SCHEMA` into the Chairman prompt and parses / builds a `DisagreementMap` from the response. Returns `disagreement_map` alongside `response` and `model`.
  - `run_full_debate()` exposes `disagreement_map` in the returned `metadata` dict.
- **File Modified**: [backend/main.py](file:///c:/proj/debateX/backend/main.py)
  - `stage3_complete` SSE event now includes `disagreement_map` field.
  - Metadata dict persisted to storage now includes `disagreement_map`.
- **File Modified**: [frontend/src/App.jsx](file:///c:/proj/debateX/frontend/src/App.jsx)
  - `assistantMessage` now has `disagreement_map: null` field.
  - `stage3_complete` handler saves `event.disagreement_map` to message state.
- **File Created**: [frontend/src/components/DisagreementPanel.jsx](file:///c:/proj/debateX/frontend/src/components/DisagreementPanel.jsx)
  - New React component rendering three visually distinct zones: CONSENSUS (all-model agreement points), DISAGREEMENT (expandable per-claim cards with model-by-model positions, divergence reasoning, and human-review flags), and CONFIDENCE MAP (stance badges + animated score bars per model per claim).
- **File Created**: [frontend/src/components/DisagreementPanel.css](file:///c:/proj/debateX/frontend/src/components/DisagreementPanel.css)
  - Premium dark glassmorphic styling with animated fade-in, consensus/disagreement color coding, stance badges (AGREE/PARTIAL/DISAGREE/UNKNOWN), and gradient score bars.
- **File Modified**: [frontend/src/components/ChatInterface.jsx](file:///c:/proj/debateX/frontend/src/components/ChatInterface.jsx)
  - Imports `DisagreementPanel` and renders it after Stage3 synthesis when `msg.disagreement_map` is present.
