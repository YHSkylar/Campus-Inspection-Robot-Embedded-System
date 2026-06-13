import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Task, TaskMode } from "../api/types";
import { MODE_LABELS } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import type { AuthUser } from "../hooks/useAuth";
import { canManageTasks } from "../hooks/useAuth";

interface TasksProps {
  user: AuthUser;
}

const DEFAULT_ROUTE_POINTS = [
  { id: "1", name: "A区入口", area: "A-1" },
  { id: "2", name: "A区配电室", area: "A-3" },
  { id: "3", name: "B区停车场", area: "B-1" },
  { id: "4", name: "充电站", area: "standby" },
];

export function Tasks({ user }: TasksProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    mode: "scheduled" as TaskMode,
    route_name: "A区日常巡检",
    speed: 0.8,
    frequency: "每日 08:00",
    conflict_policy: "reject",
    robot_id: "robot-001",
  });

  const canManage = canManageTasks(user.role);

  useEffect(() => {
    loadTasks();
  }, [statusFilter]);

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
      await api.createTask({
        ...form,
        route_points: DEFAULT_ROUTE_POINTS,
      });
      setSuccess("任务创建成功");
      setShowCreate(false);
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
            onClick={() => setShowCreate(true)}
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
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
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
                      setForm({ ...form, speed: parseFloat(e.target.value) })
                    }
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>频率</label>
                  <input
                    className="form-control"
                    value={form.frequency}
                    onChange={(e) =>
                      setForm({ ...form, frequency: e.target.value })
                    }
                  />
                </div>
                <div className="form-group">
                  <label>冲突策略</label>
                  <select
                    className="form-control"
                    value={form.conflict_policy}
                    onChange={(e) =>
                      setForm({ ...form, conflict_policy: e.target.value })
                    }
                  >
                    <option value="reject">拒绝</option>
                    <option value="queue">排队</option>
                    <option value="cover">覆盖</option>
                  </select>
                </div>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>
                默认路线：A区入口 → A区配电室 → B区停车场 → 充电站
              </p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCreate(false)}
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
