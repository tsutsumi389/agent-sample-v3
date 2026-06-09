import { useEffect, useRef, useState } from "react";

interface Props {
  running: boolean;
  onSend: (message: string) => void;
  onStop: () => void;
}

const MAX_HEIGHT = 160;

export function Composer({ running, onSend, onStop }: Props) {
  const [text, setText] = useState("");
  const areaRef = useRef<HTMLTextAreaElement>(null);

  // 入力量に合わせて高さを自動調整(上限あり)
  useEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [text]);

  // 起動時と応答完了時に入力欄へフォーカスを戻す
  useEffect(() => {
    if (!running) areaRef.current?.focus();
  }, [running]);

  const canSend = !running && text.trim().length > 0;

  const submit = () => {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <div className="composer">
      <div className="composer-row">
        <textarea
          ref={areaRef}
          value={text}
          placeholder={running ? "応答が完了したら送信できます…" : "やってほしいことを入力…"}
          aria-label="メッセージ入力"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            // IME 変換確定の Enter では送信しない(isComposing 判定)
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          rows={1}
        />
        {running ? (
          <button className="btn stop" onClick={onStop} aria-label="生成を停止">
            ■ 停止
          </button>
        ) : (
          <button className="btn send" onClick={submit} disabled={!canSend} aria-label="送信">
            送信 ↑
          </button>
        )}
      </div>
      <div className="composer-hint">
        <kbd>Enter</kbd> 送信 ・ <kbd>Shift + Enter</kbd> 改行
      </div>
    </div>
  );
}
