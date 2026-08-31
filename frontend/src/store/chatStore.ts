import { create } from "zustand";

import { fetchRoomMessages, fetchRooms } from "../lib/api";
import type { RoomSummary, StreamingMessage } from "../types/chat";
import type { Message } from "../types/domain";
import type { PresenceUser } from "../types/events";

const GEMINI_SENDER_ID = "gemini";
const GEMINI_SENDER_NAME = "Gemini";

interface ChatState {
  rooms: RoomSummary[];
  activeRoomId: string | null;
  messagesByRoom: Record<string, Message[]>;
  presenceByRoom: Record<string, PresenceUser[]>;
  typingByRoom: Record<string, PresenceUser[]>;
  streamingMessages: Record<string, StreamingMessage>;
  loading: boolean;
  error: string | null;
  realtimeError: string | null;
  setRooms: (rooms: RoomSummary[]) => void;
  addRoom: (room: RoomSummary) => void;
  setActiveRoom: (roomId: string | null) => void;
  loadRooms: (token: string) => Promise<void>;
  loadMessages: (token: string, roomId: string) => Promise<void>;
  addMessage: (roomId: string, message: Message) => void;
  startStreamingMessage: (roomId: string, messageId: string) => void;
  updateStreamingMessage: (roomId: string, messageId: string, delta: string) => void;
  completeStreamingMessage: (roomId: string, messageId: string) => void;
  failStreamingMessage: (roomId: string, messageId: string, errorMessage: string) => void;
  setPresence: (roomId: string, users: PresenceUser[]) => void;
  setTypingUsers: (roomId: string, users: PresenceUser[]) => void;
  setRealtimeError: (message: string | null) => void;
  reset: () => void;
}

const initialState = {
  rooms: [] as RoomSummary[],
  activeRoomId: null as string | null,
  messagesByRoom: {} as Record<string, Message[]>,
  presenceByRoom: {} as Record<string, PresenceUser[]>,
  typingByRoom: {} as Record<string, PresenceUser[]>,
  streamingMessages: {} as Record<string, StreamingMessage>,
  loading: false,
  error: null as string | null,
  realtimeError: null as string | null,
};

export function mergeMessages(existing: Message[], incoming: Message[]): Message[] {
  const byId = new Map<string, Message>();
  for (const message of existing) {
    byId.set(message.id, message);
  }
  for (const message of incoming) {
    byId.set(message.id, message);
  }
  return Array.from(byId.values()).sort(
    (left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime(),
  );
}

function createStreamingMessage(roomId: string, messageId: string): StreamingMessage {
  return {
    roomId,
    messageId,
    senderId: GEMINI_SENDER_ID,
    senderName: GEMINI_SENDER_NAME,
    type: "ai",
    content: "",
    createdAt: new Date().toISOString(),
    status: "streaming",
  };
}

export const useChatStore = create<ChatState>((set, get) => ({
  ...initialState,

  setRooms: (rooms) => set({ rooms }),

  addRoom: (room) => {
    set((state) => {
      if (state.rooms.some((entry) => entry.id === room.id)) {
        return state;
      }

      return {
        rooms: [...state.rooms, room].sort((left, right) =>
          left.name.localeCompare(right.name),
        ),
      };
    });
  },

  setActiveRoom: (roomId) => set({ activeRoomId: roomId }),

  loadRooms: async (token) => {
    set({ loading: true, error: null });
    try {
      const rooms = await fetchRooms(token);
      set({ rooms, loading: false });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to load rooms",
      });
    }
  },

  loadMessages: async (token, roomId) => {
    set({ loading: true, error: null });
    try {
      const messages = await fetchRoomMessages(token, roomId);
      set((state) => ({
        messagesByRoom: {
          ...state.messagesByRoom,
          [roomId]: mergeMessages(state.messagesByRoom[roomId] ?? [], messages),
        },
        loading: false,
      }));
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to load messages",
      });
    }
  },

  addMessage: (roomId, message) => {
    set((state) => {
      const existing = state.messagesByRoom[roomId] ?? [];
      if (existing.some((entry) => entry.id === message.id)) {
        return state;
      }

      return {
        messagesByRoom: {
          ...state.messagesByRoom,
          [roomId]: mergeMessages(existing, [message]),
        },
      };
    });
  },

  startStreamingMessage: (roomId, messageId) => {
    set((state) => ({
      streamingMessages: {
        ...state.streamingMessages,
        [messageId]: state.streamingMessages[messageId] ?? createStreamingMessage(roomId, messageId),
      },
    }));
  },

  updateStreamingMessage: (roomId, messageId, delta) => {
    set((state) => {
      const current =
        state.streamingMessages[messageId] ?? createStreamingMessage(roomId, messageId);

      return {
        streamingMessages: {
          ...state.streamingMessages,
          [messageId]: {
            ...current,
            roomId,
            messageId,
            content: current.content + delta,
            status: "streaming",
          },
        },
      };
    });
  },

  completeStreamingMessage: (roomId, messageId) => {
    const state = get();
    const streaming = state.streamingMessages[messageId];

    if (streaming) {
      get().addMessage(roomId, {
        id: messageId,
        senderId: streaming.senderId,
        senderName: streaming.senderName,
        type: "ai",
        content: streaming.content,
        createdAt: streaming.createdAt,
        status: "complete",
      });
    }

    set((current) => {
      if (!current.streamingMessages[messageId]) {
        return current;
      }

      const nextStreaming = { ...current.streamingMessages };
      delete nextStreaming[messageId];
      return { streamingMessages: nextStreaming };
    });
  },

  failStreamingMessage: (roomId, messageId, errorMessage) => {
    set((state) => ({
      streamingMessages: {
        ...state.streamingMessages,
        [messageId]: {
          ...(state.streamingMessages[messageId] ?? createStreamingMessage(roomId, messageId)),
          roomId,
          messageId,
          status: "error",
          errorMessage,
        },
      },
    }));
  },

  setPresence: (roomId, users) => {
    set((state) => ({
      presenceByRoom: {
        ...state.presenceByRoom,
        [roomId]: users,
      },
    }));
  },

  setTypingUsers: (roomId, users) => {
    set((state) => ({
      typingByRoom: {
        ...state.typingByRoom,
        [roomId]: users,
      },
    }));
  },

  setRealtimeError: (message) => set({ realtimeError: message }),

  reset: () => set({ ...initialState }),
}));
