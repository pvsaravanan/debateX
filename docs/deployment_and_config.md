# Deployment & Configuration

## Configuration

DebateX relies on environment variables set in a `.env` file at the root of the project.

### Environment Variables
| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | Optional | API key for OpenRouter models |
| `GROQ_API_KEY` | Optional | API key for Groq models |

*Note: At least one API key must be provided to utilize models.*

### Customizing Council Members
Edit `backend/config.py` to change which models participate. DebateX dynamically combines models based on the keys provided:

- Models prefixed with `groq/` are routed to the Groq API.
- All other models default to OpenRouter.
- You can manually set the `moderator_MODEL` or rely on the dynamic defaults.

## Deployment

### Docker Compose (Recommended)
```bash
docker compose up --build
```
This starts both the backend (`http://localhost:8001`) and frontend (`http://localhost:5173`) with hot-reload.

### Production Deployment
**Docker Swarm / Kubernetes:**
```bash
docker build -t debatex-backend ./backend
docker build -t debatex-frontend ./frontend
```
Provide the necessary environment variables (`OPENROUTER_API_KEY`, `GROQ_API_KEY`, `VITE_API_URL`) via your orchestrator.

## Performance & Cost

### Latency Profile
For a 4-model council:
- **Stage 1**: 4-8s (Parallel)
- **Stage 2**: 3-6s (Parallel)
- **Stage 3**: 2-4s (Single call)
- **Total**: ~8-15s

### Cost Optimization
- Use fast, cheap models (e.g., Llama 3 8B, Haiku) for the council members.
- Reserve an expensive, high-reasoning model (e.g., GPT-4o, Claude Opus) solely for the Chairman (`moderator_MODEL`).
