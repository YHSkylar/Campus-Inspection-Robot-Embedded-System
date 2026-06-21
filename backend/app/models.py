from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Role = Literal["admin", "control_center", "duty_manager", "security", "maintainer"]
TaskMode = Literal["fixed", "scheduled", "random", "planned_path"]
TaskAction = Literal["start", "pause", "stop", "complete"]
EventType = Literal["fire", "smoke", "obstacle", "boundary", "unauthorized_person"]
DisposeAction = Literal[
    "remote_speak",
    "light_intensify",
    "standby",
    "continue_inspection",
    "false_alarm",
    "danger_retreat",
    "handled",
]


class LoginRequest(BaseModel):
    username: str
    password: str


class TaskCreate(BaseModel):
    robot_id: Optional[str] = None
    mode: str = Field(..., examples=["scheduled"])
    route_name: str = Field(..., min_length=1)
    route_points: List[Dict[str, Any]] = Field(default_factory=list)
    speed: float = Field(..., gt=0)
    frequency: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    conflict_policy: Literal["queue"] = "queue"


class TaskUpdate(BaseModel):
    mode: Optional[str] = None
    route_name: Optional[str] = None
    route_points: Optional[List[Dict[str, Any]]] = None
    speed: Optional[float] = None
    frequency: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    conflict_policy: Optional[Literal["queue"]] = None


class TaskActionRequest(BaseModel):
    action: TaskAction


class TaskDispatchRequest(BaseModel):
    force: bool = False


class InspectionConfirmRequest(BaseModel):
    node_id: str
    location: Optional[Dict[str, Any]] = None
    snapshot_url: Optional[str] = None
    sensor_summary: Dict[str, Any] = Field(default_factory=dict)


class DetectionRequest(BaseModel):
    robot_id: Optional[str] = None
    event_type: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    image_url: Optional[str] = None
    image_tags: List[str] = Field(default_factory=list)
    image_features: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[Dict[str, Any]] = None
    orientation: Optional[Dict[str, Any]] = None
    snapshot_url: Optional[str] = None
    network_online: bool = True
    payload: Dict[str, Any] = Field(default_factory=dict)


class KnownFaceRequest(BaseModel):
    face_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    role: Optional[str] = None
    image_path: Optional[str] = None


class BatchDetectionRequest(BaseModel):
    events: List[DetectionRequest]


class DisposeRequest(BaseModel):
    action: DisposeAction
    executor: str = "operator"
    reason: Optional[str] = None
    result: Optional[str] = None


class DeviceStatusRequest(BaseModel):
    robot_id: Optional[str] = None
    battery: int = Field(..., ge=0, le=100)
    localization: Literal["normal", "lost"] = "lost"
    sensor_status: Dict[str, str] = Field(default_factory=dict)
    cpu_usage: float = Field(..., ge=0, le=100)
    memory_usage: float = Field(..., ge=0, le=100)
    signal_strength: int = Field(..., ge=0, le=100)
    online: bool = False
    location: Optional[Dict[str, Any]] = None


class InspectionStartRequest(BaseModel):
    task_id: str


class BatterySignalRequest(BaseModel):
    battery: int = Field(..., ge=0, le=100)


class MaintenanceRequest(BaseModel):
    operation: Literal["calibrate", "restart_module", "software_update", "algorithm_update"]
    operator: str = "maintainer"
    package_checksum_valid: bool = True
    target_version: Optional[str] = None
    module_name: Optional[str] = None
    dangerous: bool = False
    detail: Dict[str, Any] = Field(default_factory=dict)
