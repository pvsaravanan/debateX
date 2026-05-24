"""3-stage DebateX orchestration."""

from typing import List, Dict, Any, Optional, Tuple
from .llm import query_models_parallel, query_model
from .config import debate_MODELS, moderator_MODEL
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


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all debate models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel
    responses = await query_models_parallel(debate_MODELS, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
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

    # Get rankings from all debate models in parallel
    responses = await query_models_parallel(debate_MODELS, messages)

    # Format results
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


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: moderator synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for moderator
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    moderator_prompt = f"""You are the moderator of an DebateX. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as moderator is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

CRITICAL LANGUAGE REQUIREMENT: You MUST write your final response strictly in English, regardless of the language of the user's original question.

Provide a clear, well-reasoned final answer that represents the debate's collective wisdom:"""

    messages = [{"role": "user", "content": moderator_prompt}]

    # Query the moderator model
    response = None
    try:
        response = await query_model(moderator_MODEL, messages)
    except Exception as e:
        print(f"Moderator model {moderator_MODEL} failed with exception: {e}")

    content = response.get('content', '').strip() if response else ""

    if not content:
        # Fallback if moderator fails or returns empty - try alternative model if available
        print(f"Moderator model {moderator_MODEL} failed or returned empty. Attempting fallback synthesis...")
        
        # Try to get a simple synthesis from first available debate model
        for model in debate_MODELS:
            try:
                fallback_response = await query_model(model, messages)
                fallback_content = fallback_response.get('content', '').strip() if fallback_response else ""
                
                if fallback_content:
                    return {
                        "model": model,
                        "response": fallback_content
                    }
            except Exception as e:
                print(f"Fallback model {model} failed with exception: {e}")
                continue
        
        # Final fallback
        return {
            "model": moderator_MODEL,
            "response": "Error: Unable to generate final synthesis. All models failed or returned empty responses."
        }

    return {
        "model": moderator_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
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
    # 1. Try with moderator_MODEL first if available
    if moderator_MODEL:
        try:
            response = await query_model(moderator_MODEL, messages, timeout=15.0)
        except Exception as e:
            print(f"Failed to query title with moderator model: {e}")

    # 2. Try with nvidia/nemotron-3-nano-30b-a3b:free next
    if response is None:
        try:
            response = await query_model("nvidia/nemotron-3-nano-30b-a3b:free", messages, timeout=15.0)
        except Exception:
            pass

    # 3. Try with any of the debate_MODELS
    if response is None:
        for model in debate_MODELS:
            try:
                response = await query_model(model, messages, timeout=10.0)
                if response is not None:
                    break
            except Exception:
                continue

    # Parse and cleanup
    title = ""
    if response is not None:
        title = response.get('content', '').strip()

    title = title.strip('"\' \n\r\t')

    # If no title could be generated, fall back to first few words of the user query
    if not title or title.lower() == "new conversation":
        words = [w for w in user_query.strip().split() if w]
        if words:
            title = " ".join(words[:4])
            if len(words) > 4:
                title += "..."
        else:
            title = "New Conversation"

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def stage3_revise_or_defend(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    aggregate_rankings: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Stage 3: Models see anonymized rankings and evaluations, and revise or defend their responses.
    """
    # Create the anonymized responses text from Stage 1
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    # Format the peer evaluations
    reviews_formatted = ""
    for idx, r in enumerate(stage2_results):
        reviews_formatted += f"### Reviewer {idx+1} Evaluation:\n{r['ranking']}\n\n"

    # Format the aggregate standings
    standings_formatted = "\n".join([
        f"- {next((k for k, v in label_to_model.items() if v == item['model']), item['model'])}: Average Rank {item['average_rank']} (over {item['rankings_count']} votes)"
        for item in aggregate_rankings
    ])

    # Generate prompts for all participating models
    prompts = {}
    for result in stage1_results:
        model = result['model']
        model_label = next((k for k, v in label_to_model.items() if v == model), None)
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
        prompts[model] = [{"role": "user", "content": prompt}]

    # Query all models in parallel
    models_to_query = list(prompts.keys())
    responses = {}
    if models_to_query:
        tasks = [query_model(model, prompts[model]) for model in models_to_query]
        import asyncio
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
            full_text = response.get('content', '').strip()
            # Parse decision
            decision = "REVISE"
            cleaned_content = full_text
            if "DECISION: DEFEND" in full_text:
                decision = "DEFEND"
                lines = full_text.split('\n')
                cleaned_content = "\n".join([line for line in lines if "DECISION:" not in line]).strip()
            elif "DECISION: REVISE" in full_text:
                decision = "REVISE"
                lines = full_text.split('\n')
                cleaned_content = "\n".join([line for line in lines if "DECISION:" not in line]).strip()
            
            stage3_results.append({
                "model": model,
                "decision": decision,
                "response": cleaned_content,
                "raw_response": full_text
            })
    return stage3_results


async def stage4_challenger_critique(
    user_query: str,
    stage3_results: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 4: Assign one model as Challenger to find the weakest point in the leading answer.
    """
    if not stage3_results or not aggregate_rankings:
        return {
            "model": "Challenger Model",
            "response": "No models available to challenge."
        }

    # Find the leading model (first in aggregate rankings)
    leading_model_name = aggregate_rankings[0]['model']
    leading_result = next((r for r in stage3_results if r['model'] == leading_model_name), stage3_results[0])
    leading_response = leading_result['response']

    # Select Challenger: worst model in aggregate rankings
    # If only 1 model, it challenges itself. Otherwise, select the last model.
    challenger_model_name = aggregate_rankings[-1]['model']
    if challenger_model_name == leading_model_name and len(aggregate_rankings) > 1:
        challenger_model_name = aggregate_rankings[-2]['model']

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
        content = response.get('content', '').strip() if response else ""
    except Exception as e:
        print(f"Challenger model {challenger_model_name} failed: {e}")
        content = f"Error: Challenger {challenger_model_name} failed to generate critique."

    return {
        "model": challenger_model_name,
        "response": content,
        "target_model": leading_model_name,
        "target_response": leading_response
    }


async def stage5_chairman_synthesis(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    stage3_results: List[Dict[str, Any]],
    challenger_result: Dict[str, Any],
    label_to_model: Dict[str, str],
    aggregate_rankings: List[Dict[str, Any]],
    metacognition_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 5: Chairman synthesizes the final response using the full deliberation history.
    Also populates a structured DisagreementMap (consensus zones, disagreement zones,
    confidence scores) for the DisagreementPanel UI component.
    When metacognition_summary is provided it is injected as model confidence weights.
    """
    # Compile the deliberation history array
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

    import json
    history_json = json.dumps(deliberation_history, indent=2)

    # Narrative formatting for the model
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

    # Build metacognition weight block for Chairman prompt
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

    try:
        response = await query_model(moderator_MODEL, messages)
        content = response.get('content', '').strip() if response else ""
    except Exception as e:
        print(f"Chairman model {moderator_MODEL} failed: {e}")
        content = ""

    if not content:
        # Fallback if chairman fails - use fallback models
        print(f"Chairman model {moderator_MODEL} failed or returned empty. Using fallback synthesis...")
        for model in debate_MODELS:
            try:
                fallback_response = await query_model(model, messages)
                fallback_content = fallback_response.get('content', '').strip() if fallback_response else ""
                if fallback_content:
                    return {
                        "model": model,
                        "response": fallback_content
                    }
            except Exception as fe:
                print(f"Fallback model {model} failed: {fe}")
                continue

        # Final fallback: use the leading answer from Round 3
        leading_response = challenger_result.get('target_response', 'Error: Unable to synthesize final answer.')
        return {
            "model": "Fallback Synthesis (Leading Answer)",
            "response": leading_response
        }

    # --- Parse / build the DisagreementMap ---
    dm: Optional[DisagreementMap] = parse_disagreement_map(content)
    if dm is None:
        # LLM did not emit the JSON block → fall back to heuristic analysis
        dm = build_disagreement_map_heuristic(stage1_results, stage3_results, aggregate_rankings)

    # Strip the JSON fence from the narrative response so the UI gets clean text
    import re as _re
    clean_content = _re.sub(r'```(?:json)?\s*\{[\s\S]*?\}\s*```', '', content).strip()

    return {
        "model": moderator_MODEL,
        "response": clean_content,
        "disagreement_map": serialize_disagreement_map(dm),
    }


async def run_full_debate(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 5-round debate process with metacognition pre-flight.

    Returns:
        Tuple of (stage1_results, stage2_results, stage5_result, metadata)
    """
    import asyncio as _asyncio

    # ── Pre-flight: metacognition + stage1 fire concurrently ──────────────
    meta_task = _asyncio.create_task(run_metacognition(user_query))
    stage1_task = _asyncio.create_task(stage1_collect_responses(user_query))

    metacognition_result: MetacognitionResult = await meta_task
    stage1_results: List[Dict[str, Any]] = await stage1_task

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Revise or Defend
    stage3_results = await stage3_revise_or_defend(
        user_query,
        stage1_results,
        stage2_results,
        label_to_model,
        aggregate_rankings
    )

    # Stage 4: Challenger Critique
    stage4_result = await stage4_challenger_critique(
        user_query,
        stage3_results,
        aggregate_rankings
    )

    # Stage 5: Chairman Synthesis (with metacognition weights)
    stage5_result = await stage5_chairman_synthesis(
        user_query,
        stage1_results,
        stage2_results,
        stage3_results,
        stage4_result,
        label_to_model,
        aggregate_rankings,
        metacognition_summary=metacognition_result.summary,
    )

    # Compile the detailed rounds list
    rounds = [
        {"round": 1, "type": "initial_answers", "data": stage1_results},
        {"round": 2, "type": "peer_review", "data": stage2_results},
        {"round": 3, "type": "revise_or_defend", "data": stage3_results},
        {"round": 4, "type": "challenger", "data": stage4_result},
        {"round": 5, "type": "chairman_synthesis", "data": stage5_result}
    ]

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "rounds": rounds,
        "disagreement_map": stage5_result.get("disagreement_map"),
        "metacognition": serialize_metacognition_result(metacognition_result),
    }

    return stage1_results, stage2_results, stage5_result, metadata
