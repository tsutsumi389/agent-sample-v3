"""記憶ストアの検証(実 Ollama 埋め込み + PostgreSQL/pgvector を使用)。

前提: `docker compose up -d` で db サービスが起動していること。
"""
import pytest

from app import memory
from app.memory import assert_embed_dims, recall_memories, setup_store, teardown_store


def test_embed_dims_is_768():
    assert assert_embed_dims() == 768


@pytest.fixture
async def store():
    await setup_store()
    yield memory.store
    await teardown_store()


async def test_put_and_search_roundtrip(store):
    await store.aput(("memories", "test-user"), "m1", {"text": "ユーザーは登山が趣味"})
    await store.aput(("memories", "test-user"), "m2", {"text": "ユーザーは犬を飼っている"})
    hits = await recall_memories("test-user", "アウトドアの趣味", limit=5)
    assert any("登山" in h for h in hits)
