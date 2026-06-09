import { useAgentStream } from "./hooks/useAgentStream";
import { ChatWindow } from "./components/ChatWindow";
import { AgentActivityPanel } from "./components/AgentActivityPanel";

export default function App() {
  const { state, send, stop } = useAgentStream();

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 LangGraph オーケストレータ エージェント</h1>
        <span className="subtitle">Planner / Executor(並列) / Evaluator ・ ローカル gpt-oss</span>
      </header>
      <div className="layout">
        <ChatWindow state={state} onSend={send} onStop={stop} />
        <AgentActivityPanel state={state} />
      </div>
    </div>
  );
}
