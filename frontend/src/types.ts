// バックエンドの SSE イベントとフロントの状態モデル

export type TaskStatus = "pending" | "running" | "done" | "error";

export interface AgentTask {
  id: string;
  label: string;
  status: TaskStatus;
  parallelGroup: number;
}

export interface ThoughtEntry {
  agent: string;
  taskId?: string | null;
  content: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  at: number; // 送信/確定時刻 (epoch ms)
}

export interface EvalInfo {
  passed: boolean;
  feedback: string;
}

export interface ChatState {
  running: boolean;
  currentNode: string | null;
  statusMessage: string;
  tasks: AgentTask[];
  thoughts: ThoughtEntry[];
  memories: string[];
  evaluation: EvalInfo | null;
  answer: string; // ストリーミング中の最終回答
  messages: ChatMessage[];
  error: string | null; // 直近の実行で発生したエラー(チャット欄に表示)
}

// SSE data ペイロード(type で判別)
export type AgentEvent =
  | { type: "status"; node: string; state: "running" | "node_complete"; message?: string }
  | { type: "thinking"; agent: string; task_id?: string | null; content: string }
  | { type: "token"; agent: string; task_id?: string | null; content: string }
  | { type: "plan"; tasks: { id: string; instruction: string; parallel_group: number }[] }
  | { type: "task_update"; task_id: string; status: TaskStatus; label: string }
  | { type: "evaluation"; passed: boolean; feedback: string }
  | { type: "memory"; items: string[] }
  | { type: "final"; answer: string }
  | { type: "error"; message: string };
