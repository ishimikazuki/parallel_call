/**
 * useWebSocket hook tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useWebSocket } from "../../src/hooks/useWebSocket";

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  });

  // Test helpers
  simulateOpen() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }

  static reset() {
    MockWebSocket.instances = [];
  }

  static getLastInstance() {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
}

// Setup global mock
const originalWebSocket = global.WebSocket;

beforeEach(() => {
  MockWebSocket.reset();
  (global as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket as unknown as typeof WebSocket;
});

afterEach(() => {
  global.WebSocket = originalWebSocket;
});

describe("useWebSocket", () => {
  it("does not connect when token is null", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: null,
      })
    );

    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("connects when token is provided", () => {
    renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
      })
    );

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.getLastInstance().url).toBe("ws://test.com/ws?token=test-token");
  });

  it("sets isConnected to true when connection opens", async () => {
    const { result } = renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
      })
    );

    expect(result.current.isConnected).toBe(false);

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
  });

  it("calls onConnect callback when connected", () => {
    const onConnect = vi.fn();

    renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
        onConnect,
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    expect(onConnect).toHaveBeenCalledTimes(1);
  });

  it("updates lastMessage when message is received", async () => {
    const { result } = renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    const testMessage = {
      event: "test_event",
      data: { foo: "bar" },
      timestamp: "2024-01-01T00:00:00Z",
    };

    act(() => {
      MockWebSocket.getLastInstance().simulateMessage(testMessage);
    });

    await waitFor(() => {
      expect(result.current.lastMessage).toEqual(testMessage);
    });
  });

  it("calls onMessage callback with parsed message", () => {
    const onMessage = vi.fn();

    renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
        onMessage,
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    const testMessage = { event: "test", data: {}, timestamp: "2024-01-01T00:00:00Z" };

    act(() => {
      MockWebSocket.getLastInstance().simulateMessage(testMessage);
    });

    expect(onMessage).toHaveBeenCalledWith(testMessage);
  });

  it("sends message when sendMessage is called", () => {
    const { result } = renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    act(() => {
      result.current.sendMessage("test_action", { data: "value" });
    });

    expect(MockWebSocket.getLastInstance().send).toHaveBeenCalledWith(
      JSON.stringify({ action: "test_action", data: "value" })
    );
  });

  it("sets isConnected to false when connection closes", async () => {
    const { result } = renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    expect(result.current.isConnected).toBe(true);

    act(() => {
      MockWebSocket.getLastInstance().simulateClose();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });
  });

  it("calls onDisconnect callback when disconnected", () => {
    const onDisconnect = vi.fn();

    renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
        onDisconnect,
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    act(() => {
      MockWebSocket.getLastInstance().simulateClose();
    });

    expect(onDisconnect).toHaveBeenCalledTimes(1);
  });

  it("cleans up on unmount", () => {
    const { unmount } = renderHook(() =>
      useWebSocket({
        url: "ws://test.com/ws",
        token: "test-token",
      })
    );

    act(() => {
      MockWebSocket.getLastInstance().simulateOpen();
    });

    unmount();

    expect(MockWebSocket.getLastInstance().close).toHaveBeenCalled();
  });
});
