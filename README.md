<div align="center">

# ⚖️ debateX

**Enterprise-grade multi-LLM deliberation engine. Get council-vetted answers, not single-model guesses.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org)

</div>

---

## Overview

**debateX** is a self-hosted, production-ready multi-LLM deliberation system. Instead of asking a single LLM and accepting its potential blind spots, debateX convenes a council of diverse language models (via OpenRouter and Groq) — each generating independent responses, reviewing each other anonymously to prevent bias, and deferring to a designated Chairman LLM for high-confidence final synthesis.

### Features
- ✨ **Three-Stage Deliberation Pipeline** — Independent reasoning → anonymized peer review → chairman synthesis
- 🔐 **Architectural Anonymization** — Models review peers without knowing their identity, eliminating provider bias
- ⚡ **Async Parallel Execution** — Fast execution via concurrent LLM queries
- 🔄 **Multi-Provider Support** — Seamlessly mix and match models from OpenRouter and Groq
- 🏗️ **Zero Frameworks** — Pure Python orchestration; no LangChain/CrewAI bloat

---

## Architecture

![System Architecture](./public/images/system_arch.png)

### How It Works: Three-Stage Deliberation

![Three-Stage Deliberation Pipeline](./public/images/pipeline.png)

**Key Insight:** Stage 1 & 2 run in parallel. Anonymization in Stage 2 prevents bias toward well-known vendors. Stage 3 brings coherence using statistical consensus.

### Core Components

**Backend Orchestration** (`backend/debate.py` & `backend/llm.py`)
- `stage1_collect_responses()` — Parallel queries to all council members via OpenRouter/Groq
- `stage2_collect_rankings()` — Models evaluate anonymized peers, returns parsed rankings
- `stage3_synthesize_final()` — Chairman synthesizes Stage 1 + Stage 2 context into final answer
- `calculate_aggregate_rankings()` — Computes statistical consensus across all peer evaluations
- Dynamic routing to Groq or OpenRouter based on model prefixes.

**API Server** (`backend/main.py`)
- FastAPI endpoints for query submission and conversation history
- Full CORS support for multi-origin deployments

**Storage** (`backend/storage.py`)
- JSON-based persistence (SQLite ready in roadmap)
- Conversation history with metadata

### Key Design Decisions

1. **Anonymization is Architectural**  
   Identity masking happens in the orchestrator, not via prompt tricks. Models can't "recognize" each other's writing style.

2. **Rankings Aggregate Statistically**  
   `calculate_aggregate_rankings()` computes average rank position across all peer evaluations, not just majority vote.

3. **Metadata is Ephemeral**  
   `label_to_model` mappings and `aggregate_rankings` are returned via API only — never persisted to disk.

4. **Zero Agent Framework Dependency**  
   No LangChain, CrewAI, or AutoGen. Pure Python orchestration + direct async API calls.

5. **Full Transparency by Default**  
   All raw outputs inspectable via web UI. Parsed rankings shown next to raw text.

---

## Quick Start (5 minutes)

### 1. Clone & Setup
```bash
git clone https://github.com/YOUR_USERNAME/debateX.git
cd debateX
cp .env.example .env
```
Edit `.env` and add your API keys:
```env
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
```

### 2. Run the App
**Windows (One-Click):** Double-click `run.bat`
**macOS / Linux:** Run `./start.sh`
**Docker:** `docker compose up --build`

### 3. Start Debating
Open `http://localhost:5173` in your browser and ask a complex question!

---

## Documentation

For deep dives and configuration, see our `docs/` folder:

- 🔌 [API Reference](docs/api_reference.md)
- 🚀 [Deployment & Configuration](docs/deployment_and_config.md)
- 🛠️ [Development Guide](docs/development_guide.md)

---

## Contributing
We welcome contributions! Please check out our [Development Guide](docs/development_guide.md) to get your local environment set up, and feel free to open Pull Requests for new features, additional providers, or UI enhancements.

## License
Licensed under the [MIT License](LICENSE).