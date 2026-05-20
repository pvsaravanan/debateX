"""3-stage DebateX orchestration."""

from typing import List, Dict, Any, Tuple
from .llm import query_models_parallel, query_model
from .config import debate_MODELS, moderator_MODEL


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


async def run_full_debate(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage debate process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

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

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
