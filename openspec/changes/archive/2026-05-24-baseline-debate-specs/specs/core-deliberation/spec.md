## ADDED Requirements

### Requirement: 5-round deliberation pipeline execution
The system SHALL execute the deliberation council process sequentially in five distinct rounds: Round 1 (Initial Answers), Round 2 (Anonymized Peer Review & Ranking), Round 3 (Revise or Defend), Round 4 (Challenger Critique), and Round 5 (Chairman Synthesis).

#### Scenario: Running full debate successfully
- **WHEN** user query is received and the debate is run
- **THEN** system executes all five rounds asynchronously in sequence, calculates aggregate standings, assigns a challenger, and produces the final Chairman synthesis

### Requirement: Dynamic model provider facade routing
The system SHALL route LLM query requests dynamically to the appropriate provider (Groq or OpenRouter) based on the model name prefix (e.g. `groq/` prefix maps to the Groq API provider client).

#### Scenario: Groq prefix query
- **WHEN** model name starts with "groq/"
- **THEN** system invokes the Groq client with the model name minus the prefix

#### Scenario: OpenRouter default query
- **WHEN** model name does not start with "groq/"
- **THEN** system invokes the OpenRouter client with the full model name

### Requirement: Resilient fallback execution
The system SHALL degrade gracefully on model errors, allowing the pipeline to continue with the successful models. If the Chairman synthesis fails, the system SHALL attempt fallback models and ultimately default to the leading answer from Round 3.

#### Scenario: Chairman model failure
- **WHEN** the primary Chairman model fails to generate a response in Round 5
- **THEN** system attempts to query debate models in order for synthesis, and falls back to the leading answer from Round 3 if all fail
