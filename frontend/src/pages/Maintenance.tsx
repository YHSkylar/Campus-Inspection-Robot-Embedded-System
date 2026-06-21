import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { LogEntry, MaintenanceRecord } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import type { AuthUser } from "../hooks/useAuth";
import { canMaintain } from "../hooks/useAuth";

interface MaintenanceProps {
  user: AuthUser;
}

const OPERATIONS = [
  { value: "calibrate", label: "传感器校准" },
  { value: "restart_module", label: "模块重启" },
  { value: "software_update", label: "软件更新" },
  { value: "algorithm_update", label: "算法更新" },
];

export function Maintenance({ user }: MaintenanceProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [operation, setOperation] = useState("calibrate");
  const [moduleName, setModuleName] = useState("");
  const [targetVersion, setTargetVersion] = useState("1.1.0");
  const [dangerous, setDangerous] = useState(false);
  const [lastRecord, setLastRecord] = useState<MaintenanceRecord | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const canOperate = canMaintain(user.role);

  useEffect(() => {
    loadLogs();
  }, []);

  async function loadLogs() {
    try {
      const data = await api.maintenanceLogs();
      setLogs(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载日志失败");
    }
  }

  async function handleOperate(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const record = await api.maintenanceOperate({
        operation,
        operator: user.username,
        module_name: moduleName || undefined,
        target_version: targetVersion || undefined,
        dangerous,
        package_checksum_valid: true,
      });
      setLastRecord(record);
      setSuccess(`维护操作完成，状态: ${record.status}`);
      loadLogs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">维护操作</div>
          {!canOperate ? (
            <div className="alert alert-info">
              当前角色无维护权限，仅管理员和维护工程师可操作
            </div>
          ) : (
            <form onSubmit={handleOperate}>
              <div className="form-group">
                <label>操作类型</label>
                <select
                  className="form-control"
                  value={operation}
                  onChange={(e) => setOperation(e.target.value)}
                >
                  {OPERATIONS.map((op) => (
                    <option key={op.value} value={op.value}>
                      {op.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>目标模块</label>
                <input
                  className="form-control"
                  value={moduleName}
                  onChange={(e) => setModuleName(e.target.value)}
                  placeholder="如 smoke_sensor, camera_module"
                />
              </div>
              <div className="form-group">
                <label>目标版本</label>
                <input
                  className="form-control"
                  value={targetVersion}
                  onChange={(e) => setTargetVersion(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={dangerous}
                    onChange={(e) => setDangerous(e.target.checked)}
                    style={{ marginRight: 8 }}
                  />
                  标记为危险操作（将触发保护机制）
                </label>
              </div>
              <button
                className="btn btn-primary"
                type="submit"
                disabled={loading}
              >
                {loading ? "执行中..." : "执行维护"}
              </button>
            </form>
          )}

          {lastRecord && (
            <div style={{ marginTop: 20 }}>
              <div className="card-title" style={{ fontSize: 13 }}>
                最近操作结果
              </div>
              <dl className="detail-grid">
                <dt>记录 ID</dt>
                <dd>{lastRecord.id}</dd>
                <dt>操作</dt>
                <dd>{lastRecord.operation}</dd>
                <dt>状态</dt>
                <dd>
                  <StatusBadge status={lastRecord.status} />
                </dd>
                <dt>版本</dt>
                <dd>
                  {lastRecord.version_before} → {lastRecord.version_after}
                </dd>
                <dt>详情</dt>
                <dd>{String(lastRecord.detail?.message || "-")}</dd>
              </dl>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">系统日志</div>
          <div className="table-wrap" style={{ maxHeight: 480, overflowY: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>级别</th>
                  <th>分类</th>
                  <th>消息</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="empty-state">
                      暂无日志
                    </td>
                  </tr>
                ) : (
                  logs.slice(0, 50).map((log) => (
                    <tr key={log.id}>
                      <td>
                        {new Date(log.created_at).toLocaleString("zh-CN")}
                      </td>
                      <td>
                        <StatusBadge
                          status={
                            log.level === "WARN"
                              ? "warning"
                              : log.level === "ERROR"
                                ? "danger"
                                : "success"
                          }
                          label={log.level}
                        />
                      </td>
                      <td>{log.category}</td>
                      <td style={{ maxWidth: 280 }}>{log.message}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
