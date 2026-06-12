# ROS 接入说明

本文件说明这次基于 ROS 资料对嵌入式部分做的补充，以及如何把当前代码接入 ROS 实机或仿真环境。

参考资料：

- [启智ROS版_实验指导书_1.3.5.pdf](</D:/A北京航空航天大学/2026春季/软工嵌入式/ROS 资料/启智 ROS/启智ROS版_实验指导书_1.3.5.pdf>)
- [ROS机器人开发实践.pdf](</D:/A北京航空航天大学/2026春季/软工嵌入式/ROS 资料/ROS机器人开发实践.pdf>)

## 1. 参考文档后落下来的接口约定

从两份资料里，和当前项目最相关的接口约定是：

1. 速度控制使用 `/cmd_vel`，消息类型 `geometry_msgs/Twist`
2. 激光雷达使用 `/scan`，消息类型 `sensor_msgs/LaserScan`
3. 里程计使用 `/odom`，消息类型 `nav_msgs/Odometry`
4. 摄像头原始图像一般使用 `/usb_cam/image_raw` 或 `/kinect2/hd/image_color`
5. 图像链路通常是 `sensor_msgs/Image` 配合 `cv_bridge`
6. 底盘侧普遍采用“持续发布速度消息”的方式控制运动

这些约定已经被补到当前代码里，而不是只停留在 README 说明层。

## 2. 新增代码

新增文件：

- [ros_support.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\ros_support.py)
- [ros_node.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\ros_node.py)
- [ros_config.json](E:\Campus_Inspection_Robot_Embedded_System\config\ros_config.json)
- [test_ros_support.py](E:\Campus_Inspection_Robot_Embedded_System\tests\test_ros_support.py)

扩展文件：

- [config.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\config.py)
- [interfaces.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\interfaces.py)

## 3. 新增 ROS 能力

### 3.1 传感器 ROS topic 适配

已实现：

1. `RosStringTopicSmokeThermalSensor`
   - 从 `/inspection/smoke_thermal` 读取烟雾/热敏 JSON
2. `RosStringTopicElectricalSensor`
   - 从 `/inspection/electrical` 读取电压/电流 JSON
3. `RosFaceResultCameraAdapter`
   - 从 `/inspection/face_matches` 读取人脸识别结果 JSON
4. `RosStringTopicTelemetryProvider`
   - 从 `/inspection/telemetry` 读取设备状态 JSON

说明：

这里采用 `std_msgs/String + JSON`，是为了避免你当前仓库还没有自定义 ROS msg 包时无法直接联调。后续如果你们组已经统一了 ROS 消息定义，可以再把这层替换成自定义 msg。

### 3.2 位姿与运动控制

已实现：

1. `RosOdomPoseProvider`
   - 从 `/odom` 读取机器人位置和四元数姿态
   - 内部转换成当前系统使用的 `Pose`
2. `RosMotionController`
   - 持续向 `/cmd_vel` 发布 `Twist`
   - 离开危险区域前先读取 `/scan`
   - 如果机器人后方安全，则执行后退
   - 如果后方有障碍，则改为原地旋转

这部分是根据两份文档里对 `cmd_vel`、`LaserScan`、底盘持续速度控制方式的描述做的。

### 3.3 异常事件 ROS 上报

已实现：

1. `RosEventTopicClient`
   - 将异常事件编码成 JSON
   - 发布到 `/inspection/abnormal_event`
2. `RosInspectionNode`
   - 以 ROS 节点方式运行当前整套嵌入式识别逻辑

## 4. ROS 运行方式

使用配置文件：

- [ros_config.json](E:\Campus_Inspection_Robot_Embedded_System\config\ros_config.json)

运行命令：

```powershell
python -m campus_inspection_embedded.ros_node --config config/ros_config.json
```

前提：

1. 已安装 ROS Python 环境
2. `rospy` 可导入
3. 若你要扩展成直接吃图像并做 OpenCV 转换，还要保证 `cv_bridge` 可用

## 5. 默认 topic 规划

当前默认 topic 如下：

1. `/cmd_vel`
   - 输出
   - `geometry_msgs/Twist`
2. `/odom`
   - 输入
   - `nav_msgs/Odometry`
3. `/scan`
   - 输入
   - `sensor_msgs/LaserScan`
4. `/inspection/smoke_thermal`
   - 输入
   - `std_msgs/String`
5. `/inspection/electrical`
   - 输入
   - `std_msgs/String`
6. `/inspection/face_matches`
   - 输入
   - `std_msgs/String`
7. `/inspection/telemetry`
   - 输入
   - `std_msgs/String`
8. `/inspection/abnormal_event`
   - 输出
   - `std_msgs/String`

## 6. JSON 数据格式

烟雾/热敏：

```json
{
  "smoke_ppm": 136.5,
  "temperature_c": 72.0
}
```

电气：

```json
{
  "voltage_v": 182.0,
  "current_a": 2.8,
  "leakage_current_a": 0.22
}
```

人脸识别：

```json
{
  "frame_id": "f103",
  "capture_ref": "topic://usb_cam/image_raw#103",
  "matches": [
    {
      "person_id": "unknown-1",
      "display_name": "UNKNOWN",
      "confidence": 0.94,
      "authorized": false
    }
  ]
}
```

设备状态：

```json
{
  "battery_level": 88.0,
  "cpu_usage": 23.0,
  "memory_usage": 35.0,
  "board_temperature_c": 44.0,
  "comm_signal_dbm": -50
}
```

## 7. 推荐的 ROS 节点拆分

为了让系统更清晰，建议拆成 4 类节点：

1. 传感器驱动节点
   - 摄像头、激光雷达、烟雾/热敏、电压/电流
2. 视觉识别节点
   - 订阅图像
   - 输出 `/inspection/face_matches`
3. 当前嵌入式异常识别节点
   - 订阅传感器结果
   - 判断三类异常
   - 上报异常并下发离开动作
4. 控制中心或上位机节点
   - 消费 `/inspection/abnormal_event`

## 8. 下一步建议

如果你准备继续做 ROS 实机联调，下一步最值得补的是：

1. 明确你们的摄像头实际 topic 名称
2. 明确人脸识别是不是独立节点
3. 给烟雾/热敏、电压/电流定义正式 ROS msg
4. 把区域 ID 从静态配置改成地图/导航模块动态输出
5. 如果底盘支持反馈，再把“离开动作完成状态”回写进处置记录
