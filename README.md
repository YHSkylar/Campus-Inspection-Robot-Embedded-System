# 园区巡检机器人嵌入式传感器子系统

本目录实现了机器人端“嵌入式（传感器）部分”的可运行代码，范围按你的要求缩小为 3 类异常：

1. 火灾探测：烟雾/热敏传感器联合判定
2. 非法人员入侵：摄像头 + 人脸识别结果判定
3. 漏电：电压/电流传感器联合判定

异常处置流程按要求简化为：

1. 上报控制中心
2. 机器人离开危险区域

实现遵循文档中的 SRS / SDD / STD 约束，保留了对真实硬件、ROS 节点、控制中心接口的扩展位。

## 1. 对齐文档的设计点

本实现与四份参考文档保持一致的核心点如下：

1. 模块边界对齐 SDD：
   - 感知采集与异常识别模块
   - 设备状态监控与降级控制
   - 报警上报与本地缓存
   - 异常现场处置简化为“上报 + 离开”
2. 数据字段对齐 SDD：
   - `sensor_data`
   - `abnormal_event`
   - `disposal_record`
   - `device_status`
3. 关键流程对齐 SRS / STD：
   - 低置信度不立即告警
   - 连续确认后升级为有效异常
   - 网络中断时本地缓存，恢复后补发
   - 多异常按优先级上报：`fire > intrusion > leakage`
   - 传感器故障进入降级模式，关闭相关识别能力
4. 非功能指标留口：
   - 识别刷新周期按 `cycle_interval_sec` 控制
   - 告警上报链路、缓存补发、日志留痕均已预留

## 2. 目录结构

```text
E:\Campus_Inspection_Robot_Embedded_System
├─ campus_inspection_embedded
│  ├─ __init__.py
│  ├─ __main__.py
│  ├─ config.py
│  ├─ detectors.py
│  ├─ demo.py
│  ├─ interfaces.py
│  ├─ models.py
│  ├─ repository.py
│  ├─ runtime.py
│  └─ services.py
├─ config
│  └─ default_config.json
├─ tests
│  └─ test_system.py
├─ pyproject.toml
└─ 工作记录.md
```

## 3. 已实现功能

### 3.1 火灾探测

文件：
- [detectors.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\detectors.py)

实现方式：
- 读取烟雾浓度 `smoke_ppm`
- 读取热敏温度 `temperature_c`
- 按阈值融合生成置信度
- 连续多帧达到告警阈值后触发 `fire` 事件
- 支持 `warning / critical` 严重级别

默认规则：
- 烟雾阈值：`120 ppm`
- 温度阈值：`65 C`
- 连续 3 帧确认

### 3.2 非法人员入侵

文件：
- [detectors.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\detectors.py)
- [interfaces.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\interfaces.py)

实现方式：
- 摄像头接口返回 `CameraFrame`
- 人脸识别结果以 `FaceMatch` 列表注入
- 在限制区域内，发现 `authorized=False` 的人员则判定为非法入侵
- 连续 3 帧确认后触发 `intrusion` 事件

说明：
- 这里已经把“人脸识别结果接入接口”留好了
- 你后续只需要把真实摄像头采集和真实人脸识别模型接到 `CameraAdapter` 上即可
- 当前 demo 使用脚本化的人脸识别结果模拟真实推理输出

### 3.3 漏电检测

文件：
- [detectors.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\detectors.py)

实现方式：
- 读取 `voltage_v / current_a / leakage_current_a`
- 若有剩余漏电流传感值，优先使用
- 若没有剩余漏电流传感值，则使用电压越界 + 电流异常进行联合判断
- 连续多帧确认后触发 `leakage` 事件

说明：
- 兼容“只有电压/电流传感器”的情况
- 也兼容后续你补接漏电流专用模块的情况

### 3.4 上报 + 离开

文件：
- [services.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\services.py)

流程：
1. 异常写入本地 SQLite
2. 尝试上报控制中心
3. 若网络失败，则保留 `reported=0`
4. 网络恢复后自动补发
5. 调用运动控制接口执行离开危险区域
6. 写入 `disposal_record`

### 3.5 设备状态监控与降级

文件：
- [runtime.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\runtime.py)

已实现：
- 周期写入 `device_status`
- 传感器异常自动进入 `degraded` 模式
- 摄像头故障时自动禁用入侵识别
- 烟雾/热敏故障时自动禁用火灾识别
- 电气传感器故障时自动禁用漏电识别

## 4. 运行方式

## 4.1 环境要求

- Python `>= 3.9`
- 当前实现不强依赖第三方库
- 因为本轮主要完成接口与嵌入式逻辑骨架，所以 demo 可直接运行

## 4.2 运行 demo

在仓库根目录执行：

```powershell
python -m campus_inspection_embedded
```

运行后会生成：

- 本地数据库：`runtime/embedded_runtime.db`
- 上报结果：`runtime/reported_events.jsonl`

