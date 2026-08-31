import { useNavigate } from "react-router-dom";

import { useAuthStore } from "../../store/authStore";

export function ChatHeader() {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.currentUser);
  const organization = useAuthStore((state) => state.organization);
  const logout = useAuthStore((state) => state.logout);
  const loading = useAuthStore((state) => state.loading);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-800 bg-slate-900 px-4 py-3">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-slate-100">TeamChat AI</h1>
        <p className="text-sm text-slate-400">{organization?.name ?? "Organization"}</p>
      </div>

      <div className="flex items-center gap-3">
        <span className="hidden text-sm text-slate-300 sm:inline">
          {currentUser?.name ?? "User"}
        </span>
        <button
          type="button"
          onClick={handleLogout}
          disabled={loading}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-200 transition hover:border-slate-500 hover:bg-slate-800 disabled:opacity-60"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
