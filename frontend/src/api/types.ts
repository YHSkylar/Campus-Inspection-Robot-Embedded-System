export type Role =
  | "admin"
  | "control_center"
  | "duty_manager"
  | "security"
  | "maintainer";

export type TaskMode = "fixed" | "scheduled" | "random" | "planned_path";
export type TaskStatus =
  | "pending"
  | "running"
  | "paused"
  | "stopped"
  | "completed"
  | "interrupted"
  | "cancelled"
  | "deleted";

export type EventType =
  | "fire"
  | "smoke"
  | "obstacle"
  | "boundary"
  | "unauthorized_person";

export type FireDetectionMode = "camera" | "image";

export type DisposeAction =
  | "remote_speak"
  | "light_intensify"
  | "standby"
  | "continue_inspection"
  | "false_alarm"
  | "danger_retreat"
  | "handled";

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: Role;
}

export interface RoutePoint {
  id?: string;
  node_id?: string;
  name?: string;
  area?: string;
  waypoint_name?: string;
  x?: number;
  y?: number;
  yaw?: number;
  fire_detection_mode?: FireDetectionMode;
  fire_image_path?: string;
  face_image_path?: string;
  inspection_image_path?: string;
  note?: string;
}

export interface Task {
  id: string;
  robot_id: string;
  mode: TaskMode;
  route_name: string;
  route_points: RoutePoint[];
  speed: number;
  frequency?: string;
  start_time?: string;
  end_time?: string;
  status: TaskStatus;
  dispatch_status: string;
  conflict_policy: string;
  completed_nodes: string[];
  trajectory: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface DangerEvent {
  id: string;
  robot_id: string;
  event_type: EventType;
  confidence: number;
  priority: number;
  status: string;
  report_status: string;
  location?: Record<string, unknown>;
  orientation?: Record<string, unknown>;
  snapshot_url?: string;
  local_alert: boolean;
  voice_broadcast: boolean;
  sample_retained: boolean;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DeviceStatus {
  id: string;
  robot_id: string;
  battery: number;
  localization: string;
  sensor_status: Record<string, string>;
  cpu_usage: number;
  memory_usage: number;
  signal_strength: number;
  online: boolean;
  mode: string;
  abnormal_flags: string[];
  created_at: string;
}

export interface Robot {
  id: string;
  name: string;
  online: boolean;
  mode: string;
  status: string;
  battery: number;
  location?: Record<string, unknown>;
  updated_at: string;
}

export interface MaintenanceRecord {
  id: string;
  operation: string;
  operator: string;
  status: string;
  version_before?: string;
  version_after?: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface LogEntry {
  id: string;
  level: string;
  category: string;
  message: string;
  sensitive: number;
  created_at: string;
}

export interface QueryResult<T = unknown> {
  data_type: string;
  permission: "full" | "limited";
  message?: string;
  items: T[];
}

export interface HealthStatus {
  status: string;
  app: string;
  status_refresh_seconds: number;
  alarm_report_deadline_seconds: number;
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: "系统管理员",
  control_center: "控制中心",
  duty_manager: "值班主管",
  security: "安保人员",
  maintainer: "维护工程师",
};

export const MODE_LABELS: Record<TaskMode, string> = {
  fixed: "定点巡检",
  scheduled: "定时巡检",
  random: "随机巡检",
  planned_path: "规划路径",
};

export const EVENT_LABELS: Record<EventType, string> = {
  fire: "火焰",
  smoke: "烟雾",
  obstacle: "障碍",
  boundary: "边界",
  unauthorized_person: "未授权人员",
};

export const STATUS_LABELS: Record<string, string> = {
  pending: "待执行",
  running: "执行中",
  paused: "已暂停",
  stopped: "已停止",
  completed: "已完成",
  interrupted: "已中断",
  cancelled: "已取消",
  deleted: "已删除",
  unhandled: "未处置",
  processing: "处置中",
  handled: "已处置",
  false_alarm: "误报",
  monitoring: "监控中",
  reported: "已上报",
  cached: "缓存待补发",
  face_required: "需人脸采样",
  authorized_person: "白名单人员",
  person_face_required: "需人脸复核",
  disconnected: "未连接",
  abnormal: "异常",
  offline: "离线",
};

export const DISPOSE_LABELS: Record<DisposeAction, string> = {
  remote_speak: "远程喊话",
  light_intensify: "灯光增强",
  standby: "待命",
  continue_inspection: "继续巡检",
  false_alarm: "标记误报",
  danger_retreat: "危险后退",
  handled: "已处理",
};
