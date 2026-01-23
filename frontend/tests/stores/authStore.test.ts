/**
 * Auth store tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act } from "@testing-library/react";
import { useAuthStore } from "../../src/stores/authStore";

// Mock the API client
vi.mock("../../src/api/client", () => ({
  authApi: {
    login: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      public data: unknown
    ) {
      super(`API Error: ${status} ${statusText}`);
      this.name = "ApiError";
    }
  },
}));

import { authApi, ApiError } from "../../src/api/client";

describe("authStore", () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      error: null,
    });

    // Clear mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("initial state", () => {
    it("has null user initially", () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it("has null tokens initially", () => {
      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
    });

    it("is not loading initially", () => {
      const state = useAuthStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it("has no error initially", () => {
      const state = useAuthStore.getState();
      expect(state.error).toBeNull();
    });
  });

  describe("login", () => {
    it("sets isLoading to true during login", async () => {
      const loginMock = vi.mocked(authApi.login);
      loginMock.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      const loginPromise = useAuthStore.getState().login("user", "pass");

      // Check loading state immediately
      expect(useAuthStore.getState().isLoading).toBe(true);

      // Wait for login to complete (it will fail since we didn't resolve properly)
      await loginPromise.catch(() => {});
    });

    it("stores tokens on successful login", async () => {
      const loginMock = vi.mocked(authApi.login);
      const meMock = vi.mocked(authApi.me);

      loginMock.mockResolvedValue({
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
        token_type: "bearer",
      });

      meMock.mockResolvedValue({
        id: "user-1",
        username: "testuser",
        email: "test@example.com",
        role: "operator",
        is_active: true,
      });

      await act(async () => {
        await useAuthStore.getState().login("testuser", "password");
      });

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe("test-access-token");
      expect(state.refreshToken).toBe("test-refresh-token");
      expect(state.isLoading).toBe(false);
    });

    it("fetches user info after successful login", async () => {
      const loginMock = vi.mocked(authApi.login);
      const meMock = vi.mocked(authApi.me);

      loginMock.mockResolvedValue({
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
        token_type: "bearer",
      });

      const mockUser = {
        id: "user-1",
        username: "testuser",
        email: "test@example.com",
        role: "operator" as const,
        is_active: true,
      };

      meMock.mockResolvedValue(mockUser);

      await act(async () => {
        await useAuthStore.getState().login("testuser", "password");
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(meMock).toHaveBeenCalledWith("test-access-token");
    });

    it("sets error on login failure", async () => {
      const loginMock = vi.mocked(authApi.login);
      loginMock.mockRejectedValue(new ApiError(401, "Unauthorized", {}));

      await act(async () => {
        try {
          await useAuthStore.getState().login("wrong", "credentials");
        } catch {
          // Expected
        }
      });

      const state = useAuthStore.getState();
      expect(state.error).toBe("ログインに失敗しました");
      expect(state.isLoading).toBe(false);
    });
  });

  describe("logout", () => {
    it("clears all auth state", async () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: { id: "1", username: "test", email: null, role: "operator", is_active: true },
        accessToken: "token",
        refreshToken: "refresh",
        error: "some error",
      });

      await act(async () => {
        useAuthStore.getState().logout();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe("refreshAccessToken", () => {
    it("updates tokens on successful refresh", async () => {
      const refreshMock = vi.mocked(authApi.refresh);

      useAuthStore.setState({
        accessToken: "old-access-token",
        refreshToken: "old-refresh-token",
      });

      refreshMock.mockResolvedValue({
        access_token: "new-access-token",
        refresh_token: "new-refresh-token",
        token_type: "bearer",
      });

      await act(async () => {
        await useAuthStore.getState().refreshAccessToken();
      });

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe("new-access-token");
      expect(state.refreshToken).toBe("new-refresh-token");
    });

    it("logs out on refresh failure", async () => {
      const refreshMock = vi.mocked(authApi.refresh);

      useAuthStore.setState({
        user: { id: "1", username: "test", email: null, role: "operator", is_active: true },
        accessToken: "access-token",
        refreshToken: "refresh-token",
      });

      refreshMock.mockRejectedValue(new ApiError(401, "Unauthorized", {}));

      await act(async () => {
        await useAuthStore.getState().refreshAccessToken();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
    });

    it("logs out if no refresh token", async () => {
      useAuthStore.setState({
        user: { id: "1", username: "test", email: null, role: "operator", is_active: true },
        accessToken: "access-token",
        refreshToken: null,
      });

      await act(async () => {
        await useAuthStore.getState().refreshAccessToken();
      });

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
    });
  });

  describe("clearError", () => {
    it("clears error state", () => {
      useAuthStore.setState({ error: "some error" });

      act(() => {
        useAuthStore.getState().clearError();
      });

      expect(useAuthStore.getState().error).toBeNull();
    });
  });
});
