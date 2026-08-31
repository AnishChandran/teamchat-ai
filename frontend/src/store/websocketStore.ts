import { create } from "zustand";

import { websocketClient, type ConnectionStatus } from "../lib/websocketClient";
import type { ServerEvent } from "../types/events";

interface WebSocketState {
  status: ConnectionStatus;
  error: string | null;
  connect: (getToken: () => Promise<string>) => void;
  disconnect: () => void;
  joinRoom: (roomId: string) => void;
  leaveRoom: (roomId: string) => void;
  sendMessage: (roomId: string, content: string) => boolean;
  sendTyping: (roomId: string, isTyping: boolean) => void;
  subscribe: (listener: (event: ServerEvent) => void) => () => void;
  onConnected: (listener: () => void) => () => void;
}

let statusUnsubscribe: (() => void) | null = null;

export const useWebSocketStore = create<WebSocketState>((set) => ({
  status: websocketClient.getStatus(),
  error: websocketClient.getError(),

  connect: (getToken) => {
    if (!statusUnsubscribe) {
      statusUnsubscribe = websocketClient.onStatusChange((status, error) => {
        set({ status, error });
      });
    }

    websocketClient.connect(getToken);
  },

  disconnect: () => {
    websocketClient.disconnect();
    set({ status: "idle", error: null });
  },

  joinRoom: (roomId) => {
    websocketClient.joinRoom(roomId);
  },

  leaveRoom: (roomId) => {
    websocketClient.leaveRoom(roomId);
  },

  sendMessage: (roomId, content) => websocketClient.sendMessage(roomId, content),

  sendTyping: (roomId, isTyping) => {
    websocketClient.sendTyping(roomId, isTyping);
  },

  subscribe: (listener) => websocketClient.subscribe(listener),

  onConnected: (listener) => websocketClient.onConnected(listener),
}));
