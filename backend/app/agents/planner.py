"""Planner エージェント(独立コンパイル済みグラフ)。

ユーザー要求を、できるだけ並列実行可能な独立タスクに分解する。
親グラフとは State キーを共有せず、与えられた request / memories / feedback
のみで推論する(コンテキスト分離)。
"""
from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from ..agent_utils import parse_json, stream_agent
from ..llm import get_chat_llm
from ..schemas import PlannerState, Task

SYSTEM = """あなたは熟練のプランナーです。ユーザーの要求を、互いに独立して
並列実行できる具体的なサブタスクに分解してください。

ルール:
- 各タスクは1つの明確な指示文(instruction)にする。
- 並列実行可能なタスクには同じ parallel_group 番号(0始まり)を付ける。
- タスクは多くても5個まで。単純な要求なら1個でよい。

必ず次の JSON のみを出力してください(前後に説明文を書かない):
{"tasks":[{"id":"t1","instruction":"...","parallel_group":0}]}
"""


def _normalize(raw: dict) -> list[Task]:
    tasks = raw.get("tasks") if isinstance(raw, dict) else None
    if not isinstance(tasks, list) or not tasks:
        return []
    out: list[Task] = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue
        instruction = str(t.get("instruction", "")).strip()
        if not instruction:
            continue
        out.append(
            {
                "id": str(t.get("id") or f"t{i + 1}"),
                "instruction": instruction,
                "parallel_group": int(t.get("parallel_group", 0) or 0),
            }
        )
    return out


async def _plan(state: PlannerState) -> dict:
    writer = get_stream_writer()
    writer({"type": "status", "node": "planner", "state": "running", "message": "タスクを計画中…"})

    llm = get_chat_llm()
    parts = [f"ユーザーの要求:\n{state.get('request', '')}"]
    memories = state.get("memories") or []
    if memories:
        parts.append("関連する過去の記憶:\n- " + "\n- ".join(memories))
    feedback = state.get("feedback")
    if feedback:
        parts.append(f"前回の計画は不十分でした。次の指摘を反映して再計画してください:\n{feedback}")

    content, _ = await stream_agent(
        llm,
        [("system", SYSTEM), ("human", "\n\n".join(parts))],
        agent="planner",
        writer=writer,
    )

    plan = _normalize(parse_json(content))
    if not plan:
        # フォールバック: 分解できなければ要求そのものを1タスクにする
        plan = [
            {
                "id": "t1",
                "instruction": state.get("request", ""),
                "parallel_group": 0,
            }
        ]

    writer({"type": "plan", "tasks": plan})
    writer({"type": "status", "node": "planner", "state": "node_complete", "message": f"{len(plan)}件のタスクを作成"})
    return {"plan": plan}


def _build():
    g = StateGraph(PlannerState)
    g.add_node("plan", _plan)
    g.add_edge(START, "plan")
    g.add_edge("plan", END)
    return g.compile()


planner_agent = _build()
