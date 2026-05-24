## ADDED Requirements

### Requirement: High-performance moderator prioritization
When both the Groq API key and OpenRouter API key are present in the environment, the system SHALL concurrently load models from both providers for the debate council, and SHALL prioritize `groq/llama-3.3-70b-versatile` as the Chairman/Moderator model instead of defaulting to a free OpenRouter model.

#### Scenario: Both keys present
- **WHEN** both `OPENROUTER_API_KEY` and `GROQ_API_KEY` are defined in `.env`
- **THEN** system loads models from both providers for the council and sets the moderator model to `groq/llama-3.3-70b-versatile`
