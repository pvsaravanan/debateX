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
        "deepseek/deepseek-v4-flash:free",
        "z-ai/glm-4.5-air:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
    ])
    moderator_MODEL = "deepseek/deepseek-v4-flash:free"

if GROQ_API_KEY:
    debate_MODELS.extend([
        "groq/llama3-8b-8192",
        "groq/llama3-70b-8192",
        "groq/mixtral-8x7b-32768",
        "groq/gemma-7b-it",
    ])
    # If moderator isn't set yet, or we want Groq to be the fallback
    if not moderator_MODEL:
        moderator_MODEL = "groq/llama3-70b-8192"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
