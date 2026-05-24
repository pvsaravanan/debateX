# Core Deliberation Specification

This specification documents the core deliberation engine of **DebateX**, which coordinates a multi-LLM debate through a 5-round pipeline to construct a single high-quality, synthesized master response.

---

## 🏗️ System Overview

DebateX establishes an asynchronous deliberation council composed of multiple diverse LLMs (the Council Members) and a designated moderator model (the Chairman). The system leverages non-biased peer evaluations to identify high-quality responses and challenge weaknesses, culminating in an authoritative synthesis.

---

## 🔄 The 5-Round Pipeline Flow

All five rounds execute in sequential asynchronous operations coordinated by `backend/debate.py` and are streamed dynamically to the client via Server-Sent Events (SSE).

### Round 1: Initial Answers (`stage1_collect_responses`)
- **Action**: Queries all configured council models in parallel with the user's query.
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
- **Action**: The Chairman/Moderator model receives the complete JSON deliberation history.
- **Objective**: Weighs initial answers, subsequent revisions/defenses, peer rankings, and explicitly addresses the Challenger's critique to construct the final synthesized response.

---

## ⚙️ Model Configurations (`backend/config.py`)

- **Debate Models (`debate_MODELS`)**: Configured dynamically depending on the API keys loaded from `.env`:
  - **OpenRouter (Free Tier)**: `deepseek/deepseek-v4-flash:free`, `z-ai/glm-4.5-air:free`, `liquid/lfm-2.5-1.2b-instruct:free`, `nvidia/nemotron-3-nano-30b-a3b:free`
  - **Groq (High-Performance)**: `groq/llama-3.3-70b-versatile`, `groq/llama-3.1-8b-instant`, `groq/mixtral-8x7b-32768`, `groq/gemma2-9b-it`
- **Chairman Model (`moderator_MODEL`)**: Uses `groq/llama-3.3-70b-versatile` or `deepseek/deepseek-v4-flash:free` as the primary synthesis engine.

---

## 🛡️ Failures & Fallbacks Handling

1. **Graceful Degradation**: Individual query failures do not abort the deliberation. The pipeline continues with a subset of active models.
2. **Chairman Fallback**: If the Chairman model fails or returns empty in Round 5, the system attempts fallback synthesis using the first available debate model. If all fail, it falls back to the leading answer from Round 3.
