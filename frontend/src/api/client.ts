/**
 * API client for ParallelDialer backend
 */

import type { AuthTokens, TokenRefreshResponse, User } from "../types";

const API_BASE = "/api/v1";

interface RequestOptions extends RequestInit {
  token?: string;
}

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, response.statusText, data);
  }

  return response.json();
}

// Auth API
export const authApi = {
  login: async (username: string, password: string): Promise<AuthTokens> => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!response.ok) {
      throw new ApiError(response.status, response.statusText, await response.json());
    }

    return response.json() as Promise<AuthTokens>;
  },

  refresh: (refreshToken: string) =>
    request<TokenRefreshResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  me: (token: string) => request<User>("/auth/me", { token }),
};

// Campaign API
export const campaignApi = {
  list: (token: string) =>
    request<import("../types").Campaign[]>("/campaigns", { token }),

  get: (token: string, id: string) =>
    request<import("../types").Campaign>(`/campaigns/${id}`, { token }),

  create: (token: string, data: { name: string; description?: string; dial_ratio?: number }) =>
    request<import("../types").Campaign>("/campaigns", {
      method: "POST",
      body: JSON.stringify(data),
      token,
    }),

  start: (token: string, id: string) =>
    request<import("../types").Campaign>(`/campaigns/${id}/start`, {
      method: "POST",
      token,
    }),

  pause: (token: string, id: string) =>
    request<import("../types").Campaign>(`/campaigns/${id}/pause`, {
      method: "POST",
      token,
    }),

  resume: (token: string, id: string) =>
    request<import("../types").Campaign>(`/campaigns/${id}/resume`, {
      method: "POST",
      token,
    }),

  stop: (token: string, id: string) =>
    request<import("../types").Campaign>(`/campaigns/${id}/stop`, {
      method: "POST",
      token,
    }),

  getStats: (token: string, id: string) =>
    request<import("../types").CampaignStats>(`/campaigns/${id}/stats`, { token }),

  addLead: (token: string, campaignId: string, data: { phone_number: string; name?: string }) =>
    request<import("../types").Lead>(`/campaigns/${campaignId}/leads`, {
      method: "POST",
      body: JSON.stringify(data),
      token,
    }),

  getLeads: (token: string, campaignId: string) =>
    request<import("../types").Lead[]>(`/campaigns/${campaignId}/leads`, { token }),

  importLeads: async (token: string, campaignId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/campaigns/${campaignId}/leads/import`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    if (!response.ok) {
      throw new ApiError(response.status, response.statusText, await response.json());
    }

    return response.json() as Promise<import("../types").ImportResult>;
  },
};

export { ApiError };
