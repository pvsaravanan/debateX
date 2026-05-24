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
| `stage1_start` | `{}` | Emitted when council starts generating initial responses. |
| `stage1_complete` | `{"data": [...]}` | Array of `{"model": "name", "response": "..."}` objects representing successful Round 1 answers. |
| `stage2_start` | `{}` | Emitted when peer evaluations and ranking begins. |
| `stage2_complete` | `{"data": [...], "metadata": {"label_to_model": {...}, "aggregate_rankings": [...]}}` | Emitted with evaluation reviews, the de-anonymization mapping dictionary, and sorted list of average rankings. |
| `round3_start` | `{}` | Emitted when models start revising or defending their responses. |
| `round3_complete` | `{"data": [...]}` | Emitted with an array of decision objects: `{"model": "name", "decision": "REVISE/DEFEND", "response": "..."}`. |
| `round4_start` | `{}` | Emitted when Challenger model begins critique. |
| `round4_complete` | `{"data": {...}}` | Emitted with the challenger critique object pointing out the weakest spots of the leading answer. |
| `stage3_start` | `{}` | Emitted when Chairman starts master synthesis. |
| `stage3_complete` | `{"data": {"model": "name", "response": "..."}}` | Emitted with final synthesized master answer from the Chairman model. |
| `title_complete` | `{"data": {"title": "Generated Title"}}` | Emitted when a short conversation title is successfully generated in the background (emitted only on first message). |
| `complete` | `{}` | Sent when processing completes successfully and conversation has been saved to storage. |
| `error` | `{"message": "error reason"}` | Sent if a fatal exception occurs (e.g. invalid API key, credit exhaustion). Closes stream. |
