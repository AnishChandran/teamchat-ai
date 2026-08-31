import { useChatStore } from "../../store/chatStore";
import { RoomListItem } from "./RoomListItem";

export function RoomList() {
  const rooms = useChatStore((state) => state.rooms);
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const setActiveRoom = useChatStore((state) => state.setActiveRoom);

  if (rooms.length === 0) {
    return (
      <p className="px-3 py-2 text-sm text-slate-500">No rooms yet.</p>
    );
  }

  return (
    <nav className="space-y-1">
      {rooms.map((room) => (
        <RoomListItem
          key={room.id}
          id={room.id}
          name={room.name}
          isActive={room.id === activeRoomId}
          onSelect={setActiveRoom}
        />
      ))}
    </nav>
  );
}
