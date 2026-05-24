"""Disagreement detection engine for DebateX.

After the 5-round deliberation, this module analyses all model outputs to detect
divergence, surface consensus zones, and produce a structured DisagreementMap that
the Chairman prompt consumes to populate structured output.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ClaimScore:
    """One model's confidence score for a single claim."""
    model: str
    score: float          # 0.0 – 1.0  (1 = fully agrees / high confidence)
    stance: str           # "AGREE" | "DISAGREE" | "PARTIAL" | "UNKNOWN"
    reasoning: str = ""


@dataclass
class DisagreementZone:
    """A single point where models diverged."""
    claim: str
    model_positions: Dict[str, str]    # model_name -> what that model said
    divergence_reason: str             # synthesised reason why they diverged
    human_decision_needed: bool        # True when models flatly contradict each other
    confidence_scores: List[ClaimScore] = field(default_factory=list)


@dataclass
class DisagreementMap:
    """Top-level structured output emitted after the Chairman round."""
    consensus_points: List[str]                     # claims all models agreed on
    disagreement_zones: List[DisagreementZone]      # per-claim divergence records
    confidence_map: Dict[str, List[ClaimScore]]     # claim -> per-model scores
    overall_consensus_score: float                  # 0.0 – 1.0
    requires_human_review: bool                     # True if any zone needs human input


# ---------------------------------------------------------------------------
# Parsing helper: extract the structured JSON block from Chairman output
# ---------------------------------------------------------------------------

_JSON_RE = re.compile(
    r'```(?:json)?\s*(\{[\s\S]*?\})\s*```',
    re.MULTILINE | re.DOTALL
)


def _extract_json_block(text: str) -> Optional[dict]:
    """Pull the first fenced JSON block out of a markdown string."""
    match = _JSON_RE.search(text)
    if not match:
        # Try bare JSON (no fences)
        brace = text.find('{')
        if brace != -1:
            try:
                return json.loads(text[brace:])
            except Exception:
                pass
        return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Build DisagreementMap from Chairman-structured JSON
# ---------------------------------------------------------------------------

def parse_disagreement_map(chairman_output: str) -> Optional[DisagreementMap]:
    """
    Parse the Chairman's structured JSON output into a DisagreementMap.

    Returns None if no parseable JSON block is present.
    """
    raw = _extract_json_block(chairman_output)
    if raw is None:
        return None

    consensus_points = raw.get("consensus_points", [])
    overall_score = float(raw.get("overall_consensus_score", 0.5))
    requires_human = bool(raw.get("requires_human_review", False))

    zones: List[DisagreementZone] = []
    confidence_map: Dict[str, List[ClaimScore]] = {}

    for zone_raw in raw.get("disagreement_zones", []):
        claim = zone_raw.get("claim", "")
        model_positions = zone_raw.get("model_positions", {})
        divergence_reason = zone_raw.get("divergence_reason", "")
        human_needed = bool(zone_raw.get("human_decision_needed", False))

        scores: List[ClaimScore] = []
        for cs_raw in zone_raw.get("confidence_scores", []):
            scores.append(ClaimScore(
                model=cs_raw.get("model", ""),
                score=float(cs_raw.get("score", 0.5)),
                stance=cs_raw.get("stance", "UNKNOWN"),
                reasoning=cs_raw.get("reasoning", ""),
            ))

        zone = DisagreementZone(
            claim=claim,
            model_positions=model_positions,
            divergence_reason=divergence_reason,
            human_decision_needed=human_needed,
            confidence_scores=scores,
        )
        zones.append(zone)
        confidence_map[claim] = scores

    return DisagreementMap(
        consensus_points=consensus_points,
        disagreement_zones=zones,
        confidence_map=confidence_map,
        overall_consensus_score=overall_score,
        requires_human_review=requires_human,
    )


# ---------------------------------------------------------------------------
# Heuristic fallback: build a basic DisagreementMap from raw deliberation data
# ---------------------------------------------------------------------------

def _extract_key_claims(text: str, max_claims: int = 4) -> List[str]:
    """Very rough heuristic – extract bullet points or first N sentences."""
    # Try bullet/numbered list items first
    bullets = re.findall(r'^\s*[-*\d]+[.)]\s+(.+)', text, re.MULTILINE)
    if bullets:
        return [b.strip() for b in bullets[:max_claims]]
    # Fall back to sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences[:max_claims] if len(s.split()) > 4]


def _rough_similarity(a: str, b: str) -> float:
    """Jaccard token similarity – quick heuristic, not semantic."""
    tok_a = set(a.lower().split())
    tok_b = set(b.lower().split())
    if not tok_a or not tok_b:
        return 0.0
    return len(tok_a & tok_b) / len(tok_a | tok_b)


