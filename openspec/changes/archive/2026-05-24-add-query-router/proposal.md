## Why

When processing user queries, the LLM council currently uses a static model composition and fixed configuration, regardless of whether the query is a simple math proof, an elaborate story, or a complex software engineering task. Introducing a query classifier router allows for dynamically optimizing the council composition, ensuring the best models are used for the task, while estimating costs and controlling web search dependencies.

## What Changes

- Create a new module `backend/router.py` implementing query classification, dynamic council selection, configuration flags (disagreement panel, web access), and cost estimation.
- Utilize a fast, free LLM (like OpenRouter's `nvidia/nemotron-3-nano-30b-a3b:free` or `z-ai/glm-4.5-air:free`) to classify incoming queries.
- Support five query classes: `technical/code`, `creative`, `factual/research`, `ethical/philosophical`, `math/logic`.

## Capabilities

### New Capabilities
- `query-routing`: Classifies incoming user queries, dynamically selects optimal council compositions, determines configuration requirements, and calculates query cost estimates.

### Modified Capabilities
<!-- None -->

## Impact

- **Affected code**: Adds `backend/router.py`.
- **APIs**: Standalone module; ready for downstream pipeline integration.
- **Dependencies**: Uses the existing LLM provider facade client.
