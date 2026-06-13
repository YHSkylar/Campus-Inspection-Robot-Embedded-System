import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { DeviceStatus, Robot } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

export function Devices() {
  const [current, setCurrent] = useState<DeviceStatus | null>(null);
  const [history, setHistory] = useState<DeviceStatus[]>([]);
  const [robot, setRobot] = useState<Robot | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 3000);
    return () => clearInterval(timer);
  }, []);

  async function loadData() {
    try {
      const [status, hist, robotData] = await Promise.all([
        api.currentDeviceStatus(),
        api.deviceHistory("robot-001"),
        api.getRobot("robot-001"),
      ]);
      setCurrent(status);
      setHistory(hist);
      setRobot(robotData);
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
          <div className="label">机器人名称</div>
          <div className="value" style={{ fontSize: 18 }}>
            {robot?.name || "-"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">电量</div>
          <div
            className={`value ${(current?.battery ?? 100) <= 20 ? "danger" : "success"}`}
          >
            {current?.battery ?? robot?.battery ?? "-"}%
          </div>
        </div>
        <div className="stat-card">
          <div className="label">在线状态</div>
          <div className="value" style={{ fontSize: 18 }}>
            {robot?.online ? (
              <span style={{ color: "var(--success)" }}>在线</span>
            ) : (
              <span style={{ color: "var(--danger)" }}>离线</span>
            )}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">实时设备状态</div>
          {current ? (
            <>
              <dl className="detail-grid">
                <dt>记录 ID</dt>
                <dd>{current.id}</dd>
                <dt>机器人 ID</dt>
                <dd>{current.robot_id}</dd>
                <dt>运行模式</dt>
                <dd>
                  <StatusBadge
                    status={current.mode}
                    label={current.mode === "degraded" ? "降级模式" : "主模式"}
                  />
                </dd>
                <dt>定位状态</dt>
                <dd>
                  <StatusBadge
                    status={current.localization}
                    label={
                      current.localization === "normal" ? "定位正常" : "定位丢失"
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
            <div className="empty-state">
              等待嵌入式端通过 POST /api/devices/status 上报数据
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">机器人信息</div>
          {robot ? (
            <dl className="detail-grid">
              <dt>ID</dt>
              <dd>{robot.id}</dd>
              <dt>名称</dt>
              <dd>{robot.name}</dd>
              <dt>状态</dt>
              <dd>
                <StatusBadge status={robot.status} label={robot.status} />
              </dd>
              <dt>模式</dt>
              <dd>
                <StatusBadge status={robot.mode} />
              </dd>
              <dt>电量</dt>
              <dd>{robot.battery}%</dd>
              <dt>位置</dt>
              <dd>
                {robot.location
                  ? JSON.stringify(robot.location)
                  : "未知"}
              </dd>
              <dt>更新</dt>
              <dd>{new Date(robot.updated_at).toLocaleString("zh-CN")}</dd>
            </dl>
          ) : (
            <div className="empty-state">加载中...</div>
          )}

          <div style={{ marginTop: 20, fontSize: 12, color: "var(--text-muted)" }}>
            嵌入式降级策略：烟雾/热敏故障禁用火灾识别，摄像头故障禁用入侵识别，电气传感器故障禁用漏电识别。
          </div>
        </div>
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
