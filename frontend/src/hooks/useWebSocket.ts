/**
 * WebSocket hook for real-time communication
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage, WSEventType } from "../types";

interface UseWebSocketOptions {
  url: string;
  token: string | null;
  onMessage?: (message: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WSMessage | null;
  sendMessage: (action: string, data?: Record<string, unknown>) => void;
  reconnect: () => void;
}

export function useWebSocket({
  url,
  token,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (!token) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `${url}?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSMessage;
        setLastMessage(message);
        onMessage?.(message);
      } catch {
        console.error("Failed to parse WebSocket message:", event.data);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      onDisconnect?.();

      // Auto-reconnect
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectTimeoutRef.current = window.setTimeout(() => {
          reconnectAttemptsRef.current += 1;
          connect();
        }, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      onError?.(error);
    };

    wsRef.current = ws;
  }, [url, token, onMessage, onConnect, onDisconnect, onError, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((action: string, data: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, ...data }));
    }
  }, []);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    disconnect();
    connect();
  }, [disconnect, connect]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Ping/pong heartbeat
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      sendMessage("ping");
    }, 30000);

    return () => clearInterval(pingInterval);
  }, [isConnected, sendMessage]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect,
  };
}

// Typed hooks for specific WebSocket endpoints
export function useOperatorWebSocket(
  token: string | null,
  handlers?: {
    onIncomingCall?: (data: WSMessage["data"]) => void;
    onCallConnected?: (data: WSMessage["data"]) => void;
    onCallEnded?: (data: WSMessage["data"]) => void;
  }
) {
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.event) {
      case "incoming_call":
        handlers?.onIncomingCall?.(message.data);
        break;
      case "call_connected":
        handlers?.onCallConnected?.(message.data);
        break;
      case "call_ended":
        handlers?.onCallEnded?.(message.data);
        break;
    }
  }, [handlers]);

  const wsUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/operator`;

  return useWebSocket({
    url: wsUrl,
    token,
    onMessage: handleMessage,
  });
}

export function useDashboardWebSocket(
  token: string | null,
  handlers?: {
    onCampaignStatsUpdated?: (data: WSMessage["data"]) => void;
    onOperatorListUpdated?: (data: WSMessage["data"]) => void;
    onAlert?: (data: WSMessage["data"]) => void;
  }
) {
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.event) {
      case "campaign_stats_updated":
        handlers?.onCampaignStatsUpdated?.(message.data);
        break;
      case "operator_list_updated":
        handlers?.onOperatorListUpdated?.(message.data);
        break;
      case "alert":
        handlers?.onAlert?.(message.data);
        break;
    }
  }, [handlers]);

  const wsUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/dashboard`;

  return useWebSocket({
    url: wsUrl,
    token,
    onMessage: handleMessage,
  });
}
