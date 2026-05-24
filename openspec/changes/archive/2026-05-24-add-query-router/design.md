## Context

DebateX relies on a multi-model council debate. However, running a large 5-round debate across all available models (both paid and free tiers) can lead to high latency and unnecessary API consumption. We are building a query router to analyze user queries, select a optimal council subset, toggle disagreement panels, determine web search requirements, and estimate overall query cost.

## Goals / Non-Goals

**Goals:**
- Implement `backend/router.py` to classify incoming queries into 5 standard classes: `technical/code`, `creative`, `factual/research`, `ethical/philosophical`, `math/logic`.
- Provide a robust local keyword-based fallback classifier in case of LLM API timeouts or network failures.
- Map each category to an optimal sub-composition of available models.
- Determine whether `Disagreement Panel` is mandatory and whether `Fact-Checker` needs web access.
- Calculate query cost estimates in USD using a defined model pricing table.

**Non-Goals:**
- This proposal is design-isolated; integration into the main debate server stream is out of scope for this change (but the module will be fully ready and tested for immediate consumption).

## Decisions

### Decision: Dual-Path Classification (LLM + Regex Fallback)
The router queries a fast free model (like `z-ai/glm-4.5-air:free`) via the LLM facade. If the request fails, the router falls back to a highly descriptive regex keyword classifier.
- *Rationale*: A dual-path approach ensures maximum reliability, keeping the application robust even during network outages.

### Decision: Configurable Model Compositions
We define model mappings tailored to query category strengths (e.g. reasoning models for math, diverse context models for creative).
- *Rationale*: Different model architectures excel at different cognitive tasks. Selective composition balances quality and latency.

### Decision: Token-Based Cost Estimation Model
We calculate the cost using a standardized token estimation size (e.g., 500 input and 1000 output tokens per model) multiplied by the actual model pricing table in USD per million tokens.
- *Rationale*: Since exact consumption is only known after execution, a predicted cost estimate helps users manage their budget proactively.

## Risks / Trade-offs

- **[Risk] Cost of Classification Call** → *Mitigation*: We strictly use free-tier models on OpenRouter (e.g. `z-ai/glm-4.5-air:free`) for classification, resulting in zero additional token costs.
