from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RosConfig, SystemConfig, load_config
from .demo import default_config_path
from .interfaces import CameraAdapter, ControlCenterClient, ElectricalSensor, MotionController, PoseProvider, SmokeThermalSensor, TelemetryProvider
from .models import ActionResult, CameraFrame, DeviceTelemetry, ElectricalReading, FaceMatch, Pose, SmokeThermalReading
from .repository import SQLiteRepository
from .runtime import EmbeddedDependencies, EmbeddedInspectionSystem
from .services import EventReporter, ResponseService

try:
    import rospy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import String
except Exception:  # pragma: no cover
    rospy = None
    Twist = None
    Odometry = None
    LaserScan = None
    String = None


@dataclass(slots=True)
class LaserScanSnapshot:
    angle_min: float
    angle_increment: float
    ranges: list[float]


@dataclass(slots=True)
class TwistCommand:
    linear_x: float
    angular_z: float
    duration_sec: float
    reason: str


def parse_smoke_thermal_payload(payload: str) -> SmokeThermalReading:
    data = json.loads(payload)
    return SmokeThermalReading(
        smoke_ppm=float(data["smoke_ppm"]),
        temperature_c=float(data["temperature_c"]),
    )


def parse_electrical_payload(payload: str) -> ElectricalReading:
    data = json.loads(payload)
    leakage_current = data.get("leakage_current_a")
    return ElectricalReading(
        voltage_v=float(data["voltage_v"]),
        current_a=float(data["current_a"]),
        leakage_current_a=float(leakage_current) if leakage_current is not None else None,
    )


def parse_face_result_payload(payload: str) -> CameraFrame:
    data = json.loads(payload)
    return CameraFrame(
        frame_id=str(data.get("frame_id", "")),
        capture_ref=str(data.get("capture_ref", "")),
        matches=[
            FaceMatch(
                person_id=str(item["person_id"]),
                display_name=str(item.get("display_name", item["person_id"])),
                confidence=float(item["confidence"]),
                authorized=bool(item["authorized"]),
                source=str(item.get("source", "ros_face_result")),
            )
            for item in data.get("matches", [])
        ],
        raw_payload=data,
    )


def parse_telemetry_payload(payload: str) -> DeviceTelemetry:
    data = json.loads(payload)
    return DeviceTelemetry(
        battery_level=float(data.get("battery_level", 100.0)),
        cpu_usage=float(data.get("cpu_usage", 0.0)),
        memory_usage=float(data.get("memory_usage", 0.0)),
        board_temperature_c=float(data.get("board_temperature_c", 0.0)),
        comm_signal_dbm=int(data.get("comm_signal_dbm", -55)),
    )


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def choose_retreat_command(
    scan: LaserScanSnapshot | None,
    *,
    retreat_distance_m: float,
    reverse_speed_mps: float,
    rotate_speed_radps: float,
    step_sec: float,
    safe_back_distance_m: float,
    rear_arc_half_width_deg: float,
) -> TwistCommand:
    reverse_speed = -abs(reverse_speed_mps) if reverse_speed_mps != 0 else -0.2
    if scan is None or not scan.ranges:
        duration = max(retreat_distance_m / abs(reverse_speed), step_sec)
        return TwistCommand(reverse_speed, 0.0, duration, "scan_unavailable_reverse")

    rear_half_width = math.radians(rear_arc_half_width_deg)
    nearest_rear = math.inf
    for index, distance in enumerate(scan.ranges):
        if distance is None or distance <= 0:
            continue
        angle = scan.angle_min + (index * scan.angle_increment)
        wrapped = abs(abs(angle) - math.pi)
        if wrapped <= rear_half_width:
            nearest_rear = min(nearest_rear, distance)

    if nearest_rear < safe_back_distance_m:
        return TwistCommand(0.0, abs(rotate_speed_radps), max(step_sec, 1.0), "rear_blocked_rotate")

    duration = max(retreat_distance_m / abs(reverse_speed), step_sec)
    return TwistCommand(reverse_speed, 0.0, duration, "rear_clear_reverse")


