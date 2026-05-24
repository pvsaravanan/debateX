# Core Deliberation Specification

This specification documents the core deliberation engine of **DebateX**, which coordinates a multi-LLM debate through a **pre-flight metacognition probe** followed by a **5-round pipeline** to construct a single high-quality, synthesized master response.

---

## 🏗️ System Overview

DebateX establishes an asynchronous deliberation council composed of multiple diverse LLMs (the Council Members) and a designated moderator model (the Chairman). Before the deliberation begins, a **metacognition probe** samples every model at three temperatures to measure internal self-consistency. The resulting confidence scores influence how the Chairman weights each model's contribution in the final synthesis.

---

## 🧠 Pre-flight: Metacognition Probe (`backend/metacognition.py`)

Runs **concurrently with Round 2** (not Round 1) — started as an `asyncio.Task` after stage1 completes, so it never competes for the same rate-limit window as the main deliberation.

> **Rate-limit budget**: At most `MAX_PROBE_MODELS = 3` models are probed. Within each model, the 3 temperature calls are **staggered sequentially** (0.4s delay between them). Across the 3 models, probes run concurrently. Peak simultaneous calls = 3 (one per model). Total metacognition calls = 9.

### Process
1. After stage1 finishes, a background task probes up to **3** council models.
2. Each model is called **3 times sequentially** at temperatures `[0.3, 0.7, 1.0]` with a 0.4s stagger per step.
3. Each set of three responses is embedded using **TF-IDF cosine similarity** (no external deps — stdlib only).
4. **Three pairwise similarities** are computed: `(T0.3↔T0.7)`, `(T0.3↔T1.0)`, `(T0.7↔T1.0)`.
5. A **per-model confidence score** is derived from the average similarity:

| avg cosine | Tier | Confidence range |
|---|---|---|
| ≥ 0.70 | HIGH | 0.85 – 1.00 |
| 0.40 – 0.69 | MEDIUM | 0.50 – 0.75 |
| < 0.40 | LOW | 0.10 – 0.40 |

Linear interpolation within each band maps the raw avg similarity to the exact score.

### SSE stream ordering
```
stage1_start → stage1_complete           ← stage1 gets a clean rate-limit window
meta_task launched (asyncio.create_task) ← concurrent with stage2
stage2_start → stage2_complete
metacognition_complete                   ← result arrives after stage2
```

### Output: `MetacognitionResult`
```python
@dataclass
class TemperatureProbe:
    temperature: float
    response: str

@dataclass
class ModelConfidenceScore:
    model: str
    confidence: float        # 0.0 – 1.0
    tier: str                # "HIGH" | "MEDIUM" | "LOW"
    sim_01: float            # cosine(T0.3, T0.7)
    sim_02: float            # cosine(T0.3, T1.0)
    sim_12: float            # cosine(T0.7, T1.0)
    avg_similarity: float
    probes: list[TemperatureProbe]

@dataclass
class MetacognitionResult:
    scores: dict[str, ModelConfidenceScore]
    summary: str             # Weight table injected into Chairman prompt
```

The `summary` is a formatted table string injected into the Chairman prompt:
```
Model confidence weights (derived from self-consistency probing):
  • llama-3.3-70b-versatile   [HIGH    conf=0.91  avg_sim=0.84]
  • qwen3-32b                 [MEDIUM  conf=0.63  avg_sim=0.55]
  • glm-4.5-air               [LOW     conf=0.18  avg_sim=0.11]
```

---

## 🔄 The 5-Round Pipeline Flow

All five rounds execute in sequential asynchronous operations coordinated by `backend/debate.py` and are streamed dynamically to the client via Server-Sent Events (SSE).

### Round 1: Initial Answers (`stage1_collect_responses`)
- **Action**: Queries all configured council models in parallel with the user's query.
- **Timing**: Fires concurrently with the metacognition probe — both are launched as `asyncio.Task`s simultaneously.
- **Constraints**: Uses `asyncio.gather` with automatic timeout handling. Fails gracefully if some models fail, continuing with the successful responses.
- **Output**: A collection of named, raw markdown answers.

