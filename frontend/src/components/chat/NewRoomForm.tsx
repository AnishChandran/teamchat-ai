import { FormEvent, useEffect, useState } from "react";

import { createRoom, fetchOrgUsers } from "../../lib/api";
import { useAuthStore } from "../../store/authStore";
import { useChatStore } from "../../store/chatStore";
import type { UserSummary } from "../../types/auth";
import type { RoomSummary } from "../../types/chat";
import type { Room } from "../../types/domain";

function toRoomSummary(room: Room): RoomSummary {
  return {
    id: room.id,
    name: room.name,
    description: room.description,
    createdAt: room.createdAt,
  };
}

export function NewRoomForm() {
  const token = useAuthStore((state) => state.token);
  const currentUser = useAuthStore((state) => state.currentUser);
  const addRoom = useChatStore((state) => state.addRoom);
  const setActiveRoom = useChatStore((state) => state.setActiveRoom);

  const [expanded, setExpanded] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [orgUsers, setOrgUsers] = useState<UserSummary[]>([]);
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!expanded || !token) {
      return;
    }

    let cancelled = false;
    setLoadingUsers(true);
    setError(null);

    void fetchOrgUsers(token)
      .then((users) => {
        if (!cancelled) {
          setOrgUsers(users);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Failed to load users",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingUsers(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [expanded, token]);

  if (currentUser?.role !== "admin") {
    return null;
  }

  function resetForm() {
    setName("");
    setDescription("");
    setSelectedMemberIds([]);
    setError(null);
  }

  function closeForm() {
    setExpanded(false);
    resetForm();
  }

  function toggleMember(userId: string) {
    setSelectedMemberIds((current) =>
      current.includes(userId)
        ? current.filter((id) => id !== userId)
        : [...current, userId],
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !name.trim()) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const room = await createRoom(token, {
        name: name.trim(),
        description: description.trim(),
        memberIds: selectedMemberIds,
      });
      addRoom(toRoomSummary(room));
      setActiveRoom(room.id);
      closeForm();
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Failed to create room",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const selectableUsers = orgUsers.filter((user) => user.id !== currentUser?.id);

  if (!expanded) {
    return (
      <div className="border-t border-slate-800 px-3 py-3">
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="w-full rounded-lg border border-dashed border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:bg-slate-800/60"
        >
          + New Room
        </button>
      </div>
    );
  }

  return (
    <div className="border-t border-slate-800 px-3 py-3">
      <form onSubmit={handleSubmit} className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          New Room
        </p>
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Room name"
          required
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
        />
        <input
          type="text"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Description (optional)"
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-slate-500 focus:outline-none"
        />

        <fieldset className="space-y-1">
          <legend className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Members
          </legend>
          {loadingUsers ? (
            <p className="text-sm text-slate-500">Loading users…</p>
          ) : selectableUsers.length === 0 ? (
            <p className="text-sm text-slate-500">No other members to add.</p>
          ) : (
            <div className="max-h-32 space-y-1 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/60 p-2">
              {selectableUsers.map((user) => (
                <label
                  key={user.id}
                  className="flex cursor-pointer items-center gap-2 text-sm text-slate-300"
                >
                  <input
                    type="checkbox"
                    checked={selectedMemberIds.includes(user.id)}
                    onChange={() => toggleMember(user.id)}
                    className="rounded border-slate-600 bg-slate-950"
                  />
                  <span>
                    {user.name}
                    <span className="text-slate-500"> ({user.email})</span>
                  </span>
                </label>
              ))}
            </div>
          )}
          <p className="text-xs text-slate-500">You are added automatically.</p>
        </fieldset>

        {error ? <p className="text-xs text-red-400">{error}</p> : null}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting || !name.trim() || loadingUsers}
            className="flex-1 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-900 transition hover:bg-white disabled:opacity-60"
          >
            {submitting ? "Creating…" : "Create"}
          </button>
          <button
            type="button"
            onClick={closeForm}
            disabled={submitting}
            className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
