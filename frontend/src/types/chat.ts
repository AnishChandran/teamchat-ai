import type { Message, MessageStatus } from "./domain";

export interface CreateRoomPayload {
  name: string;
  description: string;
  memberIds?: string[];
}

export interface RoomSummary {
  id: string;
  name: string;
  description: string;
  createdAt: string;
}

export interface StreamingMessage {
  roomId: string;
  messageId: string;
  senderId: string;
  senderName: string;
  type: "ai";
  content: string;
  createdAt: string;
  status: Extract<MessageStatus, "streaming" | "error">;
  errorMessage?: string;
}

export type ChatMessage = Message | StreamingMessage;

export function isStreamingMessage(message: ChatMessage): message is StreamingMessage {
  return message.status === "streaming" || message.status === "error";
}
