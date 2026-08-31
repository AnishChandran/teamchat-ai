import { formatMessageTime } from "../../lib/formatTime";
import type { ChatMessage } from "../../types/chat";
import { isStreamingMessage } from "../../types/chat";

interface MessageItemProps {
  message: ChatMessage;
}

export function MessageItem({ message }: MessageItemProps) {
  const isAi = message.type === "ai";
  const isStreaming = isStreamingMessage(message) && message.status === "streaming";
  const isError = isStreamingMessage(message) && message.status === "error";

  return (
    <article
      className={`rounded-lg px-3 py-2 ${
        isAi
          ? "border-l-2 border-violet-500 bg-violet-950/40"
          : "border-l-2 border-slate-600 bg-slate-900/60"
      }`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className={`text-sm font-medium ${isAi ? "text-violet-300" : "text-slate-200"}`}>
          {message.senderName}
          {isAi ? " · AI" : null}
        </span>
        <time className="shrink-0 text-xs text-slate-500">
          {formatMessageTime(message.createdAt)}
        </time>
      </div>
      <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-100">
        {message.content}
        {isStreaming ? (
          <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-violet-400 align-text-bottom" />
        ) : null}
      </p>
      {isError && isStreamingMessage(message) && message.errorMessage ? (
        <p className="mt-1 text-xs text-red-400">{message.errorMessage}</p>
      ) : null}
    </article>
  );
}
