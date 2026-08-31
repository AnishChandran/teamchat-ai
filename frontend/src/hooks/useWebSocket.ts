import { useEffect } from "react";

import { useWebSocketStore } from "../store/websocketStore";
import type { ServerEvent } from "../types/events";

interface UseWebSocketOptions {
  onEvent?: (event: ServerEvent) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const status = useWebSocketStore((state) => state.status);
  const error = useWebSocketStore((state) => state.error);
  const joinRoom = useWebSocketStore((state) => state.joinRoom);
  const leaveRoom = useWebSocketStore((state) => state.leaveRoom);
  const sendMessage = useWebSocketStore((state) => state.sendMessage);
  const sendTyping = useWebSocketStore((state) => state.sendTyping);
  const subscribe = useWebSocketStore((state) => state.subscribe);

  useEffect(() => {
    if (!options.onEvent) {
      return;
    }

    return subscribe(options.onEvent);
  }, [options.onEvent, subscribe]);

  return {
    status,
    error,
    isConnected: status === "connected",
    joinRoom,
    leaveRoom,
    sendMessage,
    sendTyping,
    subscribe,
  };
}
