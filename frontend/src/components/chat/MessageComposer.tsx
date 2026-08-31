import { FormEvent, KeyboardEvent, useState } from "react";

import { useTypingEmitter } from "../../hooks/useTypingEmitter";
import { useChatStore } from "../../store/chatStore";
import { useWebSocketStore } from "../../store/websocketStore";

interface MessageComposerProps {
  roomId: string;
  disabled?: boolean;
}

export function MessageComposer({ roomId, disabled = false }: MessageComposerProps) {
  const sendMessage = useWebSocketStore((state) => state.sendMessage);
  const isConnected = useWebSocketStore((state) => state.status === "connected");
  const setRealtimeError = useChatStore((state) => state.setRealtimeError);
  const { onKeystroke, stopTyping } = useTypingEmitter(roomId);

  const [content, setContent] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || disabled || !isConnected) {
      return;
    }

    const sent = sendMessage(roomId, trimmed);
    if (!sent) {
      setSendError("Unable to send message. Reconnecting…");
      setRealtimeError("Unable to send message. Please wait for reconnection.");
      return;
    }

    setContent("");
    setSendError(null);
    setRealtimeError(null);
    stopTyping();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const inputDisabled = disabled || !isConnected;

  return (
    <form
      onSubmit={handleSubmit}
      className="shrink-0 border-t border-slate-800 bg-slate-900/50 px-4 py-3"
    >
      {!isConnected ? (
        <p className="mb-2 text-xs text-amber-400">Reconnecting to chat…</p>
      ) : null}
      {sendError ? <p className="mb-2 text-xs text-red-400">{sendError}</p> : null}
      <div className="flex gap-2">
        <textarea
          value={content}
          onChange={(event) => {
            const next = event.target.value;
            setContent(next);
            onKeystroke(next);
          }}
          onKeyDown={handleKeyDown}
          onBlur={stopTyping}
          placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
          rows={2}
          disabled={inputDisabled}
          className="min-h-[2.5rem] flex-1 resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={inputDisabled || !content.trim()}
          className="self-end rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-white disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </form>
  );
}
