from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DetectorConfig:
    suspicion_confidence_threshold: float
    alert_confidence_threshold: float
    confirmation_frames: int
    cooldown_sec: int


@dataclass(slots=True)
class FireDetectorConfig(DetectorConfig):
    smoke_ppm_threshold: float
    temperature_c_threshold: float
    critical_smoke_ppm: float
    critical_temperature_c: float


@dataclass(slots=True)
class IntrusionDetectorConfig(DetectorConfig):
    restricted_areas: list[str] = field(default_factory=list)
    policy: str = "whitelist"


@dataclass(slots=True)
class LeakageDetectorConfig(DetectorConfig):
    min_voltage_v: float
    max_voltage_v: float
    max_current_a: float
    leakage_current_threshold_a: float


@dataclass(slots=True)
class RosConfig:
    enabled: bool = False
    node_name: str = "inspection_embedded_node"
    loop_hz: float = 2.0
    cmd_vel_topic: str = "/cmd_vel"
    odom_topic: str = "/odom"
    scan_topic: str = "/scan"
    image_topic: str = "/usb_cam/image_raw"
    face_result_topic: str = "/inspection/face_matches"
    smoke_thermal_topic: str = "/inspection/smoke_thermal"
    electrical_topic: str = "/inspection/electrical"
    telemetry_topic: str = "/inspection/telemetry"
    event_topic: str = "/inspection/abnormal_event"
    queue_size: int = 10
    area_id: str = "UNKNOWN"
    frame_storage_dir: str = "runtime/ros_frames"
    retreat_linear_speed_mps: float = -0.2
    retreat_angular_speed_radps: float = 0.5
    retreat_step_sec: float = 0.2
    retreat_publish_hz: float = 10.0
    safe_back_distance_m: float = 0.6
    rear_arc_half_width_deg: float = 25.0


@dataclass(slots=True)
class SystemConfig:
    robot_id: int
    task_id: int
    handler_id: int
    cycle_interval_sec: float
    retreat_distance_m: float
    cache_db_path: str
    report_output_path: str
    fire: FireDetectorConfig
    intrusion: IntrusionDetectorConfig
    leakage: LeakageDetectorConfig
    ros: RosConfig | None = None


def _load_detector_config(data: dict, cls):
    return cls(**data)


def load_config(path: str | Path) -> SystemConfig:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SystemConfig(
        robot_id=raw["robot_id"],
        task_id=raw["task_id"],
        handler_id=raw["handler_id"],
        cycle_interval_sec=raw["cycle_interval_sec"],
        retreat_distance_m=raw["retreat_distance_m"],
        cache_db_path=raw["cache_db_path"],
        report_output_path=raw["report_output_path"],
        fire=_load_detector_config(raw["fire"], FireDetectorConfig),
        intrusion=_load_detector_config(raw["intrusion"], IntrusionDetectorConfig),
        leakage=_load_detector_config(raw["leakage"], LeakageDetectorConfig),
        ros=_load_detector_config(raw["ros"], RosConfig) if raw.get("ros") else None,
    )