def _require_ros() -> None:
    if rospy is None:
        raise RuntimeError("ROS runtime is unavailable. Install rospy in the ROS environment.")


class _LatestValue:
    def __init__(self) -> None:
        self._value: Any | None = None
        self._lock = threading.Lock()

    def set(self, value: Any) -> None:
        with self._lock:
            self._value = value

    def get(self) -> Any | None:
        with self._lock:
            return self._value


class RosStringTopicSmokeThermalSensor(SmokeThermalSensor):
    def __init__(self, topic: str, queue_size: int = 10) -> None:
        _require_ros()
        self._latest = _LatestValue()
        rospy.Subscriber(topic, String, self._callback, queue_size=queue_size)

    def _callback(self, msg) -> None:
        self._latest.set(msg.data)

    def read(self) -> SmokeThermalReading:
        payload = self._latest.get()
        if payload is None:
            raise RuntimeError("smoke/thermal ROS topic has no data yet")
        return parse_smoke_thermal_payload(payload)


class RosStringTopicElectricalSensor(ElectricalSensor):
    def __init__(self, topic: str, queue_size: int = 10) -> None:
        _require_ros()
        self._latest = _LatestValue()
        rospy.Subscriber(topic, String, self._callback, queue_size=queue_size)

    def _callback(self, msg) -> None:
        self._latest.set(msg.data)

    def read(self) -> ElectricalReading:
        payload = self._latest.get()
        if payload is None:
            raise RuntimeError("electrical ROS topic has no data yet")
        return parse_electrical_payload(payload)


class RosFaceResultCameraAdapter(CameraAdapter):
    def __init__(self, topic: str, queue_size: int = 10) -> None:
        _require_ros()
        self._latest = _LatestValue()
        rospy.Subscriber(topic, String, self._callback, queue_size=queue_size)

    def _callback(self, msg) -> None:
        self._latest.set(msg.data)

    def capture(self) -> CameraFrame:
        payload = self._latest.get()
        if payload is None:
            raise RuntimeError("face result ROS topic has no data yet")
        return parse_face_result_payload(payload)


class RosOdomPoseProvider(PoseProvider):
    def __init__(self, topic: str, area_id: str = "UNKNOWN", queue_size: int = 10) -> None:
        _require_ros()
        self.area_id = area_id
        self._latest = _LatestValue()
        rospy.Subscriber(topic, Odometry, self._callback, queue_size=queue_size)

    def _callback(self, msg) -> None:
        self._latest.set(msg)

    def get_pose(self) -> Pose:
        msg = self._latest.get()
        if msg is None:
            raise RuntimeError("odometry ROS topic has no data yet")
        orientation = msg.pose.pose.orientation
        return Pose(
            x=float(msg.pose.pose.position.x),
            y=float(msg.pose.pose.position.y),
            theta=quaternion_to_yaw(orientation.x, orientation.y, orientation.z, orientation.w),
            area_id=self.area_id,
        )


class RosStringTopicTelemetryProvider(TelemetryProvider):
    def __init__(self, topic: str, queue_size: int = 10) -> None:
        _require_ros()
        self._latest = _LatestValue()
        rospy.Subscriber(topic, String, self._callback, queue_size=queue_size)

    def _callback(self, msg) -> None:
        self._latest.set(msg.data)

    def get_telemetry(self) -> DeviceTelemetry:
        payload = self._latest.get()
        if payload is None:
            return DeviceTelemetry(
                battery_level=100.0,
                cpu_usage=0.0,
                memory_usage=0.0,
                board_temperature_c=0.0,
                comm_signal_dbm=-55,
            )
        return parse_telemetry_payload(payload)


