import { formatTypingLabel } from "../../lib/formatTypingLabel";
import { useAuthStore } from "../../store/authStore";
import { useChatStore } from "../../store/chatStore";

interface TypingIndicatorProps {
  roomId: string;
}

export function TypingIndicator({ roomId }: TypingIndicatorProps) {
  const currentUser = useAuthStore((state) => state.currentUser);
  const typingByRoom = useChatStore((state) => state.typingByRoom);

  const names = (typingByRoom[roomId] ?? [])
    .filter((user) => user.id !== currentUser?.id)
    .map((user) => user.name);

  const label = formatTypingLabel(names);
  if (!label) {
    return null;
  }

  return (
    <p className="shrink-0 px-4 py-1 text-xs italic text-slate-500">{label}</p>
  );
}
