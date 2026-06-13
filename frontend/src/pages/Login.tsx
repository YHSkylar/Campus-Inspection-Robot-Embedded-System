import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { saveUser } from "../hooks/useAuth";
import type { AuthUser } from "../hooks/useAuth";

interface LoginProps {
  onLogin: (user: AuthUser) => void;
}

export function Login({ onLogin }: LoginProps) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("center");
  const [password, setPassword] = useState("center123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(username, password);
      const user: AuthUser = {
        username: res.username,
        role: res.role,
        token: res.access_token,
      };
      saveUser(user);
      onLogin(user);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>园区巡检机器人控制中心</h1>
        <p className="subtitle">对接后端 FastAPI · 适配嵌入式传感器子系统</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>用户名</label>
            <input
              className="form-control"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              required
            />
          </div>
          <div className="form-group">
            <label>密码</label>
            <input
              className="form-control"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
            />
          </div>
          <button
            className="btn btn-primary"
            type="submit"
            disabled={loading}
            style={{ width: "100%", marginTop: 8 }}
          >
            {loading ? "登录中..." : "登录"}
          </button>
        </form>

        <div className="login-hint">
          <strong>测试账号：</strong>
          <br />
          管理员 <code>admin / admin123</code>
          <br />
          控制中心 <code>center / center123</code>
          <br />
          值班主管 <code>duty / duty123</code>
          <br />
          安保 <code>security / security123</code>
          <br />
          维护 <code>maintainer / maintainer123</code>
        </div>
      </div>
    </div>
  );
}
