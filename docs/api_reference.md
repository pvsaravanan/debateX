# API Reference

All endpoints are JSON-based. Full OpenAPI documentation is automatically available at `/docs` when running the backend locally (http://localhost:8001/docs).

## Conversations

### GET `/api/conversations`
List all conversations (metadata only: `id`, `created_at`, `title`, `message_count`). Empty conversations are filtered out.

### POST `/api/conversations`
Create a new conversation. Returns the full conversation object with a generated UUID.

### GET `/api/conversations/{id}`
Fetch a specific conversation with full message history. Assistant messages contain `stage1`, `stage2`, `stage3`, `rounds[]`, and `metadata`.

### PUT `/api/conversations/{id}`
Rename a conversation. Body: `{ "title": "New title" }`.

### DELETE `/api/conversations/{id}`
Delete a conversation and all its messages. Returns 404 if it does not exist.

## Messaging

### POST `/api/conversations/{id}/message` (batch)

Submit a user message and run the full deliberation to completion: routing → 5 rounds → synthesis.

**Request**
```bash
curl -X POST http://localhost:8001/api/conversations/{id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the architectural trade-offs between microservices and monoliths?"
  }'
```

**Response**
```jsonc
{
  "stage1": [ { "model": "...", "response": "..." } ],          // Round 1 initial answers
  "stage2": [ { "model": "...", "ranking": "...",               // Round 2 peer reviews
                "parsed_ranking": ["Response A", "..."] } ],
  "stage3": { "model": "...", "response": "...",                // Round 5 chairman synthesis
              "disagreement_map": { /* consensus & divergence */ } },
  "rounds": [ /* all 5 rounds, typed */ ],
  "metadata": {
    "routing": {
      "category": "technical/code",
      "optimal_council": ["..."],
      "chairman": "...",
      "role_map": { "<model>": "Reasoner | Devil's Advocate | Fact-Checker | Steelmanner" },
      "estimated_cost_usd": 0.0097,
      "disagreement_panel_mandatory": true,
      "fact_checker_web_access": true
    },
    "label_to_model": { "Response A": "<model>" },
    "aggregate_rankings": [ { "model": "...", "average_rank": 1.33, "rankings_count": 3 } ],
    "disagreement_map": { /* same as stage3.disagreement_map */ },
    "metacognition": null    // populated only when ENABLE_METACOGNITION=true
  }
}
```

### POST `/api/conversations/{id}/message/stream` (SSE)

Same pipeline, streamed as Server-Sent Events — this is what the frontend uses. Each event is a `data: {json}` line.

**Event protocol (in order):**

| Event | Payload |
|-------|---------|
| `routing_start` | — |
| `routing_complete` | `data`: category, optimal_council, chairman, role_map, estimated_cost_usd, flags |
| `metacognition_start` / `metacognition_complete` | only when `ENABLE_METACOGNITION=true`; `data`: per-model confidence scores |
| `round1_start` / `round1_complete` | `data`: initial answers |
| `round2_start` / `round2_complete` | `data`: peer reviews; `metadata`: `label_to_model`, `aggregate_rankings` |
| `round3_start` / `round3_complete` | `data`: REVISE/DEFEND decisions + responses |
| `round4_start` / `round4_complete` | `data`: challenger critique, target model & answer |
| `round5_start` / `round5_complete` | `data`: chairman synthesis; `disagreement_map` |
| `title_complete` | first message of a conversation only; `data.title` |
| `complete` | terminal success event (result is persisted server-side) |
| `error` | `message`: human-readable failure reason; terminal |
