/**
 * Real-time campaign statistics component
 */

import type { CampaignStats } from "../../types";

interface RealtimeStatsProps {
  stats: CampaignStats | null;
  campaignName?: string;
  isLoading?: boolean;
}

interface StatCardProps {
  label: string;
  value: number;
  color: string;
  icon: React.ReactNode;
}

function StatCard({ label, value, color, icon }: StatCardProps) {
  return (
    <div className={`bg-white rounded-lg shadow p-4 border-l-4 ${color}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-800">{value.toLocaleString()}</p>
        </div>
        <div className="text-gray-400">{icon}</div>
      </div>
    </div>
  );
}

export function RealtimeStats({ stats, campaignName, isLoading }: RealtimeStatsProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="bg-white rounded-lg shadow p-4">
              <div className="h-4 bg-gray-200 rounded w-20 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-16"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-8 text-gray-500">
        キャンペーンを選択してください
      </div>
    );
  }

  const abandonRateColor = stats.abandon_rate > 0.05 ? "text-red-600" : "text-green-600";

  return (
    <div>
      {campaignName && (
        <h2 className="text-lg font-bold text-gray-800 mb-4">{campaignName}</h2>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="総リード数"
          value={stats.total_leads}
          color="border-blue-500"
          icon={<UsersIcon />}
        />
        <StatCard
          label="待機中"
          value={stats.pending_leads}
          color="border-gray-500"
          icon={<ClockIcon />}
        />
        <StatCard
          label="発信中"
          value={stats.calling_leads}
          color="border-yellow-500"
          icon={<PhoneOutgoingIcon />}
        />
        <StatCard
          label="通話中"
          value={stats.connected_leads}
          color="border-green-500"
          icon={<PhoneIcon />}
        />
        <StatCard
          label="完了"
          value={stats.completed_leads}
          color="border-blue-500"
          icon={<CheckIcon />}
        />
        <StatCard
          label="失敗"
          value={stats.failed_leads}
          color="border-red-500"
          icon={<XIcon />}
        />
        <StatCard
          label="DNC"
          value={stats.dnc_leads}
          color="border-purple-500"
          icon={<BanIcon />}
        />

        {/* Abandon Rate - Special Card */}
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">放棄率</p>
              <p className={`text-2xl font-bold ${abandonRateColor}`}>
                {(stats.abandon_rate * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-gray-400">
              <ChartIcon />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-1">目標: 3%以下</p>
        </div>
      </div>
    </div>
  );
}

// Simple SVG Icons
function UsersIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function PhoneOutgoingIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 3h5m0 0v5m0-5l-6 6M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function BanIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

export default RealtimeStats;
