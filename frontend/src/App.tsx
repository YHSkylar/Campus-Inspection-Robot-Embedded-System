import { useState } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { Layout } from "./components/Layout";
import { getStoredUser } from "./hooks/useAuth";
import type { AuthUser } from "./hooks/useAuth";
import { Dashboard } from "./pages/Dashboard";
import { Devices } from "./pages/Devices";
import { Events } from "./pages/Events";
import { Inspection } from "./pages/Inspection";
import { Login } from "./pages/Login";
import { Maintenance } from "./pages/Maintenance";
import { QueryPage } from "./pages/Query";
import { Tasks } from "./pages/Tasks";

function RequireAuth({
  user,
  children,
}: {
  user: AuthUser | null;
  children: React.ReactNode;
}) {
  const location = useLocation();
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(getStoredUser);

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={setUser} />} />
      <Route
        element={
          <RequireAuth user={user}>
            <Layout user={user!} />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="tasks" element={<Tasks user={user!} />} />
        <Route path="inspection" element={<Inspection user={user!} />} />
        <Route path="events" element={<Events user={user!} />} />
        <Route path="devices" element={<Devices />} />
        <Route path="maintenance" element={<Maintenance user={user!} />} />
        <Route path="query" element={<QueryPage user={user!} />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
