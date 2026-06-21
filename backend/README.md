# 园区巡检机器人后端

该后端使用 FastAPI + SQLite，实现园区巡检机器人控制中心所需的任务管理、巡检执行、危险事件、设备状态、维护日志和数据查询接口。

当前机器人 ROS 执行层统一使用：

- `catkin_ws/src/campus_inspection_robot`
- ROS 包名：`campus_inspection_robot`

## 功能范围

- 巡检任务管理：`/api/tasks`
- 巡检执行流程：`/api/inspection/*`
- 危险事件识别与补发：`/api/events/*`
- 设备状态监控：`/api/devices/status`
- 系统维护：`/api/maintenance/*`
- 数据查询与导出：`/api/query*`

## 启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后可访问：

- 前端页面：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`GET /api/health`

开发模式下也可以单独启动前端：

```bash
cd frontend
npm install
npm run dev
```

此时前端入口是 `http://127.0.0.1:5173/`，开发服务器会把 `/api` 代理到后端。

## 默认账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | admin |
| center | center123 | control_center |
| duty | duty123 | duty_manager |
| security | security123 | security |
| maintainer | maintainer123 | maintainer |

登录接口：`POST /api/auth/login`

调试时也可以直接通过请求头 `X-Role` 指定角色。

## 与机器人 ROS 层的对接

机器人侧 `campus_inspection_robot` 会主动调用这些接口：

- 任务轮询：`GET /api/tasks`
- 任务下发：`POST /api/tasks/{task_id}/dispatch`
- 巡检开始：`POST /api/inspection/start`
- 点位确认：`POST /api/inspection/{task_id}/confirm`
- 障碍回报：`POST /api/inspection/{task_id}/obstacle`
- 危险事件：`POST /api/events/detect`
- 设备状态：`POST /api/devices/status`

机器人侧配置文件：

- `catkin_ws/src/campus_inspection_robot/config/campus_inspection.yaml`

其中 `backend.base_url` 必须配置成机器人实际可访问的后端地址，例如：

```yaml
backend:
  base_url: "http://192.168.1.100:8000/api"
```

## 火焰识别和人脸识别说明

当前这套系统中：

- 火焰识别使用任务点位中的 `fire_image_path`
- 人脸识别使用任务点位中的 `face_image_path`
- 白名单人脸样本图使用 `campus_inspection.yaml` 中的 `face.whitelist[].image_path`

后端不会依赖 ROS 实时视频流，而是接收机器人侧上报后的识别结果和事件数据。

## Ubuntu 机器人端部署

完整部署步骤见：

- [UBUNTU_DEPLOYMENT.md](../UBUNTU_DEPLOYMENT.md)
