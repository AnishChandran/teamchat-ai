import { useChatStore } from "../../store/chatStore";

export function OnlineUsers() {
  const activeRoomId = useChatStore((state) => state.activeRoomId);
  const presenceByRoom = useChatStore((state) => state.presenceByRoom);

  const users = activeRoomId ? (presenceByRoom[activeRoomId] ?? []) : [];

  return (
    <div className="border-t border-slate-800 px-3 py-3">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
        Online
      </h3>
      {!activeRoomId ? (
        <p className="text-sm text-slate-500">Select a room</p>
      ) : users.length === 0 ? (
        <p className="text-sm text-slate-500">No one online</p>
      ) : (
        <ul className="space-y-1">
          {users.map((user) => (
            <li key={user.id} className="flex items-center gap-2 text-sm text-slate-300">
              <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-500" />
              {user.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
