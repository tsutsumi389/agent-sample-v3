"""アプリ設定。環境変数 / .env から読み込む。"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    chat_model: str = "gpt-oss:20b"
    embed_model: str = "nomic-embed-text"

    reasoning_effort: str = "medium"  # low | medium | high
    num_ctx: int = 8192
    max_iterations: int = 2
    embed_dims: int = 768

    frontend_origin: str = "http://localhost:5173"

    # 長期記憶(LangMem)を永続化する PostgreSQL(pgvector)接続文字列。
    # docker-compose.yml の db サービスがこの値に対応している。
    database_url: str = "postgresql://agent:agent@localhost:5432/agent"


settings = Settings()
