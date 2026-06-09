"""LangMem による長期記憶。

- nomic-embed-text(768次元)で意味検索する InMemoryStore を構築。
- 読み出し(recall): store.search で関連記憶を取得 → Planner に渡す。
- 書き込み(background): 会話終了後に ReflectionExecutor で非同期に記憶を抽出・統合。

注意: InMemoryStore はプロセス内メモリのみ(再起動で消える)。本番では
AsyncPostgresStore に差し替える。
"""
from __future__ import annotations

import logging

from langgraph.store.memory import InMemoryStore

from .config import settings
from .llm import get_chat_llm, get_embeddings

logger = logging.getLogger(__name__)

# 記憶の名前空間。書き込み/読み出しで完全に一致させること(LangMem #140)。
NAMESPACE = ("memories", "{user_id}")


def _build_store() -> InMemoryStore:
    return InMemoryStore(
        index={
            "dims": settings.embed_dims,  # nomic-embed-text = 768 固定
            "embed": get_embeddings(),
            "fields": ["text"],
        }
    )


store = _build_store()

# 背景での記憶抽出は遅延初期化する(import 時にネットワーク/モデル初期化で
# ブロックしないように)。初回 remember_async 呼び出し時に一度だけ構築。
_reflection = None
_reflection_ready = False


def _get_reflection():
    global _reflection, _reflection_ready
    if _reflection_ready:
        return _reflection
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


def recall_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    """ユーザーに紐づく関連記憶をテキストのリストで返す。"""
    try:
        items = store.search(("memories", user_id), query=query, limit=limit)
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
