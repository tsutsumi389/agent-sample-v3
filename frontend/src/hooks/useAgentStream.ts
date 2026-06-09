import { useCallback, useReducer, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { AgentEvent, AgentTask, ChatState } from "../types";

const initialState: ChatState = {
  running: false,
  currentNode: null,
  statusMessage: "",
  plan: [],
  tasks: [],
  thoughts: [],
  memories: [],
  evaluation: null,
  answer: "",
  messages: [],
};

type Action =
  | { kind: "start"; message: string }
  | { kind: "event"; event: AgentEvent }
  | { kind: "finish" }
  | { kind: "fail"; message: string };

function reducer(state: ChatState, action: Action): ChatState {
  switch (action.kind) {
    case "start":
      return {
        ...initialState,
        messages: [...state.messages, { role: "user", content: action.message }],
        running: true,
        statusMessage: "起動中…",
      };
    case "finish": {
      // ストリーミングした answer を確定メッセージにコミット
      const msgs = state.answer
        ? [...state.messages, { role: "assistant" as const, content: state.answer }]
        : state.messages;
      return { ...state, running: false, currentNode: null, messages: msgs, answer: "" };
    }
    case "fail":
      return { ...state, running: false, statusMessage: `エラー: ${action.message}` };
    case "event":
      return applyEvent(state, action.event);
  }
}

function applyEvent(state: ChatState, ev: AgentEvent): ChatState {
  switch (ev.type) {
    case "status":
      return {
        ...state,
        currentNode: ev.state === "running" ? ev.node : state.currentNode,
        statusMessage: ev.message || state.statusMessage,
      };
    case "plan": {
      const tasks: AgentTask[] = ev.tasks.map((t) => ({
        id: t.id,
        label: t.instruction,
        status: "pending",
        parallelGroup: t.parallel_group,
      }));
      return { ...state, plan: tasks, tasks };
    }
    case "task_update": {
      const tasks = state.tasks.map((t) =>
        t.id === ev.task_id ? { ...t, status: ev.status, label: ev.label || t.label } : t
      );
      return { ...state, tasks };
    }
    case "thinking": {
      // 同一 agent/task の連続する思考は末尾に追記してまとめる
      const last = state.thoughts[state.thoughts.length - 1];
      if (last && last.agent === ev.agent && last.taskId === (ev.task_id ?? null)) {
        const merged = [...state.thoughts];
        merged[merged.length - 1] = { ...last, content: last.content + ev.content };
        return { ...state, thoughts: merged };
      }
      return {
        ...state,
        thoughts: [...state.thoughts, { agent: ev.agent, taskId: ev.task_id ?? null, content: ev.content }],
      };
    }
    case "token":
      // finalize の本文トークンを最終回答へ追記
      return { ...state, answer: state.answer + ev.content };
    case "evaluation":
      return { ...state, evaluation: { passed: ev.passed, feedback: ev.feedback } };
    case "memory":
      return { ...state, memories: ev.items };
    case "final":
      return { ...state, answer: ev.answer || state.answer };
    case "error":
      return { ...state, statusMessage: `エラー: ${ev.message}` };
  }
}

export function useAgentStream() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const ctrlRef = useRef<AbortController | null>(null);

  const send = useCallback(async (message: string, userId = "default-user") => {
    if (!message.trim()) return;
    dispatch({ kind: "start", message });

    const ctrl = new AbortController();
    ctrlRef.current = ctrl;

    try {
      await fetchEventSource("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, user_id: userId }),
        signal: ctrl.signal,
        openWhenHidden: true, // バックグラウンドタブでも実行を継続
        onmessage(msg) {
          if (msg.data === "[DONE]") {
            dispatch({ kind: "finish" });
            ctrl.abort();
            return;
          }
          if (!msg.data) return;
          try {
            const parsed = JSON.parse(msg.data) as AgentEvent;
            dispatch({ kind: "event", event: parsed });
          } catch {
            // パースできないフレームは無視
          }
        },
        onerror(err) {
          dispatch({ kind: "fail", message: String(err) });
          throw err; // 自動リトライを止める
        },
      });
    } catch {
      // abort / error は dispatch 済み
    }
  }, []);

  const stop = useCallback(() => {
    ctrlRef.current?.abort();
    dispatch({ kind: "finish" });
  }, []);

  return { state, send, stop };
}
