import type { Role } from "../api/types";

export interface AuthUser {
  username: string;
  role: Role;
  token: string;
}

const STORAGE_KEY = "auth_user";

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveUser(user: AuthUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  localStorage.setItem("access_token", user.token);
}

export function clearUser(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem("access_token");
}

export function canManageTasks(role: Role): boolean {
  return role === "admin" || role === "control_center" || role === "duty_manager";
}

export function canOperateInspection(role: Role): boolean {
  return (
    role === "admin" ||
    role === "control_center" ||
    role === "duty_manager" ||
    role === "security"
  );
}

export function canDisposeEvents(role: Role): boolean {
  return role === "admin" || role === "control_center" || role === "security";
}

export function canMaintain(role: Role): boolean {
  return role === "admin" || role === "maintainer";
}

export function canViewSensitiveLogs(role: Role): boolean {
  return role === "admin" || role === "maintainer";
}
