import type {
  DangerEvent,
  DeviceStatus,
  DisposeAction,
  HealthStatus,
  KnownFace,
  LogEntry,
  LoginResponse,
  MaintenanceRecord,
  QueryResult,
  RoutePoint,
  Task,
  TaskMode,
} from "./types";
import { API_BASE_URL } from "../config/app";

const API_BASE = API_BASE_URL.replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) {
        message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthStatus>("/health"),

  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  // FU-001 任务管理
  listTasks: (status?: string) =>
    request<Task[]>(status ? `/tasks?status=${status}` : "/tasks"),

  getTask: (taskId: string) => request<Task>(`/tasks/${taskId}`),

  createTask: (data: {
    robot_id?: string;
    mode: TaskMode | string;
    route_name: string;
    route_points: RoutePoint[];
    speed: number;
    frequency?: string;
    start_time?: string;
    end_time?: string;
    conflict_policy?: string;
  }) =>
    request<Task>("/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateTask: (taskId: string, data: Record<string, unknown>) =>
    request<Task>(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  taskAction: (taskId: string, action: string) =>
    request<Task>(`/tasks/${taskId}/action`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),

  dispatchTask: (taskId: string, force = false) =>
    request<{ message: string; task: Task; robot_online: boolean }>(
      `/tasks/${taskId}/dispatch`,
      {
        method: "POST",
        body: JSON.stringify({ force }),
      },
    ),

  deleteTask: (taskId: string) =>
    request<{ message: string; task_id: string }>(`/tasks/${taskId}`, {
      method: "DELETE",
    }),

  // FU-002 巡检执行
  startInspection: (taskId: string) =>
    request<{ task: Task; slam: string; path_plan: string }>("/inspection/start", {
      method: "POST",
      body: JSON.stringify({ task_id: taskId }),
    }),

  confirmNode: (
    taskId: string,
    data: {
      node_id: string;
      location?: Record<string, unknown>;
      snapshot_url?: string;
      sensor_summary?: Record<string, unknown>;
    },
  ) =>
    request<{
      task: Task;
      confirmed_node: string;
      confirmed_count: number;
      total_nodes: number;
      all_confirmed: boolean;
      detection_results?: Array<Record<string, unknown>>;
      fire_event_result?: Record<string, unknown>;
    }>(`/inspection/${taskId}/confirm`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  emergencyPause: (taskId: string) =>
    request<{ task_id: string; status: string; robot_action: string }>(
      `/inspection/${taskId}/emergency-pause`,
      { method: "POST" },
    ),

  // FU-003 危险识别
  listEvents: (eventType?: string, status?: string) => {
    const params = new URLSearchParams();
    if (eventType) params.set("event_type", eventType);
    if (status) params.set("status", status);
    const qs = params.toString();
    return request<DangerEvent[]>(qs ? `/events?${qs}` : "/events");
  },

  getEvent: (eventId: string) => request<DangerEvent>(`/events/${eventId}`),

  flushCache: () =>
    request<{ flushed: number; report_status: string }>("/events/flush-cache", {
      method: "POST",
    }),

  listFaces: () => request<KnownFace[]>("/faces"),

  uploadFace: async (
    data: {
      face_id: string;
      name: string;
      role?: string;
      filename?: string;
    },
    file: File,
  ) => {
    const token = getToken();
    const params = new URLSearchParams({
      face_id: data.face_id,
      name: data.name,
    });
    if (data.role) params.set("role_name", data.role);
    if (data.filename) params.set("filename", data.filename);

    const headers: Record<string, string> = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/faces/upload?${params.toString()}`, {
      method: "POST",
      headers,
      body: await file.arrayBuffer(),
    });

    if (!response.ok) {
      let message = `请求失败 (${response.status})`;
      try {
        const body = await response.json();
        if (body.detail) {
          message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        }
      } catch {
        // ignore
      }
      throw new ApiError(response.status, message);
    }

    return response.json() as Promise<{ face: KnownFace; upload: Record<string, unknown> }>;
  },

  deleteFace: (faceId: string) =>
    request<{ id: string; message: string }>(`/faces/${encodeURIComponent(faceId)}`, {
      method: "DELETE",
    }),

  // FU-004 危险处置
  disposeEvent: (
    eventId: string,
    data: {
      action: DisposeAction;
      executor?: string;
      reason?: string;
      result?: string;
    },
  ) =>
    request<{ event: DangerEvent; record: Record<string, unknown> }>(
      `/events/${eventId}/dispose`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),

  // FU-005 设备监控
  currentDeviceStatus: () =>
    request<DeviceStatus>("/devices/status/current"),

  deviceHistory: (robotId?: string) =>
    request<DeviceStatus[]>(
      robotId
        ? `/devices/status/history?robot_id=${robotId}`
        : "/devices/status/history",
    ),

  // FU-006 系统维护
  maintenanceOperate: (data: {
    operation: string;
    operator?: string;
    package_checksum_valid?: boolean;
    target_version?: string;
    module_name?: string;
    dangerous?: boolean;
    detail?: Record<string, unknown>;
  }) =>
    request<MaintenanceRecord>("/maintenance/operate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  maintenanceLogs: () => request<LogEntry[]>("/maintenance/logs"),

  // FU-007 数据查询
  queryData: (params: {
    data_type: string;
    type?: string;
    status?: string;
    robot_id?: string;
  }) => {
    const qs = new URLSearchParams();
    qs.set("data_type", params.data_type);
    if (params.type) qs.set("type", params.type);
    if (params.status) qs.set("status", params.status);
    if (params.robot_id) qs.set("robot_id", params.robot_id);
    return request<QueryResult>(`/query?${qs.toString()}`);
  },

  exportData: (params: {
    data_type: string;
    export_format?: string;
    type?: string;
    status?: string;
    robot_id?: string;
  }) => {
    const qs = new URLSearchParams();
    qs.set("data_type", params.data_type);
    if (params.export_format) qs.set("export_format", params.export_format);
    if (params.type) qs.set("type", params.type);
    if (params.status) qs.set("status", params.status);
    if (params.robot_id) qs.set("robot_id", params.robot_id);
    return request<QueryResult & { file_name: string; rows: number; download_url: string }>(
      `/query/export?${qs.toString()}`,
    );
  },
};
