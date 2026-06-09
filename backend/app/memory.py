"""LangMem による長期記憶(PostgreSQL + pgvector で永続化)。

- nomic-embed-text(768次元)で意味検索する AsyncPostgresStore を構築。
- 読み出し(recall): store.asearch で関連記憶を取得 → Planner に渡す。
- 書き込み(background): 会話終了後に ReflectionExecutor で非同期に記憶を抽出・統合。

ストアは pgvector を有効化した PostgreSQL に永続化されるため、プロセスを
再起動しても記憶は残る。接続先は settings.database_url(docker-compose.yml の
db サービス)。ストアは非同期接続プールを張るため、アプリ起動時に setup_store()
で初期化し、終了時に teardown_store() で破棄する(main.py の lifespan)。
"""
from __future__ import annotations

import logging

from langgraph.store.postgres.aio import AsyncPostgresStore

from .config import settings
from .llm import get_chat_llm, get_embeddings

logger = logging.getLogger(__name__)

# 記憶の名前空間。書き込み/読み出しで完全に一致させること(LangMem #140)。
NAMESPACE = ("memories", "{user_id}")

# AsyncPostgresStore は非同期コンテキストマネージャ。アプリのライフサイクルに
# 合わせて手動で enter/exit するため、ストア本体と CM を別々に保持する。
store: AsyncPostgresStore | None = None
_store_cm = None

# 背景での記憶抽出は遅延初期化する(初回 remember_async 呼び出し時に一度だけ構築)。
_reflection = None
_reflection_ready = False


async def setup_store() -> None:
    """PostgreSQL ストアを初期化する(接続プール確立 + テーブル/拡張のセットアップ)。

    store.setup() が pgvector 拡張の有効化とテーブル作成(IF NOT EXISTS)を行う。
    冪等なので再起動時に再実行しても安全。
    """
    global store, _store_cm
    if store is not None:
        return
    _store_cm = AsyncPostgresStore.from_conn_string(
        settings.database_url,
        index={
            "dims": settings.embed_dims,  # nomic-embed-text = 768 固定
            "embed": get_embeddings(),
            "fields": ["text"],
        },
    )
    store = await _store_cm.__aenter__()
    await store.setup()


async def teardown_store() -> None:
    """ストアの接続プールを破棄する(アプリ終了時)。"""
    global store, _store_cm, _reflection, _reflection_ready
    if _store_cm is not None:
        await _store_cm.__aexit__(None, None, None)
    _store_cm = None
    store = None
    _reflection = None
    _reflection_ready = False


def _get_reflection():
    global _reflection, _reflection_ready
    if _reflection_ready:
        return _reflection
    if store is None:  # ストア未初期化なら今は構築しない(次回再試行)
        return None
    _reflection_ready = True
    try:  # pragma: no cover - 環境依存
        from langmem import ReflectionExecutor, create_memory_store_manager

        manager = create_memory_store_manager(
            get_chat_llm(streaming=False),
            namespace=NAMESPACE,
            store=store,
        )
        _reflection = ReflectionExecutor(manager, store=store)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LangMem の背景記憶マネージャを初期化できませんでした: %s", exc)
        _reflection = None
    return _reflection


def assert_embed_dims() -> int:
    """起動時の健全性チェック。nomic-embed-text の次元が想定通りか検証する。

    (古い/壊れたタグだと 8192 を返し意味検索が静かに壊れるため。)
    """
    dim = len(get_embeddings().embed_query("dimension probe"))
    if dim != settings.embed_dims:
        raise RuntimeError(
            f"埋め込み次元が想定と不一致: 実際={dim}, 期待={settings.embed_dims}. "
            f"EMBED_DIMS を {dim} に合わせるか、正しい埋め込みモデルを使ってください。"
        )
    return dim


async def recall_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    """ユーザーに紐づく関連記憶をテキストのリストで返す。"""
    if store is None:
        return []
    try:
        items = await store.asearch(("memories", user_id), query=query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("記憶検索に失敗: %s", exc)
        return []
    out: list[str] = []
    for it in items:
        val = it.value or {}
        out.append(str(val.get("text") or val.get("content") or val))
    return out


def remember_async(user_id: str, user_message: str, assistant_message: str) -> None:
    """会話を背景スレッドで記憶化する(ホットパスをブロックしない)。"""
    reflection = _get_reflection()
    if reflection is None:
        return
    try:  # pragma: no cover - 環境依存
        payload = {
            "messages": [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        }
        config = {"configurable": {"user_id": user_id}}
        reflection.submit(payload, after_seconds=0.5, config=config)
    except Exception as exc:  # noqa: BLE001
        logger.warning("背景記憶化に失敗: %s", exc)
