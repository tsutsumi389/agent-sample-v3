import { useEffect, useRef } from "react";
import type { ChatState } from "../types";
import { Composer } from "./Composer";

interface Props {
  state: ChatState;
  onSend: (message: string) => void;
  onStop: () => void;
}

export function ChatWindow({ state, onSend, onStop }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, state.answer]);

  return (
    <section className="chat">
      <div className="messages">
        {state.messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <div className="role">{m.role === "user" ? "あなた" : "アシスタント"}</div>
            <div className="content">{m.content}</div>
          </div>
        ))}

        {/* ストリーミング中の最終回答 */}
        {state.running && state.answer && (
          <div className="bubble assistant streaming">
            <div className="role">アシスタント</div>
            <div className="content">
              {state.answer}
              <span className="cursor">▍</span>
            </div>
          </div>
        )}

        {state.running && !state.answer && (
          <div className="bubble assistant working">
            <span className="spinner" /> {state.statusMessage || "考え中…"}
          </div>
        )}

        <div ref={endRef} />
      </div>

      <Composer running={state.running} onSend={onSend} onStop={onStop} />
    </section>
  );
}
