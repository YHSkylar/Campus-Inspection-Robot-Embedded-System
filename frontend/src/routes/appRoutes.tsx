import type { ReactNode } from "react";

import { Dashboard } from "../pages/Dashboard";
import { Devices } from "../pages/Devices";
import { Events } from "../pages/Events";
import { Inspection } from "../pages/Inspection";
import { Maintenance } from "../pages/Maintenance";
import { QueryPage } from "../pages/Query";
import { Tasks } from "../pages/Tasks";
import type { AuthUser } from "../hooks/useAuth";

export interface NavItem {
  to: string;
  label: string;
  title: string;
  icon: string;
  end?: boolean;
}

interface ProtectedRouteConfig {
  path?: string;
  index?: boolean;
  nav: NavItem;
  render: (user: AuthUser) => ReactNode;
}

export const PROTECTED_ROUTES: ProtectedRouteConfig[] = [
  {
    index: true,
    nav: {
      to: "/",
      label: "总览",
      title: "系统总览",
      icon: "📊",
      end: true,
    },
    render: () => <Dashboard />,
  },
  {
    path: "tasks",
    nav: {
      to: "/tasks",
      label: "巡检任务",
      title: "巡检任务管理",
      icon: "📋",
    },
    render: (user) => <Tasks user={user} />,
  },
  {
    path: "inspection",
    nav: {
      to: "/inspection",
      label: "巡检执行",
      title: "自主巡检执行",
      icon: "🤖",
    },
    render: (user) => <Inspection user={user} />,
  },
  {
    path: "events",
    nav: {
      to: "/events",
      label: "危险告警",
      title: "危险识别与告警",
      icon: "🚨",
    },
    render: (user) => <Events user={user} />,
  },
  {
    path: "devices",
    nav: {
      to: "/devices",
      label: "设备监控",
      title: "设备状态监控",
      icon: "📡",
    },
    render: () => <Devices />,
  },
  {
    path: "maintenance",
    nav: {
      to: "/maintenance",
      label: "系统维护",
      title: "系统维护",
      icon: "🔧",
    },
    render: (user) => <Maintenance user={user} />,
  },
  {
    path: "query",
    nav: {
      to: "/query",
      label: "数据查询",
      title: "数据查询与统计",
      icon: "📈",
    },
    render: (user) => <QueryPage user={user} />,
  },
];

export const NAV_ITEMS = PROTECTED_ROUTES.map((route) => route.nav);

export const PAGE_TITLES = NAV_ITEMS.reduce<Record<string, string>>(
  (titles, item) => {
    titles[item.to] = item.title;
    return titles;
  },
  {},
);