def build_disagreement_map_heuristic(
    stage1_results: List[Dict[str, Any]],
    stage3_results: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]],
) -> DisagreementMap:
    """
    Heuristic fallback: construct a DisagreementMap when the Chairman did not
    produce parseable structured JSON.

    Analyses Round-1 responses and Round-3 revised/defended answers to detect
    topical divergence at a coarse level.
    """
    if not stage1_results:
        return DisagreementMap(
            consensus_points=[],
            disagreement_zones=[],
            confidence_map={},
            overall_consensus_score=0.5,
            requires_human_review=False,
        )

    # Collect final answers (Round-3 revised/defended wins over Round-1)
    final_answers: Dict[str, str] = {r["model"]: r["response"] for r in stage1_results}
    for r in stage3_results:
        if r.get("response"):
            final_answers[r["model"]] = r["response"]

    models = list(final_answers.keys())

    # Build claim sets per model
    claims_per_model: Dict[str, List[str]] = {
        m: _extract_key_claims(final_answers[m]) for m in models
    }

    # Detect consensus: claims that appear (similar) across all models
    consensus_candidates: List[str] = []
    all_claims = [c for claims in claims_per_model.values() for c in claims]

    seen: set = set()
    for claim in all_claims:
        if claim in seen:
            continue
        seen.add(claim)
        # Check if this claim (loosely) appears in every model's output
        appeared_in = [
            m for m in models
            if any(_rough_similarity(claim, c) > 0.3 for c in claims_per_model[m])
        ]
        if len(appeared_in) == len(models) and len(models) > 1:
            consensus_candidates.append(claim)

    # Detect disagreement: claims mentioned by only a subset of models
    zones: List[DisagreementZone] = []
    confidence_map: Dict[str, List[ClaimScore]] = {}

    for claim in all_claims:
        if claim in seen and claim in consensus_candidates:
            continue
        appeared_in = [
            m for m in models
            if any(_rough_similarity(claim, c) > 0.3 for c in claims_per_model[m])
        ]
        if len(appeared_in) < len(models):
            model_positions: Dict[str, str] = {}
            scores: List[ClaimScore] = []
            for m in models:
                if any(_rough_similarity(claim, c) > 0.3 for c in claims_per_model[m]):
                    model_positions[m] = "Included this point"
                    scores.append(ClaimScore(model=m, score=0.8, stance="AGREE",
                                             reasoning="Model raised this point"))
                else:
                    model_positions[m] = "Did not address this point"
                    scores.append(ClaimScore(model=m, score=0.2, stance="DISAGREE",
                                             reasoning="Model omitted this point"))

            # Avoid duplicate zone claims
            if claim not in [z.claim for z in zones]:
                human_needed = len(appeared_in) <= len(models) // 2
                zone = DisagreementZone(
                    claim=claim,
                    model_positions=model_positions,
                    divergence_reason="Models differed on whether to include this point.",
                    human_decision_needed=human_needed,
                    confidence_scores=scores,
                )
                zones.append(zone)
                confidence_map[claim] = scores

            if len(zones) >= 5:
                break  # cap at 5 zones for readability

    # Overall consensus score: proportion of all claims that achieved consensus
    total = max(len(consensus_candidates) + len(zones), 1)
    overall_score = round(len(consensus_candidates) / total, 2)
    requires_human = any(z.human_decision_needed for z in zones)

    return DisagreementMap(
        consensus_points=consensus_candidates[:6],
        disagreement_zones=zones,
        confidence_map=confidence_map,
        overall_consensus_score=overall_score,
        requires_human_review=requires_human,
    )


# ---------------------------------------------------------------------------
# Chairman prompt fragment
# ---------------------------------------------------------------------------

CHAIRMAN_DISAGREEMENT_SCHEMA = """
In addition to your narrative synthesis, you MUST append a structured JSON block (fenced with ```json ... ```) that follows this schema EXACTLY:

```json
{
  "consensus_points": [
    "Short claim that ALL models agreed on",
    "Another shared point..."
  ],
  "disagreement_zones": [
    {
      "claim": "The specific claim or topic where models diverged",
      "model_positions": {
        "<model_name_1>": "What this model said about this claim",
        "<model_name_2>": "What this model said about this claim"
      },
      "divergence_reason": "Why you think the models diverged on this point",
      "human_decision_needed": true,
      "confidence_scores": [
        { "model": "<model_name_1>", "score": 0.9, "stance": "AGREE",    "reasoning": "Short reason" },
        { "model": "<model_name_2>", "score": 0.3, "stance": "DISAGREE", "reasoning": "Short reason" }
      ]
    }
  ],
  "overall_consensus_score": 0.75,
  "requires_human_review": false
}
```

Rules for the JSON block:
- `consensus_points`: 2–6 short sentences that every model endorsed.
- `disagreement_zones`: 1–5 zones where models materially diverged. Set `human_decision_needed` to true when models flatly contradict each other.
- `confidence_scores.score`: 0.0 (complete disagreement / low confidence) to 1.0 (full agreement / high confidence).
- `confidence_scores.stance`: one of "AGREE", "PARTIAL", "DISAGREE", "UNKNOWN".
- `overall_consensus_score`: fraction of claims where consensus was reached (0.0–1.0).
- Do NOT include any text inside the JSON fences other than valid JSON.
"""


def serialize_disagreement_map(dm: DisagreementMap) -> Dict[str, Any]:
    """Convert DisagreementMap to a plain dict suitable for JSON serialisation."""
    return asdict(dm)
