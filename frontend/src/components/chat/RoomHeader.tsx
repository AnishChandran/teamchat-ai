import { useChatStore } from "../../store/chatStore";

export function RoomHeader() {
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const rooms = useChatStore((state) => state.rooms);

  const room = rooms.find((entry) => entry.id === activeRoomId);

  if (!room) {
    return (
      <div className="shrink-0 border-b border-slate-800 px-4 py-3">
        <h2 className="text-lg font-medium text-slate-300">Select a room</h2>
      </div>
    );
  }

  return (
    <div className="shrink-0 border-b border-slate-800 px-4 py-3">
      <h2 className="text-lg font-medium text-slate-100">{room.name}</h2>
      {room.description ? (
        <p className="mt-1 text-sm text-slate-400">{room.description}</p>
      ) : null}
    </div>
  );
}
