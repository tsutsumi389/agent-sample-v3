"""LangGraph の astream を SSE イベントへ変換する。

graph.astream(stream_mode=["custom","updates"], subgraphs=True) を消費する。
- custom: 各ノードが writer() で発行した dict(type を持つ) → そのまま中継。
- updates: ノード完了の {node: delta} → status(node_complete) に変換。

subgraphs=True なので、サブエージェント(planner/executor/evaluator)内部の
writer イベントも親ストリームに浮上する。これがチャット画面に「今何が動いて
いて、何を考えているか」を流すための要。
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from .orchestrator import orchestrator


def _sse(event: str, data: Any) -> dict:
    """sse-starlette の EventSourceResponse が受け取る形に整形。"""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _unpack(item: Any) -> tuple[str, Any]:
    """astream の出力形を (mode, chunk) に正規化する。

    subgraphs=True + 複数 stream_mode では (namespace, mode, chunk) の3要素、
    単一 stream_mode では (namespace, chunk) の2要素になりうるため両対応。
    """
    if isinstance(item, tuple):
        if len(item) == 3:
            _, mode, chunk = item
            return mode, chunk
        if len(item) == 2:
            return item[0], item[1]
    return "custom", item


async def run_agent_stream(
    user_request: str, user_id: str, thread_id: str
) -> AsyncGenerator[dict, None]:
    config = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
    inputs = {"user_request": user_request, "user_id": user_id}

    yield _sse("status", {"type": "status", "node": "orchestrator",
                          "state": "running", "message": "エージェント起動"})

    try:
        async for item in orchestrator.astream(
            inputs,
            config=config,
            stream_mode=["custom", "updates"],
            subgraphs=True,
        ):
            mode, chunk = _unpack(item)

            if mode == "custom" and isinstance(chunk, dict):
                event = chunk.get("type", "status")
                yield _sse(event, chunk)

            elif mode == "updates" and isinstance(chunk, dict):
                for node in chunk:
                    yield _sse(
                        "status",
                        {"type": "status", "node": node, "state": "node_complete", "message": ""},
                    )
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"type": "error", "message": str(exc)})

    # 終端センチネル(SSE には終了通知が無いためクライアントはこれで停止)
    yield _sse("final", "[DONE]")