demo 会模拟：
- 连续高烟雾/高温，触发火灾事件
- 连续陌生人脸，触发非法入侵事件
- 连续电气异常，触发漏电事件

## 4.3 运行测试

```powershell
python -m unittest discover -s tests -v
```

当前测试覆盖：
- 火灾连续确认
- 入侵事件网络断开缓存与恢复补发
- 摄像头故障进入降级模式
- 漏电阈值触发

## 5. 配置说明

配置文件：
- [default_config.json](E:\Campus_Inspection_Robot_Embedded_System\config\default_config.json)

关键配置项：

```json
{
  "cycle_interval_sec": 0.2,
  "retreat_distance_m": 3.0,
  "fire": {
    "smoke_ppm_threshold": 120.0,
    "temperature_c_threshold": 65.0,
    "confirmation_frames": 3
  },
  "intrusion": {
    "restricted_areas": ["A-3", "A-4", "B-1"],
    "confirmation_frames": 3
  },
  "leakage": {
    "min_voltage_v": 200.0,
    "max_voltage_v": 240.0,
    "max_current_a": 2.0,
    "leakage_current_threshold_a": 0.15
  }
}
```

你后续最常改的是：
- 告警阈值
- 连续确认帧数
- 限制区域
- 离开危险区的后退距离
- 本地 SQLite 路径
- 控制中心上报方式

## 6. 如何接真实硬件

## 6.1 接烟雾/热敏传感器

实现接口：
- [interfaces.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\interfaces.py) 中的 `SmokeThermalSensor`

你只需要补一个类：

```python
class MySmokeThermalSensor(SmokeThermalSensor):
    def read(self) -> SmokeThermalReading:
        # 从串口/I2C/ADC 读取真实数据
        return SmokeThermalReading(smoke_ppm=..., temperature_c=...)
```

## 6.2 接电压/电流传感器

实现接口：
- `ElectricalSensor`

```python
class MyElectricalSensor(ElectricalSensor):
    def read(self) -> ElectricalReading:
        return ElectricalReading(voltage_v=..., current_a=..., leakage_current_a=...)
```

## 6.3 接摄像头和人脸识别模型

实现接口：
- `CameraAdapter`

建议做法：
1. 摄像头负责采集图片/视频帧
2. 调用你的人脸识别模型
3. 将模型输出转成 `FaceMatch`
4. 返回 `CameraFrame`

```python
class MyCameraAdapter(CameraAdapter):
    def capture(self) -> CameraFrame:
        return CameraFrame(
            frame_id="...",
            capture_ref="/path/to/frame.jpg",
            matches=[
                FaceMatch(
                    person_id="stu_001",
                    display_name="张三",
                    confidence=0.97,
                    authorized=True
                )
            ]
        )
```

## 6.4 接控制中心上报

当前提供了两种实现：
- `JsonlControlCenterClient`：本地文件模拟上报
- `HttpControlCenterClient`：HTTP POST 上报

如果你们组后端已有接口，只要替换为真实 URL 即可。

## 6.5 接底盘“离开危险区域”

实现接口：
- `MotionController`

当前 `SimpleMotionController` 只是记录动作，真实机器人需要把它替换成：
- ROS topic 发布速度命令
- 串口给 MCU 发后退/转向命令
- 或调用底盘 SDK

## 7. 代码入口关系

主入口：
- [__main__.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\__main__.py)

核心调度：
- [runtime.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\runtime.py)

核心逻辑顺序：
1. 采集传感器数据
2. 保存 `sensor_data`
3. 保存 `device_status`
4. 执行三类异常检测
5. 连续确认与优先级排序
6. 写入 `abnormal_event`
7. 上报控制中心
8. 执行离开动作
9. 保存 `disposal_record`
10. 补发未上报事件

## 8. 数据落库说明

SQLite 表结构在 [repository.py](E:\Campus_Inspection_Robot_Embedded_System\campus_inspection_embedded\repository.py) 内初始化。

已实现表：
- `sensor_data`
- `abnormal_event`
- `disposal_record`
- `device_status`

关键字段：
- `abnormal_event.reported`
  - `0` 未上报
  - `1` 已上报
- `abnormal_event.status`
  - `unhandled`
  - `processing`
  - `handled`
  - `false_alarm`

## 9. 当前假设

因为文档没有给出具体硬件型号、通信协议和人脸库来源，本实现先采用以下默认假设：

1. 非法入侵判定规则为“白名单外人员进入限制区域”
2. 火灾采用烟雾 + 温度联合判定
3. 漏电优先用漏电流值，没有时退化为电压/电流异常联合判定
4. 异常处置在机器人侧只执行“上报 + 离开”，后续人工处置由控制中心闭环

如果你们组已经确定了：
- 具体烟雾/热敏/电流传感器型号
- 摄像头型号
- 人脸识别模型或人脸库格式
- ROS topic / 串口协议 / HTTP 接口

我可以下一轮直接把这些接口补成对应的真实驱动版本。
