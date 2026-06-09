"""LangGraph の State 定義。

コンテキスト分離の要:
- 親(オーケストレータ)の ParentState と、各サブエージェントの State は
  キーを一切共有しない。共有すると暗黙の共有チャネルになり分離が壊れる。
- 並列実行された Executor の書き込みをマージするため task_results には
  operator.add のリデューサを付ける(無いと InvalidUpdateError)。
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

# --- ドメイン型 -------------------------------------------------------------


class Task(TypedDict):
    id: str
    instruction: str
    parallel_group: int
    depends_on: list[str]


class TaskResult(TypedDict):
    task_id: str
    instruction: str
    result: str


class Evaluation(TypedDict):
    passed: bool
    feedback: str
    retry_instructions: list[str]


# --- 親グラフ(オーケストレータ) -------------------------------------------


class ParentState(TypedDict, total=False):
    user_request: str
    user_id: str
    retrieved_memories: list[str]
    plan: list[Task]
    task_results: Annotated[list[TaskResult], operator.add]  # 並列マージ
    evaluation: Evaluation
    iteration: int
    final_answer: str


# --- 各サブエージェントの独立 State(親とキーを共有しない) ------------------


class PlannerState(TypedDict, total=False):
    request: str
    memories: list[str]
    feedback: str
    plan: list[Task]


class ExecutorState(TypedDict, total=False):
    instruction: str
    task_id: str
    result: str


class EvaluatorState(TypedDict, total=False):
    request: str
    results: list[TaskResult]
    evaluation: Evaluation


def empty_evaluation() -> Evaluation:
    return {"passed": True, "feedback": "", "retry_instructions": []}
