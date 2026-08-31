import { parseServerEvent } from "./parseServerEvent";
import type { ClientEvent, ServerEvent } from "../types/events";

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting";

type EventListener = (event: ServerEvent) => void;
type StatusListener = (status: ConnectionStatus, error: string | null) => void;
type ConnectedListener = () => void;
type TokenProvider = () => Promise<string>;

export const SESSION_EXPIRED_MESSAGE = "Session expired. Please sign in again.";

const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;

function getWebSocketBaseUrl(): string {
  const configured = import.meta.env.VITE_WS_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}`;
  }

  return "ws://localhost:5173";
}

export class WebSocketClient {
  private socket: WebSocket | null = null;
  private tokenProvider: TokenProvider | null = null;
  private status: ConnectionStatus = "idle";
  private error: string | null = null;
  private joinedRoomIds = new Set<string>();
  private reconnectAttempt = 0;
  private reconnectTimer: number | null = null;
  private shouldReconnect = false;
  private readonly eventListeners = new Set<EventListener>();
  private readonly statusListeners = new Set<StatusListener>();
  private readonly connectedListeners = new Set<ConnectedListener>();

  connect(tokenProvider: TokenProvider): void {
    this.tokenProvider = tokenProvider;
    this.shouldReconnect = true;
    this.clearReconnectTimer();
    void this.openConnection();
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.clearReconnectTimer();
    this.closeSocket();
    this.joinedRoomIds.clear();
    this.reconnectAttempt = 0;
    this.setStatus("idle", null);
  }

  joinRoom(roomId: string): void {
    this.joinedRoomIds.add(roomId);
    this.sendClientEvent({ type: "join_room", roomId });
  }

  leaveRoom(roomId: string): void {
    this.joinedRoomIds.delete(roomId);
    this.sendClientEvent({ type: "leave_room", roomId });
  }

  sendMessage(roomId: string, content: string): boolean {
    return this.sendClientEvent({ type: "send_message", roomId, content });
  }

  sendTyping(roomId: string, isTyping: boolean): void {
    this.sendClientEvent({ type: "typing", roomId, isTyping });
  }

  subscribe(listener: EventListener): () => void {
    this.eventListeners.add(listener);
    return () => {
      this.eventListeners.delete(listener);
    };
  }

  onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.status, this.error);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  onConnected(listener: ConnectedListener): () => void {
    this.connectedListeners.add(listener);
    return () => {
      this.connectedListeners.delete(listener);
    };
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  getError(): string | null {
    return this.error;
  }

  private async openConnection(): Promise<void> {
    if (!this.tokenProvider || !this.shouldReconnect) {
      return;
    }

    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.setStatus(this.reconnectAttempt > 0 ? "reconnecting" : "connecting", null);

    try {
      const token = await this.tokenProvider();
      const url = `${getWebSocketBaseUrl()}/ws?token=${encodeURIComponent(token)}`;
      const socket = new WebSocket(url);
      this.socket = socket;

      socket.onopen = () => {
        this.reconnectAttempt = 0;
        this.setStatus("connected", null);
        this.rejoinTrackedRooms();
        for (const listener of this.connectedListeners) {
          listener();
        }
      };

      socket.onmessage = (messageEvent) => {
        this.handleMessage(messageEvent.data);
      };

      socket.onerror = () => {
        if (this.status !== "connected") {
          this.setStatus(this.status, "WebSocket connection error");
        }
      };

      socket.onclose = (closeEvent) => {
        this.socket = null;

        if (!this.shouldReconnect) {
          this.setStatus("idle", null);
          return;
        }

        if (closeEvent.code === 1008) {
          this.shouldReconnect = false;
          this.setStatus("disconnected", SESSION_EXPIRED_MESSAGE);
          return;
        }

        this.setStatus("disconnected", "Connection lost. Reconnecting...");
        this.scheduleReconnect();
      };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to connect to realtime service";
      this.setStatus("disconnected", message);
      this.scheduleReconnect();
    }
  }

  private handleMessage(raw: unknown): void {
    if (typeof raw !== "string") {
      return;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      console.warn("Ignored invalid WebSocket payload");
      return;
    }

    const event = parseServerEvent(parsed);
    if (!event) {
      console.warn("Ignored unknown WebSocket event", parsed);
      return;
    }

    for (const listener of this.eventListeners) {
      listener(event);
    }
  }

  private sendClientEvent(event: ClientEvent): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket is not connected; dropped client event", event.type);
      return false;
    }

    this.socket.send(JSON.stringify(event));
    return true;
  }

  private rejoinTrackedRooms(): void {
    for (const roomId of this.joinedRoomIds) {
      this.sendClientEvent({ type: "join_room", roomId });
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer !== null) {
      return;
    }

    const delay = Math.min(
      INITIAL_BACKOFF_MS * 2 ** this.reconnectAttempt,
      MAX_BACKOFF_MS,
    );
    this.reconnectAttempt += 1;
    this.setStatus("reconnecting", this.error);

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      void this.openConnection();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private closeSocket(): void {
    if (!this.socket) {
      return;
    }

    this.socket.onopen = null;
    this.socket.onmessage = null;
    this.socket.onerror = null;
    this.socket.onclose = null;
    this.socket.close();
    this.socket = null;
  }

  private setStatus(status: ConnectionStatus, error: string | null): void {
    this.status = status;
    this.error = error;
    for (const listener of this.statusListeners) {
      listener(status, error);
    }
  }
}

export const websocketClient = new WebSocketClient();
