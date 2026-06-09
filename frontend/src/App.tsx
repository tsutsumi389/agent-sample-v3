import { useEffect, useState } from "react";
import { useAgentStream } from "./hooks/useAgentStream";
import { ChatWindow } from "./components/ChatWindow";
import { AgentActivityPanel } from "./components/AgentActivityPanel";

export default function App() {
  const { state, send, stop } = useAgentStream();
  // モバイル幅では稼働パネルをドロワー表示に切り替える
  const [panelOpen, setPanelOpen] = useState(false);

  // ESC でドロワーを閉じる
  useEffect(() => {
    if (!panelOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPanelOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panelOpen]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 LangGraph オーケストレータ エージェント</h1>
        <span className="subtitle">Planner / Executor(並列) / Evaluator ・ ローカル gpt-oss</span>
        <button
          className="panel-toggle"
          onClick={() => setPanelOpen((o) => !o)}
          aria-expanded={panelOpen}
          aria-label="稼働状況パネルの表示切り替え"
        >
          {state.running && <span className="live-dot" />}
          {panelOpen ? "✕ 閉じる" : "📊 稼働状況"}
        </button>
      </header>
      <div className={`layout ${panelOpen ? "panel-open" : ""}`}>
        <ChatWindow state={state} onSend={send} onStop={stop} />
        {panelOpen && (
          <div className="drawer-overlay" onClick={() => setPanelOpen(false)} aria-hidden="true" />
        )}
        <AgentActivityPanel state={state} />
      </div>
    </div>
  );
}