class RosEventTopicClient(ControlCenterClient):
    def __init__(self, topic: str, queue_size: int = 10) -> None:
        _require_ros()
        self.publisher = rospy.Publisher(topic, String, queue_size=queue_size)

    def report_event(self, event) -> ActionResult:
        self.publisher.publish(String(data=json.dumps(event.to_payload(), ensure_ascii=False)))
        return ActionResult(ok=True, message="reported_to_ros_topic")


class RosMotionController(MotionController):
    def __init__(self, ros_config: RosConfig) -> None:
        _require_ros()
        self.ros_config = ros_config
        self.publisher = rospy.Publisher(ros_config.cmd_vel_topic, Twist, queue_size=ros_config.queue_size)
        self._latest_scan = _LatestValue()
        rospy.Subscriber(ros_config.scan_topic, LaserScan, self._scan_callback, queue_size=ros_config.queue_size)

    def _scan_callback(self, msg) -> None:
        self._latest_scan.set(
            LaserScanSnapshot(
                angle_min=float(msg.angle_min),
                angle_increment=float(msg.angle_increment),
                ranges=[float(item) for item in msg.ranges],
            )
        )

    def leave_danger_area(self, event, retreat_distance_m: float) -> ActionResult:
        command = choose_retreat_command(
            self._latest_scan.get(),
            retreat_distance_m=retreat_distance_m,
            reverse_speed_mps=self.ros_config.retreat_linear_speed_mps,
            rotate_speed_radps=self.ros_config.retreat_angular_speed_radps,
            step_sec=self.ros_config.retreat_step_sec,
            safe_back_distance_m=self.ros_config.safe_back_distance_m,
            rear_arc_half_width_deg=self.ros_config.rear_arc_half_width_deg,
        )
        twist = Twist()
        twist.linear.x = command.linear_x
        twist.angular.z = command.angular_z
        stop = Twist()
        end_at = time.time() + command.duration_sec
        rate = rospy.Rate(max(self.ros_config.retreat_publish_hz, 1.0))
        while not rospy.is_shutdown() and time.time() < end_at:
            self.publisher.publish(twist)
            rate.sleep()
        self.publisher.publish(stop)
        return ActionResult(ok=True, message=command.reason)


class RosInspectionNode:
    def __init__(self, config: SystemConfig) -> None:
        _require_ros()
        if config.ros is None or not config.ros.enabled:
            raise RuntimeError("ROS config is missing or disabled")
        ros_config = config.ros
        repository = SQLiteRepository(config.cache_db_path)
        deps = EmbeddedDependencies(
            smoke_thermal_sensor=RosStringTopicSmokeThermalSensor(ros_config.smoke_thermal_topic, ros_config.queue_size),
            electrical_sensor=RosStringTopicElectricalSensor(ros_config.electrical_topic, ros_config.queue_size),
            camera_adapter=RosFaceResultCameraAdapter(ros_config.face_result_topic, ros_config.queue_size),
            pose_provider=RosOdomPoseProvider(ros_config.odom_topic, ros_config.area_id, ros_config.queue_size),
            telemetry_provider=RosStringTopicTelemetryProvider(ros_config.telemetry_topic, ros_config.queue_size),
            repository=repository,
            reporter=EventReporter(repository, RosEventTopicClient(ros_config.event_topic, ros_config.queue_size)),
            response_service=ResponseService(
                repository=repository,
                motion_controller=RosMotionController(ros_config),
                retreat_distance_m=config.retreat_distance_m,
                handler_id=config.handler_id,
            ),
        )
        self.system = EmbeddedInspectionSystem(config, deps)
        self.ros_config = ros_config

    def spin(self) -> None:
        rate = rospy.Rate(max(self.ros_config.loop_hz, 1.0))
        while not rospy.is_shutdown():
            self.system.run_cycle()
            rate.sleep()


def default_ros_config_path() -> Path:
    return Path(default_config_path()).resolve().parent / "ros_config.json"


def build_ros_node_from_file(config_path: str | Path) -> RosInspectionNode:
    return RosInspectionNode(load_config(config_path))
