"""ChatOllama / OllamaEmbeddings のファクトリ。

gpt-oss 特有の注意点:
- reasoning="medium" を渡すと思考(CoT)が content の <think> ではなく
  AIMessageChunk.additional_kwargs['reasoning_content'] に分離される。
  → UI の「思考」表示に使える。古い langchain-ollama では文字列を受け付けず
    bool_parsing エラーになるため、段階的にフォールバックする。
- num_ctx を明示しないと Ollama が ~4096 に切り詰める。
"""
from __future__ import annotations

from functools import lru_cache

from langchain_ollama import ChatOllama, OllamaEmbeddings

from .config import settings


def get_chat_llm(*, streaming: bool = True, temperature: float = 0.0) -> ChatOllama:
    """エージェント用の ChatOllama を生成する。

    各エージェントは同じモデルを使うが、インスタンスは独立。会話履歴は
    一切共有せず、呼び出しごとに渡されたメッセージのみで推論する。
    """
    base = dict(
        model=settings.chat_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        num_ctx=settings.num_ctx,
        streaming=streaming,
    )
    # reasoning パラメータをバージョン差異に強い形で適用する。
    for reasoning in (settings.reasoning_effort, True, None):
        try:
            kwargs = dict(base)
            if reasoning is not None:
                kwargs["reasoning"] = reasoning
            return ChatOllama(**kwargs)
        except Exception:  # noqa: BLE001 - バージョン非対応値を順に試す
            continue
    return ChatOllama(**base)


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.embed_model,
        base_url=settings.ollama_base_url,
    )
