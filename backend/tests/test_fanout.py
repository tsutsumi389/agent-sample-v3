"""Send による並列ファンアウトと operator.add リデューサの検証。

実 LLM を使わず、ParentState の reducer 挙動と assign_executors の Send 生成を
ユニットテストする(InvalidUpdateError が出ないこと)。
"""
from langgraph.types import Send

from app.orchestrator import assign_executors


def test_assign_executors_emits_parallel_sends():
    state = {
        "plan": [
            {"id": "t1", "instruction": "A", "parallel_group": 0, "depends_on": []},
            {"id": "t2", "instruction": "B", "parallel_group": 0, "depends_on": []},
            {"id": "t3", "instruction": "C", "parallel_group": 0, "depends_on": []},
        ]
    }
    # get_stream_writer はグラフ実行外では no-op を返すので直接呼べる
    sends = assign_executors(state)
    assert len(sends) == 3
    assert all(isinstance(s, Send) for s in sends)
    assert all(s.node == "executor" for s in sends)
    # 各 Send は単一タスクの instruction/task_id のみ運ぶ(コンテキスト分離)
    payload_keys = {tuple(sorted(s.arg.keys())) for s in sends}
    assert payload_keys == {("instruction", "task_id")}


def test_task_results_reducer_merges():
    """operator.add リデューサで並列書き込みが連結されることを確認。"""
    import operator
    from typing import get_args, get_type_hints

    from app.schemas import ParentState

    hints = get_type_hints(ParentState, include_extras=True)
    # task_results は Annotated[list, operator.add]
    annotated = hints["task_results"]
    reducer = get_args(annotated)[1]
    assert reducer is operator.add
    assert reducer([{"a": 1}], [{"b": 2}]) == [{"a": 1}, {"b": 2}]
