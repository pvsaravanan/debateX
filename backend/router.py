import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Tuple
from .config import debate_MODELS, moderator_MODEL
from .llm import query_model


@dataclass
class QueryRouting:
    """Dataclass holding the query routing configuration and cost metrics."""
    category: str  # technical/code, creative, factual/research, ethical/philosophical, math/logic
    optimal_council: List[str] = field(default_factory=list)
    disagreement_panel_mandatory: bool = False
    fact_checker_web_access: bool = False
    estimated_cost_usd: float = 0.0


# Bridge between router categories and roles.py persona query types
CATEGORY_TO_ROLE_TYPE = {
    "technical/code": "technical",
    "creative": "creative",
    "factual/research": "factual",
    "ethical/philosophical": "ethical",
    "math/logic": "math",
}


def serialize_routing(routing: "QueryRouting") -> Dict[str, Any]:
    """Convert QueryRouting to a JSON-serialisable dict for SSE/metadata."""
    return asdict(routing)


# Pricing Table in USD per 1 Million (1M) tokens
PRICING_TABLE = {
    # Groq Models
    "groq/llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "groq/llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "groq/openai/gpt-oss-20b": {"input": 0.15, "output": 0.60},
    
    # OpenRouter Free Models
    "nvidia/nemotron-3-ultra-550b-a55b:free": {"input": 0.0, "output": 0.0},
    "poolside/laguna-m.1:free": {"input": 0.0, "output": 0.0},
    "google/gemma-4-31b-it:free": {"input": 0.0, "output": 0.0},
    "poolside/laguna-xs-2.1:free": {"input": 0.0, "output": 0.0},
}


def classify_query_local(query: str) -> str:
    """
    Local fallback query classifier using keywords and regex mapping.
    Used if the LLM classification fails.
    """
    normalized_query = query.strip().lower()

    # Keyword mappings
    kw_tech = [
        r"\bcode\b", r"\bpython\b", r"\bjavascript\b", r"\bapi\b", r"\bendpoint\b",
        r"\bhtml\b", r"\bcss\b", r"\breact\b", r"\bprogram\b", r"\bscript\b",
        r"\bfunction\b", r"\bclass\b", r"\bdatabase\b", r"\bfastapi\b", r"\bc\+\+\b",
        r"\brust\b", r"\bimport\b", r"\bcompile\b", r"\bgit\b", r"\bnode\b",
        r"\bdocker\b", r"\bsql\b"
    ]
    kw_math = [
        r"\bmath\b", r"\bequation\b", r"\bprove\b", r"\bproof\b", r"\bcalculate\b",
        r"\bintegral\b", r"\balgebra\b", r"\bgeometry\b", r"\bmatrix\b", r"\btheorem\b",
        r"\blogic\b", r"\bsum\b", r"\bfraction\b", r"\bdivide\b", r"\bmultiply\b"
    ]
    kw_ethical = [
        r"\bmoral\b", r"\bethics\b", r"\bethical\b", r"\bphilosophical\b", r"\bphilosophy\b",
        r"\bright\b", r"\bwrong\b", r"\bshould\b", r"\bgood\b", r"\bbad\b",
        r"\butilitarian\b", r"\bdilemma\b", r"\bsocrates\b", r"\bjustice\b"
    ]
    kw_creative = [
        r"\bwrite\b", r"\bstory\b", r"\bpoem\b", r"\bcreative\b", r"\bnovel\b",
        r"\bsong\b", r"\blyrics\b", r"\bimagine\b", r"\bplot\b", r"\bcharacter\b",
        r"\bmetaphor\b", r"\bfiction\b", r"\bdraft\b"
    ]
    kw_factual = [
        r"\bfactual\b", r"\bresearch\b", r"\bverify\b", r"\bhistory\b", r"\bdate\b",
        r"\bwhen\b", r"\bwho\b", r"\bwhere\b", r"\bcapital\b", r"\bscience\b",
        r"\bstatistics\b", r"\bevidence\b", r"\bdata\b", r"\bearth\b", r"\bspace\b",
        r"\bnews\b", r"\bwhat is\b", r"\bdefinition\b"
    ]

    for pattern in kw_tech:
        if re.search(pattern, normalized_query):
            return "technical/code"
    for pattern in kw_math:
        if re.search(pattern, normalized_query):
            return "math/logic"
    for pattern in kw_ethical:
        if re.search(pattern, normalized_query):
            return "ethical/philosophical"
    for pattern in kw_creative:
        if re.search(pattern, normalized_query):
            return "creative"
    for pattern in kw_factual:
        if re.search(pattern, normalized_query):
            return "factual/research"

    return "factual/research"


def calculate_predicted_cost(
    selected_council: List[str],
    moderator_model: str
) -> float:
    """
    Calculates predicted USD cost for a full 5-round debate query.
    Uses standard token assumptions per round and role.
    """
    def get_model_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
        # OpenRouter free-tier models cost nothing regardless of table membership
        if model_name.endswith(":free"):
            return 0.0
        # Default pricing fallback if model is not in table
        rates = PRICING_TABLE.get(model_name, {"input": 0.10, "output": 0.15})
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        return input_cost + output_cost

    total_cost = 0.0

    # 1. Cost for each model in council (active in Rounds 1, 2, and 3)
    for m in selected_council:
        # Round 1 + Round 2 + Round 3 average consumption: ~5000 input, ~2500 output tokens
        total_cost += get_model_cost(m, 5000, 2500)

    # 2. Challenger Model cost (active in Round 4)
    if selected_council:
        # Assign worst or last model as challenger
        challenger_model = selected_council[-1]
        # Round 4 critique average consumption: ~3500 input, ~800 output tokens
        total_cost += get_model_cost(challenger_model, 3500, 800)

    # 3. Chairman Model cost (active in Round 5)
    if moderator_model:
        # Round 5 synthesis average consumption: ~6000 input, ~1500 output tokens
        total_cost += get_model_cost(moderator_model, 6000, 1500)

    return round(total_cost, 6)


