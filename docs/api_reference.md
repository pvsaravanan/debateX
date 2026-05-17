# API Reference

All endpoints are JSON-based. Full OpenAPI documentation is automatically available at `/docs` when running the backend locally.

### POST `/api/conversations/{id}/message`

Submit a user message to the debate pipeline. Runs all 3 stages and returns full council output.

**Request**
```bash
curl -X POST http://localhost:8001/api/conversations/{id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the architectural trade-offs between microservices and monoliths?"
  }'
```

**Response Overview**
Returns a JSON object containing:
- `stage1`: Array of responses from individual models.
- `stage2`: Peer rankings and evaluations.
- `stage3`: The synthesized final answer from the Chairman.
- `metadata`: The `label_to_model` mapping and `aggregate_rankings`.

### GET `/api/conversations`
Fetch all conversations for the user.

### GET `/api/conversations/{id}`
Fetch a specific conversation with full message history.

### DELETE `/api/conversations/{id}`
Delete a conversation and all its messages.
