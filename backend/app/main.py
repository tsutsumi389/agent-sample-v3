"""FastAPI エントリポイント。POST /chat/stream で SSE を返す。"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .memory import assert_embed_dims, setup_store, teardown_store
from .service import run_agent_stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        dim = assert_embed_dims()
        logger.info("埋め込み次元チェックOK: %d", dim)
    except Exception as exc:  # noqa: BLE001
        logger.warning("埋め込み次元チェックに失敗(記憶検索が動かない可能性): %s", exc)

    try:
        await setup_store()
        logger.info("PostgreSQL 記憶ストアを初期化しました: %s", settings.database_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PostgreSQL ストア初期化に失敗(記憶が永続化されません): %s", exc)

    try:
        yield
    finally:
        await teardown_store()


app = FastAPI(title="LangGraph Orchestrator Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default-user"
    thread_id: str | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "chat_model": settings.chat_model, "embed_model": settings.embed_model}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> EventSourceResponse:
    thread_id = req.thread_id or str(uuid.uuid4())

    async def event_source():
        async for event in run_agent_stream(req.message, req.user_id, thread_id):
            # クライアント切断時は実行を打ち切る(無駄な計算を止める)
            if await request.is_disconnected():
                break
            yield event

    return EventSourceResponse(event_source())
