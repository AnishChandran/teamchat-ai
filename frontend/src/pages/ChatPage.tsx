import { useEffect } from "react";

import { useActiveRoom } from "../hooks/useActiveRoom";
import { useAuthStore } from "../store/authStore";
import { useChatStore } from "../store/chatStore";
import { ChatLayout } from "../components/chat/ChatLayout";
import { ChatMain } from "../components/chat/ChatMain";
import { ChatSidebar } from "../components/chat/ChatSidebar";

export function ChatPage() {
  const token = useAuthStore((state) => state.token);
  const rooms = useChatStore((state) => state.rooms);
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const loadRooms = useChatStore((state) => state.loadRooms);
  const setActiveRoom = useChatStore((state) => state.setActiveRoom);
  const loading = useChatStore((state) => state.loading);
  const error = useChatStore((state) => state.error);

  useActiveRoom();

  useEffect(() => {
    if (!token) {
      return;
    }

    void loadRooms(token);
  }, [token, loadRooms]);

  useEffect(() => {
    if (rooms.length > 0 && !activeRoomId) {
      setActiveRoom(rooms[0].id);
    }
  }, [rooms, activeRoomId, setActiveRoom]);

  return (
    <ChatLayout
      sidebar={
        <>
          {loading && rooms.length === 0 ? (
            <p className="px-3 py-4 text-sm text-slate-500">Loading rooms…</p>
          ) : null}
          {error && rooms.length === 0 ? (
            <p className="px-3 py-4 text-sm text-red-400">{error}</p>
          ) : null}
          <ChatSidebar />
        </>
      }
      main={<ChatMain />}
    />
  );
}
