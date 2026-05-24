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
        "rounds": [ "..." ],
        "disagreement_map": {
          "consensus_points": ["..."],
          "disagreement_zones": [
            {
              "claim": "...",
              "positions": { "model-A": "...", "model-B": "..." },
              "divergence_reason": "...",
              "human_review_needed": false
            }
          ],
          "confidence_map": [
            { "claim": "...", "model_scores": { "model-A": 0.9 } }
          ],
          "overall_consensus_score": 0.72
        },
        "metacognition": {
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
    -   `metadata` dictionary containing de-anonymization lookup map, aggregate statistics, `disagreement_map`, and `metacognition` results.
    -   `disagreement_map`: Structured consensus/disagreement analysis populated by the Chairman or heuristic fallback.
    -   `metacognition`: Per-model self-consistency scores derived from 3-temperature probing. Includes raw probe responses.
2.  **Client-Side Computation / Dynamic Presentation**:
    -   **De-anonymization Rendering**: Models are anonymized under strict labels in the backend (`Response A`). The React client reads the `metadata.label_to_model` mapping to display model names in **bold** directly in the peer review panels. The backend does not modify the raw peer-review text files before saving.
    -   **Active loading states**: Managed fully in-memory by React `App.jsx` during SSE event streaming and are never saved to disk.
    -   **ConfidenceHeatmap visual state** (expanded/collapsed per row): Pure React local state, not persisted.
