"""Evaluator エージェント(独立コンパイル済みグラフ)。

元の要求と各タスク結果を受け取り、要求を満たしているか評価する。
不十分なら再計画用のフィードバックを返す。コンテキストは渡された
request / results のみ。
"""
from __future__ import annotations

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from ..agent_utils import parse_json, stream_agent
from ..llm import get_chat_llm
from ..schemas import Evaluation, EvaluatorState

SYSTEM = """あなたは品質評価者です。ユーザーの元の要求と、各タスクの実行結果を
読み、要求が十分に満たされているか判定してください。

必ず次の JSON のみを出力してください(前後に説明文を書かない):
{"passed": true/false, "feedback": "改善点や不足。passedがtrueなら空文字でよい",
 "retry_instructions": ["再実行すべき具体的な指示", "..."]}
"""


def _normalize(raw: dict) -> Evaluation:
    passed = bool(raw.get("passed", True))
    return {
        "passed": passed,
        "feedback": str(raw.get("feedback", "")),
        "retry_instructions": [str(x) for x in raw.get("retry_instructions", []) if x],
    }


async def _evaluate(state: EvaluatorState) -> dict:
    writer = get_stream_writer()
    writer({"type": "status", "node": "evaluator", "state": "running", "message": "結果を評価中…"})

    results = state.get("results") or []
    results_text = "\n\n".join(
        f"[タスク {r.get('task_id')}] 指示: {r.get('instruction', '')}\n結果: {r.get('result', '')}"
        for r in results
    )
    human = (
        f"ユーザーの元の要求:\n{state.get('request', '')}\n\n"
        f"各タスクの結果:\n{results_text}"
    )

    content, _ = await stream_agent(
        llm := get_chat_llm(),
        [("system", SYSTEM), ("human", human)],
        agent="evaluator",
        writer=writer,
    )

    parsed = parse_json(content)
    evaluation = _normalize(parsed) if parsed else {"passed": True, "feedback": "", "retry_instructions": []}

    writer(
        {
            "type": "evaluation",
            "passed": evaluation["passed"],
            "feedback": evaluation["feedback"],
        }
    )
    writer(
        {
            "type": "status",
            "node": "evaluator",
            "state": "node_complete",
            "message": "合格" if evaluation["passed"] else "再計画が必要",
        }
    )
    return {"evaluation": evaluation}


def _build():
    g = StateGraph(EvaluatorState)
    g.add_node("evaluate", _evaluate)
    g.add_edge(START, "evaluate")
    g.add_edge("evaluate", END)
    return g.compile()


evaluator_agent = _build()
