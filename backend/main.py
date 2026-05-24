"""FastAPI backend for DebateX."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from .debate import run_full_debate, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings, stage3_revise_or_defend, stage4_challenger_critique, stage5_chairman_synthesis
from .metacognition import run_metacognition, serialize_metacognition_result

app = FastAPI(title="DebateX API")

# Enable CORS for local development - MUST be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class UpdateConversationRequest(BaseModel):
    """Request to update/rename a conversation."""
    title: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "DebateX API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """Update a specific conversation's properties (like title)."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        storage.update_conversation_title(conversation_id, request.title)
        return {"success": True, "title": request.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating conversation title: {str(e)}")


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a specific conversation."""
    try:
        success = storage.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True, "message": "Conversation deleted"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 5-round debate process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 5-round debate process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_debate(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        rounds=metadata.get("rounds"),
        metadata=metadata
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
        "rounds": metadata.get("rounds")
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 5-round debate process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # METACOGNITION DISABLED — re-enable by restoring meta_task block
            metacognition_serialized = None

            # Round 1: Initial responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"

            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Round 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Round 3: Revise or Defend
            yield f"data: {json.dumps({'type': 'round3_start'})}\n\n"
            stage3_results = await stage3_revise_or_defend(request.content, stage1_results, stage2_results, label_to_model, aggregate_rankings)
            yield f"data: {json.dumps({'type': 'round3_complete', 'data': stage3_results})}\n\n"

            # Round 4: Challenger Critique
            yield f"data: {json.dumps({'type': 'round4_start'})}\n\n"
            stage4_result = await stage4_challenger_critique(request.content, stage3_results, aggregate_rankings)
            yield f"data: {json.dumps({'type': 'round4_complete', 'data': stage4_result})}\n\n"

            # Round 5: Chairman Synthesis
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage5_result = await stage5_chairman_synthesis(
                request.content,
                stage1_results,
                stage2_results,
                stage3_results,
                stage4_result,
                label_to_model,
                aggregate_rankings,
                metacognition_summary=metacognition_result.summary,
            )
            disagreement_map = stage5_result.get("disagreement_map")
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage5_result, 'disagreement_map': disagreement_map})}\n\n"

            # Compile new rounds list
            rounds = [
                {"round": 1, "type": "initial_answers", "data": stage1_results},
                {"round": 2, "type": "peer_review", "data": stage2_results},
                {"round": 3, "type": "revise_or_defend", "data": stage3_results},
                {"round": 4, "type": "challenger", "data": stage4_result},
                {"round": 5, "type": "chairman_synthesis", "data": stage5_result}
            ]

            metadata = {
                "label_to_model": label_to_model,
                "aggregate_rankings": aggregate_rankings,
                "rounds": rounds,
                "disagreement_map": disagreement_map,
                "metacognition": metacognition_serialized,
            }

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage5_result,
                rounds=rounds,
                metadata=metadata
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
