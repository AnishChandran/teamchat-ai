import { useEffect, useRef } from "react";

import { useAuthStore } from "../store/authStore";
import { useChatStore } from "../store/chatStore";
import { useWebSocketStore } from "../store/websocketStore";

export function useActiveRoom() {
  const token = useAuthStore((state) => state.token);
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const loadMessages = useChatStore((state) => state.loadMessages);
  const joinRoom = useWebSocketStore((state) => state.joinRoom);
  const leaveRoom = useWebSocketStore((state) => state.leaveRoom);
  const previousRoomId = useRef<string | null>(null);

  useEffect(() => {
    if (!token || !activeRoomId) {
      if (previousRoomId.current) {
        leaveRoom(previousRoomId.current);
        previousRoomId.current = null;
      }
      return;
    }

    const previous = previousRoomId.current;
    if (previous && previous !== activeRoomId) {
      leaveRoom(previous);
    }

    joinRoom(activeRoomId);
    void loadMessages(token, activeRoomId);
    previousRoomId.current = activeRoomId;
  }, [token, activeRoomId, loadMessages, joinRoom, leaveRoom]);
}
