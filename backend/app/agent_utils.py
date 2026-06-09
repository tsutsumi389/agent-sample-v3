"""エージェント共通ユーティリティ: LLM のストリーミングと JSON 抽出。"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage


def safe_writer():
    """グラフ実行コンテキスト内なら stream writer を、外なら no-op を返す。

    ルータ関数やユニットテストから安全に呼べるようにするためのラッパー。
    """
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:  # noqa: BLE001
        return lambda *_args, **_kwargs: None


async def stream_agent(
    llm: BaseChatModel,
    messages: list[BaseMessage] | list[tuple[str, str]],
    *,
    agent: str,
    writer,
    task_id: str | None = None,
    emit_tokens: bool = False,
) -> tuple[str, str]:
    """LLM を astream し、思考(reasoning_content)と本文を逐次イベント送出する。

    - thinking イベント: gpt-oss の reasoning_content の差分
    - token イベント:    本文の差分(emit_tokens=True のとき)

    戻り値は (本文全体, 思考全体)。
    """
    content_parts: list[str] = []
    reasoning_parts: list[str] = []

    async for chunk in llm.astream(messages):
        # 本文の差分
        text = _as_text(getattr(chunk, "content", ""))
        if text:
            content_parts.append(text)
            if emit_tokens:
                writer({"type": "token", "agent": agent, "task_id": task_id, "content": text})

        # 思考(reasoning)の差分。バージョンにより格納先が異なるため両対応。
        extra = getattr(chunk, "additional_kwargs", {}) or {}
        reasoning = extra.get("reasoning_content") or extra.get("reasoning")
        if reasoning:
            reasoning_parts.append(reasoning)
            writer(
                {
                    "type": "thinking",
                    "agent": agent,
                    "task_id": task_id,
                    "content": reasoning,
                }
            )

    return "".join(content_parts), "".join(reasoning_parts)


def _as_text(content: Any) -> str:
    """content が str / list(ブロック) どちらでも文字列に正規化する。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for block in content:
            if isinstance(block, str):
                out.append(block)
            elif isinstance(block, dict):
                out.append(block.get("text", ""))
        return "".join(out)
    return str(content or "")


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json(text: str) -> dict[str, Any]:
    """LLM 出力から JSON オブジェクトを頑健に取り出す。

    コードフェンス除去 → 直接 parse → 最初の {...} ブロック抽出、の順に試す。
    gpt-oss の structured output は不安定なため寛容にパースする。
    """
    if not text:
        return {}
    text = text.strip()

    m = _FENCE.search(text)
    if m:
        text = m.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 最初の波括弧ブロックを抽出
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}
