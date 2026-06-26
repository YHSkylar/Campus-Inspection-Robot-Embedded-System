import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { RoutePoint, Task, TaskMode } from "../api/types";
import { MODE_LABELS } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import type { AuthUser } from "../hooks/useAuth";
import { canManageTasks } from "../hooks/useAuth";

interface TasksProps {
  user: AuthUser;
}

const WAYPOINT_OPTIONS = ["area_A", "area_B", "area_C"];

function createEmptyRoutePoint(index: number): RoutePoint {
  return {
    id: String(index + 1),
    node_id: String(index + 1),
    waypoint_name: "",
  };
}

function normalizeRoutePoints(routePoints: RoutePoint[]): RoutePoint[] {
  return routePoints
    .map((point, index) => ({
      id: String(point.id || point.node_id || index + 1),
      node_id: String(point.node_id || point.id || index + 1),
      waypoint_name: point.waypoint_name?.trim() || undefined,
    }))
    .filter((point) => Boolean(point.waypoint_name));
}

export function Tasks({ user }: TasksProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    mode: "scheduled" as TaskMode,
    route_name: "",
    speed: 0.8,
  });
  const [routePoints, setRoutePoints] = useState<RoutePoint[]>([createEmptyRoutePoint(0)]);

  const canManage = canManageTasks(user.role);

  useEffect(() => {
    loadTasks();
  }, [statusFilter]);

  function resetCreateForm() {
    setForm({
      mode: "scheduled",
      route_name: "",
      speed: 0.8,
    });
    setRoutePoints([createEmptyRoutePoint(0)]);
  }

  function closeCreateModal() {
    setShowCreate(false);
    setLoading(false);
    resetCreateForm();
  }

  function updateRoutePoint(index: number, patch: Partial<RoutePoint>) {
    setRoutePoints((current) =>
      current.map((point, pointIndex) =>
        pointIndex === index ? { ...point, ...patch } : point,
      ),
    );
  }

  function addRoutePoint() {
    setRoutePoints((current) => [...current, createEmptyRoutePoint(current.length)]);
  }

  function removeRoutePoint(index: number) {
    setRoutePoints((current) => {
      if (current.length === 1) {
        return [createEmptyRoutePoint(0)];
      }
      return current
        .filter((_, pointIndex) => pointIndex !== index)
        .map((point, pointIndex) => ({
          ...point,
          id: String(pointIndex + 1),
          node_id: String(point.node_id || pointIndex + 1),
        }));
    });
  }

  async function loadTasks() {
    try {
      const data = await api.listTasks(statusFilter || undefined);
      setTasks(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const normalizedRoutePoints = normalizeRoutePoints(routePoints);
      if (normalizedRoutePoints.length === 0) {
        setError("至少需要配置一个巡检点，并选择航点名");
        setLoading(false);
        return;
      }
      await api.createTask({
        ...form,
        route_points: normalizedRoutePoints,
      });
      setSuccess("任务创建成功");
      closeCreateModal();
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(taskId: string, action: string) {
    setError("");
    try {
      await api.taskAction(taskId, action);
      setSuccess(`任务 ${action} 操作成功`);
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
    }
  }

  async function handleDispatch(taskId: string) {
    setError("");
    try {
      const res = await api.dispatchTask(taskId);
      setSuccess(res.message);
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "下发失败");
    }
  }

  async function handleDelete(taskId: string) {
    if (!confirm("确认删除该任务？")) return;
    setError("");
    try {
      await api.deleteTask(taskId);
      setSuccess("任务已删除");
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败");
    }
  }

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="filter-bar">
        <div className="form-group">
          <label>状态筛选</label>
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">全部</option>
            <option value="pending">待执行</option>
            <option value="running">执行中</option>
            <option value="paused">已暂停</option>
            <option value="completed">已完成</option>
          </select>
        </div>
        {canManage && (
          <button
            className="btn btn-primary"
            onClick={() => {
              resetCreateForm();
              setShowCreate(true);
            }}
          >
            + 创建任务
          </button>
        )}
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>任务 ID</th>
                <th>路线名称</th>
                <th>模式</th>
                <th>速度</th>
                <th>状态</th>
                <th>下发状态</th>
                <th>进度</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-state">
                    暂无任务
                  </td>
                </tr>
              ) : (
                tasks.map((task) => {
                  const total = task.route_points.length;
                  const done = task.completed_nodes.length;
                  const progress = total > 0 ? Math.round((done / total) * 100) : 0;
                  return (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.route_name}</td>
                      <td>{MODE_LABELS[task.mode] || task.mode}</td>
                      <td>{task.speed} m/s</td>
                      <td>
                        <StatusBadge status={task.status} />
                      </td>
                      <td>
                        <StatusBadge status={task.dispatch_status} />
                      </td>
                      <td>
                        {done}/{total} ({progress}%)
                      </td>
                      <td>
                        <div className="actions">
                          {canManage && task.status === "pending" && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handleDispatch(task.id)}
                            >
                              下发
                            </button>
                          )}
                          {task.status === "running" && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleAction(task.id, "pause")}
                            >
                              暂停
                            </button>
                          )}
                          {task.status === "paused" && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handleAction(task.id, "start")}
                            >
                              继续
                            </button>
                          )}
                          {["running", "paused"].includes(task.status) && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleAction(task.id, "complete")}
                            >
                              完成
                            </button>
                          )}
                          {canManage && !["deleted", "completed"].includes(task.status) && (
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => handleDelete(task.id)}
                            >
                              删除
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={closeCreateModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>创建巡检任务</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>路线名称</label>
                <input
                  className="form-control"
                  value={form.route_name}
                  onChange={(e) =>
                    setForm({ ...form, route_name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>巡检模式</label>
                  <select
                    className="form-control"
                    value={form.mode}
                    onChange={(e) =>
                      setForm({ ...form, mode: e.target.value as TaskMode })
                    }
                  >
                    {Object.entries(MODE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>速度 (m/s)</label>
                  <input
                    className="form-control"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="2"
                    value={form.speed}
                    onChange={(e) =>
                      setForm({ ...form, speed: Number(e.target.value) || 0.1 })
                    }
                    required
                    />
                </div>
              </div>
              <div className="card" style={{ padding: 16, marginTop: 12 }}>
                <div className="card-title" style={{ marginBottom: 12 }}>
                  巡检点配置
                  <button type="button" className="btn btn-secondary btn-sm" onClick={addRoutePoint}>
                    + 添加点位
                  </button>
                </div>
                {routePoints.map((point, index) => (
                  <div
                    key={`${point.id || index}-${index}`}
                    style={{
                      border: "1px solid var(--border)",
                      borderRadius: 10,
                      padding: 12,
                      marginBottom: 12,
                      background: "var(--bg)",
                    }}
                  >
                    <div className="actions" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                      <strong>巡检点 {index + 1}</strong>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        onClick={() => removeRoutePoint(index)}
                      >
                        删除
                      </button>
                    </div>
                    <div className="form-group">
                      <label>航点名</label>
                      <select
                        className="form-control"
                        value={point.waypoint_name || ""}
                        onChange={(e) => updateRoutePoint(index, { waypoint_name: e.target.value })}
                        required
                      >
                        <option value="">请选择航点</option>
                        {WAYPOINT_OPTIONS.map((waypoint) => (
                          <option key={waypoint} value={waypoint}>
                            {waypoint}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={closeCreateModal}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? "创建中..." : "创建"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
