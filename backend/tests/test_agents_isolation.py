"""各サブエージェントが独立 State で単体起動できる(コンテキスト分離)ことの検証。"""
import pytest

from app.agents import evaluator_agent, executor_agent, planner_agent
from app.schemas import ExecutorState, ParentState, PlannerState


def test_state_schemas_are_disjoint():
    """親とサブエージェントが State キーを共有していないこと(分離の前提)。"""
    parent = set(ParentState.__annotations__)
    planner = set(PlannerState.__annotations__)
    executor = set(ExecutorState.__annotations__)
    # 親はサブの内部キー(request/instruction/result)を持たない
    assert "instruction" not in parent
    assert "result" not in parent
    assert "request" not in parent
    # サブ同士も無関係
    assert planner.isdisjoint(executor)


@pytest.mark.asyncio
async def test_executor_runs_in_isolation():
    """Executor は instruction だけで単体実行できる。"""
    out = await executor_agent.ainvoke(
        {"instruction": "「こんにちは」とだけ出力して。", "task_id": "t1"}
    )
    assert isinstance(out.get("result"), str)
    assert out["result"]


@pytest.mark.asyncio
async def test_planner_produces_tasks():
    out = await planner_agent.ainvoke({"request": "東京の天気と人口を調べて", "memories": []})
    plan = out.get("plan")
    assert isinstance(plan, list) and len(plan) >= 1
    assert all("instruction" in t and "id" in t for t in plan)


@pytest.mark.asyncio
async def test_evaluator_returns_verdict():
    out = await evaluator_agent.ainvoke(
        {
            "request": "1+1は?",
            "results": [{"task_id": "t1", "instruction": "1+1を計算", "result": "2"}],
        }
    )
    ev = out.get("evaluation")
    assert isinstance(ev["passed"], bool)
