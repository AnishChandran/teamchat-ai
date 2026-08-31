import type { MeResponse, UserSummary } from "../types/auth";
import type { CreateRoomPayload, RoomSummary } from "../types/chat";
import type { Message, Room } from "../types/domain";

const API_URL = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function authorizedFetch(token: string, path: string): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function fetchMe(token: string): Promise<MeResponse> {
  const response = await authorizedFetch(token, "/api/me");

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || "Failed to load profile");
  }

  return response.json() as Promise<MeResponse>;
}

export async function fetchRooms(token: string): Promise<RoomSummary[]> {
  const response = await authorizedFetch(token, "/api/rooms");

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || "Failed to load rooms");
  }

  const payload = (await response.json()) as { rooms: RoomSummary[] };
  return payload.rooms;
}

export async function fetchRoomMessages(
  token: string,
  roomId: string,
  limit = 50,
): Promise<Message[]> {
  const response = await authorizedFetch(
    token,
    `/api/rooms/${encodeURIComponent(roomId)}/messages?limit=${limit}`,
  );

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || "Failed to load messages");
  }

  const payload = (await response.json()) as { messages: Message[] };
  return payload.messages;
}

export async function createRoom(token: string, payload: CreateRoomPayload): Promise<Room> {
  const response = await fetch(`${API_URL}/api/rooms`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: payload.name,
      description: payload.description,
      memberIds: payload.memberIds ?? [],
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || "Failed to create room");
  }

  return response.json() as Promise<Room>;
}

export async function fetchOrgUsers(token: string): Promise<UserSummary[]> {
  const response = await authorizedFetch(token, "/api/users");

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || "Failed to load users");
  }

  const payload = (await response.json()) as { users: UserSummary[] };
  return payload.users;
}
