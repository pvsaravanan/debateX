<div align="center">

# ⚖️ debateX

**Enterprise-grade multi-LLM deliberation engine. Get council-vetted answers, not single-model guesses.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![OpenRouter](https://img.shields.io/badge/Powered%20by-OpenRouter-orange)](https://openrouter.ai)
[![Self-Hosted](https://img.shields.io/badge/Self--Hosted-100%25-success)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

[Features](#features) · [Why debateX](#why-debatex) · [Quick Start](#quick-start) · [Architecture](#architecture) · [Configuration](#configuration) · [API Reference](#api-reference) · [Deployment](#deployment) · [Contributing](#contributing)

</div>

---

## Features

- ✨ **Three-Stage Deliberation Pipeline** — Independent reasoning → anonymized peer review → chairman synthesis
- 🔐 **Architectural Anonymization** — Models review peers without knowing their identity, eliminating provider bias
- ⚡ **Async Parallel Execution** — All stage 1 & stage 2 queries run in parallel for minimal latency
- 🎯 **Aggregate Ranking Intelligence** — Statistical consensus across evaluations, not just majority vote
- 🏗️ **Zero Frameworks** — Pure Python orchestration. No LangChain, CrewAI, or AutoGen bloat
- 📊 **Full Transparency** — Inspect all raw outputs, parsed rankings, and aggregates via rich web UI
- 🔄 **Model Agnostic** — Supports any OpenRouter-compatible model (GPT, Claude, Gemini, Grok, Mistral, Llama, etc.)
- 📦 **Self-Hosted** — Full control over your data and inference pipeline
- 💾 **Conversation Persistence** — Built-in SQLite storage with PostgreSQL ready for scale
- 🚀 **Production Ready** — Docker Compose, async/await throughout, type-safe with Pydantic

---

## Overview

**debateX** is a self-hosted, production-ready multi-LLM deliberation system inspired by [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council). Instead of asking a single LLM and accepting its potential blind spots, debateX convenes a council of diverse language models — each generating independent responses, reviewing each other anonymously to prevent bias, and deferring to a designated Chairman LLM for high-confidence final synthesis.

The result: **higher-quality, bias-reduced answers** for mission-critical tasks like architectural decisions, legal analysis, medical research, code review, strategic planning, and any complex reasoning where a single model's perspective isn't enough.

## How It Works: Three-Stage Deliberation

![Three-Stage Deliberation Pipeline](./public/images/pipeline.png)

**Key Insight:** Stage 1 & 2 run in parallel. Anonymization in Stage 2 prevents bias toward well-known vendors. Stage 3 brings coherence using statistical consensus.

## Architecture

debateX is built for **developer extensibility and operational clarity**. Here's the design philosophy:

### Core Components

**Backend Orchestration** (`debate.py`)
- `stage1_collect_responses()` — Parallel queries to all council members via OpenRouter
- `stage2_collect_rankings()` — Models evaluate anonymized peers, returns parsed rankings
- `stage3_synthesize_final()` — Chairman synthesizes Stage 1 + Stage 2 context into final answer
- `calculate_aggregate_rankings()` — Computes statistical consensus across all peer evaluations

**API Server** (`main.py`)
- FastAPI endpoints for query submission and conversation history
- Full CORS support for multi-origin deployments
- OpenAPI docs auto-generated at `/docs`

**LLM Client** (`openrouter.py`)
- Async HTTP client for OpenRouter API
- Parallel query batching via `asyncio.gather()`
- Graceful degradation: continues if some models fail

**Storage** (`storage.py`)
- JSON-based persistence (SQLite ready in roadmap)
- Conversation history with metadata
- No vendor lock-in

### Key Design Decisions

1. **Anonymization is Architectural**  
   Identity masking happens in the orchestrator, not via prompt tricks. Models can't "recognize" each other's writing style.

2. **Rankings Aggregate Statistically**  
   `calculate_aggregate_rankings()` computes average rank position across all peer evaluations, not just majority vote. This surfaces consensus and outlier opinions.

3. **Metadata is Ephemeral**  
   `label_to_model` mappings and `aggregate_rankings` are returned via API only — never persisted to disk. Keeps storage clean, metadata fresh per request.

4. **Zero Agent Framework Dependency**  
   No LangChain, CrewAI, or AutoGen. Pure Python orchestration + direct async API calls. Full control. Minimal dependencies. Fast startup.

5. **Full Transparency by Default**  
   All raw outputs inspectable via web UI. Parsed rankings shown next to raw text. Users validate system interpretation. Builds trust.

---

## System Architecture

![System Architecture](./public/images/system_arch.png)

**Data Flow:** User query via React UI → FastAPI routes → Orchestration layer runs 3 stages in parallel → OpenRouter handles all LLM calls → Results persisted & returned to frontend with full audit trail.

---

## Tech Stack & Requirements

### Recommended Stack

| Layer | Technology | Why This Choice |
|---|---|---|
| **Backend Orchestration** | Python 3.11+ · FastAPI | Async-native, type-safe with Pydantic, zero-config OpenAPI docs |
| **LLM Gateway** | OpenRouter | Single API key → access GPT, Claude, Gemini, Grok, Mistral, Llama, etc. |
| **Frontend UI** | React 18 · Vite | Hot reload, fast builds, component isolation, modern tooling |
| **Styling** | Vanilla CSS + design system | Minimal dependencies, full control over theme and responsiveness |
| **Package Management** | `uv` (Python) · `npm` (JS) | `uv` is 10-100x faster than pip; npm is industry standard |
| **Persistence** | JSON (dev) · SQLite (default) · PostgreSQL (production) | JSON for quick prototyping, SQLite for single-node, PG for scaled deployments |
| **Containerization** | Docker Compose | One-command reproducible local + remote deployments |
| **Process Management** | Uvicorn (dev) · Gunicorn (prod) | Production-grade ASGI with worker pooling |

### System Requirements

```bash
# Minimum
Python       ≥ 3.11
Node.js      ≥ 20 LTS
npm          ≥ 10

# Recommended (Python package manager)
uv           ≥ 0.1  (pip install uv)
```

### Key Dependencies

**Backend** (`pyproject.toml`)
```
fastapi           # Web framework
uvicorn[standard] # ASGI server
httpx              # Async HTTP client
pydantic-settings  # Config management
python-dotenv      # .env file loading
```

**Frontend** (`package.json`)
```
react, react-dom
vite               # Build tool + dev server
react-markdown     # Render Stage outputs
```

---

## Quick Start (5 minutes)

### Step 1: Clone & Setup Environment

```bash
git clone https://github.com/YOUR_USERNAME/debateX.git
cd debateX

# Create .env file with your OpenRouter API key
cp .env.example .env
```

**Get your API key:**
1. Sign up free at [openrouter.ai](https://openrouter.ai)
2. Navigate to [openrouter.ai/keys](https://openrouter.ai/keys)
3. Copy your API key into `.env`:

```env
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 2: Start Backend (Port 8001)

```bash
# Install Python dependencies
uv sync

# Run the backend as a module from the root
uv run python -m backend.main
```

**Backend is ready when you see:**
```
Uvicorn running on http://127.0.0.1:8001
```

**View API docs:**
- OpenAPI Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Step 3: Start Frontend (Port 5173)

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

**Frontend is ready when you see:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

### Step 4: Start Asking Questions

1. Open http://localhost:5173 in your browser
2. Type a complex question in the chat
3. Watch as debateX runs all 3 stages in ~8-15 seconds
4. Inspect individual responses, peer reviews, and final synthesis in tabs

---

## ⚡ One-Command Start (Recommended)

### Windows
Double-click `run.bat` in the root directory. This will:
1. Sync backend dependencies (`uv sync`)
2. Start the FastAPI backend on port 8001
3. Install frontend dependencies (`npm install`)
4. Start the Vite frontend on port 5173

### macOS / Linux
Run the start script from the root:
```bash
chmod +x start.sh
./start.sh
```

### Optional: Docker (Single Command)

```bash
docker compose up --build
```

This starts:
- Backend: http://localhost:8001
- Frontend: http://localhost:5173
- Full hot-reload on code changes

---

## Configuration

### Configuring Council Members

Edit `backend/config.py` to change which models participate:

```python
debate_MODELS = [
    "openai/gpt-4o",                    # GPT-4o
    "anthropic/claude-sonnet-4-5",      # Claude Sonnet
    "google/gemini-pro-1.5",            # Gemini Pro
    "x-ai/grok-3",                      # Grok 3
]

moderator_MODEL = "anthropic/claude-sonnet-4-5"  # Chairman model
```

**Available Models:** Browse all [openrouter.ai/models](https://openrouter.ai/models)

- **Cheap/Fast**: Mistral Nemo, Llama 3.1, GPT-4o Mini
- **High Quality**: GPT-4o, Claude 3.5 Sonnet, Gemini 2.0
- **Specialized**: o1 (reasoning), GPT-4o (vision)

### Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENROUTER_API_KEY` | ✅ Yes | — | Your OpenRouter API key |
| `OPENROUTER_HTTP_REFERER` | ❌ | `http://localhost` | Request header for OpenRouter |
| `OPENROUTER_TITLE` | ❌ | `debateX` | User agent title |

**See `.env.example` for all options.**

---

## API Reference

All endpoints are JSON-based. Full OpenAPI documentation available at `/docs` when running locally.

### POST `/api/conversations/{id}/message`

Submit a user message to the debate pipeline. Runs all 3 stages and returns full council output.

**Request**
```bash
curl -X POST http://localhost:8001/api/conversations/{id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the architectural trade-offs between microservices and monoliths for a 5-person team?"
  }'
```

**Response** (JSON)
```json
{
  "id": "msg-uuid",
  "role": "assistant",
  "stage1": [
    {
      "label": "Response A",
      "content": "Microservices provide flexibility but introduce complexity..."
    },
    {
      "label": "Response B",
      "content": "For a team of 5, monolith is likely the better starting point..."
    }
  ],
  "stage2": [
    {
      "label": "Model A",
      "raw_evaluation": "Response B makes strong points about cognitive overhead...",
      "parsed_ranking": ["Response B", "Response A"],
      "ranking_scores": [1, 2]
    },
    {
      "label": "Model B",
      "raw_evaluation": "Both responses valid; depends on team skillset...",
      "parsed_ranking": ["Response A", "Response B"],
      "ranking_scores": [1, 2]
    }
  ],
  "stage3": {
    "content": "For a 5-person team, a monolith is the pragmatic choice initially..."
  },
  "metadata": {
    "label_to_model": {
      "Response A": "openai/gpt-4o",
      "Response B": "anthropic/claude-sonnet-4-5"
    },
    "aggregate_rankings": {
      "Response B": 1.5,
      "Response A": 1.5
    }
  },
  "latency_ms": 12847
}
```

### GET `/api/conversations`

Fetch all conversations for the user.

**Response**
```json
{
  "conversations": [
    {
      "id": "conv-uuid",
      "created_at": "2025-01-15T10:30:00Z",
      "message_count": 4,
      "title": "Microservices vs Monolith"
    }
  ]
}
```

### GET `/api/conversations/{id}`

Fetch a specific conversation with full message history.

### DELETE `/api/conversations/{id}`

Delete a conversation and all its messages.

---

## Performance & Cost

### Latency Profile

For a 4-model council answering a typical question:

| Stage | Duration | Notes |
|---|---|---|
| **Stage 1** | 4-8s | Parallel, 4 concurrent queries |
| **Stage 2** | 3-6s | Parallel, 4 concurrent evaluations |
| **Stage 3** | 2-4s | Single synthesizer call |
| **Total** | ~8-15s | Network + inference latency |

*(Times vary by model size and OpenRouter load)*

### Cost Analysis

For a 4-model council with typical models:

| Stage | Calls | Cost (Est.) |
|---|---|---|
| Stage 1 | 4 queries | ~$0.02-0.10 |
| Stage 2 | 4 evaluations | ~$0.02-0.10 |
| Stage 3 | 1 synthesis | ~$0.01-0.05 |
| **Total per query** | **9 API calls** | **~$0.05-0.25** |

**Cost Optimization:**
- Use cheaper models (Mistral Nemo, Llama) for council members
- Reserve expensive models (GPT-4o, Claude Opus) for Chairman only
- Example: 4 x Haiku ($0.003/1k tokens) + 1 x Claude Sonnet = ~$0.03 per query

---

## Deployment

### Local Development

```bash
# Terminal 1: Backend
cd backend && uv run uvicorn main:app --reload --port 8001

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Docker Compose (Recommended)

```bash
docker compose up --build
```

Starts both services with hot-reload on code changes.

### Production Deployment

**Docker Swarm / Kubernetes:**

```bash
# Build images
docker build -t debatex-backend ./backend
docker build -t debatex-frontend ./frontend

# Deploy with your orchestrator
# Backend needs env: OPENROUTER_API_KEY, PORT=8001
# Frontend needs env: VITE_API_URL=https://api.example.com
```

**Environment Variables for Production:**

```bash
# Backend (.env or container env)
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_HTTP_REFERER=https://myapp.example.com

# Frontend (vite.config.js)
VITE_API_URL=https://api.example.com  # Points to backend URL
```

---

## Project Structure

```
debateX/
├── backend/                    # FastAPI server (Python 3.11+)
│   ├── main.py                 # API entrypoint, FastAPI app setup
│   ├── config.py               # Model configuration (edit here to change council)
│   ├── debate.py               # 3-stage orchestration (stage1/2/3 logic)
│   ├── openrouter.py           # OpenRouter async HTTP client
│   ├── storage.py              # Conversation persistence (JSON → SQLite later)
│   ├── .env.example            # Environment template
│   └── pyproject.toml          # Python dependencies (uv)
│
├── frontend/                   # React + Vite UI
│   ├── src/
│   │   ├── App.jsx             # Main component, state management
│   │   ├── main.jsx            # React entrypoint
│   │   ├── api.js              # HTTP client for backend
│   │   ├── index.css           # Global styles + design tokens
│   │   └── components/
│   │       ├── ChatInterface.jsx  # Message UI + response tabs
│   │       ├── Stage1.jsx         # Individual model responses
│   │       ├── Stage2.jsx         # Peer reviews + rankings
│   │       ├── Stage3.jsx         # Final synthesis
│   │       └── Sidebar.jsx        # Conversation list
│   ├── package.json            # JS dependencies
│   ├── vite.config.js          # Build config
│   └── index.html              # HTML entrypoint
│
├── data/
│   └── conversations/          # JSON storage (development)
│
├── docker-compose.yml          # Local/remote deployment
├── .env.example                # Environment template
├── README.md                   # This file
└── CLAUDE.md                   # Technical architecture notes
```

---

## Development Guide

### For Backend Developers

**Setting up your environment:**

```bash
cd backend

# Install Python dependencies
uv sync

# Run with auto-reload
uv run uvicorn main:app --reload --port 8001

# Run linting
uv run ruff check .

# Run type checking
uv run mypy .

# Run tests (when you write them)
uv run pytest tests/ -v
```

**Key files to understand:**
- `config.py` — Council member definitions (edit to change models)
- `debate.py` — Core 3-stage logic; start here to understand the pipeline
- `openrouter.py` — OpenRouter API client; inspect to see parallel query patterns
- `main.py` — FastAPI endpoints; add new routes here

**Common tasks:**
- Add a new model: Edit `debate_MODELS` list in `config.py`, restart backend
- Change chairman: Edit `moderator_MODEL` in `config.py`
- Debug a stage: Add print statements in `debate.py`, check terminal output

### For Frontend Developers

**Setting up your environment:**

```bash
cd frontend

# Install dependencies
npm install

# Start dev server with hot reload
npm run dev

# Lint your code
npm run lint

# Build for production
npm run build
```

**Key files to understand:**
- `src/App.jsx` — Main state management; follows React hooks pattern
- `src/api.js` — HTTP client for backend; add new endpoints here
- `src/components/Stage*.jsx` — Each stage's display logic
- `src/index.css` — Design tokens and global styles

**Common tasks:**
- Add a UI component: Create in `src/components/`, import in `App.jsx`
- Call backend API: Use functions from `api.js` (already configured CORS)
- Change styling: Edit component CSS or `index.css` for global changes

### Running Full Tests

```bash
# Backend tests
cd backend && uv run pytest tests/ -v

# Frontend tests
cd frontend && npm run test
```

### Code Quality

```bash
# Lint and format code
cd backend
uv run ruff check . --fix  # Auto-fix simple issues
uv run ruff format .

cd ../frontend
npm run lint -- --fix
```

---

## Common Workflows

### Adding a New Model to the Council

1. **Check model availability** on [openrouter.ai/models](https://openrouter.ai/models)
2. **Edit backend/config.py:**
   ```python
   debate_MODELS = [
       "openai/gpt-4o",
       "anthropic/claude-sonnet-4-5",
       "google/gemini-pro-1.5",
       "mistral-ai/mistral-nemo",  # <-- Add here
   ]
   ```
3. **Restart backend** — no code changes needed
4. **Test with a query** — new model should appear in Stage 1

### Customizing the Chairman

Change the final synthesis model:

```python
# backend/config.py
moderator_MODEL = "anthropic/claude-opus-4-1"  # Or any OpenRouter model
```

### Extending the Pipeline

Want to add a Stage 4? Modify `debate.py`:

```python
async def stage4_custom_step(responses, rankings):
    """Your custom logic here"""
    pass

# Add to the main orchestration flow
```

---

## Cost Considerations

### Understanding the Cost Model

debateX multiplies inference cost by the number of rounds. For a 4-model council with typical OpenRouter pricing:

| Scenario | Models | Calls | Est. Cost |
|---|---|---|---|
| **Small council** | Haiku × 4 | 9 | ~$0.03 |
| **Medium council** | GPT-4o Mini × 2 + Haiku × 2 | 9 | ~$0.08 |
| **Large council** | GPT-4o + Sonnet + Gemini + Grok | 9 | ~$0.20 |

### Optimization Strategies

**Cost Optimization:**

1. **Use tiered models** — Cheap council members (Haiku, Mistral) + expensive chairman (GPT-4o)
2. **Reduce council size** — 3 models often gives 80% of 4 models' quality at 75% cost
3. **Smart chairman** — Only the chairman needs maximum quality
4. **Cache responses** — Don't re-run Stage 1-2 for identical queries (in roadmap)

**Example optimal setup:**
```python
debate_MODELS = [
    "mistral-ai/mistral-nemo",        # ~$0.003/1k tokens
    "openai/gpt-4o-mini",             # ~$0.005/1k tokens
    "anthropic/claude-haiku-3",       # ~$0.005/1k tokens
]
moderator_MODEL = "openai/gpt-4o"     # ~$0.010/1k tokens (only once)
# Total cost: ~$0.08 per query vs ~$0.20 with all expensive models
```

---

## Roadmap

Core features currently shipping:
- ✅ Three-stage deliberation with anonymization
- ✅ Full web UI with conversation history
- ✅ OpenRouter integration (all major LLM providers)
- ✅ Docker Compose for local/remote deployment

Planned for future releases:
- [ ] Streaming responses (Stage 3 outputs in real-time)
- [ ] Domain-specific review prompts (legal, medical, code)
- [ ] Cost estimation before running queries
- [ ] Session comparison (diff two council runs side-by-side)
- [ ] Plugin system for custom post-processing
- [ ] Export transcripts as Markdown/PDF
- [ ] Distributed caching (Redis) for high-volume deployments
- [ ] Analytics dashboard (model performance over time)

---

## Troubleshooting

### Backend won't start

**Error: `ModuleNotFoundError: No module named 'backend'`**
- Make sure you're running from project root: `cd debateX && python -m backend.main`
- Or use the correct uvicorn command: `cd backend && uv run uvicorn main:app --reload`

**Error: `OPENROUTER_API_KEY not found`**
- Create `.env` file in project root: `cp .env.example .env`
- Add your API key: `OPENROUTER_API_KEY=sk-or-xxx`

### Frontend can't reach backend

**Error: `POST http://localhost:8001/api/... failed`**
- Make sure backend is running on port 8001
- Check CORS settings in `backend/main.py`
- Browser console (F12) should show CORS error details

### Models timing out in Stage 2

**Symptoms: Only Stage 1 responses, no Stage 2 rankings**
- Some models are slow to evaluate. Increase timeout in `config.py`
- Or remove slow models from the council
- Check OpenRouter status page for outages

### High latency (>30 seconds)

**Possible causes:**
- OpenRouter API is slow (check their status page)
- Too many models (try reducing council size)
- Network issue (check your internet connection)

---

## Contributing

We welcome contributions! Here's how:

1. **Fork & branch:**
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes:**
   - Backend: Follow PEP 8, use type hints, add docstrings
   - Frontend: Use React best practices, keep components small

3. **Test locally:**
   ```bash
   # Backend
   cd backend && uv run pytest tests/

   # Frontend
   cd frontend && npm run test
   ```

4. **Commit with conventional commits:**
   ```bash
   git commit -m "feat: add new council member management UI"
   ```

5. **Push & open PR:**
   ```bash
   git push origin feat/your-feature-name
   ```

**Areas we need help with:**
- Performance optimizations (caching, streaming)
- UI enhancements (dark mode, responsive design)
- Additional tests and edge case coverage
- Documentation improvements
- Model-specific prompting strategies

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

Licensed under the [MIT License](LICENSE). You're free to fork, modify, and deploy debateX for personal or commercial use.

---

## Acknowledgements & Attribution

- **Inspired by** [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council)
- **Powered by** [OpenRouter](https://openrouter.ai) for unified multi-provider LLM access
- **Built with** FastAPI, React, and a passionate open-source community

---

<div align="center">

### Questions?

📖 See [CLAUDE.md](CLAUDE.md) for deep technical architecture notes.

💬 Open an issue on GitHub for bugs, features, or discussions.

⭐ Consider starring if you find debateX useful!

---

**debateX** — because one voice is debate. A council is wisdom.

</div>