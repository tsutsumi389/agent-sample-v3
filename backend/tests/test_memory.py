"""記憶ストアの検証(実 Ollama 埋め込みを使用)。"""
from app.memory import assert_embed_dims, recall_memories, store


def test_embed_dims_is_768():
    assert assert_embed_dims() == 768


def test_put_and_search_roundtrip():
    store.put(("memories", "test-user"), "m1", {"text": "ユーザーは登山が趣味"})
    store.put(("memories", "test-user"), "m2", {"text": "ユーザーは犬を飼っている"})
    hits = recall_memories("test-user", "アウトドアの趣味", limit=5)
    assert any("登山" in h for h in hits)
