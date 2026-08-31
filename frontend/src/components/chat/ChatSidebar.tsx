import { NewRoomForm } from "./NewRoomForm";
import { OnlineUsers } from "./OnlineUsers";
import { RoomList } from "./RoomList";

export function ChatSidebar() {
  return (
    <>
      <div className="flex-1 overflow-y-auto px-2 py-3">
        <h2 className="mb-2 px-1 text-xs font-medium uppercase tracking-wide text-slate-500">
          Rooms
        </h2>
        <RoomList />
      </div>
      <OnlineUsers />
      <NewRoomForm />
    </>
  );
}
