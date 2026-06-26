import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DangerEvent, DeviceStatus, Task } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

export function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<DangerEvent[]>([]);
  const [device, setDevice] = useState<DeviceStatus | null>(null);
  const [health, setHealth] = useState<string>("");

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, []);

  async function loadData() {
    try {
      const [taskList, eventList, status, healthRes] = await Promise.all([
        api.listTasks(),
        api.listEvents(),
        api.currentDeviceStatus(),
        api.health(),
      ]);
      setTasks(taskList);
      setEvents(eventList);
      setDevice(status);
      setHealth(healthRes.status);
    } catch {
      // silent refresh
    }
  }

  const runningTasks = tasks.filter((t) => t.status === "running").length;
  const pendingEvents = events.filter((e) => e.status === "unhandled").length;
  const cachedEvents = events.filter((e) => e.report_status === "cached").length;

  return (
    <>
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">系统状态</div>
          <div className={`value ${health === "ok" ? "success" : "warning"}`}>
            {health === "ok" ? "正常" : "异常"}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">执行中任务</div>
          <div className="value">{runningTasks}</div>
        </div>
        <div className="stat-card">
          <div className="label">待处置告警</div>
          <div className={`value ${pendingEvents > 0 ? "danger" : ""}`}>
            {pendingEvents}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">缓存待补发</div>
          <div className={`value ${cachedEvents > 0 ? "warning" : ""}`}>
            {cachedEvents}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">机器人状态</div>
          {device ? (
            <dl className="detail-grid">
              <dt>电量</dt>
              <dd>
                {device.battery}%
                <div className="progress-bar">
                  <div
                    className="fill"
                    style={{
                      width: `${device.battery}%`,
                      background:
                        device.battery <= 20
                          ? "var(--danger)"
                          : "var(--primary)",
                    }}
                  />
                </div>
              </dd>
              <dt>运行模式</dt>
              <dd>
                <StatusBadge status={device.mode} />
              </dd>
              <dt>定位</dt>
              <dd>
                <StatusBadge
                  status={device.localization}
                  label={device.localization === "normal" ? "正常" : "丢失"}
                />
              </dd>
              <dt>在线</dt>
              <dd>
                <StatusBadge
                  status={device.online ? "success" : "offline"}
                  label={device.online ? "在线" : "离线"}
                />
              </dd>
              <dt>CPU / 内存</dt>
              <dd>
                {device.cpu_usage.toFixed(1)}% / {device.memory_usage.toFixed(1)}%
              </dd>
              <dt>信号强度</dt>
              <dd>{device.signal_strength}%</dd>
              {device.abnormal_flags.length > 0 && (
                <>
                  <dt>异常标记</dt>
                  <dd>{device.abnormal_flags.join(", ")}</dd>
                </>
              )}
            </dl>
          ) : (
            <div className="empty-state">暂无设备状态</div>
          )}
        </div>

        <div className="card">
          <div className="card-title">最近危险事件</div>
          {events.length === 0 ? (
            <div className="empty-state">暂无危险事件</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>置信度</th>
                    <th>状态</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  {events.slice(0, 5).map((ev) => (
                    <tr key={ev.id}>
                      <td>{ev.event_type}</td>
                      <td>{(ev.confidence * 100).toFixed(0)}%</td>
                      <td>
                        <StatusBadge status={ev.status} />
                      </td>
                      <td>{new Date(ev.created_at).toLocaleString("zh-CN")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">最近任务</div>
        {tasks.length === 0 ? (
          <div className="empty-state">暂无巡检任务</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务 ID</th>
                  <th>路线</th>
                  <th>模式</th>
                  <th>状态</th>
                  <th>下发</th>
                </tr>
              </thead>
              <tbody>
                {tasks.slice(0, 5).map((task) => (
                  <tr key={task.id}>
                    <td>{task.id}</td>
                    <td>{task.route_name}</td>
                    <td>{task.mode}</td>
                    <td>
                      <StatusBadge status={task.status} />
                    </td>
                    <td>
                      <StatusBadge status={task.dispatch_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
