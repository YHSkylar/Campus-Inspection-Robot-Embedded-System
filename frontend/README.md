# 园区巡检机器人前端控制中心

该前端基于 React + Vite + TypeScript 构建，通过 HTTP API 对接 `backend/`，用于控制和观察园区巡检机器人执行状态。

当前机器人 ROS 执行层统一使用：

- `catkin_ws/src/campus_inspection_robot`
- ROS 包名：`campus_inspection_robot`

## 功能模块

| 模块 | 页面 | 后端接口 |
| --- | --- | --- |
| 巡检任务管理 | `/tasks` | `GET/POST/PATCH/DELETE /api/tasks` |
| 巡检执行 | `/inspection` | `POST /api/inspection/*` |
| 危险事件 | `/events` | `GET /api/events`, `POST /api/events/flush-cache` |
| 设备监控 | `/devices` | `GET /api/devices/status/*` |
| 系统维护 | `/maintenance` | `POST /api/maintenance/operate`, `GET /api/maintenance/logs` |
| 数据查询 | `/query` | `GET /api/query`, `GET /api/query/export` |

## 启动

开发模式：

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

访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端文档：`http://127.0.0.1:8000/docs`

后端单服务模式：

```bash
cd frontend
npm install
npm run build

cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

此时页面和 API 都由后端统一提供：

- 页面：`http://127.0.0.1:8000/`
- API：`http://127.0.0.1:8000/docs`

## 默认账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 系统管理员 |
| center | center123 | 控制中心 |
| duty | duty123 | 值班主管 |
| security | security123 | 安保 |
| maintainer | maintainer123 | 维护工程师 |

## 与机器人侧的配置对应关系

创建任务时，每个巡检点建议填写：

- `waypoint_name`
- `fire_image_path`
- `face_image_path`

其中：

- `waypoint_name` 必须与 `catkin_ws/src/campus_inspection_robot/config/waypoints.xml` 中的航点名一致
- `fire_image_path` 必须是 Ubuntu 机器人端真实存在的图片路径
- `face_image_path` 必须是 Ubuntu 机器人端真实存在的图片路径

## 机器人执行链路

前端只负责下发任务和显示状态，真正驱动机器人的是 ROS 包 `campus_inspection_robot`：

- 导航：`transport_node.py`
- 巡检执行：`campus_inspection_executor.py`
- 自动避障：`obstacle_monitor_node.py`

统一启动入口：

```bash
roslaunch campus_inspection_robot hardware_runtime.launch map_file:=/absolute/path/to/map.yaml
```

