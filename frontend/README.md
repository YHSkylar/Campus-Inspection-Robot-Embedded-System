# 园区巡检机器人前端控制中心

基于 React + Vite + TypeScript 构建，对接 `backend/` FastAPI 后端，适配 `embedded/` 嵌入式传感器子系统上报的数据格式。

**不修改后端和嵌入式代码**，前端通过 HTTP API 与后端通信。

## 功能模块（对齐 SRS FU-001 ~ FU-007）

| 模块 | 页面 | 后端接口 |
| --- | --- | --- |
| FU-001 巡检任务管理 | `/tasks` | `GET/POST/PATCH/DELETE /api/tasks` |
| FU-002 自主巡检执行 | `/inspection` | `POST /api/inspection/*` |
| FU-003 危险识别与告警 | `/events` | `GET /api/events`, `POST /api/events/flush-cache` |
| FU-004 危险现场处置 | `/events` | `POST /api/events/{id}/dispose` |
| FU-005 设备状态监控 | `/devices` | `GET /api/devices/status/*` |
| FU-006 系统维护 | `/maintenance` | `POST /api/maintenance/operate`, `GET /api/maintenance/logs` |
| FU-007 数据查询与统计 | `/query` | `GET /api/query`, `GET /api/query/export` |

## 启动方式

### 1. 开发模式

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`（开发模式自动代理 `/api` 到后端）

### 2. 后端单服务模式

```bash
cd frontend
npm install
npm run build

cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

页面和 API 都通过后端服务访问：

- 前端页面：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`

## 默认账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 系统管理员 |
| center | center123 | 控制中心 |
| duty | duty123 | 值班主管 |
| security | security123 | 安保 |
| maintainer | maintainer123 | 维护工程师 |

## 与嵌入式系统的对接说明

嵌入式端通过 HTTP 上报至后端，前端实时展示：

- **危险事件**：嵌入式检测火焰/烟雾/障碍/边界/未授权人员后，调用 `POST /api/events/detect` 上报，前端在「危险告警」页展示
- **设备状态**：嵌入式周期上报 `POST /api/devices/status`，前端在「设备监控」页展示降级模式与传感器状态
- **缓存补发**：网络中断时事件缓存，恢复后可通过「补发缓存」按钮触发 `POST /api/events/flush-cache`

## 角色权限

- **控制中心/值班主管**：任务创建、下发、修改、删除
- **安保/控制中心**：巡检启动、紧急暂停、危险事件处置
- **维护工程师**：系统维护操作、完整日志查看
- **管理员**：全部权限