### Round 2: Peer Review & Ranking (`stage2_collect_rankings`)
- **Action**: Anonymizes Round 1 responses as `Response A`, `Response B`, `Response C`, etc. Queries all council models to evaluate and rank these responses.
- **Strict Prompt Guidelines**:
  - Evaluate each response individually (explaining merits and flaws).
  - Include a terminal section: `FINAL RANKING:` followed by a numbered list in strict format (e.g. `1. Response B`).
  - Output is strictly in English.
- **Aggregation**: Computes the average rank position for each model. Sorting determines the leading response.

### Round 3: Revise or Defend (`stage3_revise_or_defend`)
- **Action**: Council models receive all peer reviews, aggregate rankings, and their own anonymous label.
- **Decisions**: Models must start their response with:
  - `DECISION: REVISE` followed by a complete, updated response incorporating peer critiques.
  - `DECISION: DEFEND` followed by a logical defense of their original reasoning.

### Round 4: Challenger Critique (`stage4_challenger_critique`)
- **Action**: Assigns the lowest-ranked model (from Round 2) as the Challenger.
- **Objective**: Aggressively critique the leading answer (first place in Round 2) to reveal logical flaws, incorrect assumptions, or overlooked edge cases.

### Round 5: Chairman Synthesis (`stage5_chairman_synthesis`)
- **Action**: The Chairman/Moderator model receives the complete JSON deliberation history **plus the metacognition weight table**.
- **Metacognition Injection**: The Chairman prompt includes a `PRE-DELIBERATION METACOGNITION SCORES` block listing per-model confidence scores. The Chairman is instructed to weight HIGH-confidence models more heavily and treat LOW-confidence models with scepticism.
- **Disagreement Map**: The Chairman is also instructed to produce a structured JSON block (the `DisagreementMap`) inside the narrative response. This block is parsed and stripped before returning clean text to the client.
- **Objective**: Weighs initial answers, subsequent revisions/defenses, peer rankings, metacognition weights, and explicitly addresses the Challenger's critique to construct the final synthesized response.

---

## ⚡ Disagreement Detection (`backend/disagreement.py`)

Runs as part of Round 5. The Chairman is prompted to emit a structured JSON block:

```python
@dataclass
class ClaimScore:
    claim: str
    model_scores: dict[str, float]  # model → confidence 0–1

@dataclass
class DisagreementZone:
    claim: str
    positions: dict[str, str]       # model → stance text
    divergence_reason: str
    human_review_needed: bool

@dataclass
class DisagreementMap:
    consensus_points: list[str]
    disagreement_zones: list[DisagreementZone]
    confidence_map: list[ClaimScore]
    overall_consensus_score: float  # 0–1
```

If the LLM fails to emit parseable JSON, a **heuristic fallback** uses Jaccard similarity on Round 1 vs Round 3 responses to build the map automatically.

---

## ⚙️ Model Configurations (`backend/config.py`)

- **Debate Models (`debate_MODELS`)**: Configured dynamically depending on the API keys loaded from `.env`:
  - **OpenRouter (Free Tier)**: `deepseek/deepseek-v4-flash:free`, `z-ai/glm-4.5-air:free`, `liquid/lfm-2.5-1.2b-instruct:free`, `nvidia/nemotron-3-nano-30b-a3b:free`
  - **Groq (High-Performance)**: `groq/llama-3.1-8b-instant`, `groq/openai/gpt-oss-120b`, `groq/qwen/qwen3-32b`, `groq/llama-3.3-70b-versatile`
- **Chairman Model (`moderator_MODEL`)**: Uses `groq/llama-3.3-70b-versatile` when Groq key is present, else `deepseek/deepseek-v4-flash:free`.
- **Temperature Support**: All provider clients (`groq.py`, `openrouter.py`, `llm.py`) accept a `temperature: float = 0.7` parameter used by the metacognition probe.

---

## 🛡️ Failures & Fallbacks Handling

1. **Graceful Degradation**: Individual query failures do not abort the deliberation. The pipeline continues with a subset of active models.
2. **Metacognition Failure**: If a model returns fewer than 2 valid probes, its `ModelConfidenceScore` is omitted (treated as unknown weight by the Chairman).
3. **Chairman Fallback**: If the Chairman model fails or returns empty in Round 5, the system attempts fallback synthesis using the first available debate model. If all fail, it falls back to the leading answer from Round 3.
4. **Disagreement Fallback**: If the Chairman does not emit a parseable JSON block, `build_disagreement_map_heuristic()` runs automatically.
