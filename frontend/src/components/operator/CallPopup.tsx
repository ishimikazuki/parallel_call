/**
 * Incoming call popup component
 */

import { useEffect, useState } from "react";
import type { IncomingCall } from "../../types";

interface CallPopupProps {
  call: IncomingCall | null;
  onAccept: () => void;
  onReject: () => void;
  autoAnswerSeconds?: number;
}

export function CallPopup({ call, onAccept, onReject, autoAnswerSeconds = 0 }: CallPopupProps) {
  const [countdown, setCountdown] = useState(autoAnswerSeconds);

  useEffect(() => {
    if (!call || autoAnswerSeconds <= 0) return;

    setCountdown(autoAnswerSeconds);
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onAccept();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [call, autoAnswerSeconds, onAccept]);

  if (!call) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl p-6 w-80 animate-bounce-in">
        {/* Header */}
        <div className="text-center mb-4">
          <div className="w-16 h-16 mx-auto mb-3 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-green-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-gray-800">着信があります</h2>
        </div>

        {/* Call Info */}
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <div className="text-center">
            <p className="text-2xl font-mono font-bold text-gray-800">
              {formatPhoneNumber(call.phone_number)}
            </p>
            {call.name && (
              <p className="text-gray-600 mt-1">{call.name}</p>
            )}
          </div>
        </div>

        {/* Auto-answer countdown */}
        {autoAnswerSeconds > 0 && countdown > 0 && (
          <p className="text-center text-sm text-gray-500 mb-4">
            {countdown}秒後に自動応答します
          </p>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onReject}
            className="flex-1 py-3 px-4 rounded-lg bg-red-100 text-red-600 font-medium hover:bg-red-200 transition-colors"
          >
            拒否
          </button>
          <button
            type="button"
            onClick={onAccept}
            className="flex-1 py-3 px-4 rounded-lg bg-green-500 text-white font-medium hover:bg-green-600 transition-colors"
          >
            応答
          </button>
        </div>
      </div>
    </div>
  );
}

function formatPhoneNumber(phone: string): string {
  // Format Japanese phone number: 090-1234-5678
  const cleaned = phone.replace(/\D/g, "");
  if (cleaned.length === 11 && cleaned.startsWith("0")) {
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7)}`;
  }
  if (cleaned.length === 10 && cleaned.startsWith("0")) {
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  return phone;
}

export default CallPopup;
