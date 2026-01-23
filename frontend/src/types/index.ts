/**
 * Type definitions for ParallelDialer
 */

// Auth
export interface User {
  id: string;
  username: string;
  email: string | null;
  role: "admin" | "operator";
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Lead
export type LeadStatus =
  | "pending"
  | "calling"
  | "connected"
  | "completed"
  | "failed"
  | "dnc";

export interface Lead {
  id: string;
  phone_number: string;
  name: string | null;
  company: string | null;
  email: string | null;
  status: LeadStatus;
  outcome: string | null;
  retry_count: number;
  created_at: string;
  last_called_at: string | null;
}

// Campaign
export type CampaignStatus =
  | "draft"
  | "running"
  | "paused"
  | "stopped"
  | "completed";

export interface Campaign {
  id: string;
  name: string;
  description: string;
  status: CampaignStatus;
  dial_ratio: number;
  caller_id: string | null;
  lead_count: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface CampaignStats {
  total_leads: number;
  pending_leads: number;
  calling_leads: number;
  connected_leads: number;
  completed_leads: number;
  failed_leads: number;
  dnc_leads: number;
  abandon_rate: number;
}

// Operator
export type OperatorStatus =
  | "offline"
  | "available"
  | "on_call"
  | "on_break"
  | "wrap_up";

export interface Operator {
  id: string;
  name: string;
  status: OperatorStatus;
  current_call_sid: string | null;
  idle_duration_seconds: number;
  calls_handled: number;
}

// WebSocket Events
export type WSEventType =
  | "connected"
  | "incoming_call"
  | "call_connected"
  | "call_ended"
  | "operator_status_changed"
  | "campaign_stats_updated"
  | "operator_list_updated"
  | "alert"
  | "error"
  | "pong";

export interface WSMessage<T = unknown> {
  event: WSEventType;
  data: T;
  timestamp: string;
}

export interface IncomingCall {
  call_sid: string;
  lead_id: string;
  phone_number: string;
  name: string | null;
}

export interface Alert {
  alert_type: string;
  message: string;
  severity: "info" | "warning" | "error";
}

// Import
export interface ImportResult {
  imported_count: number;
  skipped_count: number;
  errors: Array<{ row?: string; phone?: string; error: string }>;
}
