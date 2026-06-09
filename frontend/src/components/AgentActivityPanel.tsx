import type { ChatState } from "../types";
import { NODE_LABELS, PIPELINE_STEPS } from "../labels";
import { TaskChecklist } from "./TaskChecklist";
import { ThoughtsFeed } from "./ThoughtsFeed";

// 記憶→計画→実行→評価→回答 の進行を一目で示すステッパー
function Pipeline({ currentNode, running }: { currentNode: string | null; running: boolean }) {
  const activeIndex = PIPELINE_STEPS.findIndex((s) => currentNode != null && s.keys.includes(currentNode));

  return (
    <div className="pipeline" aria-label="処理フロー">
      {PIPELINE_STEPS.map((step, i) => {
        const status = !running ? "idle" : i < activeIndex ? "done" : i === activeIndex ? "active" : "idle";
        return (
          <div key={step.label} className={`step ${status}`}>
            <span className="step-icon">{status === "done" ? "✓" : step.icon}</span>
            <span className="step-label">{step.label}</span>
            {i < PIPELINE_STEPS.length - 1 && <span className="step-arrow">›</span>}
          </div>
        );
      })}
    </div>
  );
}

export function AgentActivityPanel({ state }: { state: ChatState }) {
  const doneCount = state.tasks.filter((t) => t.status === "done").length;
  const progressPct = state.tasks.length > 0 ? Math.round((doneCount / state.tasks.length) * 100) : 0;

  return (
    <aside className="activity">
      <div className="activity-head">
        <h2>エージェント稼働状況</h2>
        <span className={`badge ${state.running ? "live" : "idle"}`}>
          {state.running
            ? NODE_LABELS[state.currentNode ?? ""] ?? state.currentNode ?? "起動中"
            : "待機中"}
        </span>
      </div>

      <Pipeline currentNode={state.currentNode} running={state.running} />

      {state.running && state.statusMessage && (
        <p className="status-msg">{state.statusMessage}</p>
      )}

      {state.memories.length > 0 && (
        <div className="block">
          <h3>🧠 想起した記憶</h3>
          <ul className="memories">
            {state.memories.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {state.tasks.length > 0 && (
        <div className="block">
          <h3>
            📋 タスク進捗
            <span className="task-count">
              {doneCount} / {state.tasks.length}
            </span>
          </h3>
          <div className="progress" role="progressbar" aria-valuenow={progressPct} aria-valuemin={0} aria-valuemax={100}>
            <div className="progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <TaskChecklist tasks={state.tasks} />
        </div>
      )}

      {state.evaluation && (
        <div className="block">
          <h3>🔍 評価</h3>
          <div className={`eval ${state.evaluation.passed ? "pass" : "fail"}`}>
            <strong>{state.evaluation.passed ? "✅ 合格" : "🔁 再計画中"}</strong>
            {state.evaluation.feedback && <p>{state.evaluation.feedback}</p>}
          </div>
        </div>
      )}

      <div className="block grow">
        <h3>💭 思考ログ</h3>
        <ThoughtsFeed thoughts={state.thoughts} />
      </div>
    </aside>
  );
}
