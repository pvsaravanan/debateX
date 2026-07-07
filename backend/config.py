"""Configuration for the DebateX."""

import os
from dotenv import load_dotenv

load_dotenv()

# API keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# API endpoints
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Dynamic Model Configuration based on available keys
debate_MODELS = []
moderator_MODEL = ""

if OPENROUTER_API_KEY:
    debate_MODELS.extend([
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "poolside/laguna-m.1:free",
        "google/gemma-4-31b-it:free",
        "poolside/laguna-xs-2.1:free"
    ])
    moderator_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

if GROQ_API_KEY:
    debate_MODELS.extend([
        "groq/llama-3.1-8b-instant",
        "groq/openai/gpt-oss-20b",
        "groq/llama-3.3-70b-versatile",
    ])
    # Prioritize Groq's high-performance model as the moderator
    moderator_MODEL = "groq/llama-3.3-70b-versatile"

# Metacognition pre-flight probing (3 temperature samples per model) multiplies
# API call volume; disabled by default to stay inside free-tier rate limits.
# Set ENABLE_METACOGNITION=true in .env to re-enable.
ENABLE_METACOGNITION = os.getenv("ENABLE_METACOGNITION", "false").strip().lower() == "true"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
