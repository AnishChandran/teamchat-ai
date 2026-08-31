export function formatTypingLabel(names: string[]): string | null {
  if (names.length === 0) {
    return null;
  }

  if (names.length === 1) {
    return `${names[0]} is typing…`;
  }

  if (names.length === 2) {
    return `${names[0]} and ${names[1]} are typing…`;
  }

  const leading = names.slice(0, -1).join(", ");
  const last = names[names.length - 1];
  return `${leading} and ${last} are typing…`;
}
