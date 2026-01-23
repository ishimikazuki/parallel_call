/**
 * Real-time operator list component
 */

import type { Operator, OperatorStatus } from "../../types";

interface OperatorListProps {
  operators: Operator[];
  isLoading?: boolean;
}

const STATUS_CONFIG: Record<OperatorStatus, { label: string; color: string; bgColor: string }> = {
  offline: { label: "オフライン", color: "text-gray-600", bgColor: "bg-gray-100" },
  available: { label: "対応可能", color: "text-green-600", bgColor: "bg-green-100" },
  on_call: { label: "通話中", color: "text-blue-600", bgColor: "bg-blue-100" },
  on_break: { label: "休憩中", color: "text-yellow-600", bgColor: "bg-yellow-100" },
  wrap_up: { label: "後処理中", color: "text-purple-600", bgColor: "bg-purple-100" },
};

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return `${minutes}分${remainingSeconds > 0 ? `${remainingSeconds}秒` : ""}`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}時間${remainingMinutes > 0 ? `${remainingMinutes}分` : ""}`;
}

export function OperatorList({ operators, isLoading }: OperatorListProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <div className="h-6 bg-gray-200 rounded w-32 animate-pulse"></div>
        </div>
        <div className="divide-y">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="p-4 flex items-center gap-4 animate-pulse">
              <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-16"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Sort operators: on_call > available > wrap_up > on_break > offline
  const statusOrder: OperatorStatus[] = ["on_call", "available", "wrap_up", "on_break", "offline"];
  const sortedOperators = [...operators].sort((a, b) => {
    const aIndex = statusOrder.indexOf(a.status);
    const bIndex = statusOrder.indexOf(b.status);
    if (aIndex !== bIndex) return aIndex - bIndex;
    // Secondary sort by idle duration (shorter idle = higher priority)
    return a.idle_duration_seconds - b.idle_duration_seconds;
  });

  const availableCount = operators.filter(op => op.status === "available").length;
  const onCallCount = operators.filter(op => op.status === "on_call").length;

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="font-bold text-gray-800">オペレーター一覧</h3>
        <div className="flex gap-3 text-sm">
          <span className="text-green-600">
            対応可能: <strong>{availableCount}</strong>
          </span>
          <span className="text-blue-600">
            通話中: <strong>{onCallCount}</strong>
          </span>
        </div>
      </div>

      {/* List */}
      {sortedOperators.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          オペレーターがいません
        </div>
      ) : (
        <div className="divide-y max-h-96 overflow-y-auto">
          {sortedOperators.map((operator) => {
            const config = STATUS_CONFIG[operator.status];
            return (
              <div key={operator.id} className="p-4 flex items-center gap-4 hover:bg-gray-50">
                {/* Avatar */}
                <div className="relative">
                  <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 font-medium">
                    {operator.name.charAt(0).toUpperCase()}
                  </div>
                  {/* Status indicator */}
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${
                      operator.status === "available" ? "bg-green-500" :
                      operator.status === "on_call" ? "bg-blue-500" :
                      operator.status === "wrap_up" ? "bg-purple-500" :
                      operator.status === "on_break" ? "bg-yellow-500" :
                      "bg-gray-400"
                    }`}
                  />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-800 truncate">{operator.name}</p>
                  <p className={`text-sm ${config.color}`}>{config.label}</p>
                </div>

                {/* Stats */}
                <div className="text-right text-sm">
                  {operator.status === "available" && (
                    <p className="text-gray-500">
                      待機: {formatDuration(operator.idle_duration_seconds)}
                    </p>
                  )}
                  {operator.status === "on_call" && (
                    <p className="text-blue-600 font-medium">通話中...</p>
                  )}
                  <p className="text-gray-400 text-xs">
                    {operator.calls_handled}件対応
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default OperatorList;
