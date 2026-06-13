import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Task } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import type { AuthUser } from "../hooks/useAuth";
import { canOperateInspection } from "../hooks/useAuth";

interface InspectionProps {
  user: AuthUser;
}

export function Inspection({ user }: InspectionProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [nodeId, setNodeId] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canOperate = canOperateInspection(user.role);

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    if (selectedId) {
      api.getTask(selectedId).then(setSelectedTask).catch(() => setSelectedTask(null));
    } else {
      setSelectedTask(null);
    }
  }, [selectedId]);

  async function loadTasks() {
    try {
      const data = await api.listTasks();
      const active = data.filter((t) =>
        ["pending", "running", "paused"].includes(t.status),
      );
      setTasks(active);
      if (active.length > 0 && !selectedId) {
        setSelectedId(active[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  async function handleStart() {
    if (!selectedId) return;
    setError("");
    try {
      const res = await api.startInspection(selectedId);
      setSuccess(`巡检已启动，SLAM: ${res.slam}，路径规划: ${res.path_plan}`);
      setSelectedId(res.task.id);
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "启动失败");
    }
  }

  async function handleConfirm() {
    if (!selectedId || !nodeId) return;
    setError("");
    try {
      const res = await api.confirmNode(selectedId, {
        node_id: nodeId,
        location: { area: nodeId },
        sensor_summary: { status: "normal" },
      });
      setSuccess(
        `已确认巡检点 ${res.confirmed_node}（${res.confirmed_count}/${res.total_nodes}）` +
          (res.all_confirmed ? "，全部点位已确认" : ""),
      );
      api.getTask(selectedId).then(setSelectedTask);
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "确认失败");
    }
  }

  async function handleEmergencyPause() {
    if (!selectedId) return;
    setError("");
    try {
      const res = await api.emergencyPause(selectedId);
      setSuccess(`紧急暂停成功，机器人动作: ${res.robot_action}`);
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "暂停失败");
    }
  }

  const routePoints = selectedTask?.route_points || [];
  const completed = selectedTask?.completed_nodes || [];

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">选择任务</div>
          <div className="form-group">
            <select
              className="form-control"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              <option value="">请选择任务</option>
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.route_name} ({t.id}) - {t.status}
                </option>
              ))}
            </select>
          </div>

          {selectedTask && (
            <>
              <dl className="detail-grid" style={{ marginBottom: 16 }}>
                <dt>状态</dt>
                <dd>
                  <StatusBadge status={selectedTask.status} />
                </dd>
                <dt>机器人</dt>
                <dd>{selectedTask.robot_id}</dd>
                <dt>速度</dt>
                <dd>{selectedTask.speed} m/s</dd>
                <dt>下发</dt>
                <dd>
                  <StatusBadge status={selectedTask.dispatch_status} />
                </dd>
              </dl>

              {canOperate && (
                <div className="actions">
                  {selectedTask.status === "pending" && (
                    <button className="btn btn-primary" onClick={handleStart}>
                      启动巡检
                    </button>
                  )}
                  {selectedTask.status === "running" && (
                    <button
                      className="btn btn-danger"
                      onClick={handleEmergencyPause}
                    >
                      紧急暂停
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <div className="card">
          <div className="card-title">巡检点确认</div>
          {routePoints.length === 0 ? (
            <div className="empty-state">该任务暂无巡检路线点位</div>
          ) : (
            <>
              <div className="form-group">
                <label>选择巡检点</label>
                <select
                  className="form-control"
                  value={nodeId}
                  onChange={(e) => setNodeId(e.target.value)}
                >
                  <option value="">请选择</option>
                  {routePoints.map((pt, i) => {
                    const id = String(pt.id || pt.node_id || i + 1);
                    const done = completed.includes(id);
                    return (
                      <option key={id} value={id}>
                        {pt.name || pt.area || id}
                        {done ? " ✓" : ""}
                      </option>
                    );
                  })}
                </select>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleConfirm}
                disabled={!nodeId || !canOperate}
              >
                确认到达
              </button>

              <div style={{ marginTop: 20 }}>
                <div className="label" style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  巡检进度 {completed.length}/{routePoints.length}
                </div>
                <div className="progress-bar">
                  <div
                    className="fill"
                    style={{
                      width: `${routePoints.length > 0 ? (completed.length / routePoints.length) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                {routePoints.map((pt, i) => {
                  const id = String(pt.id || pt.node_id || i + 1);
                  const done = completed.includes(id);
                  return (
                    <div
                      key={id}
                      style={{
                        padding: "8px 12px",
                        marginBottom: 6,
                        borderRadius: 8,
                        background: done ? "rgba(34,197,94,0.1)" : "var(--bg)",
                        border: `1px solid ${done ? "rgba(34,197,94,0.3)" : "var(--border)"}`,
                        fontSize: 13,
                      }}
                    >
                      {done ? "✓ " : "○ "}
                      {pt.name || pt.area || `点位 ${id}`}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {selectedTask && selectedTask.trajectory.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">轨迹记录</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>动作</th>
                  <th>详情</th>
                </tr>
              </thead>
              <tbody>
                {selectedTask.trajectory.map((item, i) => (
                  <tr key={i}>
                    <td>{String(item.time || "-")}</td>
                    <td>{String(item.action || "-")}</td>
                    <td>{JSON.stringify(item)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
