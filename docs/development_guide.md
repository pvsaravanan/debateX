# Development Guide

## Tech Stack & Requirements

- **Backend**: Python 3.11+, FastAPI, Uvicorn, httpx, pydantic
- **Frontend**: React 18, Vite, react-markdown, vanilla CSS
- **System**: Node.js >= 20 LTS, npm >= 10, uv (Python package manager)

## Setup for Development

### Backend
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Common Workflows

### Adding a New Provider
The LLM integration is modular. To add a new provider:
1. Create `backend/new_provider.py`.
2. Update `backend/llm.py` to route prefixes (e.g., `new_provider/`) to your new file.
3. Add the required API keys to `.env` and `config.py`.

### Troubleshooting
- **Backend won't start (`ModuleNotFoundError`)**: Ensure you are running it from the project root (`uv run python -m backend.main`) or using Uvicorn directly in the `backend` folder.
- **Frontend CORS errors**: Ensure the backend is running on port `8001`.
- **Models timing out**: Check if OpenRouter/Groq are experiencing high load or increase the timeout limit in `query_model`.
