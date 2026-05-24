# query-routing Specification

## Purpose
TBD - created by archiving change add-query-router. Update Purpose after archive.
## Requirements
### Requirement: Query Classification
The system SHALL classify any incoming string query into one of five standard categories: `technical/code`, `creative`, `factual/research`, `ethical/philosophical`, `math/logic` using a fast, free LLM query.

#### Scenario: Verify successful classification
- **WHEN** client requests routing for the query "write a quicksort in python"
- **THEN** system classifies the query as `technical/code`

### Requirement: Configuration Extraction
The system SHALL extract configuration properties based on the query classification:
- **Optimal Council**: Returns a filtered subset of available models best suited for the category.
- **Disagreement Panel**: Mandatory for `factual/research`, `technical/code`, and `math/logic`; optional/false for `creative` and `ethical/philosophical`.
- **Web Access**: Mandatory for `factual/research` and `technical/code` (for fresh API references); optional/false for others.

#### Scenario: Configuration for math query
- **WHEN** a query is classified as `math/logic`
- **THEN** system returns that Disagreement Panel is mandatory, Web Access is false, and selects reasoning-capable models as the optimal council

### Requirement: Query Cost Estimation
The system SHALL calculate and return a query cost estimate in USD based on input/output token pricing parameters for the selected council composition models.

#### Scenario: Verify cost calculation logic
- **WHEN** a technical query selects Llama 3.3 70B and Llama 3.1 8B in the council composition
- **THEN** the system returns a non-zero, float cost estimate representing the predicted cost in USD for the query

