from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.claude_chat_service import ClaudeChatService
from app.services.key_manager import get_key_manager_instance, KeyManager
from app.schemas.openai_models import ChatRequest
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/v1/chat/completions", response_model=ChatResponse)  # 保持与OpenAI兼容的路径
async def chat_completions(
    request: ChatRequest,
    claude_service: ClaudeChatService = Depends(lambda: ClaudeChatService(key_manager=get_key_manager_instance())),
):
    if request.stream:
        return StreamingResponse(claude_service.create_chat_completion(request, key_group_name="claude"), media_type="text/event-stream")
    else:
        return await claude_service.create_chat_completion(request)

@router.get("/v1/models") # 保持与OpenAI兼容的路径
async def list_models(
        claude_service: ClaudeChatService = Depends(lambda: ClaudeChatService(key_manager=get_key_manager_instance())),
):
    return await claude_service.list_models() 