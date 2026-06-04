# 园区巡检机器人后端

该后端使用 FastAPI + SQLite 实现，覆盖 SRS/STD 中 FU-001 到 FU-007 的核心测试流程。

## 启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

服务启动后访问：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`GET /api/health`
- 路由记录：`GET /api/routes`

## 默认账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | admin |
| center | center123 | control_center |
| duty | duty123 | duty_manager |
| security | security123 | security |
| maintainer | maintainer123 | maintainer |

登录接口为 `POST /api/auth/login`。调试时也可以使用请求头 `X-Role` 指定角色。

## 测试项接口映射

- FU-001 巡检任务管理：`/api/tasks`
- FU-002 自主巡检执行：`/api/inspection/*`
- FU-003 危险识别与告警：`/api/events/detect`、`/api/events/flush-cache`
- FU-004 危险现场处置：`/api/events/{event_id}/dispose`
- FU-005 设备状态监控：`/api/devices/status`
- FU-006 系统维护：`/api/maintenance/operate`、`/api/maintenance/logs`
- FU-007 数据查询与统计：`/api/query`、`/api/query/export`

## 关键接口补充

- 任务下发：`POST /api/tasks/{task_id}/dispatch`
- 巡检点确认：`POST /api/inspection/{task_id}/confirm`
- 后端图像识别：`POST /api/events/detect`

危险识别接口不要求调用方直接给出最终危险类型。后端会根据 `image_url`、`image_tags`、`image_features` 推断火警、烟雾、入侵、越界停留或漏电风险，并在返回值中给出 `inference`。

示例：

```json
{
  "image_url": "/camera/frame-smoke-001.jpg",
  "image_tags": ["smoke", "gray haze"],
  "image_features": {
    "smoke_score": 0.95
  },
  "network_online": true
}
```
