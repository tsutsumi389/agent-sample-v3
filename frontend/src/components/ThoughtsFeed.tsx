import { useEffect, useRef } from "react";
import type { ThoughtEntry } from "../types";
import { NODE_LABELS } from "../labels";

export function ThoughtsFeed({ thoughts }: { thoughts: ThoughtEntry[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thoughts]);

  if (thoughts.length === 0) {
    return <p className="empty">まだ思考はありません。</p>;
  }

  return (
    <div className="thoughts">
      {thoughts.map((t, i) => (
        <div key={i} className="thought">
          <div className="thought-head">
            {NODE_LABELS[t.agent] ?? t.agent}
            {t.taskId && <span className="tid">#{t.taskId}</span>}
          </div>
          <div className="thought-body">{t.content}</div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
