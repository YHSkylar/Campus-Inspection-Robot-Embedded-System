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
import { Login } from "./pages/Login";
import { PROTECTED_ROUTES } from "./routes/appRoutes";

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
        {PROTECTED_ROUTES.map((route) => (
          <Route
            key={route.nav.to}
            index={route.index}
            path={route.path}
            element={route.render(user!)}
          />
        ))}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
