from app.schemas.openai_models import ChatRequest, ChatResponse, ChatCompletionMessage
from app.services.key_manager import KeyManager
from app.core import config
import httpx
import json

class ClaudeChatService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.base_url = config.settings.CLAUDE_BASE_URL # 从配置读取

    async def create_chat_completion(self, request: ChatRequest, key_group_name: str = "claude"):  # 默认 claude
        api_key = self.key_manager.get_next_working_key(key_group_name)
        if api_key is None:
            raise Exception(f"No valid {key_group_name} API key found")

        headers = {
            "x-api-key": f"{api_key}",  # Claude 使用 x-api-key
            "content-type": "application/json"
        }
        # 重点修改
        data = {
            "model": request.model,
            "messages": [message.dict() for message in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            'stream': request.stream  # 移动到这里
        }

        async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",  # 使用 base_url
                    headers=headers,
                    data=json.dumps(data),
                    timeout=config.settings.HTTP_TIMEOUT,
                )

    def _convert_messages(self, messages):
        # 将 OpenAI 格式的消息转换为 Claude 格式
        claude_messages = []
        for message in messages:
            claude_messages.append({
                "role": message.role,
                "content": message.content
                # 可能需要根据 Claude API 的具体要求进行调整
            })
        return claude_messages

    def _convert_claude_response(self, response_json):
        # 将 Claude 的响应转换为 OpenAI 格式的消息
        return ChatCompletionMessage(
            role="assistant",  # 根据实际情况调整
            content=response_json["content"][0]["text"]  # 根据实际情况调整
        )
