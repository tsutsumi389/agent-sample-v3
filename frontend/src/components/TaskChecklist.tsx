import type { AgentTask } from "../types";

const ICONS: Record<AgentTask["status"], string> = {
  pending: "⚪",
  running: "🔵",
  done: "✅",
  error: "❌",
};

export function TaskChecklist({ tasks }: { tasks: AgentTask[] }) {
  // parallel_group ごとにまとめて、同一グループは並列実行であることを示す
  const groups = new Map<number, AgentTask[]>();
  for (const t of tasks) {
    const g = groups.get(t.parallelGroup) ?? [];
    g.push(t);
    groups.set(t.parallelGroup, g);
  }

  return (
    <div className="tasks">
      {[...groups.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([group, items]) => (
          <div key={group} className="task-group">
            {items.length > 1 && <div className="group-label">グループ{group}（同時実行）</div>}
            {items.map((t) => (
              <div key={t.id} className={`task ${t.status}`}>
                <span className="icon">{ICONS[t.status]}</span>
                <span className="task-label">{t.label}</span>
                {t.status === "running" && <span className="spinner small" />}
              </div>
            ))}
          </div>
        ))}
    </div>
  );
}
