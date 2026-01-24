/**
 * Twilio Voice SDK hook
 *
 * Note: This requires @twilio/voice-sdk to be installed
 * npm install @twilio/voice-sdk
 */

import { useCallback, useEffect, useRef, useState } from "react";

// Twilio types (will be fully typed when @twilio/voice-sdk is installed)
interface TwilioDevice {
  register: () => Promise<void>;
  unregister: () => Promise<void>;
  destroy: () => void;
  on: (event: string, handler: (...args: unknown[]) => void) => void;
  off: (event: string, handler: (...args: unknown[]) => void) => void;
  calls: Map<string, TwilioCall>;
}

interface TwilioCall {
  accept: () => void;
  reject: () => void;
  disconnect: () => void;
  mute: (muted: boolean) => void;
  isMuted: () => boolean;
  parameters: {
    CallSid: string;
    From: string;
    To: string;
  };
  on: (event: string, handler: (...args: unknown[]) => void) => void;
}

type DeviceState = "offline" | "registering" | "registered" | "error";

interface UseTwilioDeviceOptions {
  token: string | null;
  onIncomingCall?: (call: TwilioCall) => void;
  onCallAccepted?: (call: TwilioCall) => void;
  onCallDisconnected?: (call: TwilioCall) => void;
  onError?: (error: Error) => void;
}

interface UseTwilioDeviceReturn {
  state: DeviceState;
  currentCall: TwilioCall | null;
  isMuted: boolean;
  acceptCall: () => void;
  rejectCall: () => void;
  hangUp: () => void;
  toggleMute: () => void;
  register: () => Promise<void>;
  unregister: () => Promise<void>;
}

export function useTwilioDevice({
  token,
  onIncomingCall,
  onCallAccepted,
  onCallDisconnected,
  onError,
}: UseTwilioDeviceOptions): UseTwilioDeviceReturn {
  const [state, setState] = useState<DeviceState>("offline");
  const [currentCall, setCurrentCall] = useState<TwilioCall | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const deviceRef = useRef<TwilioDevice | null>(null);
  const pendingCallRef = useRef<TwilioCall | null>(null);

  // Initialize device
  useEffect(() => {
    if (!token) {
      setState("offline");
      return;
    }

    const initDevice = async () => {
      try {
        // Dynamic import to avoid SSR issues
        const { Device, Call } = await import("@twilio/voice-sdk");

        const device = new Device(token, {
          codecPreferences: [Call.Codec.Opus, Call.Codec.PCMU],
          enableRingingState: true,
        });

        // Device events
        device.on("registered", () => {
          setState("registered");
        });

        device.on("unregistered", () => {
          setState("offline");
        });

        device.on("error", (error: Error) => {
          setState("error");
          onError?.(error);
        });

        device.on("incoming", (call: TwilioCall) => {
          pendingCallRef.current = call;

          // Call events
          call.on("accept", () => {
            setCurrentCall(call);
            pendingCallRef.current = null;
            onCallAccepted?.(call);
          });

          call.on("disconnect", () => {
            setCurrentCall(null);
            setIsMuted(false);
            onCallDisconnected?.(call);
          });

          call.on("cancel", () => {
            pendingCallRef.current = null;
            setCurrentCall(null);
          });

          onIncomingCall?.(call);
        });

        deviceRef.current = device as unknown as TwilioDevice;

        // Register the device
        setState("registering");
        await device.register();
      } catch (error) {
        setState("error");
        onError?.(error as Error);
      }
    };

    initDevice();

    return () => {
      if (deviceRef.current) {
        deviceRef.current.destroy();
        deviceRef.current = null;
      }
    };
  }, [token, onIncomingCall, onCallAccepted, onCallDisconnected, onError]);

  const acceptCall = useCallback(() => {
    if (pendingCallRef.current) {
      pendingCallRef.current.accept();
    }
  }, []);

  const rejectCall = useCallback(() => {
    if (pendingCallRef.current) {
      pendingCallRef.current.reject();
      pendingCallRef.current = null;
    }
  }, []);

  const hangUp = useCallback(() => {
    if (currentCall) {
      currentCall.disconnect();
    }
  }, [currentCall]);

  const toggleMute = useCallback(() => {
    if (currentCall) {
      const newMuted = !currentCall.isMuted();
      currentCall.mute(newMuted);
      setIsMuted(newMuted);
    }
  }, [currentCall]);

  const register = useCallback(async () => {
    if (deviceRef.current) {
      setState("registering");
      await deviceRef.current.register();
    }
  }, []);

  const unregister = useCallback(async () => {
    if (deviceRef.current) {
      await deviceRef.current.unregister();
    }
  }, []);

  return {
    state,
    currentCall,
    isMuted,
    acceptCall,
    rejectCall,
    hangUp,
    toggleMute,
    register,
    unregister,
  };
}

export default useTwilioDevice;
