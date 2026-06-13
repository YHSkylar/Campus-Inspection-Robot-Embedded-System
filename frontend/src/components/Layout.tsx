import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { ROLE_LABELS } from "../api/types";
import type { AuthUser } from "../hooks/useAuth";
import { clearUser } from "../hooks/useAuth";

interface LayoutProps {
  user: AuthUser;
}

const NAV_ITEMS = [
  { to: "/", label: "总览", icon: "📊" },
  { to: "/tasks", label: "巡检任务", icon: "📋" },
  { to: "/inspection", label: "巡检执行", icon: "🤖" },
  { to: "/events", label: "危险告警", icon: "🚨" },
  { to: "/devices", label: "设备监控", icon: "📡" },
  { to: "/maintenance", label: "系统维护", icon: "🔧" },
  { to: "/query", label: "数据查询", icon: "📈" },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "系统总览",
  "/tasks": "巡检任务管理",
  "/inspection": "自主巡检执行",
  "/events": "危险识别与告警",
  "/devices": "设备状态监控",
  "/maintenance": "系统维护",
  "/query": "数据查询与统计",
};

export function Layout({ user }: LayoutProps) {
  const navigate = useNavigate();
  const currentPath = window.location.pathname;
  const pageTitle = PAGE_TITLES[currentPath] || "园区巡检机器人";

  function handleLogout() {
    clearUser();
    navigate("/login");
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>园区巡检机器人</h1>
          <p>控制中心 FU-001 ~ FU-007</p>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `nav-link${isActive ? " active" : ""}`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">
            <div>{user.username}</div>
            <div className="role">{ROLE_LABELS[user.role]}</div>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            style={{ marginTop: 12, width: "100%" }}
            onClick={handleLogout}
          >
            退出登录
          </button>
        </div>
      </aside>
      <div className="main-content">
        <header className="topbar">
          <h2>{pageTitle}</h2>
          <span className="refresh-indicator">后端 API · /api</span>
        </header>
        <main className="page-body">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
