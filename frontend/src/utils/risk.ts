import type { ActionCode, RiskLevel } from '../types/api';

export const RISK_LEVELS: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

// Visual presentation is owned by the frontend (the backend never specifies colours).
export const RISK_STYLE: Record<RiskLevel, { color: string; bg: string; border: string; label: string; rank: number }> = {
  LOW: { color: '#0F766E', bg: '#E3F4F1', border: '#9ED5CD', label: 'Low', rank: 0 },
  MEDIUM: { color: '#B45309', bg: '#FDF1DC', border: '#EBC98D', label: 'Medium', rank: 1 },
  HIGH: { color: '#C2410C', bg: '#FCE8DC', border: '#EFB596', label: 'High', rank: 2 },
  CRITICAL: { color: '#9F1239', bg: '#FBE4EA', border: '#E8A3B6', label: 'Critical', rank: 3 },
};

export const ACTION_LABEL: Record<ActionCode, string> = {
  APPROVE: 'Approve',
  REQUEST_MFA: 'Request MFA',
  TEMPORARILY_BLOCK: 'Temporarily block',
  FLAG_FOR_ANALYST_REVIEW: 'Flag for analyst review',
};

export const STATUS_LABEL: Record<string, string> = {
  APPROVED: 'Approved',
  PENDING_VERIFICATION: 'Pending verification',
  BLOCKED: 'Blocked',
  UNDER_REVIEW: 'Under analyst review',
};

export const KIND_STYLE: Record<string, { label: string; fill: string; stroke: string; text: string }> = {
  observed: { label: 'Observed', fill: '#E8EEF7', stroke: '#8DA4C7', text: '#1B3150' },
  behavioural: { label: 'Behavioural', fill: '#E9F5F6', stroke: '#7FC0C6', text: '#0A5F67' },
  constraint: { label: 'Constraint', fill: '#F3ECF8', stroke: '#B79BD0', text: '#4A2C66' },
  indicator: { label: 'Indicator', fill: '#FDF1DC', stroke: '#E0B25F', text: '#7A4A06' },
  risk: { label: 'Risk conclusion', fill: '#FBE4EA', stroke: '#D77A96', text: '#7A0E2C' },
  external: { label: 'External', fill: '#EEF0F3', stroke: '#A9B1BC', text: '#334155' },
};
