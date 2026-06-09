import type { ChatState } from "../types";
import { TaskChecklist } from "./TaskChecklist";
import { ThoughtsFeed } from "./ThoughtsFeed";

const NODE_LABELS: Record<string, string> = {
  orchestrator: "オーケストレータ",
  memory: "記憶想起",
  recall_memory: "記憶想起",
  planner: "プランナー",
  executor: "エグゼキューター",
  evaluator: "エヴァリュエーター",
  finalize: "最終統合",
};

export function AgentActivityPanel({ state }: { state: ChatState }) {
  return (
    <aside className="activity">
      <h2>エージェント稼働状況</h2>

      <div className="current-node">
        <span className="label">現在の処理</span>
        <span className={`badge ${state.running ? "live" : "idle"}`}>
          {state.running ? NODE_LABELS[state.currentNode ?? ""] ?? state.currentNode ?? "—" : "待機中"}
        </span>
        {state.running && <span className="status-msg">{state.statusMessage}</span>}
      </div>

      {state.memories.length > 0 && (
        <div className="block">
          <h3>想起した記憶</h3>
          <ul className="memories">
            {state.memories.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {state.tasks.length > 0 && (
        <div className="block">
          <h3>計画タスク（並列実行）</h3>
          <TaskChecklist tasks={state.tasks} />
        </div>
      )}

      {state.evaluation && (
        <div className="block">
          <h3>評価</h3>
          <div className={`eval ${state.evaluation.passed ? "pass" : "fail"}`}>
            <strong>{state.evaluation.passed ? "✅ 合格" : "🔁 再計画"}</strong>
            {state.evaluation.feedback && <p>{state.evaluation.feedback}</p>}
          </div>
        </div>
      )}

      <div className="block grow">
        <h3>思考ログ</h3>
        <ThoughtsFeed thoughts={state.thoughts} />
      </div>
    </aside>
  );
}
