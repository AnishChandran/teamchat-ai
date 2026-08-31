import { FirebaseError } from "firebase/app";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User as FirebaseUser,
} from "firebase/auth";
import { create } from "zustand";

import { ApiError, fetchMe } from "../lib/api";
import { auth } from "../lib/firebase";
import { useChatStore } from "./chatStore";
import type { OrganizationSummary, UserSummary } from "../types/auth";

interface AuthState {
  firebaseUser: FirebaseUser | null;
  currentUser: UserSummary | null;
  organization: OrganizationSummary | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  initialize: () => () => void;
  clearError: () => void;
}

async function loadSession(firebaseUser: FirebaseUser) {
  const token = await firebaseUser.getIdToken();
  const me = await fetchMe(token);
  return {
    firebaseUser,
    token,
    currentUser: me.user,
    organization: me.organization,
    error: null as string | null,
  };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return "Your account is not authorized for this application.";
    }
    return "Unable to load your profile. Please try again.";
  }

  if (error instanceof FirebaseError) {
    switch (error.code) {
      case "auth/invalid-credential":
      case "auth/wrong-password":
      case "auth/user-not-found":
        return "Invalid email or password.";
      case "auth/invalid-email":
        return "Please enter a valid email address.";
      case "auth/too-many-requests":
        return "Too many attempts. Please try again later.";
      default:
        return error.message;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong. Please try again.";
}

export const useAuthStore = create<AuthState>((set) => ({
  firebaseUser: null,
  currentUser: null,
  organization: null,
  token: null,
  loading: true,
  error: null,

  clearError: () => set({ error: null }),

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      const credential = await signInWithEmailAndPassword(auth, email, password);
      const session = await loadSession(credential.user);
      set({ ...session, loading: false });
    } catch (error) {
      set({
        firebaseUser: null,
        currentUser: null,
        organization: null,
        token: null,
        loading: false,
        error: getErrorMessage(error),
      });
      throw error;
    }
  },

  logout: async () => {
    set({ loading: true, error: null });
    try {
      await signOut(auth);
    } finally {
      useChatStore.getState().reset();
      set({
        firebaseUser: null,
        currentUser: null,
        organization: null,
        token: null,
        loading: false,
        error: null,
      });
    }
  },

  initialize: () => {
    set({ loading: true });

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        useChatStore.getState().reset();
        set({
          firebaseUser: null,
          currentUser: null,
          organization: null,
          token: null,
          loading: false,
          error: null,
        });
        return;
      }

      try {
        const session = await loadSession(firebaseUser);
        set({ ...session, loading: false });
      } catch (error) {
        await signOut(auth);
        set({
          firebaseUser: null,
          currentUser: null,
          organization: null,
          token: null,
          loading: false,
          error: getErrorMessage(error),
        });
      }
    });

    return unsubscribe;
  },
}));
