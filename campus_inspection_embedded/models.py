from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Pose:
    x: float
    y: float
    theta: float = 0.0
    area_id: str = ""

    def to_location_text(self) -> str:
        return f"x={self.x:.2f},y={self.y:.2f},theta={self.theta:.2f},area={self.area_id or 'unknown'}"


@dataclass(slots=True)
class FaceMatch:
    person_id: str
    display_name: str
    confidence: float
    authorized: bool
    source: str = "face_recognition"


@dataclass(slots=True)
class CameraFrame:
    frame_id: str
    capture_ref: str = ""
    matches: list[FaceMatch] = field(default_factory=list)
    raw_payload: Any | None = None


@dataclass(slots=True)
class SmokeThermalReading:
    smoke_ppm: float
    temperature_c: float


@dataclass(slots=True)
class ElectricalReading:
    voltage_v: float
    current_a: float
    leakage_current_a: float | None = None


@dataclass(slots=True)
class DeviceTelemetry:
    battery_level: float = 100.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    board_temperature_c: float = 0.0
    comm_signal_dbm: int = -55


@dataclass(slots=True)
class SensorSnapshot:
    robot_id: int
    task_id: int
    timestamp: datetime
    pose: Pose
    smoke_thermal: SmokeThermalReading | None
    electrical: ElectricalReading | None
    camera_frame: CameraFrame | None
    sensor_status: dict[str, bool]
    telemetry: DeviceTelemetry


@dataclass(slots=True)
class DeviceStatus:
    robot_id: int
    timestamp: datetime
    battery_level: float
    cpu_usage: float
    memory_usage: float
    temperature: float
    sensor_status: dict[str, bool]
    comm_signal: int
    mode: str


@dataclass(slots=True)
class DetectionCandidate:
    detector_name: str
    event_type: str
    severity: str
    confidence: float
    source: str
    image_path: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AbnormalEvent:
    robot_id: int
    task_id: int
    event_type: str
    severity: str
    confidence: float
    occurred_at: datetime
    location: str
    image_path: str = ""
    status: str = "unhandled"
    reported: bool = False
    source: str = ""
    bearing_deg: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    event_id: int | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "robot_id": self.robot_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "confidence": round(self.confidence, 4),
            "occurred_at": self.occurred_at.isoformat(),
            "location": self.location,
            "image_path": self.image_path,
            "status": self.status,
            "reported": self.reported,
            "source": self.source,
            "bearing_deg": self.bearing_deg,
            "details": self.details,
        }


@dataclass(slots=True)
class DisposalRecord:
    event_id: int
    handler_id: int
    action: str
    action_time: datetime
    remark: str


@dataclass(slots=True)
class ActionResult:
    ok: bool
    message: str


def dataclass_to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {k: dataclass_to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [dataclass_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {k: dataclass_to_jsonable(v) for k, v in value.items()}
    return value
