"""Metacognition probe engine for DebateX.

Before the main deliberation, each model is sampled three times at
temperatures [0.3, 0.7, 1.0] on the same query.  The three responses are
embedded with TF-IDF vectors and their pairwise cosine similarities are
measured.  A per-model confidence score is derived from average similarity:

    avg_sim ≥ 0.70  → HIGH    → score 0.85 – 1.00
    avg_sim 0.40–0.69 → MEDIUM → score 0.50 – 0.75
    avg_sim < 0.40  → LOW     → score 0.10 – 0.40

The final MetacognitionResult is:
  • Returned to the caller for inclusion in SSE metadata
  • Summarised as a weight table injected into the Chairman prompt
"""

from __future__ import annotations

import asyncio
import math
import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from .llm import query_model
from .config import debate_MODELS

# ── Temperature schedule ───────────────────────────────────────────────────
PROBE_TEMPERATURES: List[float] = [0.3, 0.7, 1.0]


# ── Data model ─────────────────────────────────────────────────────────────

@dataclass
class TemperatureProbe:
    temperature: float
    response: str


@dataclass
class ModelConfidenceScore:
    model: str
    confidence: float          # 0.0 – 1.0
    tier: str                  # "HIGH" | "MEDIUM" | "LOW"
    sim_01: float              # cosine(temp0.3, temp0.7)
    sim_02: float              # cosine(temp0.3, temp1.0)
    sim_12: float              # cosine(temp0.7, temp1.0)
    avg_similarity: float
    probes: List[TemperatureProbe] = field(default_factory=list)


@dataclass
class MetacognitionResult:
    scores: Dict[str, ModelConfidenceScore]
    summary: str  # human-readable for Chairman prompt injection


# ── TF-IDF cosine similarity (zero external deps beyond stdlib) ────────────

