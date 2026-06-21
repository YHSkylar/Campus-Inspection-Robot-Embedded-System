# campus_inspection_robot Ubuntu 机器人端完整部署步骤

本文档适用于下面这套部署方式：

- Windows 电脑运行前端和后端
- Ubuntu 电脑连接机器人并运行 ROS
- ROS 包名：`campus_inspection_robot`

## 1. 需要上传到 Ubuntu 的内容

至少上传这些内容：

- `catkin_ws/`
- 地图文件 `map.yaml` 和对应 `.pgm`
- 火焰识别图片
- 人脸识别图片
- 白名单人脸样本图片

建议在 Ubuntu 上放成下面这种结构：

```text
/home/robot/project/
  catkin_ws/
  assets/
    fire/
    face/
    whitelist/
  maps/
```

## 2. Ubuntu 环境准备

确保 Ubuntu 机器已经安装：

- ROS1
- `catkin_make`
- `move_base`
- `map_server`
- `amcl`
- `waterplus_map_tools`
- `wpr_simulation`
- `wpb_home_tutorials`

如果是实机，还要确认机器人本身能正常提供：

- `/scan`
- `move_base`
- `/waterplus/get_waypoint_name`

## 3. 放置工作区

假设工作区路径为：

```bash
/home/robot/project/catkin_ws
```

进入工作区：

```bash
cd /home/robot/project/catkin_ws
```

## 4. 修改机器人侧配置

编辑：

```bash
/home/robot/project/catkin_ws/src/campus_inspection_robot/config/campus_inspection.yaml
```

重点检查：

### 4.1 后端地址

如果 Windows 主机 IP 是 `192.168.1.100`，改成：

```yaml
backend:
  base_url: "http://192.168.1.100:8000/api"
```

不要保留 `127.0.0.1`，否则机器人会把请求打到 Ubuntu 本机。

### 4.2 白名单样本图

例如：

```yaml
face:
  match_threshold: 0.82
  whitelist:
    - face_id: "security"
      label: "security"
      image_path: "/home/robot/project/assets/whitelist/security.jpg"
    - face_id: "maintainer"
      label: "maintainer"
      image_path: "/home/robot/project/assets/whitelist/maintainer.jpg"
```

### 4.3 激光话题

默认是：

```yaml
obstacle:
  scan_topic: "/scan"
```

如果你们雷达话题不是 `/scan`，这里要改成真实话题名。

## 5. 地图和航点

### 5.1 地图文件

把地图放到例如：

```bash
/home/robot/project/maps/campus_map.yaml
/home/robot/project/maps/campus_map.pgm
```

### 5.2 航点文件

编辑：

```bash
/home/robot/project/catkin_ws/src/campus_inspection_robot/config/waypoints.xml
```

前端任务里填的 `waypoint_name` 必须和这里一致。

如果还没录航点，可以用：

```bash
roslaunch campus_inspection_robot add_waypoint.launch map_file:=/home/robot/project/maps/campus_map.yaml
```

## 6. 编译 ROS 工作区

```bash
cd /home/robot/project/catkin_ws
catkin_make
source devel/setup.bash
```

建议把 `source /home/robot/project/catkin_ws/devel/setup.bash` 加到 `~/.bashrc`。

## 7. 启动前后端

### 7.1 Windows 启动后端

```powershell
cd "E:\new Campus\Campus-Inspection-Robot-Embedded-System-ljt\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 7.2 Windows 启动前端

```powershell
cd "E:\new Campus\Campus-Inspection-Robot-Embedded-System-ljt\frontend"
npm install
npm run dev
```

## 8. 启动机器人 ROS

### 8.1 实机模式

```bash
cd /home/robot/project/catkin_ws
source devel/setup.bash
roslaunch campus_inspection_robot hardware_runtime.launch map_file:=/home/robot/project/maps/campus_map.yaml
```

### 8.2 仿真模式

```bash
cd /home/robot/project/catkin_ws
source devel/setup.bash
roslaunch campus_inspection_robot campus_inspection_runtime.launch map_file:=/home/robot/project/maps/campus_map.yaml include_simulation:=true
```

## 9. 前端如何下发任务

在前端 `任务管理` 页面：

1. 创建任务
2. 为每个巡检点填写 `waypoint_name`
3. 需要火焰识别的点填写 `fire_image_path`
4. 需要人脸识别的点填写 `face_image_path`
5. 下发任务到 `robot-001`

图片路径必须写 Ubuntu 上的绝对路径，例如：

```text
/home/robot/project/assets/fire/fire01.jpg
/home/robot/project/assets/face/face01.jpg
```

不能再写 Windows 路径，例如 `E:\...`

## 10. 启动后应观察到的现象

- 机器人开始向航点移动
- `/transport/status` 有状态输出
- 前端 `设备监控` 页面持续刷新
- 前端 `巡检执行` 页面显示点位推进
- 前端 `危险告警` 页面出现火焰、人脸或障碍事件

## 11. 常见故障

### 11.1 机器人不动

重点检查：

- `waypoint_name` 是否存在于 `waypoints.xml`
- `move_base` 是否正常
- `/waterplus/get_waypoint_name` 是否存在

### 11.2 机器人连不上后端

重点检查：

- `backend.base_url` 是否还是 `127.0.0.1`
- Ubuntu 是否能访问 Windows IP
- Windows 防火墙是否放行 `8000`

### 11.3 识别没有结果

重点检查：

- `fire_image_path` 和 `face_image_path` 是否是 Ubuntu 真实路径
- 白名单样本图路径是否存在
- Ubuntu 是否安装了 OpenCV 和 NumPy

### 11.4 避障无效

重点检查：

- `/scan` 是否有数据
- `obstacle.scan_topic` 是否配置正确
- 雷达量程和阈值是否合适

## 12. 推荐启动顺序

1. Windows 启动后端
2. Windows 启动前端
3. Ubuntu `catkin_make`
4. Ubuntu `source devel/setup.bash`
5. Ubuntu 启动 `campus_inspection_robot`
6. 前端创建并下发任务
