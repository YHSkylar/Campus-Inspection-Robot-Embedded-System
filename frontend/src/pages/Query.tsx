import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { QueryResult } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import type { AuthUser } from "../hooks/useAuth";

interface QueryPageProps {
  user: AuthUser;
}

const DATA_TYPES = [
  { value: "events", label: "危险事件" },
  { value: "tasks", label: "巡检记录" },
  { value: "device_status", label: "设备状态" },
  { value: "disposal_records", label: "处置记录" },
  { value: "logs", label: "系统日志" },
  { value: "maintenance", label: "维护记录" },
];

export function QueryPage({ user }: QueryPageProps) {
  const [dataType, setDataType] = useState("events");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [exportInfo, setExportInfo] = useState<{
    file_name: string;
    rows: number;
    download_url: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleQuery() {
    setError("");
    setExportInfo(null);
    setLoading(true);
    try {
      const data = await api.queryData({
        data_type: dataType,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "查询失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setError("");
    setLoading(true);
    try {
      const data = await api.exportData({
        data_type: dataType,
        export_format: "xlsx",
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      });
      setExportInfo({
        file_name: data.file_name,
        rows: data.rows,
        download_url: data.download_url,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "导出失败");
    } finally {
      setLoading(false);
    }
  }

  function downloadJson() {
    if (!result?.items) return;
    const blob = new Blob([JSON.stringify(result.items, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${dataType}_export.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const columns =
    result && result.items.length > 0
      ? Object.keys(result.items[0] as Record<string, unknown>)
      : [];

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="card-title">数据查询 (FU-007)</div>
        <div className="filter-bar">
          <div className="form-group">
            <label>数据类型</label>
            <select
              className="form-control"
              value={dataType}
              onChange={(e) => setDataType(e.target.value)}
            >
              {DATA_TYPES.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {dt.label}
                </option>
              ))}
            </select>
          </div>
          {(dataType === "events" || dataType === "tasks") && (
            <div className="form-group">
              <label>状态筛选</label>
              <input
                className="form-control"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                placeholder="如 unhandled, running"
              />
            </div>
          )}
          {dataType === "events" && (
            <div className="form-group">
              <label>事件类型</label>
              <input
                className="form-control"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                placeholder="如 fire, intrusion"
              />
            </div>
          )}
          <button
            className="btn btn-primary"
            onClick={handleQuery}
            disabled={loading}
          >
            {loading ? "查询中..." : "查询"}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleExport}
            disabled={loading}
          >
            导出
          </button>
        </div>

        {result && (
          <div style={{ marginBottom: 12 }}>
            <StatusBadge
              status={result.permission === "full" ? "success" : "warning"}
              label={
                result.permission === "full"
                  ? `共 ${result.items.length} 条记录`
                  : result.message || "权限受限"
              }
            />
            {result.permission === "full" && result.items.length > 0 && (
              <button
                className="btn btn-secondary btn-sm"
                style={{ marginLeft: 12 }}
                onClick={downloadJson}
              >
                下载 JSON
              </button>
            )}
          </div>
        )}

        {exportInfo && (
          <div className="alert alert-success">
            导出成功：{exportInfo.file_name}，共 {exportInfo.rows} 行
            （后端返回路径: {exportInfo.download_url}）
          </div>
        )}

        {result && result.items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {columns.slice(0, 8).map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.items.slice(0, 100).map((item, i) => {
                  const row = item as Record<string, unknown>;
                  return (
                    <tr key={i}>
                      {columns.slice(0, 8).map((col) => (
                        <td key={col}>
                          {typeof row[col] === "object"
                            ? JSON.stringify(row[col])
                            : String(row[col] ?? "-")}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : result ? (
          <div className="empty-state">无匹配数据</div>
        ) : null}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">查询说明</div>
        <p style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.8 }}>
          当前用户：<strong>{user.username}</strong>（{user.role}）。
          日志和维护记录为敏感数据，仅 admin 和 maintainer 可查看完整内容。
          导出接口返回数据列表，前端支持 JSON 本地下载。
        </p>
      </div>
    </>
  );
}
