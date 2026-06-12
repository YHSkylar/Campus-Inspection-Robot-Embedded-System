# ROS 工作补充记录

## 1. 本轮目标

在原有“嵌入式传感器子系统”基础上，参考 ROS 资料继续把代码补到可接入 ROS 运行环境的程度，而不是只停留在模拟版。

## 2. 参考资料

- [启智ROS版_实验指导书_1.3.5.pdf](</D:/A北京航空航天大学/2026春季/软工嵌入式/ROS 资料/启智 ROS/启智ROS版_实验指导书_1.3.5.pdf>)
- [ROS机器人开发实践.pdf](</D:/A北京航空航天大学/2026春季/软工嵌入式/ROS 资料/ROS机器人开发实践.pdf>)

## 3. 从资料中提取出的关键结论

1. 速度控制普遍围绕 `/cmd_vel` + `geometry_msgs/Twist`
2. 激光雷达输入围绕 `/scan` + `sensor_msgs/LaserScan`
3. 位姿与里程计围绕 `/odom` + `nav_msgs/Odometry`
4. 摄像头图像 topic 常见为 `/usb_cam/image_raw` 或 `/kinect2/hd/image_color`
5. ROS 图像到 OpenCV 一般通过 `cv_bridge`
6. 底盘控制通常需要持续发布速度命令，而不是只发一次

## 4. 已完成的 ROS 代码补充

新增：

- [ros_support.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\ros_support.py)
- [ros_node.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\ros_node.py)
- [ros_config.json](E:\Campus_Inspection_Robot_Embedded_System\config\ros_config.json)
- [test_ros_support.py](E:\Campus_Inspection_Robot_Embedded_System\tests\test_ros_support.py)

调整：

- [config.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\config.py)
- [interfaces.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\interfaces.py)

## 5. 新增能力

### 5.1 ROS 输入侧

已支持从 ROS topic 取：

1. 烟雾/热敏
2. 电压/电流
3. 人脸识别结果
4. 设备状态
5. 机器人位姿
6. 激光雷达扫描

### 5.2 ROS 输出侧

已支持：

1. 向 `/inspection/abnormal_event` 发布异常事件
2. 向 `/cmd_vel` 发布离开危险区域的速度命令

### 5.3 安全退避

新增了基于 `/scan` 的退避决策：

1. 后方安全时，直接后退
2. 后方被障碍物占据时，先旋转

这比原来的“只记录离开动作”更接近真实 ROS 机器人执行逻辑。

## 6. 测试结果

本轮新增测试覆盖：

1. ROS JSON payload 解析
2. 四元数转 yaw
3. 后方安全时的后退指令生成
4. 后方受阻时的旋转指令生成

与原有测试一起运行后，整体通过。

## 7. 当前仍保留的限制

虽然已经接到 ROS 层，但下面这些部分仍然是“接口已预留，尚未绑实机”的状态：

1. 烟雾/热敏真实驱动节点
2. 电压/电流真实驱动节点
3. 人脸识别真实节点
4. 控制中心真实 ROS 上位机消费节点
5. 更细的地图区域识别逻辑

## 8. 后续建议

继续往真实实验平台推进时，建议优先做：

1. 确认实际 topic 名称
2. 确认识别结果消息格式
3. 用自定义 ROS msg 代替 `std_msgs/String + JSON`
4. 将 `area_id` 改为动态输入
5. 和底盘/导航模块做一次真实联调
