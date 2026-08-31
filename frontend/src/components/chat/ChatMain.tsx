import { useChatStore } from "../../store/chatStore";
import { useWebSocketStore } from "../../store/websocketStore";
import { MessageComposer } from "./MessageComposer";
import { MessageList } from "./MessageList";
import { RoomHeader } from "./RoomHeader";
import { TypingIndicator } from "./TypingIndicator";

export function ChatMain() {
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const loading = useChatStore((state) => state.loading);
  const error = useChatStore((state) => state.error);
  const realtimeError = useChatStore((state) => state.realtimeError);
  const wsStatus = useWebSocketStore((state) => state.status);
  const wsError = useWebSocketStore((state) => state.error);

  if (!activeRoomId) {
    return (
      <div className="flex flex-1 items-center justify-center px-4">
        <p className="text-slate-400">Select a room from the sidebar to start chatting.</p>
      </div>
    );
  }

  return (
    <>
      <RoomHeader />
      {wsError && wsStatus !== "connected" ? (
        <p className="shrink-0 bg-amber-950/50 px-4 py-2 text-sm text-amber-200">{wsError}</p>
      ) : null}
      {realtimeError ? (
        <p className="shrink-0 bg-red-950/50 px-4 py-2 text-sm text-red-300">{realtimeError}</p>
      ) : null}
      {error ? (
        <p className="shrink-0 bg-red-950/50 px-4 py-2 text-sm text-red-300">{error}</p>
      ) : null}
      {loading && wsStatus === "connected" ? (
        <p className="shrink-0 px-4 py-1 text-xs text-slate-500">Loading messages…</p>
      ) : null}
      <MessageList roomId={activeRoomId} />
      <TypingIndicator roomId={activeRoomId} />
      <MessageComposer roomId={activeRoomId} />
    </>
  );
}
