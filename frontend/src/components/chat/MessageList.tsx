import { useEffect, useMemo, useRef } from "react";

import { useChatStore } from "../../store/chatStore";
import type { ChatMessage } from "../../types/chat";
import { isStreamingMessage } from "../../types/chat";
import { MessageItem } from "./MessageItem";

interface MessageListProps {
  roomId: string;
}

function getMessageKey(message: ChatMessage): string {
  return isStreamingMessage(message) ? message.messageId : message.id;
}

export function MessageList({ roomId }: MessageListProps) {
  const messagesByRoom = useChatStore((state) => state.messagesByRoom);
  const streamingMessages = useChatStore((state) => state.streamingMessages);
  const bottomRef = useRef<HTMLDivElement>(null);

  const displayMessages = useMemo(() => {
    const persisted = messagesByRoom[roomId] ?? [];
    const streaming = Object.values(streamingMessages).filter(
      (message) => message.roomId === roomId,
    );

    const persistedIds = new Set(persisted.map((message) => message.id));
    const activeStreaming = streaming.filter(
      (message) => !persistedIds.has(message.messageId),
    );

    const combined: ChatMessage[] = [...persisted, ...activeStreaming];

    return combined.sort(
      (left, right) =>
        new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime(),
    );
  }, [messagesByRoom, streamingMessages, roomId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages]);

  if (displayMessages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-4">
        <p className="text-sm text-slate-500">No messages yet. Say hello!</p>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {displayMessages.map((message) => (
        <MessageItem key={getMessageKey(message)} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
