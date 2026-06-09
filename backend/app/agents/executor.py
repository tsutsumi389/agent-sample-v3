"""Executor エージェント(独立コンパイル済みグラフ)。

1つの instruction だけを受け取り実行する。複数の Executor が Send により
並列起動される。コンテキストは instruction のみ(会話履歴を持たない)。
"""
from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from ..agent_utils import stream_agent
from ..llm import get_chat_llm
from ..schemas import ExecutorState

SYSTEM = """あなたは与えられた1つのタスクだけを忠実に実行するエグゼキューターです。
余計な前置きをせず、指示された成果物を簡潔かつ具体的に出力してください。
あなたは1タスク専任であり、他のタスクや会話の文脈は知りません。"""


async def _execute(state: ExecutorState) -> dict:
    writer = get_stream_writer()
    task_id = state.get("task_id", "t?")
    instruction = state.get("instruction", "")
    label = instruction[:60]

    writer({"type": "task_update", "task_id": task_id, "status": "running", "label": label})

    llm = get_chat_llm()
    content, _ = await stream_agent(
        llm,
        [("system", SYSTEM), ("human", instruction)],
        agent="executor",
        writer=writer,
        task_id=task_id,
        emit_tokens=True,
    )

    writer({"type": "task_update", "task_id": task_id, "status": "done", "label": label})
    return {"result": content}


def _build():
    g = StateGraph(ExecutorState)
    g.add_node("execute", _execute)
    g.add_edge(START, "execute")
    g.add_edge("execute", END)
    return g.compile()


executor_agent = _build()
