import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { handleChatServerEvent } from "./lib/chatEventHandler";
import { SESSION_EXPIRED_MESSAGE } from "./lib/websocketClient";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ChatPage } from "./pages/ChatPage";
import { LoginPage } from "./pages/LoginPage";
import { useAuthStore } from "./store/authStore";
import { useChatStore } from "./store/chatStore";
import { useWebSocketStore } from "./store/websocketStore";

function AppRoutes() {
  const navigate = useNavigate();
  const initialize = useAuthStore((state) => state.initialize);
  const loading = useAuthStore((state) => state.loading);
  const token = useAuthStore((state) => state.token);
  const currentUser = useAuthStore((state) => state.currentUser);
  const firebaseUser = useAuthStore((state) => state.firebaseUser);
  const logout = useAuthStore((state) => state.logout);
  const wsStatus = useWebSocketStore((state) => state.status);
  const wsError = useWebSocketStore((state) => state.error);
  const connectWebSocket = useWebSocketStore((state) => state.connect);
  const disconnectWebSocket = useWebSocketStore((state) => state.disconnect);
  const subscribeWebSocket = useWebSocketStore((state) => state.subscribe);
  const onConnected = useWebSocketStore((state) => state.onConnected);

  useEffect(() => {
    const unsubscribe = initialize();
    return unsubscribe;
  }, [initialize]);

  useEffect(() => {
    if (!token) {
      return;
    }

    return subscribeWebSocket(handleChatServerEvent);
  }, [token, subscribeWebSocket]);

  useEffect(() => {
    if (!token || !firebaseUser) {
      disconnectWebSocket();
      return;
    }

    connectWebSocket(() => firebaseUser.getIdToken(true));
    return () => {
      disconnectWebSocket();
    };
  }, [token, firebaseUser, connectWebSocket, disconnectWebSocket]);

  useEffect(() => {
    if (wsStatus !== "disconnected" || wsError !== SESSION_EXPIRED_MESSAGE) {
      return;
    }

    void logout().then(() => {
      navigate("/login", { replace: true });
    });
  }, [wsStatus, wsError, logout, navigate]);

  useEffect(() => {
    return onConnected(() => {
      const activeToken = useAuthStore.getState().token;
      const activeRoomId = useChatStore.getState().activeRoomId;
      if (activeToken && activeRoomId) {
        void useChatStore.getState().loadMessages(activeToken, activeRoomId);
      }
    });
  }, [onConnected]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
        <p className="text-slate-400">Loading session...</p>
      </main>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          token && currentUser ? (
            <Navigate to="/chat" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<ChatPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
