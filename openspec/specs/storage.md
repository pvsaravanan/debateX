# Storage Specification

This specification defines the file system layouts, JSON serialization schemas, and persistence architecture for saving and restoring conversations in **DebateX**.

---

## 📁 Directory Layout

All conversation files are stored inside a dedicated data directory in the project root:
```
debateX/
└── data/
    └── conversations/
        ├── {conversation_uuid}.json
        └── ...
```

---

## 📄 Conversation JSON Schema

Each `{conversation_uuid}.json` file stores a single conversation document represented as a JSON object:

```json
{
  "id": "uuid-v4-string",
  "created_at": "ISO-8601-UTC-timestamp",
  "title": "Generated Short Title",
  "messages": [
    {
      "role": "user",
      "content": "Original user query text"
    },
    {
      "role": "assistant",
      "stage1": [
        {
          "model": "model-name-identifier",
          "response": "Raw answer markdown content"
        }
      ],
      "stage2": [
        {
          "model": "model-name-identifier",
          "ranking": "Full review text and ranking comments strictly in English",
          "parsed_ranking": [
            "Response A",
            "Response B"
          ]
        }
      ],
      "stage3": {
        "model": "moderator-model-name",
        "response": "Final synthesized answer markdown content"
      },
      "rounds": [
        {
          "round": 1,
          "type": "initial_answers",
          "data": [ ... ]
        },
        {
          "round": 2,
          "type": "peer_review",
          "data": [ ... ]
        },
        {
          "round": 3,
          "type": "revise_or_defend",
          "data": [ ... ]
        },
        {
          "round": 4,
          "type": "challenger",
          "data": { ... }
        },
        {
          "round": 5,
          "type": "chairman_synthesis",
          "data": { ... }
        }
      ],
      "metadata": {
        "label_to_model": {
          "Response A": "model-name-1",
          "Response B": "model-name-2"
        },
        "aggregate_rankings": [
          {
            "model": "model-name-1",
            "average_rank": 1.5,
            "rankings_count": 4
          }
        ],
        "rounds": [ ... ]
      }
    }
  ]
}
```

---

## ⚖️ Persistence vs. Ephemeral Data

To optimize storage space and runtime performance, DebateX enforces a clean division between stored structure and client-side presentation:

1.  **Persisted Structures**:
    -   Rounds 1, 2, and 5 (representing Stage 1 initial responses, Stage 2 rankings, and Stage 3 final response for backward compatibility).
    -   Detailed `rounds` array (storing every step of the 5-round deliberation pipeline).
    -   `metadata` dictionary containing de-anonymization lookup map and final aggregate statistics.
2.  **Client-Side Computation / Dynamic Presentation**:
    -   **De-anonymization Rendering**: Models are anonymized under strict labels in the backend (`Response A`). The React client reads the `metadata.label_to_model` mapping to display model names in **bold** directly in the peer review panels. The backend does not modify the raw peer-review text files before saving.
    -   **Active loading states**: Managed fully in-memory by React `App.jsx` during SSE event streaming and are never saved to disk.
