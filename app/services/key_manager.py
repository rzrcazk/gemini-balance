import asyncio
from itertools import cycle
from typing import Dict
from app.core.logger import get_key_manager_logger
from app.core.config import settings


logger = get_key_manager_logger()


class KeyManager:
    def __init__(self, key_config: dict = None):
        if key_config is None:
            key_config = settings.KEY_CONFIG

        self.key_groups = {}  # 存储不同模型组的密钥和配置
        self.key_statuses = {}  # 存储密钥的状态（是否有效、失败次数）
        self.lock = asyncio.Lock()  # 异步锁，用于保护密钥状态的更新

        # 初始化密钥组和状态
        for group_name, conf in key_config.items():
            self.key_groups[group_name] = {
                "keys": cycle(conf["keys"]),  # 使用 cycle 创建无限循环的密钥迭代器
                "paid_model": conf.get("paid_model"),
                "prefix": conf.get("prefix", "")  # 增加 prefix 支持
            }
            self.key_statuses[group_name] = {}
            for key in conf["keys"]:
                self.key_statuses[group_name][key] = {"valid": True, "failure_count": 0}

    def get_next_key(self, group_name: str):
        """获取指定模型组的下一个密钥"""
        if group_name not in self.key_groups:
            raise ValueError(f"Invalid key group name: {group_name}")

        return next(self.key_groups[group_name]["keys"])

    def is_key_valid(self, group_name: str, key: str):
        """检查密钥是否有效"""
        return self.key_statuses[group_name][key]["valid"]

    def get_next_working_key(self, group_name: str):
        """获取指定模型组的下一个有效密钥"""
        async with self.lock:  # 使用锁保护密钥状态
            for _ in range(len(self.key_statuses[group_name])):  # 遍历所有密钥，最多循环一轮
                key = self.get_next_key(group_name)
                if self.is_key_valid(group_name, key):
                    return key
            return None  # 如果没有找到有效密钥，返回 None

    def handle_api_failure(self, group_name: str, key: str):
        """处理 API 密钥失败"""
        async with self.lock:
            self.key_statuses[group_name][key]["failure_count"] += 1
            # 如果失败次数超过阈值，标记为无效
            if self.key_statuses[group_name][key]["failure_count"] >= settings.MAX_FAILED_ATTEMPTS:
                self.key_statuses[group_name][key]["valid"] = False

    def get_paid_key(self, group_name: str):
        """获取指定模型组的付费密钥（如果有）"""
        return self.key_groups[group_name].get("paid_model")

    def get_keys_by_status(self, group_name: str):
        """获取指定模型组的密钥状态"""
        return self.key_statuses[group_name]

    def get_key_group_name(self, model_name: str) -> str:
        """根据模型名称获取 key group"""
        for group_name, config in self.key_groups.items():
            if config["prefix"] and model_name.startswith(config["prefix"]):
                return group_name
        return "gemini"  # 默认使用 gemini


_singleton_instance = None
_singleton_lock = asyncio.Lock()

async def get_key_manager_instance(api_keys: list = None) -> KeyManager:
    """
    获取 KeyManager 单例实例。

    如果尚未创建实例，将使用提供的 api_keys 初始化 KeyManager。
    如果已创建实例，则忽略 api_keys 参数，返回现有单例。
    """
    global _singleton_instance

    async with _singleton_lock:
        if _singleton_instance is None:
            if api_keys is None:
                raise ValueError("API keys are required to initialize the KeyManager")
            _singleton_instance = KeyManager(api_keys)
        return _singleton_instance
