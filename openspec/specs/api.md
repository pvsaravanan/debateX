# API Specification

This specification defines the communication protocols, REST endpoints, and Server-Sent Events (SSE) streaming API for the **DebateX** application.

---

## ⚙️ General Configuration

- **Protocol**: HTTP/1.1
- **Host / Port**: `http://localhost:8001` (specifically port 8001 to prevent conflicts with common default local servers running on 8000).
- **CORS Policy**: Enabled for `http://localhost:5173`, `http://localhost:3000`, and wildcard `*`. Supports standard methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`.

---

## 📂 REST Endpoints

### 1. Health Check
*   **Method**: `GET`
*   **Path**: `/`
*   **Response (JSON)**:
    ```json
    {
      "status": "ok",
      "service": "DebateX API"
    }
    ```

### 2. List Conversations
*   **Method**: `GET`
*   **Path**: `/api/conversations`
*   **Response (JSON)**: Array of conversation metadata (newest first, filtering out empty chats).
    ```json
    [
      {
        "id": "uuid-string",
        "created_at": "ISO-8601-timestamp",
        "title": "Title of Conversation",
        "message_count": 2
      }
    ]
    ```

### 3. Create Conversation
*   **Method**: `POST`
*   **Path**: `/api/conversations`
*   **Request Body (JSON)**: `{}` (empty object)
*   **Response (JSON)**:
    ```json
    {
      "id": "uuid-string",
      "created_at": "ISO-8601-timestamp",
      "title": "New Conversation",
      "messages": []
    }
    ```

### 4. Get Conversation
*   **Method**: `GET`
*   **Path**: `/api/conversations/{conversation_id}`
*   **Response (JSON)**: Full conversation details containing full history of user and assistant messages.

### 5. Update Conversation Title
*   **Method**: `PUT`
*   **Path**: `/api/conversations/{conversation_id}`
*   **Request Body (JSON)**: `{"title": "New Title String"}`
*   **Response (JSON)**: `{"success": true, "title": "New Title String"}`

### 6. Delete Conversation
*   **Method**: `DELETE`
*   **Path**: `/api/conversations/{conversation_id}`
*   **Response (JSON)**: `{"success": true, "message": "Conversation deleted"}`

---

## ⚡ Server-Sent Events (SSE) Streaming Lifecycle

*   **Method**: `POST`
*   **Path**: `/api/conversations/{conversation_id}/message/stream`
*   **Request Body (JSON)**: `{"content": "User question here"}`
*   **Header**: `Content-Type: text/event-stream`

### Stream Event Chunks Schema

The endpoint yields lines starting with `data: ` containing serialized JSON objects. The object structure depends on the `type` property:

| Event `type` | Payload Keys / Format | Description |
| :--- | :--- | :--- |
| `metacognition_start` | `{}` | Emitted at the same time as `stage1_start`. Signals the UI to show a "probing consistency…" indicator. |
| `stage1_start` | `{}` | Emitted when council starts generating initial responses. |
| `stage1_complete` | `{"data": [...]}` | Array of `{"model": "name", "response": "..."}` objects representing successful Round 1 answers. |
| `stage2_start` | `{}` | Emitted when peer evaluations and ranking begins. Metacognition runs concurrently in the background. |
| `stage2_complete` | `{"data": [...], "metadata": {"label_to_model": {...}, "aggregate_rankings": [...]}}` | Emitted with evaluation reviews, the de-anonymization mapping dictionary, and sorted list of average rankings. |
| `metacognition_complete` | `{"data": MetacognitionResult}` | Emitted after stage2, with per-model confidence scores, pairwise similarities, and tier assignments. See `MetacognitionResult` schema below. |
| `round3_start` | `{}` | Emitted when models start revising or defending their responses. |
| `round3_complete` | `{"data": [...]}` | Emitted with an array of decision objects: `{"model": "name", "decision": "REVISE/DEFEND", "response": "..."}`. |
| `round4_start` | `{}` | Emitted when Challenger model begins critique. |
| `round4_complete` | `{"data": {...}}` | Emitted with the challenger critique object pointing out the weakest spots of the leading answer. |
| `stage3_start` | `{}` | Emitted when Chairman starts master synthesis. |
| `stage3_complete` | `{"data": ChairmanResult, "disagreement_map": DisagreementMap}` | Emitted with final synthesized answer. Includes structured `disagreement_map` (consensus zones, divergence details, confidence map). See schemas below. |
| `title_complete` | `{"data": {"title": "Generated Title"}}` | Emitted when a short conversation title is successfully generated (first message only). |
| `complete` | `{}` | Sent when processing completes and conversation is saved to storage. |
| `error` | `{"message": "error reason"}` | Sent if a fatal exception occurs. Closes stream. |

---

## 📦 Key Payload Schemas

### `MetacognitionResult`
```json
{
  "scores": {
    "groq/llama-3.3-70b-versatile": {
      "model": "groq/llama-3.3-70b-versatile",
      "confidence": 0.91,
      "tier": "HIGH",
      "sim_01": 0.88,
      "sim_02": 0.85,
      "sim_12": 0.90,
      "avg_similarity": 0.876,
      "probes": [
        { "temperature": 0.3, "response": "..." },
        { "temperature": 0.7, "response": "..." },
        { "temperature": 1.0, "response": "..." }
      ]
    }
  },
  "summary": "Model confidence weights (derived from self-consistency probing):\n  ..."
}
```

### `DisagreementMap` (inside `stage3_complete`)
```json
{
  "consensus_points": ["Both models agreed X is correct", "..."],
  "disagreement_zones": [
    {
      "claim": "Whether Y approach is optimal",
      "positions": {
        "model-A": "Y is optimal because ...",
        "model-B": "Y has limitations due to ..."
      },
      "divergence_reason": "Different assumptions about scale",
      "human_review_needed": true
    }
  ],
  "confidence_map": [
    {
      "claim": "X is correct",
      "model_scores": { "model-A": 0.95, "model-B": 0.88 }
    }
  ],
  "overall_consensus_score": 0.72
}
```

### `ChairmanResult` (inside `stage3_complete.data`)
```json
{
  "model": "groq/llama-3.3-70b-versatile",
  "response": "Final synthesized narrative (JSON block stripped out)",
  "disagreement_map": { ... }
}
```
