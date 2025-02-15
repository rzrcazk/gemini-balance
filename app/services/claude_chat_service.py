from app.schemas.openai_models import ChatRequest, ChatResponse, ChatCompletionMessage
from app.services.key_manager import KeyManager
from app.core import config
import httpx
import json

class ClaudeChatService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.base_url = config.settings.CLAUDE_BASE_URL

    async def create_chat_completion(self, request: ChatRequest, key_group_name: str = "claude"):
        api_key = await self.key_manager.get_next_working_key(key_group_name)
        if api_key is None:
            raise Exception(f"No valid {key_group_name} API key found")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",  # 修改请求头
        }
        data = {
            "model": request.model,
            "messages": [message.dict() for message in request.messages],
            "stream": request.stream,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            # 其他参数，如果你的代理支持
        }

        try:
            if request.stream:
                async def generate_claude_stream():
                    async with httpx.AsyncClient() as client:
                        async with client.stream("POST", f"{self.base_url}/v1/chat/completions", headers=headers,
                                                  json=data, timeout=config.settings.HTTP_TIMEOUT) as response: # 使用配置的超时
                            async for chunk in response.aiter_bytes():
                                # 假设你的服务返回的是类似 OpenAI 的 JSON 格式
                                for line in chunk.split(b"\n"):
                                    if not line.strip():
                                        continue
                                    if b"data:" in line:
                                        try:
                                            line_str = line.decode("utf-8").replace("data:", "").strip()
                                            data_json = json.loads(line_str)

                                            # 根据你的服务的实际响应格式进行解析
                                            if "choices" in data_json and data_json["choices"]:
                                                delta_content = data_json["choices"][0].get("delta", {}).get("content", "")
                                                openai_chunk = {
                                                    "choices": [
                                                        {
                                                            "delta": {"content": delta_content},
                                                            "index": 0,
                                                            "finish_reason": None
                                                        }
                                                    ]
                                                }
                                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                                            elif data_json.get("finish_reason"): # 假设有finish_reason
                                                openai_chunk = {
                                                    "choices": [
                                                        {
                                                            "delta": {},
                                                            "index": 0,
                                                            "finish_reason": "stop"
                                                        }
                                                    ]
                                                }
                                                yield f"data: {json.dumps(openai_chunk)}\n\n"

                                        except (json.JSONDecodeError, KeyError) as e:
                                            # 处理 JSON 解析错误或字段缺失的情况
                                            print(f"error: {e}")
                                            continue
                    yield b"data: [DONE]\n\n"
                return generate_claude_stream()
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(f"{self.base_url}/v1/chat/completions", headers=headers, json=data, timeout=config.settings.HTTP_TIMEOUT)
                    response.raise_for_status()
                    response_json = response.json()
                    # 假设你的服务返回的也是 OpenAI 格式的响应

                    return ChatResponse(
                        id=response_json.get("id", "default_id"),
                        object="chat.completion",
                        created=response_json.get("created", 0),
                        model=response_json.get("model", request.model),
                        choices=[
                            {
                                "index": 0,
                                "message": {
                                    "role": response_json.get("choices", [{}])[0].get("message", {}).get("role", "assistant"),
                                    "content": response_json.get("choices", [{}])[0].get("message", {}).get("content", ""),
                                },
                                "finish_reason": response_json.get("choices", [{}])[0].get("finish_reason", "stop"),
                            }
                        ],
                        usage=response_json.get("usage", {}),
                    )
        except Exception as e:
            await self.key_manager.handle_api_failure(key_group_name, api_key)
            raise

    async def list_models(self, key_group_name: str = "claude"):
        """
        获取模型列表。由于你的代理只支持 /v1/models，这里我们简单地返回一个模拟的模型列表。
        """
        api_key = await self.key_manager.get_next_working_key(key_group_name)
        if api_key is None:
            raise Exception(f"No valid {key_group_name} API key found")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",  # 修改请求头
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/v1/models", headers=headers, timeout=config.settings.HTTP_TIMEOUT)
            response.raise_for_status()
            return response.json()
        # return {
        #     "data": [
        #         {"id": "claude-3.5-sonnet", "object": "model", "created": 1678888888, "owned_by": "zhucn"},
        #         {"id": "claude-3-opus", "object": "model", "created": 1678888888, "owned_by": "zhucn"},
        #     ],
        #     "object": "list"
        # }

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
