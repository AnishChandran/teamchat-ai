import { useCallback, useEffect, useRef } from "react";

import { useWebSocketStore } from "../store/websocketStore";

const TYPING_IDLE_MS = 2_000;

export function useTypingEmitter(roomId: string) {
  const sendTyping = useWebSocketStore((state) => state.sendTyping);
  const isConnected = useWebSocketStore((state) => state.status === "connected");

  const isTyping = useRef(false);
  const idleTimer = useRef<number | null>(null);

  const stopTyping = useCallback(() => {
    if (idleTimer.current !== null) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = null;
    }

    if (!isTyping.current) {
      return;
    }

    isTyping.current = false;
    sendTyping(roomId, false);
  }, [roomId, sendTyping]);

  const onKeystroke = useCallback(
    (content: string) => {
      if (!isConnected) {
        return;
      }

      if (!content.trim()) {
        stopTyping();
        return;
      }

      if (!isTyping.current) {
        isTyping.current = true;
        sendTyping(roomId, true);
      }

      if (idleTimer.current !== null) {
        window.clearTimeout(idleTimer.current);
      }

      idleTimer.current = window.setTimeout(() => {
        stopTyping();
      }, TYPING_IDLE_MS);
    },
    [roomId, isConnected, sendTyping, stopTyping],
  );

  useEffect(() => {
    return () => {
      stopTyping();
    };
  }, [roomId, stopTyping]);

  return { onKeystroke, stopTyping };
}
