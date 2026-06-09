import { useState } from "react";

interface Props {
  running: boolean;
  onSend: (message: string) => void;
  onStop: () => void;
}

export function Composer({ running, onSend, onStop }: Props) {
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim() || running) return;
    onSend(text);
    setText("");
  };

  return (
    <div className="composer">
      <textarea
        value={text}
        placeholder="やってほしいことを入力（Enterで送信 / Shift+Enterで改行）"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={2}
      />
      {running ? (
        <button className="btn stop" onClick={onStop}>
          停止
        </button>
      ) : (
        <button className="btn send" onClick={submit} disabled={!text.trim()}>
          送信
        </button>
      )}
    </div>
  );
}
