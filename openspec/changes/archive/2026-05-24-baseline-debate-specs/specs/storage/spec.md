## ADDED Requirements

### Requirement: JSON conversation serialization
The system SHALL persist conversation history under a dedicated `data/conversations/` directory, using JSON formatting where each conversation file is named as `<conversation_uuid>.json`.

#### Scenario: Saving a conversation
- **WHEN** a new user or assistant message is added to a conversation
- **THEN** system serializes the complete conversation object to disk in indented JSON format

### Requirement: Deliberation metadata and round persistence
The system SHALL serialize the detailed `rounds` array (storing every step of the 5-round deliberation pipeline) and a `metadata` dictionary containing de-anonymization lookup maps and final aggregate statistics.

#### Scenario: Loading conversation history
- **WHEN** client retrieves a conversation by ID
- **THEN** system reads the JSON file and returns the complete conversation object, including the rounds array and de-anonymization metadata
