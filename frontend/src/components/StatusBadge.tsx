import { STATUS_LABELS } from "../api/types";

const STATUS_VARIANTS: Record<string, string> = {
  pending: "badge-muted",
  running: "badge-primary",
  paused: "badge-warning",
  stopped: "badge-muted",
  completed: "badge-success",
  interrupted: "badge-danger",
  cancelled: "badge-muted",
  deleted: "badge-muted",
  unhandled: "badge-danger",
  processing: "badge-warning",
  handled: "badge-success",
  false_alarm: "badge-muted",
  monitoring: "badge-info",
  reported: "badge-success",
  cached: "badge-warning",
  success: "badge-success",
  blocked: "badge-danger",
  rolled_back: "badge-danger",
  normal: "badge-success",
  degraded: "badge-warning",
  main: "badge-success",
  abnormal: "badge-danger",
  disconnected: "badge-danger",
  offline: "badge-danger",
};

interface StatusBadgeProps {
  status: string;
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const variant = STATUS_VARIANTS[status] || "badge-muted";
  const text = label || STATUS_LABELS[status] || status;
  return <span className={`badge ${variant}`}>{text}</span>;
}
