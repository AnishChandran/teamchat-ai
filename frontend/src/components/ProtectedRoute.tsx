import { Navigate, Outlet } from "react-router-dom";

import { useAuthStore } from "../store/authStore";

export function ProtectedRoute() {
  const loading = useAuthStore((state) => state.loading);
  const token = useAuthStore((state) => state.token);
  const currentUser = useAuthStore((state) => state.currentUser);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <p className="text-slate-400">Loading session...</p>
      </main>
    );
  }

  if (!token || !currentUser) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
