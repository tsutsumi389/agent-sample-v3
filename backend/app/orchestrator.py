"""オーケストレータ(親グラフ)。

flow:
  START → recall_memory → planner → [Send 並列ファンアウト] executor×N
        → evaluator → (合格/上限 → finalize / 不合格 → planner で再計画) → END

各ブリッジノードは「明示的な指示だけ」をサブエージェントに渡し、戻り値の
必要なキーだけを親 State に書き戻す。これによりエージェント間でコンテキスト
(会話履歴)を一切引き継がない。
"""
from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .agents import evaluator_agent, executor_agent, planner_agent
from .agent_utils import safe_writer, stream_agent
from .config import settings
from .llm import get_chat_llm
from .memory import recall_memories, remember_async
from .schemas import ParentState, empty_evaluation

FINALIZE_SYSTEM = """あなたはオーケストレータの統括役です。各サブタスクの結果を
統合し、ユーザーの元の要求に対する最終回答を分かりやすくまとめてください。"""


# --- ノード ---------------------------------------------------------------


async def recall_memory(state: ParentState) -> dict:
    writer = get_stream_writer()
    writer({"type": "status", "node": "memory", "state": "running", "message": "記憶を想起中…"})
    memories = await recall_memories(state["user_id"], state["user_request"])
    if memories:
        writer({"type": "memory", "items": memories})
    writer({"type": "status", "node": "memory", "state": "node_complete",
            "message": f"{len(memories)}件の記憶を取得"})
    return {"retrieved_memories": memories, "iteration": 0}


async def planner_node(state: ParentState) -> dict:
    """Planner サブグラフを呼ぶブリッジ。要求/記憶/評価フィードバックのみ渡す。"""
    feedback = (state.get("evaluation") or {}).get("feedback", "")
    out = await planner_agent.ainvoke(
        {
            "request": state["user_request"],
            "memories": state.get("retrieved_memories", []),
            "feedback": feedback,
        }
    )
    return {"plan": out.get("plan", [])}


def assign_executors(state: ParentState):
    """plan の各タスクを並列 Executor として Send でファンアウトする。"""
    plan = state.get("plan") or []
    writer = safe_writer()
    writer({"type": "status", "node": "orchestrator", "state": "running",
            "message": f"{len(plan)}件のタスクを並列実行へ振り分け"})
    return [
        Send("executor", {"instruction": t["instruction"], "task_id": t["id"]})
        for t in plan
    ]


async def executor_node(state: ParentState) -> dict:
    """Executor サブグラフを呼ぶブリッジ。instruction/task_id のみ渡す。

    Send により本ノードは並列起動される。戻り値の task_results は
    operator.add リデューサで安全にマージされる。
    """
    # この実行に割り当てられた単一タスク(Send のペイロード)
    instruction = state["instruction"]  # type: ignore[typeddict-item]
    task_id = state["task_id"]  # type: ignore[typeddict-item]
    out = await executor_agent.ainvoke({"instruction": instruction, "task_id": task_id})
    return {
        "task_results": [
            {"task_id": task_id, "instruction": instruction, "result": out.get("result", "")}
        ]
    }


async def evaluator_node(state: ParentState) -> dict:
    """Evaluator サブグラフを呼ぶブリッジ。要求と結果のみ渡す。"""
    out = await evaluator_agent.ainvoke(
        {"request": state["user_request"], "results": state.get("task_results", [])}
    )
    return {
        "evaluation": out.get("evaluation", empty_evaluation()),
        "iteration": state.get("iteration", 0) + 1,
    }


def route_after_eval(state: ParentState) -> str:
    evaluation = state.get("evaluation") or {}
    if evaluation.get("passed", True) or state.get("iteration", 0) >= settings.max_iterations:
        return "finalize"
    return "replan"


async def finalize(state: ParentState) -> dict:
    writer = get_stream_writer()
    writer({"type": "status", "node": "finalize", "state": "running", "message": "最終回答を生成中…"})

    results = state.get("task_results") or []
    results_text = "\n\n".join(
        f"[{r.get('task_id')}] {r.get('instruction', '')}\n→ {r.get('result', '')}" for r in results
    )
    human = f"元の要求:\n{state['user_request']}\n\n各タスクの結果:\n{results_text}\n\n最終回答をまとめてください。"

    answer, _ = await stream_agent(
        get_chat_llm(),
        [("system", FINALIZE_SYSTEM), ("human", human)],
        agent="finalize",
        writer=writer,
        emit_tokens=True,
    )

    writer({"type": "final", "answer": answer})
    writer({"type": "status", "node": "finalize", "state": "node_complete", "message": "完了"})

    # 背景で会話を記憶化(ホットパスをブロックしない)
    remember_async(state["user_id"], state["user_request"], answer)
    return {"final_answer": answer}


# --- グラフ構築 -------------------------------------------------------------


def build_orchestrator():
    g = StateGraph(ParentState)
    g.add_node("recall_memory", recall_memory)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("evaluator", evaluator_node)
    g.add_node("finalize", finalize)

    g.add_edge(START, "recall_memory")
    g.add_edge("recall_memory", "planner")
    # planner → Send 並列ファンアウト(条件エッジで Send のリストを返す)
    g.add_conditional_edges("planner", assign_executors, ["executor"])
    # executor → evaluator は fan-in バリア(全 executor 完了後に evaluator)
    g.add_edge("executor", "evaluator")
    g.add_conditional_edges(
        "evaluator", route_after_eval, {"replan": "planner", "finalize": "finalize"}
    )
    g.add_edge("finalize", END)
    return g.compile()


orchestrator = build_orchestrator()
