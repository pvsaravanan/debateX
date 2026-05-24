## ADDED Requirements

### Requirement: CRUD operations for conversations
The system SHALL expose REST endpoints on port 8001 to list conversations, create new empty conversations, load existing conversations, update a conversation's title, and delete a conversation.

#### Scenario: Listing conversations
- **WHEN** client sends a GET request to `/api/conversations`
- **THEN** system returns a JSON list of all active conversations, sorted by creation date with the newest first, excluding empty ones

#### Scenario: Creating a conversation
- **WHEN** client sends a POST request to `/api/conversations`
- **THEN** system creates a new conversation with a unique UUID and returns the created conversation JSON structure

### Requirement: Server-Sent Events (SSE) debate streaming
The system SHALL support Server-Sent Events (SSE) to stream the progress of each of the 5 deliberation rounds to the client progressively in real time.

#### Scenario: Streaming a debate message
- **WHEN** client sends a POST request to `/api/conversations/{conversation_id}/message/stream`
- **THEN** system emits SSE messages with type keys corresponding to `stage1_start`, `stage1_complete`, `stage2_start`, `stage2_complete`, `round3_start`, `round3_complete`, `round4_start`, `round4_complete`, `stage3_start`, `stage3_complete`, and `complete`
