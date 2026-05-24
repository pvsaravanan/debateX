## ADDED Requirements

### Requirement: RoleAssignment dataclass structure
The system SHALL return role assignments using a `RoleAssignment` dataclass containing the following fields: `reasoners` (list of strings), `fact_checker` (string), `devils_advocate` (string), `steelmanner` (string), `chairman` (string), and `system_prompts` (dictionary mapping model names to their role-specific prompts).

#### Scenario: Verify dataclass properties
- **WHEN** a RoleAssignment object is created
- **THEN** it must contain valid reasoners list, fact_checker, devils_advocate, steelmanner, chairman, and a dictionary of model system prompts

### Requirement: Dynamic role allocation and rotation
The system SHALL allocate council roles dynamically to a given list of models using a query rotation offset. It SHALL shift/rotate the model array deterministically based on `query_index` before assigning roles to ensure even load and perspective distribution across queries.

#### Scenario: Deteministic role rotation
- **WHEN** allocating roles with a list of 5 models and a query index of 2
- **THEN** the model array is shifted by 2, and roles are assigned to the rotated models in order

#### Scenario: Graceful degradation for fewer models
- **WHEN** allocating roles with fewer than 5 models (e.g. 3 models)
- **THEN** the system allocates Chairman, Devil's Advocate, and Reasoner roles, leaving Fact-Checker and Steelmanner empty or fallback to maintain operation

### Requirement: Specialized system prompts by query type
The system SHALL generate a unique system prompt for each role based on the `query_type` (technical, creative, factual, ethical, math), outlining specific cognitive objectives (e.g., Fact-Checker gets a prompt with instructions to verify references, Reasoner gets step-by-step thinking instructions).

#### Scenario: Technical query prompt generation
- **WHEN** generating prompts for the "technical" query type
- **THEN** the system generates role prompts emphasizing code standards, algorithms, verification, and technical trade-offs
