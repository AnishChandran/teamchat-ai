interface RoomListItemProps {
  id: string;
  name: string;
  isActive: boolean;
  onSelect: (roomId: string) => void;
}

export function RoomListItem({ id, name, isActive, onSelect }: RoomListItemProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
        isActive
          ? "bg-slate-800 font-medium text-slate-100"
          : "text-slate-300 hover:bg-slate-800/60 hover:text-slate-100"
      }`}
    >
      {name}
    </button>
  );
}
