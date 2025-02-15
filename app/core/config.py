import json
from typing import List, Dict, Union
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pydantic import validator

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Application"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/v1"

    # API Keys
    API_KEYS: List[str]  # 保持原样，给 Gemini 用
    CLAUDE_API_KEYS: List[str] # 新增
    CLAUDE_BASE_URL: str = "https://zhucn.org"  # 修改默认值

    ALLOWED_TOKENS: List[str]
    BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    MODEL_SEARCH: List[str] = ["gemini-2.0-flash-exp"]
    TOOLS_CODE_EXECUTION_ENABLED: bool = False
    SHOW_SEARCH_LINK: bool = True
    SHOW_THINKING_PROCESS: bool = True
    AUTH_TOKEN: str = ""
    MAX_FAILURES: int = 3
    PAID_KEY: str = ""
    CREATE_IMAGE_MODEL: str = "imagen-3.0-generate-002"
    UPLOAD_PROVIDER: str = "smms"
    SMMS_SECRET_TOKEN: str = ""
    MAX_FAILED_ATTEMPTS: int = 3
    HTTP_TIMEOUT: int = 600  # 新增：HTTP 请求超时时间

    def __init__(self):
        super().__init__()
        if not self.AUTH_TOKEN:
            self.AUTH_TOKEN = self.ALLOWED_TOKENS[0] if self.ALLOWED_TOKENS else ""

    @validator("CLAUDE_API_KEYS", pre=True)
    def validate_claude_api_keys(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return v.split(",") # 简单分割
        return v

    class Config:
        env_file = ".env"


settings = Settings()
