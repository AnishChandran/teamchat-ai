import type { ServerEvent } from "../types/events";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parsePresenceUsers(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((user) => ({
      id: typeof user.id === "string" ? user.id : "",
      name: typeof user.name === "string" ? user.name : "",
    }))
    .filter((user) => user.id.length > 0);
}

export function parseServerEvent(raw: unknown): ServerEvent | null {
  if (!isRecord(raw) || typeof raw.type !== "string") {
    return null;
  }

  switch (raw.type) {
    case "message_created":
      if (!isRecord(raw.message)) {
        return null;
      }
      return raw as unknown as ServerEvent;

    case "presence_updated":
    case "typing_updated": {
      if (!isRecord(raw.payload)) {
        return null;
      }
      const roomId = raw.payload.roomId;
      if (typeof roomId !== "string") {
        return null;
      }
      const users = parsePresenceUsers(raw.payload.users);
      if (raw.type === "presence_updated") {
        return {
          type: "presence_updated",
          payload: { roomId, users },
        };
      }
      return {
        type: "typing_updated",
        payload: { roomId, users },
      };
    }

    case "ai_started":
    case "ai_completed": {
      if (!isRecord(raw.payload)) {
        return null;
      }
      const roomId = raw.payload.roomId;
      const messageId = raw.payload.messageId;
      if (typeof roomId !== "string" || typeof messageId !== "string") {
        return null;
      }
      return {
        type: raw.type,
        payload: { roomId, messageId },
      } as ServerEvent;
    }

    case "ai_chunk": {
      if (!isRecord(raw.payload)) {
        return null;
      }
      const roomId = raw.payload.roomId;
      const messageId = raw.payload.messageId;
      const delta = raw.payload.delta;
      if (
        typeof roomId !== "string" ||
        typeof messageId !== "string" ||
        typeof delta !== "string"
      ) {
        return null;
      }
      return {
        type: "ai_chunk",
        payload: { roomId, messageId, delta },
      };
    }

    case "ai_error": {
      if (!isRecord(raw.payload)) {
        return null;
      }
      const roomId = raw.payload.roomId;
      const messageId = raw.payload.messageId;
      const message = raw.payload.message;
      if (
        typeof roomId !== "string" ||
        typeof messageId !== "string" ||
        typeof message !== "string"
      ) {
        return null;
      }
      return {
        type: "ai_error",
        payload: { roomId, messageId, message },
      };
    }

    case "room_joined":
    case "room_left": {
      const roomId = raw.roomId;
      if (typeof roomId !== "string") {
        return null;
      }
      return {
        type: raw.type,
        roomId,
      } as ServerEvent;
    }

    case "error": {
      const message = raw.message;
      if (typeof message !== "string") {
        return null;
      }
      const roomId = raw.roomId;
      return {
        type: "error",
        message,
        roomId: typeof roomId === "string" ? roomId : undefined,
      };
    }

    default:
      return null;
  }
}
