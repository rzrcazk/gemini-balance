import asyncio
from itertools import cycle
from typing import Dict
from app.core.logger import get_key_manager_logger
from app.core.config import settings


logger = get_key_manager_logger()

_singleton_instance = None

class KeyManager:
    def __init__(self, key_config: dict = None):
        # 移除 key_config 参数和相关逻辑, 直接在内部使用 settings
        self.key_groups = {}
        self.key_statuses = {}
        self.lock = asyncio.Lock()

        # Gemini 密钥组
        self.key_groups["gemini"] = {
            "keys": cycle(settings.API_KEYS),
            "prefix": "gemini"  # 可以根据需要调整
        }
        self.key_statuses["gemini"] = {}
        for key in settings.API_KEYS:
            self.key_statuses["gemini"][key] = {"valid": True, "failure_count": 0}

        # Claude 密钥组
        self.key_groups["claude"] = {
            "keys": cycle(settings.CLAUDE_API_KEYS),
            "prefix": "claude"  # 根据需要调整
        }
        self.key_statuses["claude"] = {}
        for key in settings.CLAUDE_API_KEYS:
            self.key_statuses["claude"][key] = {"valid": True, "failure_count": 0}

    async def get_next_working_key(self, group_name: str):
        async with self.lock:
            for _ in range(len(self.key_statuses[group_name])):
                key = self.get_next_key(group_name)
                if self.is_key_valid(group_name, key):
                    return key
            return None

    def get_next_key(self, group_name: str):
        return next(self.key_groups[group_name]["keys"])

    def is_key_valid(self, group_name: str, key: str):
        return self.key_statuses[group_name][key]["valid"]

    async def handle_api_failure(self, group_name: str, key: str):
        async with self.lock:
            self.key_statuses[group_name][key]["failure_count"] += 1
            if self.key_statuses[group_name][key]["failure_count"] >= settings.MAX_FAILED_ATTEMPTS:
                self.key_statuses[group_name][key]["valid"] = False

    def get_key_group_name(self, model_name: str) -> str:
        for group_name, config in self.key_groups.items():
            if config["prefix"] and model_name.startswith(config["prefix"]):
                return group_name
        raise ValueError(f"No key group found for model: {model_name}")

async def get_key_manager_instance():
    global _singleton_instance
    if _singleton_instance is None:
        # 直接创建，不再需要参数
        _singleton_instance = KeyManager()
    return _singleton_instance
