import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ROLE_LABELS } from "../api/types";
import { API_BASE_URL, APP_NAME } from "../config/app";
import type { AuthUser } from "../hooks/useAuth";
import { clearUser } from "../hooks/useAuth";
import { NAV_ITEMS, PAGE_TITLES } from "../routes/appRoutes";

interface LayoutProps {
  user: AuthUser;
}

export function Layout({ user }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] || APP_NAME;

  function handleLogout() {
    clearUser();
    navigate("/login");
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>{APP_NAME}</h1>
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
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
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
          <span className="refresh-indicator">后端 API · {API_BASE_URL}</span>
        </header>
        <main className="page-body">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
