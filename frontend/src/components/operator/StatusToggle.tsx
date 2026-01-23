/**
 * Operator status toggle component
 */

import { useState } from "react";
import type { OperatorStatus } from "../../types";

interface StatusToggleProps {
  currentStatus: OperatorStatus;
  onStatusChange: (status: OperatorStatus) => void;
  disabled?: boolean;
}

const STATUS_CONFIG: Record<OperatorStatus, { label: string; color: string; bgColor: string }> = {
  offline: { label: "オフライン", color: "text-gray-600", bgColor: "bg-gray-100" },
  available: { label: "対応可能", color: "text-green-600", bgColor: "bg-green-100" },
  on_call: { label: "通話中", color: "text-blue-600", bgColor: "bg-blue-100" },
  on_break: { label: "休憩中", color: "text-yellow-600", bgColor: "bg-yellow-100" },
  wrap_up: { label: "後処理中", color: "text-purple-600", bgColor: "bg-purple-100" },
};

const SELECTABLE_STATUSES: OperatorStatus[] = ["offline", "available", "on_break"];

export function StatusToggle({ currentStatus, onStatusChange, disabled = false }: StatusToggleProps) {
  const [isOpen, setIsOpen] = useState(false);
  const config = STATUS_CONFIG[currentStatus];

  // on_call と wrap_up は手動選択不可
  const isManuallyChangeable = SELECTABLE_STATUSES.includes(currentStatus);

  const handleSelect = (status: OperatorStatus) => {
    if (status !== currentStatus) {
      onStatusChange(status);
    }
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => isManuallyChangeable && !disabled && setIsOpen(!isOpen)}
        disabled={disabled || !isManuallyChangeable}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-medium
          ${config.bgColor} ${config.color}
          ${isManuallyChangeable && !disabled ? "cursor-pointer hover:opacity-80" : "cursor-not-allowed"}
          transition-opacity
        `}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span
          className={`w-2 h-2 rounded-full ${
            currentStatus === "available" ? "bg-green-500 animate-pulse" :
            currentStatus === "on_call" ? "bg-blue-500" :
            "bg-gray-400"
          }`}
        />
        {config.label}
        {isManuallyChangeable && !disabled && (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <ul
            className="absolute top-full left-0 mt-1 w-40 bg-white rounded-lg shadow-lg border z-20"
            role="listbox"
          >
            {SELECTABLE_STATUSES.map((status) => {
              const statusConfig = STATUS_CONFIG[status];
              return (
                <li key={status}>
                  <button
                    type="button"
                    onClick={() => handleSelect(status)}
                    className={`
                      w-full px-4 py-2 text-left flex items-center gap-2
                      hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg
                      ${status === currentStatus ? "bg-gray-50" : ""}
                    `}
                    role="option"
                    aria-selected={status === currentStatus}
                  >
                    <span className={`w-2 h-2 rounded-full ${
                      status === "available" ? "bg-green-500" :
                      status === "on_break" ? "bg-yellow-500" :
                      "bg-gray-400"
                    }`} />
                    <span className={statusConfig.color}>{statusConfig.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

export default StatusToggle;
