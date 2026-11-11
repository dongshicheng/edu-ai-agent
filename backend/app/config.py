from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings
from pathlib import Path


def _normalize_openai_base_url(url: str) -> str:
    """OpenAI SDK 要求 base_url 指向 …/v1；仅填域名时会误打到网站首页并返回 HTML。"""
    url = (url or "").strip().rstrip("/")
    if not url:
        return "https://api.openai.com/v1"
    parsed = urlparse(url)
    path = parsed.path or ""
    if path in ("", "/"):
        return f"{parsed.scheme}://{parsed.netloc}/v1"
    return url


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    zhipu_api_key: str = ""
    primary_model: str = "gpt-4o"
    secondary_model: str = "glm-4"

    # Embedding
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    embedding_device: str = "cpu"

    # Redis（可选，当前未使用，预留给 Celery 任务队列）
    redis_url: str = "redis://localhost:6379/0"

    # Database
    database_url: str = "sqlite+aiosqlite:///./edu_project.db"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"

    # File Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 100

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    @field_validator("openai_base_url", mode="before")
    @classmethod
    def normalize_openai_base_url_field(cls, v: str) -> str:
        if v is None or not str(v).strip():
            return "https://api.openai.com/v1"
        return _normalize_openai_base_url(str(v))


settings = Settings()
