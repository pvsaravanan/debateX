## Why

Currently, when both `OPENROUTER_API_KEY` and `GROQ_API_KEY` are present, the backend uses models from both providers for the debate council, but defaults the Moderator/Chairman to `deepseek/deepseek-v4-flash:free` from OpenRouter. This proposal explicitly modifies the model configurations to select the high-performance `groq/llama-3.3-70b-versatile` as the Chairman when both keys are available to improve synthesis quality and latency.

## What Changes

- Modify model initialization logic in `backend/config.py` to prioritize `groq/llama-3.3-70b-versatile` as the `moderator_MODEL` when both keys are present.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `core-deliberation`: Prioritizes the high-performance Groq model as the moderator when both OpenRouter and Groq keys are available.

## Impact

- **Affected code**: Modifies `backend/config.py` model loading priorities.
- **APIs**: No endpoint signature modifications.
- **Dependencies**: No new packages.