async def route_query(
    query: str,
    available_models: List[str]
) -> QueryRouting:
    """
    Classifies the incoming user query using a fast free LLM (or falls back locally)
    and resolves the optimal council composition, configuration flags, and predicted query cost.

    Args:
        query: The user query string
        available_models: List of available model identifiers loaded in config

    Returns:
        QueryRouting configuration object.
    """
    if not available_models:
        available_models = debate_MODELS

    category = ""

    # Select a small/fast model for classification (prefer instant/small tiers,
    # then any free model, then the moderator as a last resort)
    classifier_model = next(
        (m for m in available_models
         if "instant" in m or "-xs-" in m or "8b" in m or "gemma" in m),
        None
    )
    if not classifier_model:
        classifier_model = next((m for m in available_models if "free" in m), None)
    if not classifier_model:
        classifier_model = moderator_MODEL

    # Prompt requesting category ONLY
    prompt = (
        "Classify the following user query into exactly one of these categories:\n"
        "1. technical/code\n"
        "2. creative\n"
        "3. factual/research\n"
        "4. ethical/philosophical\n"
        "5. math/logic\n\n"
        "Your response MUST contain ONLY the category name matching exactly one of the five categories "
        "listed above. Do not add any punctuation, quotes, introduction, or formatting.\n\n"
        f"User Query: {query}\n"
        "Category:"
    )

    messages = [{"role": "user", "content": prompt}]

    # 1. Attempt classification via fast LLM
    try:
        response = await query_model(classifier_model, messages, timeout=10.0)
        content = response.get("content", "").strip().lower() if response else ""
        
        # Strip quotes and periods
        content = content.replace('"', '').replace("'", '').replace('.', '')
        
        valid_categories = ["technical/code", "creative", "factual/research", "ethical/philosophical", "math/logic"]
        for cat in valid_categories:
            if cat in content:
                category = cat
                break
    except Exception as e:
        print(f"Fast LLM classification failed with exception: {e}. Falling back to local classifier...")

    # 2. Fall back to local regex classifier if LLM failed
    if not category:
        category = classify_query_local(query)

    # 3. Resolve configurations based on classification category.
    # Each category lists model-name substrings in PREFERENCE order — the council
    # is assembled by scanning preferences first so the strongest fits lead.
    category_config = {
        "technical/code": {
            "disagreement_panel_mandatory": True,
            "fact_checker_web_access": True,
            # Coding & reasoning models (poolside/laguna are code-specialised)
            "preferences": ["llama-3.3", "nemotron", "gpt-oss", "laguna", "qwen", "deepseek", "llama-3.1"],
        },
        "creative": {
            "disagreement_panel_mandatory": False,
            "fact_checker_web_access": False,
            # Context-rich & diverse models
            "preferences": ["gemma", "gpt-oss", "nemotron", "qwen", "glm-4.5", "llama-3.3"],
        },
        "factual/research": {
            "disagreement_panel_mandatory": True,
            "fact_checker_web_access": True,
            # Comprehensive & precision models
            "preferences": ["llama-3.3", "nemotron", "gpt-oss", "gemma", "qwen", "deepseek"],
        },
        "ethical/philosophical": {
            "disagreement_panel_mandatory": False,
            "fact_checker_web_access": False,
            # Highly articulate & reasoning models
            "preferences": ["nemotron", "gpt-oss", "llama-3.3", "gemma", "glm-4.5"],
        },
        "math/logic": {
            "disagreement_panel_mandatory": True,
            "fact_checker_web_access": False,
            # Reasoning & proof-capable models
            "preferences": ["llama-3.3", "nemotron", "gpt-oss", "deepseek", "qwen", "llama-3.1"],
        },
    }

    config = category_config.get(category, category_config["factual/research"])
    disagreement_panel_mandatory = config["disagreement_panel_mandatory"]
    fact_checker_web_access = config["fact_checker_web_access"]

    optimal_council = []
    for pref in config["preferences"]:
        for m in available_models:
            if pref in m and m not in optimal_council:
                optimal_council.append(m)

    # Graceful fallback: if no optimal models match, use the first 3 available models
    if not optimal_council:
        optimal_council = available_models[:3]

    # Cap large councils at 4 models to save cost and latency
    if len(optimal_council) > 4:
        optimal_council = optimal_council[:4]

    # 4. Calculate overall cost estimate
    estimated_cost_usd = calculate_predicted_cost(optimal_council, moderator_MODEL)

    return QueryRouting(
        category=category,
        optimal_council=optimal_council,
        disagreement_panel_mandatory=disagreement_panel_mandatory,
        fact_checker_web_access=fact_checker_web_access,
        estimated_cost_usd=estimated_cost_usd
    )