def _tokenise(text: str) -> List[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _tfidf_vector(text: str, vocab: List[str]) -> List[float]:
    """
    Return a simple TF vector over the shared vocabulary.
    (No IDF weighting needed for 2-document comparison.)
    """
    tokens = _tokenise(text)
    counts = Counter(tokens)
    total = max(len(tokens), 1)
    return [counts.get(w, 0) / total for w in vocab]


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


def _pairwise_cosine(texts: List[str]) -> Tuple[float, float, float]:
    """
    Compute cosine similarities for (0,1), (0,2), (1,2) from a list of 3 texts.
    Returns (sim_01, sim_02, sim_12).
    """
    # Build shared vocabulary across all three texts
    vocab = sorted(set(
        w for t in texts for w in _tokenise(t)
    ))
    if not vocab:
        return 0.0, 0.0, 0.0

    vecs = [_tfidf_vector(t, vocab) for t in texts]
    sim_01 = _cosine(vecs[0], vecs[1])
    sim_02 = _cosine(vecs[0], vecs[2])
    sim_12 = _cosine(vecs[1], vecs[2])
    return sim_01, sim_02, sim_12


# ── Confidence derivation ──────────────────────────────────────────────────

def _derive_confidence(avg_sim: float) -> Tuple[float, str]:
    """
    Map average pairwise cosine similarity → (confidence, tier).

    Bands:
        avg_sim ≥ 0.70  → HIGH   → [0.85, 1.00]
        avg_sim 0.40-0.69 → MEDIUM → [0.50, 0.75]
        avg_sim < 0.40  → LOW    → [0.10, 0.40]
    """
    if avg_sim >= 0.70:
        # linear interp: 0.70 → 0.85, 1.00 → 1.00
        t = (avg_sim - 0.70) / 0.30
        score = 0.85 + t * 0.15
        tier = "HIGH"
    elif avg_sim >= 0.40:
        # linear interp: 0.40 → 0.50, 0.70 → 0.75
        t = (avg_sim - 0.40) / 0.30
        score = 0.50 + t * 0.25
        tier = "MEDIUM"
    else:
        # linear interp: 0.00 → 0.10, 0.40 → 0.40
        t = avg_sim / 0.40
        score = 0.10 + t * 0.30
        tier = "LOW"

    return round(min(max(score, 0.0), 1.0), 3), tier


# ── Per-model probe ────────────────────────────────────────────────────────

async def _probe_model_at_temperature(
    model: str,
    messages: list,
    temperature: float,
    timeout: float = 60.0,
) -> Optional[str]:
    """Call one model at one temperature; return text content or None."""
    try:
        resp = await query_model(model, messages, timeout=timeout, temperature=temperature)
        return (resp or {}).get("content") or None
    except Exception as exc:
        print(f"[metacognition] {model} @ temp={temperature} failed: {exc}")
        return None


async def probe_model(
    model: str,
    user_query: str,
) -> Optional[ModelConfidenceScore]:
    """
    Sample *model* three times at temperatures 0.3, 0.7, 1.0 in parallel.
    Returns a ModelConfidenceScore or None if too many probes failed.
    """
    messages = [{"role": "user", "content": user_query}]

    # Fire all three probes in parallel
    tasks = [
        _probe_model_at_temperature(model, messages, t)
        for t in PROBE_TEMPERATURES
    ]
    raw_responses: List[Optional[str]] = await asyncio.gather(*tasks, return_exceptions=False)

    # Build TemperatureProbe list, using fallback text for failures
    probes: List[TemperatureProbe] = []
    valid_texts: List[str] = []
    for temp, resp in zip(PROBE_TEMPERATURES, raw_responses):
        text = resp or ""
        probes.append(TemperatureProbe(temperature=temp, response=text))
        if text:
            valid_texts.append(text)

    # Need at least 2 valid responses to compute similarity
    if len(valid_texts) < 2:
        return None

    # Pad to exactly 3 texts if one probe failed (duplicate first valid)
    texts_for_sim = [p.response if p.response else valid_texts[0] for p in probes]

    sim_01, sim_02, sim_12 = _pairwise_cosine(texts_for_sim)
    avg_sim = round((sim_01 + sim_02 + sim_12) / 3.0, 4)
    confidence, tier = _derive_confidence(avg_sim)

    return ModelConfidenceScore(
        model=model,
        confidence=confidence,
        tier=tier,
        sim_01=sim_01,
        sim_02=sim_02,
        sim_12=sim_12,
        avg_similarity=avg_sim,
        probes=probes,
    )


# ── Main entry point ───────────────────────────────────────────────────────

async def run_metacognition(
    user_query: str,
    models: Optional[List[str]] = None,
) -> MetacognitionResult:
    """
    Run metacognition probes on *all* (or the supplied) models in parallel.

    Returns a MetacognitionResult with per-model confidence scores and a
    human-readable summary string suitable for injection into the Chairman prompt.
    """
    if models is None:
        models = debate_MODELS

    # All probes for all models fire simultaneously
    tasks = [probe_model(m, user_query) for m in models]
    results: List[Optional[ModelConfidenceScore]] = await asyncio.gather(
        *tasks, return_exceptions=False
    )

    scores: Dict[str, ModelConfidenceScore] = {}
    for mcs in results:
        if mcs is not None:
            scores[mcs.model] = mcs

    summary = _build_summary(scores)
    return MetacognitionResult(scores=scores, summary=summary)


def _build_summary(scores: Dict[str, ModelConfidenceScore]) -> str:
    """Build a table string for the Chairman prompt weight injection."""
    if not scores:
        return "No metacognition data available."

    lines = ["Model confidence weights (derived from self-consistency probing):"]
    # Sort by confidence descending
    for mcs in sorted(scores.values(), key=lambda s: s.confidence, reverse=True):
        short = mcs.model.split("/")[-1] or mcs.model
        lines.append(
            f"  • {short:<35} [{mcs.tier:<6}  conf={mcs.confidence:.2f}  "
            f"avg_sim={mcs.avg_similarity:.2f}]"
        )

    lines.append(
        "\nInstruction: Weight each model's contribution proportionally to its "
        "confidence score. HIGH-confidence models showed strong self-consistency "
        "across temperatures — treat their conclusions as more reliable. "
        "LOW-confidence models exhibited high variance — treat with scepticism."
    )
    return "\n".join(lines)


# ── Serialisation ─────────────────────────────────────────────────────────

def serialize_metacognition_result(result: MetacognitionResult) -> dict:
    """Convert MetacognitionResult to a JSON-serialisable dict."""
    return {
        "scores": {
            model: asdict(mcs)
            for model, mcs in result.scores.items()
        },
        "summary": result.summary,
    }
