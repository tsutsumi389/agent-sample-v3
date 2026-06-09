import { useEffect, useRef, useState } from "react";
import type { ChatMessage, ChatState } from "../types";
import { NODE_LABELS } from "../labels";
import { Composer } from "./Composer";

interface Props {
  state: ChatState;
  onSend: (message: string) => void;
  onStop: () => void;
}

const SAMPLE_PROMPTS = [
  "LangGraph とは何か、3行で説明して",
  "TypeScript と Python の違いを表で比較して",
  "週末の東京観光プランを午前・午後・夜に分けて提案して",
];

// 最下部からこの距離以内なら「追従中」とみなして自動スクロールする
const STICK_THRESHOLD = 80;

// 非 HTTPS 環境などでは clipboard API 自体が存在しない
const CLIPBOARD_AVAILABLE = typeof navigator !== "undefined" && !!navigator.clipboard;

function formatTime(at: number): string {
  return new Date(at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // クリップボード非対応環境(非 HTTPS など)では何もしない
    }
  };

  return (
    <button className="copy-btn" onClick={copy} aria-label="回答をコピー">
      {copied ? "✓ コピーしました" : "コピー"}
    </button>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`bubble ${message.role}`}>
      <div className="role">
        {isUser ? "あなた" : "アシスタント"}
        <span className="time">{formatTime(message.at)}</span>
      </div>
      <div className="content">{message.content}</div>
      {!isUser && CLIPBOARD_AVAILABLE && <CopyButton text={message.content} />}
    </div>
  );
}

export function ChatWindow({ state, onSend, onStop }: Props) {
  const listRef = useRef<HTMLDivElement>(null);
  const [stickToBottom, setStickToBottom] = useState(true);
  const stickRef = useRef(stickToBottom);
  stickRef.current = stickToBottom;

  const scrollToBottom = (smooth = false) => {
    const el = listRef.current;
    el?.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  };

  // ユーザーが読み返し中(上にスクロール中)は自動追従しない
  const handleScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    setStickToBottom(distance < STICK_THRESHOLD);
  };

  // 追従状態は ref で参照する(依存に入れると下端復帰時に余計なジャンプが起きる)
  useEffect(() => {
    if (stickRef.current) scrollToBottom();
  }, [state.messages, state.answer, state.statusMessage]);

  const isEmpty = state.messages.length === 0 && !state.running;
  const workingLabel = NODE_LABELS[state.currentNode ?? ""] ?? "準備中";

  return (
    <section className="chat">
      <div className="messages" ref={listRef} onScroll={handleScroll}>
        {isEmpty && (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <h2>何をお手伝いしましょうか？</h2>
            <p>
              依頼を送ると、エージェントが「記憶 → 計画 → 並列実行 → 評価 → 回答」の流れで処理します。
              進行状況は右の稼働パネルにリアルタイム表示されます。
            </p>
            <div className="samples">
              {SAMPLE_PROMPTS.map((p) => (
                <button key={p} className="sample" onClick={() => onSend(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {state.messages.map((m, i) => (
          <MessageBubble key={`${m.at}-${i}`} message={m} />
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

        {/* 回答開始前は現在の工程を表示 */}
        {state.running && !state.answer && (
          <div className="bubble assistant working">
            <span className="spinner" />
            <div className="working-text">
              <span className="working-step">{workingLabel}</span>
              <span className="working-msg">{state.statusMessage || "考え中…"}</span>
            </div>
          </div>
        )}

        {state.error && !state.running && (
          <div className="bubble error" role="alert">
            ⚠️ エラーが発生しました: {state.error}
          </div>
        )}
      </div>

      {!stickToBottom && (
        <button className="jump-bottom" onClick={() => scrollToBottom(true)} aria-label="最新のメッセージへ移動">
          ↓ 最新へ
        </button>
      )}

      <Composer running={state.running} onSend={onSend} onStop={onStop} />
    </section>
  );
}
