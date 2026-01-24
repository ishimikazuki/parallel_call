/**
 * Auth store using Zustand
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, AuthTokens } from "../types";
import { authApi, ApiError } from "../api/client";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  fetchCurrentUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const tokens: AuthTokens = await authApi.login(username, password);
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            isLoading: false,
          });

          // Fetch user info
          await get().fetchCurrentUser();
        } catch (err) {
          const message = err instanceof ApiError
            ? "ログインに失敗しました"
            : "ネットワークエラーが発生しました";
          set({ isLoading: false, error: message });
          throw err;
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          error: null,
        });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) {
          get().logout();
          return;
        }

        try {
          const tokens = await authApi.refresh(refreshToken);
          set({
            accessToken: tokens.access_token,
            refreshToken: tokens.refresh_token ?? refreshToken,
          });
        } catch {
          // Refresh failed, logout
          get().logout();
        }
      },

      fetchCurrentUser: async () => {
        const { accessToken } = get();
        if (!accessToken) return;

        try {
          const user = await authApi.me(accessToken);
          set({ user });
        } catch (err) {
          if (err instanceof ApiError && err.status === 401) {
            // Try to refresh token
            await get().refreshAccessToken();
            const newToken = get().accessToken;
            if (newToken) {
              const user = await authApi.me(newToken) as User;
              set({ user });
            }
          }
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);

// Selector hooks for convenience
export const useUser = () => useAuthStore((state) => state.user);
export const useAccessToken = () => useAuthStore((state) => state.accessToken);
export const useIsAuthenticated = () => useAuthStore((state) => !!state.accessToken);
