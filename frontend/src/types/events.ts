import type { Message } from "./domain";

export interface PresenceUser {
  id: string;
  name: string;
}

// Client → Server

export interface JoinRoomEvent {
  type: "join_room";
  roomId: string;
}

export interface LeaveRoomEvent {
  type: "leave_room";
  roomId: string;
}

export interface SendMessageEvent {
  type: "send_message";
  roomId: string;
  content: string;
}

export interface TypingEvent {
  type: "typing";
  roomId: string;
  isTyping: boolean;
}

export type ClientEvent =
  | JoinRoomEvent
  | LeaveRoomEvent
  | SendMessageEvent
  | TypingEvent;

// Server → Client

export interface MessageCreatedEvent {
  type: "message_created";
  message: Message;
}

export interface PresencePayload {
  roomId: string;
  users: PresenceUser[];
}

export interface PresenceUpdatedEvent {
  type: "presence_updated";
  payload: PresencePayload;
}

export interface TypingPayload {
  roomId: string;
  users: PresenceUser[];
}

export interface TypingUpdatedEvent {
  type: "typing_updated";
  payload: TypingPayload;
}

export interface AiStartedPayload {
  roomId: string;
  messageId: string;
}

export interface AiStartedEvent {
  type: "ai_started";
  payload: AiStartedPayload;
}

export interface AiChunkPayload {
  roomId: string;
  messageId: string;
  delta: string;
}

export interface AiChunkEvent {
  type: "ai_chunk";
  payload: AiChunkPayload;
}

export interface AiCompletedPayload {
  roomId: string;
  messageId: string;
}

export interface AiCompletedEvent {
  type: "ai_completed";
  payload: AiCompletedPayload;
}

export interface AiErrorPayload {
  roomId: string;
  messageId: string;
  message: string;
}

export interface AiErrorEvent {
  type: "ai_error";
  payload: AiErrorPayload;
}

export interface RoomJoinedEvent {
  type: "room_joined";
  roomId: string;
}

export interface RoomLeftEvent {
  type: "room_left";
  roomId: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
  roomId?: string;
}

export type ServerEvent =
  | MessageCreatedEvent
  | PresenceUpdatedEvent
  | TypingUpdatedEvent
  | AiStartedEvent
  | AiChunkEvent
  | AiCompletedEvent
  | AiErrorEvent
  | RoomJoinedEvent
  | RoomLeftEvent
  | ErrorEvent;

export type ParsedServerEvent = ServerEvent | null;
