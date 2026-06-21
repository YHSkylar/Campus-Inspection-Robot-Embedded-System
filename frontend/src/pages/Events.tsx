import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { DangerEvent, DisposeAction, EventType } from "../api/types";
import { DISPOSE_LABELS, EVENT_LABELS } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import type { AuthUser } from "../hooks/useAuth";
import { canDisposeEvents } from "../hooks/useAuth";

interface EventsProps {
  user: AuthUser;
}

export function Events({ user }: EventsProps) {
  const [events, setEvents] = useState<DangerEvent[]>([]);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<DangerEvent | null>(null);
  const [disposeAction, setDisposeAction] = useState<DisposeAction>("handled");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canDispose = canDisposeEvents(user.role);

  useEffect(() => {
    loadEvents();
    const timer = setInterval(loadEvents, 8000);
    return () => clearInterval(timer);
  }, [typeFilter, statusFilter]);

  async function loadEvents() {
    try {
      const data = await api.listEvents(
        typeFilter || undefined,
        statusFilter || undefined,
      );
      setEvents(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  async function handleFlushCache() {
    setError("");
    try {
      const res = await api.flushCache();
      setSuccess(`已补发 ${res.flushed} 条缓存事件`);
      loadEvents();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "补发失败");
    }
  }

  async function handleDispose() {
    if (!selected) return;
    setError("");
    try {
      await api.disposeEvent(selected.id, {
        action: disposeAction,
        executor: user.username,
        reason: reason || undefined,
      });
      setSuccess("处置指令已下发");
      setSelected(null);
      setReason("");
      loadEvents();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "处置失败");
    }
  }

  const cachedCount = events.filter((e) => e.report_status === "cached").length;

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="filter-bar">
        <div className="form-group">
          <label>事件类型</label>
          <select
            className="form-control"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">全部</option>
            {Object.entries(EVENT_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>处置状态</label>
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">全部</option>
            <option value="unhandled">未处置</option>
            <option value="processing">处置中</option>
            <option value="handled">已处置</option>
            <option value="false_alarm">误报</option>
            <option value="monitoring">监控中</option>
          </select>
        </div>
        {cachedCount > 0 && (
          <button className="btn btn-warning btn-secondary" onClick={handleFlushCache}>
            补发缓存 ({cachedCount})
          </button>
        )}
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">危险事件列表</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>类型</th>
                  <th>置信度</th>
                  <th>状态</th>
                  <th>上报</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="empty-state">
                      暂无事件（嵌入式端检测到异常后将上报至此）
                    </td>
                  </tr>
                ) : (
                  events.map((ev) => (
                    <tr
                      key={ev.id}
                      className={`event-priority-${Math.min(ev.priority, 3)}`}
                      style={{
                        cursor: "pointer",
                        background:
                          selected?.id === ev.id
                            ? "var(--bg-hover)"
                            : undefined,
                      }}
                      onClick={() => setSelected(ev)}
                    >
                  <td>{EVENT_LABELS[ev.event_type as EventType] || ev.event_type}</td>
                      <td>{(ev.confidence * 100).toFixed(0)}%</td>
                      <td>
                        <StatusBadge status={ev.status} />
                      </td>
                      <td>
                        <StatusBadge status={ev.report_status} />
                      </td>
                      <td>{new Date(ev.created_at).toLocaleString("zh-CN")}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">事件详情与处置</div>
          {!selected ? (
            <div className="empty-state">点击左侧事件查看详情</div>
          ) : (
            <>
              <dl className="detail-grid" style={{ marginBottom: 20 }}>
                <dt>事件 ID</dt>
                <dd>{selected.id}</dd>
                <dt>机器人</dt>
                <dd>{selected.robot_id}</dd>
                <dt>类型</dt>
                <dd>
                  {EVENT_LABELS[selected.event_type as EventType] ||
                    selected.event_type}
                </dd>
                <dt>置信度</dt>
                <dd>{(selected.confidence * 100).toFixed(1)}%</dd>
                <dt>优先级</dt>
                <dd>{selected.priority}</dd>
                <dt>状态</dt>
                <dd>
                  <StatusBadge status={selected.status} />
                </dd>
                <dt>上报状态</dt>
                <dd>
                  <StatusBadge status={selected.report_status} />
                </dd>
                <dt>本地告警</dt>
                <dd>{selected.local_alert ? "是" : "否"}</dd>
                {selected.event_type === "unauthorized_person" && (
                  <>
                    <dt>人脸校验</dt>
                    <dd>未命中白名单即告警</dd>
                  </>
                )}
                <dt>语音播报</dt>
                <dd>{selected.voice_broadcast ? "是" : "否"}</dd>
                {selected.snapshot_url && (
                  <>
                    <dt>快照</dt>
                    <dd>{selected.snapshot_url}</dd>
                  </>
                )}
              </dl>

              {canDispose && selected.status === "unhandled" && (
                <>
                  <div className="form-group">
                    <label>处置动作</label>
                    <select
                      className="form-control"
                      value={disposeAction}
                      onChange={(e) =>
                        setDisposeAction(e.target.value as DisposeAction)
                      }
                    >
                      {Object.entries(DISPOSE_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>备注</label>
                    <input
                      className="form-control"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="处置原因或说明"
                    />
                  </div>
                  <button className="btn btn-primary" onClick={handleDispose}>
                    执行处置
                  </button>
                </>
              )}

              {!canDispose && (
                <div className="alert alert-info">当前角色无处置权限</div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
