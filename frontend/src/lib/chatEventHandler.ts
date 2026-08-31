import { useAuthStore } from "../store/authStore";
import { useChatStore } from "../store/chatStore";
import type { ServerEvent } from "../types/events";

export function handleChatServerEvent(event: ServerEvent): void {
  const chatStore = useChatStore.getState();

  switch (event.type) {
    case "message_created": {
      const roomId = chatStore.activeRoomId;
      if (roomId) {
        chatStore.addMessage(roomId, event.message);
        chatStore.setRealtimeError(null);
      }
      break;
    }

    case "presence_updated":
      chatStore.setPresence(event.payload.roomId, event.payload.users);
      break;

    case "typing_updated":
      chatStore.setTypingUsers(event.payload.roomId, event.payload.users);
      break;

    case "ai_started":
      chatStore.startStreamingMessage(event.payload.roomId, event.payload.messageId);
      break;

    case "ai_chunk":
      chatStore.updateStreamingMessage(
        event.payload.roomId,
        event.payload.messageId,
        event.payload.delta,
      );
      break;

    case "ai_completed": {
      const { roomId, messageId } = event.payload;
      const hadStreaming = Boolean(chatStore.streamingMessages[messageId]);
      chatStore.completeStreamingMessage(roomId, messageId);
      if (!hadStreaming) {
        void reloadMessages(roomId);
      }
      break;
    }

    case "ai_error":
      chatStore.failStreamingMessage(
        event.payload.roomId,
        event.payload.messageId,
        event.payload.message,
      );
      break;

    case "error":
      chatStore.setRealtimeError(event.message);
      break;

    default:
      break;
  }
}

async function reloadMessages(roomId: string): Promise<void> {
  const token = useAuthStore.getState().token;
  if (!token) {
    return;
  }

  await useChatStore.getState().loadMessages(token, roomId);
}
