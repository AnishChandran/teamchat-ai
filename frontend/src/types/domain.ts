export type UserRole = "admin" | "member";
export type MessageType = "user" | "ai" | "system";
export type MessageStatus = "streaming" | "complete" | "error";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
}

export interface User {
  id: string;
  firebaseUid: string;
  name: string;
  email: string;
  role: UserRole;
  createdAt: string;
}

export interface Room {
  id: string;
  name: string;
  description: string;
  memberIds: string[];
  createdBy: string;
  createdAt: string;
}

export interface Message {
  id: string;
  senderId: string;
  senderName: string;
  type: MessageType;
  content: string;
  createdAt: string;
  status: MessageStatus;
}
