import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { DeviceStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

export function Devices() {
  const [current, setCurrent] = useState<DeviceStatus | null>(null);
  const [history, setHistory] = useState<DeviceStatus[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 3000);
    return () => clearInterval(timer);
  }, []);

  async function loadData() {
    try {
      const [status, hist] = await Promise.all([
        api.currentDeviceStatus(),
        api.deviceHistory(),
      ]);
      setCurrent(status);
      setHistory(hist);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="grid-3" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">在线状态</div>
          <div className="value" style={{ fontSize: 18 }}>
            {current?.online ? (
              <span style={{ color: "var(--success)" }}>在线</span>
            ) : (
              <span style={{ color: "var(--danger)" }}>离线</span>
            )}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">电量</div>
          <div
            className={`value ${(current?.battery ?? 0) <= 20 ? "danger" : "success"}`}
          >
            {current?.battery ?? "-"}%
          </div>
        </div>
        <div className="stat-card">
          <div className="label">定位状态</div>
          <div className="value" style={{ fontSize: 18 }}>
            {current?.localization === "normal" ? (
              <span style={{ color: "var(--success)" }}>正常</span>
            ) : (
              <span style={{ color: "var(--danger)" }}>丢失</span>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">实时设备状态</div>
        {current ? (
          <>
            <dl className="detail-grid">
              <dt>运行模式</dt>
              <dd>
                <StatusBadge
                  status={current.mode}
                  label={
                    current.mode === "disconnected"
                      ? "未连接"
                      : current.mode === "degraded"
                        ? "降级模式"
                        : "主模式"
                  }
                />
              </dd>
              <dt>CPU 使用率</dt>
              <dd>
                {current.cpu_usage.toFixed(1)}%
                <div className="progress-bar">
                  <div
                    className="fill"
                    style={{ width: `${current.cpu_usage}%` }}
                  />
                </div>
              </dd>
              <dt>内存使用率</dt>
              <dd>
                {current.memory_usage.toFixed(1)}%
                <div className="progress-bar">
                  <div
                    className="fill"
                    style={{ width: `${current.memory_usage}%` }}
                  />
                </div>
              </dd>
              <dt>信号强度</dt>
              <dd>{current.signal_strength}%</dd>
              <dt>更新时间</dt>
              <dd>{new Date(current.created_at).toLocaleString("zh-CN")}</dd>
            </dl>

            {Object.keys(current.sensor_status).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div className="card-title" style={{ fontSize: 13 }}>
                  传感器状态
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>传感器</th>
                        <th>状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(current.sensor_status).map(
                        ([name, status]) => (
                          <tr key={name}>
                            <td>{name}</td>
                            <td>
                              <StatusBadge
                                status={
                                  status === "normal" ? "success" : "fault"
                                }
                                label={status}
                              />
                            </td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {current.abnormal_flags.length > 0 && (
              <div className="alert alert-error" style={{ marginTop: 16 }}>
                异常标记：{current.abnormal_flags.join("、")}
              </div>
            )}
          </>
        ) : (
          <div className="empty-state">暂无设备状态</div>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">状态历史记录</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>电量</th>
                <th>模式</th>
                <th>定位</th>
                <th>CPU</th>
                <th>内存</th>
                <th>信号</th>
                <th>在线</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-state">
                    暂无历史记录
                  </td>
                </tr>
              ) : (
                history.slice(0, 20).map((row) => (
                  <tr key={row.id}>
                    <td>{new Date(row.created_at).toLocaleString("zh-CN")}</td>
                    <td>{row.battery}%</td>
                    <td>
                      <StatusBadge status={row.mode} />
                    </td>
                    <td>{row.localization}</td>
                    <td>{row.cpu_usage.toFixed(0)}%</td>
                    <td>{row.memory_usage.toFixed(0)}%</td>
                    <td>{row.signal_strength}%</td>
                    <td>{row.online ? "是" : "否"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
