"""DebateX 5-round deliberation orchestration.

Pipeline (single source of truth: run_debate_stream):
    Routing  → classify query, pick optimal council, allocate personas, estimate cost
    Round 1  → council answers in parallel (persona system prompts)
    Round 2  → anonymized peer review & ranking
    Round 3  → revise or defend under peer pressure
    Round 4  → challenger critique of the leading answer (Devil's Advocate preferred)
    Round 5  → chairman synthesis + structured disagreement map
"""

import asyncio
import json
import re
import zlib
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from .llm import query_models_parallel, query_model
from .config import debate_MODELS, moderator_MODEL, ENABLE_METACOGNITION
from .router import route_query, serialize_routing, CATEGORY_TO_ROLE_TYPE
from .roles import allocate_personas, get_role_map, RoleAssignment
from .disagreement import (
    CHAIRMAN_DISAGREEMENT_SCHEMA,
    DisagreementMap,
    build_disagreement_map_heuristic,
    parse_disagreement_map,
    serialize_disagreement_map,
)
from .metacognition import (
    MetacognitionResult,
    run_metacognition,
    serialize_metacognition_result,
)


# ---------------------------------------------------------------------------
# Round 1: initial answers
# ---------------------------------------------------------------------------

async def stage1_collect_responses(
    user_query: str,
    council: Optional[List[str]] = None,
    system_prompts: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Round 1: Collect individual responses from the council models in parallel.
    Each model may carry a persona system prompt (Reasoner, Devil's Advocate, ...).

    Returns:
        List of dicts with 'model' and 'response' keys (failed models omitted).
    """
    models = council or debate_MODELS
    messages = [{"role": "user", "content": user_query}]

    responses = await query_models_parallel(models, messages, system_prompts=system_prompts)

    stage1_results = []
    for model, response in responses.items():
        if response is not None and (response.get('content') or '').strip():
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


# ---------------------------------------------------------------------------
# Round 2: anonymized peer review & ranking
# ---------------------------------------------------------------------------

async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council: Optional[List[str]] = None,
    system_prompts: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Round 2: Each council model ranks the anonymized responses.

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    models = council or debate_MODELS

    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]

    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

CRITICAL LANGUAGE REQUIREMENT: You MUST write all your comments and evaluations strictly in English, regardless of the language of the user's original question. The "FINAL RANKING:" header and label format (e.g., "Response A") must also remain in English.

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    responses = await query_models_parallel(models, messages, system_prompts=system_prompts)

    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Returns:
        List of response labels in ranked order (deduplicated, first occurrence wins).
    """
    def dedupe(labels: List[str]) -> List[str]:
        seen = set()
        out = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                out.append(label)
        return out

    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Numbered list format (e.g., "1. Response A")
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return dedupe([re.search(r'Response [A-Z]', m).group() for m in numbered_matches])

            # Fallback: any "Response X" patterns in order
            return dedupe(re.findall(r'Response [A-Z]', ranking_section))

    # Fallback: any "Response X" patterns anywhere in the text
    return dedupe(re.findall(r'Response [A-Z]', ranking_text))


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all peer evaluations.

    Returns:
        List of dicts with model name and average rank, sorted best to worst.
    """
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.get('parsed_ranking') or parse_ranking_from_text(ranking['ranking'])

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    aggregate.sort(key=lambda x: x['average_rank'])
    return aggregate


# ---------------------------------------------------------------------------
# Round 3: revise or defend
# ---------------------------------------------------------------------------

async def stage3_revise_or_defend(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    aggregate_rankings: List[Dict[str, Any]],
    system_prompts: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Round 3: Models see anonymized rankings and evaluations, and revise or defend
    their responses. Each model keeps its persona system prompt.
    """
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    reviews_formatted = ""
    for idx, r in enumerate(stage2_results):
        reviews_formatted += f"### Reviewer {idx+1} Evaluation:\n{r['ranking']}\n\n"

    model_to_label = {v: k for k, v in label_to_model.items()}
    standings_formatted = "\n".join([
        f"- {model_to_label.get(item['model'], item['model'])}: Average Rank {item['average_rank']} (over {item['rankings_count']} votes)"
        for item in aggregate_rankings
    ])

    prompts = {}
    for result in stage1_results:
        model = result['model']
        model_label = model_to_label.get(model)
        if not model_label:
            continue

        prompt = f"""You are a council member of an LLM deliberation system. In the initial round, you provided a response to the following question.

Original Question: {user_query}

Here are the anonymized initial responses from all council members:
{responses_text}

Here is the feedback and evaluations from your peers (including evaluations of your response and others):
{reviews_formatted}

Here are the aggregate rankings calculated from peer evaluations (lower average rank is better):
{standings_formatted}

Your initial response is labeled as: {model_label}

Based on this peer feedback, you now have the opportunity to either REVISE or DEFEND your response.
- Choose REVISE if you agree with valid criticisms and want to improve your answer.
- Choose DEFEND if you believe your original answer is correct and you want to explain why the critiques are invalid or why your reasoning stands.

CRITICAL INSTRUCTIONS:
1. You MUST start your response with a decision header on the very first line:
   - Either "DECISION: REVISE"
   - Or "DECISION: DEFEND"
2. Next, write your explanation/defense (if defending) or your newly revised, complete answer (if revising).
   - If you chose REVISE, provide your complete, updated, and improved final answer.
   - If you chose DEFEND, explain your defense clearly.
3. You MUST write all your comments and response strictly in English.

Your decision and response:"""

        model_messages = [{"role": "user", "content": prompt}]
        persona = (system_prompts or {}).get(model)
        if persona:
            model_messages = [{"role": "system", "content": persona}] + model_messages
        prompts[model] = model_messages

    models_to_query = list(prompts.keys())
    responses = {}
    if models_to_query:
        tasks = [query_model(model, prompts[model]) for model in models_to_query]
        gathers = await asyncio.gather(*tasks, return_exceptions=True)
        for model, resp in zip(models_to_query, gathers):
            if isinstance(resp, Exception):
                print(f"Model {model} failed in Round 3 with exception: {resp}")
                responses[model] = None
            else:
                responses[model] = resp

    stage3_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = (response.get('content') or '').strip()
            if not full_text:
                continue
            decision = "REVISE"
            cleaned_content = full_text
            if "DECISION: DEFEND" in full_text:
                decision = "DEFEND"
            if "DECISION:" in full_text:
                lines = full_text.split('\n')
                cleaned_content = "\n".join(
                    line for line in lines if "DECISION:" not in line
                ).strip()

            stage3_results.append({
                "model": model,
                "decision": decision,
                "response": cleaned_content,
                "raw_response": full_text
            })
    return stage3_results


# ---------------------------------------------------------------------------
# Round 4: challenger critique
# ---------------------------------------------------------------------------

async def stage4_challenger_critique(
    user_query: str,
    stage3_results: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]],
    preferred_challenger: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Round 4: One model is assigned as Challenger to attack the leading answer.

    Challenger selection: the council's Devil's Advocate when available (and not
    itself the leader), otherwise the worst-ranked model.
    """
    if not stage3_results:
        return {
            "model": "Challenger Model",
            "response": "No models available to challenge."
        }

    # Leading model: best in aggregate rankings, falling back to first Round-3 result
    if aggregate_rankings:
        leading_model_name = aggregate_rankings[0]['model']
    else:
        leading_model_name = stage3_results[0]['model']
    leading_result = next((r for r in stage3_results if r['model'] == leading_model_name), stage3_results[0])
    leading_model_name = leading_result['model']
    leading_response = leading_result['response']

    # Challenger: Devil's Advocate persona preferred, else worst-ranked model
    stage3_models = [r['model'] for r in stage3_results]
    challenger_model_name = None
    if preferred_challenger and preferred_challenger in stage3_models and preferred_challenger != leading_model_name:
        challenger_model_name = preferred_challenger
    else:
        ranked_worst_first = [item['model'] for item in reversed(aggregate_rankings)]
        for candidate in ranked_worst_first:
            if candidate in stage3_models and (candidate != leading_model_name or len(stage3_models) == 1):
                challenger_model_name = candidate
                break
    if challenger_model_name is None:
        challenger_model_name = stage3_models[-1]

    challenger_prompt = f"""You are the assigned Challenger in an LLM Deliberation Council.

The council has been debating the following question:
Question: {user_query}

After multiple rounds of discussion and revision, the leading answer generated by the council's top-performing model is:

---
LEADING ANSWER:
{leading_response}
---

Your ONLY job is to challenge this leading answer. Be critical, aggressive, and thorough. Find its weakest point, logical flaws, incorrect assumptions, overlooked details, or potential edge cases that it fails to address.

Do NOT provide a general answer to the original question. Focus 100% on pointing out the flaws and weaknesses in the leading answer.

CRITICAL: You MUST write your critique strictly in English.

Your critique:"""

    messages = [{"role": "user", "content": challenger_prompt}]

    try:
        response = await query_model(challenger_model_name, messages)
        content = (response.get('content') or '').strip() if response else ""
    except Exception as e:
        print(f"Challenger model {challenger_model_name} failed: {e}")
        content = ""

    if not content:
        content = f"Error: Challenger {challenger_model_name} failed to generate critique."

    return {
        "model": challenger_model_name,
        "response": content,
        "target_model": leading_model_name,
        "target_response": leading_response
    }


# ---------------------------------------------------------------------------
# Round 5: chairman synthesis
# ---------------------------------------------------------------------------

async def stage5_chairman_synthesis(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    stage3_results: List[Dict[str, Any]],
    challenger_result: Dict[str, Any],
    label_to_model: Dict[str, str],
    aggregate_rankings: List[Dict[str, Any]],
    metacognition_summary: Optional[str] = None,
    chairman_model: Optional[str] = None,
    chairman_system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Round 5: Chairman synthesizes the final response using the full deliberation
    history, and emits a structured DisagreementMap (consensus zones, disagreement
    zones, confidence scores) for the DisagreementPanel UI component.
    """
    chairman = chairman_model or moderator_MODEL

    deliberation_history = [
        {
            "round": 1,
            "name": "Initial Answers",
            "data": [
                {"model": r['model'], "response": r['response']}
                for r in stage1_results
            ]
        },
        {
            "round": 2,
            "name": "Peer Review & Rankings",
            "data": [
                {"model": r['model'], "ranking": r['ranking'], "parsed_ranking": r['parsed_ranking']}
                for r in stage2_results
            ],
            "aggregate_rankings": aggregate_rankings,
            "label_to_model": label_to_model
        },
        {
            "round": 3,
            "name": "Revise or Defend",
            "data": [
                {"model": r['model'], "decision": r.get('decision', 'REVISE'), "response": r['response']}
                for r in stage3_results
            ]
        },
        {
            "round": 4,
            "name": "Challenger Critique",
            "data": {
                "challenger_model": challenger_result.get('model'),
                "critique": challenger_result.get('response'),
                "target_model": challenger_result.get('target_model'),
                "target_answer": challenger_result.get('target_response')
            }
        }
    ]

    history_json = json.dumps(deliberation_history, indent=2)

    stage1_summary = "\n\n".join([
        f"- Model: {r['model']}\n  Response: {r['response']}"
        for r in stage1_results
    ])

    stage2_summary = "\n\n".join([
        f"- Model: {r['model']}\n  Peer Ranking Content: {r['ranking']}"
        for r in stage2_results
    ])

    stage3_summary = "\n\n".join([
        f"- Model: {r['model']} ({r.get('decision', 'REVISE')}):\n  Answer: {r['response']}"
        for r in stage3_results
    ])

    if metacognition_summary:
        metacognition_block = (
            "PRE-DELIBERATION METACOGNITION SCORES (self-consistency across temperatures):\n"
            + metacognition_summary
        )
    else:
        metacognition_block = ""

    chairman_prompt = f"""You are the Chairman/Moderator of a 5-round LLM deliberation council.

The council has debated the following question:
Question: {user_query}

Below is the complete structured `deliberation_history` array containing the transcript and outputs of all 4 preceding rounds:

```json
{history_json}
```

Here is a summary of the rounds for your review:

ROUND 1 - Initial Answers:
{stage1_summary}

ROUND 2 - Peer Rankings & Evaluations:
{stage2_summary}

ROUND 3 - Revise or Defend Responses:
{stage3_summary}

ROUND 4 - Challenger Critique:
- Challenger Model: {challenger_result.get('model')}
- Target/Leading Model: {challenger_result.get('target_model')}
- Challenger's Critique: {challenger_result.get('response')}

Your task as Chairman is to synthesize the entire history of this deliberation. You must:
1. Analyze the initial answers and subsequent revisions/defenses.
2. Weigh the peer rankings and evaluations carefully.
3. Address the Challenger's critique: either incorporate its valid concerns to strengthen the final answer, or explain why the critique is addressed or invalid.
4. Synthesize all insights into a single, comprehensive, highly authoritative, and definitive master answer to the user's original question.
5. Identify points of CONSENSUS (all models agreed) and points of DISAGREEMENT (models diverged), then populate the structured JSON block described below.

{metacognition_block}

CRITICAL: You MUST write your final synthesis response strictly in English.

{CHAIRMAN_DISAGREEMENT_SCHEMA}

Provide your definitive final synthesized response followed by the JSON block:"""

    messages = [{"role": "user", "content": chairman_prompt}]
    if chairman_system_prompt:
        messages = [{"role": "system", "content": chairman_system_prompt}] + messages

    content = ""
    synthesizer = chairman
    try:
        response = await query_model(chairman, messages)
        content = (response.get('content') or '').strip() if response else ""
    except Exception as e:
        print(f"Chairman model {chairman} failed: {e}")

    if not content:
        # Fallback chain: any council/config model, then the leading Round-3 answer
        print(f"Chairman model {chairman} failed or returned empty. Using fallback synthesis...")
        for model in debate_MODELS:
            if model == chairman:
                continue
            try:
                fallback_response = await query_model(model, messages)
                content = (fallback_response.get('content') or '').strip() if fallback_response else ""
                if content:
                    synthesizer = model
                    break
            except Exception as fe:
                print(f"Fallback model {model} failed: {fe}")
                continue

    if not content:
        leading_response = challenger_result.get('target_response', 'Error: Unable to synthesize final answer.')
        return {
            "model": "Fallback Synthesis (Leading Answer)",
            "response": leading_response,
            "disagreement_map": serialize_disagreement_map(
                build_disagreement_map_heuristic(stage1_results, stage3_results, aggregate_rankings)
            ),
        }

    # --- Parse / build the DisagreementMap ---
    dm: Optional[DisagreementMap] = parse_disagreement_map(content)
    if dm is None:
        # LLM did not emit the JSON block → fall back to heuristic analysis
        dm = build_disagreement_map_heuristic(stage1_results, stage3_results, aggregate_rankings)

    # Strip the JSON fence from the narrative response so the UI gets clean text
    clean_content = re.sub(r'```(?:json)?\s*\{[\s\S]*?\}\s*```', '', content).strip()

    return {
        "model": synthesizer,
        "response": clean_content,
        "disagreement_map": serialize_disagreement_map(dm),
    }


# ---------------------------------------------------------------------------
# Conversation title generation
# ---------------------------------------------------------------------------

async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.
    """
    title_prompt = (
        "Generate a very short title (3-5 words maximum) that summarizes the following question.\n"
        "The title should be concise and descriptive. Do not use quotes or punctuation.\n"
        "IMPORTANT: You MUST generate the title in the same language as the question (e.g., if Tamil, write in Tamil; if Spanish, write in Spanish; if French, write in French, etc.).\n\n"
        f"Question: {user_query}\n\n"
        "Title:"
    )

    messages = [{"role": "user", "content": title_prompt}]

    response = None
    if moderator_MODEL:
        try:
            response = await query_model(moderator_MODEL, messages, timeout=15.0)
        except Exception as e:
            print(f"Failed to query title with moderator model: {e}")

    if response is None:
        for model in debate_MODELS:
            try:
                response = await query_model(model, messages, timeout=10.0)
                if response is not None:
                    break
            except Exception:
                continue

    title = ""
    if response is not None:
        title = (response.get('content') or '').strip()

    title = title.strip('"\' \n\r\t')

    if not title or title.lower() == "new conversation":
        words = [w for w in user_query.strip().split() if w]
        if words:
            title = " ".join(words[:4])
            if len(words) > 4:
                title += "..."
        else:
            title = "New Conversation"

    if len(title) > 50:
        title = title[:47] + "..."

    return title


# ---------------------------------------------------------------------------
# Unified orchestration: single async event stream for both endpoints
# ---------------------------------------------------------------------------

def _query_rotation_index(user_query: str) -> int:
    """Stable per-query index so persona rotation is deterministic."""
    return zlib.crc32(user_query.encode("utf-8"))


async def run_debate_stream(user_query: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Run the full deliberation, yielding an event dict per phase transition.

    Event types:
        routing_start / routing_complete
        metacognition_start / metacognition_complete   (only when enabled)
        round1_start / round1_complete
        round2_start / round2_complete   (metadata: label_to_model, aggregate_rankings)
        round3_start / round3_complete
        round4_start / round4_complete
        round5_start / round5_complete   (disagreement_map)
        complete   (carries the full assembled `result` for persistence)
        error

    Both the SSE endpoint and run_full_debate() consume this generator, so the
    round logic exists exactly once.
    """
    if not debate_MODELS:
        yield {
            "type": "error",
            "message": "No models configured. Set OPENROUTER_API_KEY and/or GROQ_API_KEY in .env."
        }
        return

    # ── Routing: classification, council selection, personas, cost ──────────
    yield {"type": "routing_start"}

    try:
        routing = await route_query(user_query, debate_MODELS)
    except Exception as e:
        print(f"Routing failed, using full council: {e}")
        from .router import QueryRouting, calculate_predicted_cost
        routing = QueryRouting(
            category="factual/research",
            optimal_council=debate_MODELS[:4],
            disagreement_panel_mandatory=True,
            fact_checker_web_access=False,
            estimated_cost_usd=calculate_predicted_cost(debate_MODELS[:4], moderator_MODEL),
        )

    council = routing.optimal_council or debate_MODELS[:4]
    chairman_model = moderator_MODEL or council[0]
    query_type = CATEGORY_TO_ROLE_TYPE.get(routing.category, "factual")

    personas: RoleAssignment = allocate_personas(
        council, chairman_model, query_type,
        query_index=_query_rotation_index(user_query)
    )
    role_map = get_role_map(personas)

    routing_data = {
        **serialize_routing(routing),
        "query_type": query_type,
        "chairman": chairman_model,
        "role_map": role_map,
    }
    yield {"type": "routing_complete", "data": routing_data}

    # ── Optional metacognition pre-flight (concurrent with Round 1) ─────────
    meta_task = None
    if ENABLE_METACOGNITION:
        yield {"type": "metacognition_start"}
        meta_task = asyncio.create_task(run_metacognition(user_query, council))

    # ── Round 1: initial answers ─────────────────────────────────────────────
    yield {"type": "round1_start"}
    stage1_results = await stage1_collect_responses(
        user_query, council, personas.system_prompts
    )

    if not stage1_results:
        if meta_task:
            meta_task.cancel()
        yield {
            "type": "error",
            "message": "All council models failed to respond. Please check API keys / rate limits and try again."
        }
        return

    yield {"type": "round1_complete", "data": stage1_results}

    # ── Round 2: anonymized peer review ──────────────────────────────────────
    yield {"type": "round2_start"}
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query, stage1_results, council, personas.system_prompts
    )
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
    yield {
        "type": "round2_complete",
        "data": stage2_results,
        "metadata": {
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings,
        }
    }

    # Resolve metacognition now (it has had rounds 1-2 of wall time to finish)
    metacognition_result: Optional[MetacognitionResult] = None
    metacognition_serialized = None
    if meta_task:
        try:
            metacognition_result = await meta_task
            metacognition_serialized = serialize_metacognition_result(metacognition_result)
            yield {"type": "metacognition_complete", "data": metacognition_serialized}
        except Exception as e:
            print(f"Metacognition failed: {e}")

    # ── Round 3: revise or defend ─────────────────────────────────────────────
    yield {"type": "round3_start"}
    stage3_results = await stage3_revise_or_defend(
        user_query, stage1_results, stage2_results,
        label_to_model, aggregate_rankings, personas.system_prompts
    )
    if not stage3_results:
        # Degrade gracefully: reuse Round-1 answers as implicit defenses
        stage3_results = [
            {"model": r["model"], "decision": "DEFEND",
             "response": r["response"], "raw_response": r["response"]}
            for r in stage1_results
        ]
    yield {"type": "round3_complete", "data": stage3_results}

    # ── Round 4: challenger critique ─────────────────────────────────────────
    yield {"type": "round4_start"}
    stage4_result = await stage4_challenger_critique(
        user_query, stage3_results, aggregate_rankings,
        preferred_challenger=personas.devils_advocate or None,
    )
    yield {"type": "round4_complete", "data": stage4_result}

    # ── Round 5: chairman synthesis ──────────────────────────────────────────
    yield {"type": "round5_start"}
    stage5_result = await stage5_chairman_synthesis(
        user_query, stage1_results, stage2_results, stage3_results,
        stage4_result, label_to_model, aggregate_rankings,
        metacognition_summary=metacognition_result.summary if metacognition_result else None,
        chairman_model=chairman_model,
        chairman_system_prompt=personas.chairman_prompt or None,
    )
    disagreement_map = stage5_result.get("disagreement_map")
    yield {
        "type": "round5_complete",
        "data": stage5_result,
        "disagreement_map": disagreement_map,
    }

    # ── Assemble the persistable result ──────────────────────────────────────
    rounds = [
        {"round": 1, "type": "initial_answers", "data": stage1_results},
        {"round": 2, "type": "peer_review", "data": stage2_results},
        {"round": 3, "type": "revise_or_defend", "data": stage3_results},
        {"round": 4, "type": "challenger", "data": stage4_result},
        {"round": 5, "type": "chairman_synthesis", "data": stage5_result}
    ]

    metadata = {
        "routing": routing_data,
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "rounds": rounds,
        "disagreement_map": disagreement_map,
        "metacognition": metacognition_serialized,
    }

    yield {
        "type": "complete",
        "result": {
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage5_result,
            "rounds": rounds,
            "metadata": metadata,
        }
    }


async def run_full_debate(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete deliberation to completion (batch mode).

    Returns:
        Tuple of (stage1_results, stage2_results, stage5_result, metadata)
    """
    result = None
    error_message = None

    async for event in run_debate_stream(user_query):
        if event["type"] == "complete":
            result = event["result"]
        elif event["type"] == "error":
            error_message = event["message"]

    if result is None:
        return [], [], {
            "model": "error",
            "response": error_message or "Debate failed to produce a result."
        }, {}

    return result["stage1"], result["stage2"], result["stage3"], result["metadata"]
