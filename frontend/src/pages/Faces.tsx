import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { KnownFace } from "../api/types";
import type { AuthUser } from "../hooks/useAuth";

interface FacesProps {
  user: AuthUser;
}

function canManageFaces(role: AuthUser["role"]): boolean {
  return (
    role === "admin" ||
    role === "control_center" ||
    role === "security" ||
    role === "maintainer"
  );
}

export function Faces({ user }: FacesProps) {
  const [faces, setFaces] = useState<KnownFace[]>([]);
  const [faceId, setFaceId] = useState("");
  const [name, setName] = useState("");
  const [roleName, setRoleName] = useState("security");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const canManage = canManageFaces(user.role);

  useEffect(() => {
    loadFaces();
  }, []);

  async function loadFaces() {
    try {
      const data = await api.listFaces();
      setFaces(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "加载失败");
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      if (!file) {
        throw new Error("请先上传样本图");
      }
      await api.uploadFace(
        {
          face_id: faceId.trim(),
          name: name.trim(),
          role: roleName.trim() || undefined,
          filename: file.name,
        },
        file,
      );
      setSuccess("白名单已保存");
      setFaceId("");
      setName("");
      setRoleName("security");
      setFile(null);
      const input = document.getElementById("face-file") as HTMLInputElement | null;
      if (input) input.value = "";
      loadFaces();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(face: KnownFace) {
    if (!window.confirm(`删除 ${face.name}？`)) return;
    setError("");
    setSuccess("");
    try {
      await api.deleteFace(face.id);
      setSuccess("白名单已删除");
      loadFaces();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败");
    }
  }

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">人脸录入</div>
          {!canManage ? (
            <div className="alert alert-info">当前角色无白名单维护权限</div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>人脸 ID</label>
                  <input
                    className="form-control"
                    value={faceId}
                    onChange={(e) => setFaceId(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>姓名/标签</label>
                  <input
                    className="form-control"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>角色</label>
                <input
                  className="form-control"
                  value={roleName}
                  onChange={(e) => setRoleName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>上传样本图</label>
                <input
                  id="face-file"
                  className="form-control"
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </div>

              <button
                className="btn btn-primary"
                type="submit"
                disabled={loading || !faceId.trim() || !name.trim() || !file}
              >
                {loading ? "保存中..." : "保存白名单"}
              </button>
            </form>
          )}
        </div>

        <div className="card">
          <div className="card-title">白名单列表</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>姓名/标签</th>
                  <th>角色</th>
                  <th>样本</th>
                  <th>更新</th>
                  {canManage && <th>操作</th>}
                </tr>
              </thead>
              <tbody>
                {faces.length === 0 ? (
                  <tr>
                    <td colSpan={canManage ? 6 : 5} className="empty-state">
                      暂无白名单
                    </td>
                  </tr>
                ) : (
                  faces.map((face) => (
                    <tr key={face.id}>
                      <td>{face.id}</td>
                      <td>{face.name}</td>
                      <td>{face.role || "-"}</td>
                      <td>{face.image_path ? "已上传" : "-"}</td>
                      <td>{new Date(face.updated_at).toLocaleString("zh-CN")}</td>
                      {canManage && (
                        <td>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDelete(face)}
                          >
                            删除
                          </button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
