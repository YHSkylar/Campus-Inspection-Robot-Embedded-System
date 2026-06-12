from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    AbnormalEvent,
    ActionResult,
    CameraFrame,
    DeviceTelemetry,
    ElectricalReading,
    FaceMatch,
    Pose,
    SmokeThermalReading,
)


class SmokeThermalSensor(ABC):
    @abstractmethod
    def read(self) -> SmokeThermalReading:
        raise NotImplementedError


class ElectricalSensor(ABC):
    @abstractmethod
    def read(self) -> ElectricalReading:
        raise NotImplementedError


class CameraAdapter(ABC):
    @abstractmethod
    def capture(self) -> CameraFrame:
        raise NotImplementedError


class FaceMatcher(ABC):
    @abstractmethod
    def analyze(self, image: object, capture_ref: str = "") -> list[FaceMatch]:
        raise NotImplementedError


class PoseProvider(ABC):
    @abstractmethod
    def get_pose(self) -> Pose:
        raise NotImplementedError


class TelemetryProvider(ABC):
    @abstractmethod
    def get_telemetry(self) -> DeviceTelemetry:
        raise NotImplementedError


class ControlCenterClient(ABC):
    @abstractmethod
    def report_event(self, event: AbnormalEvent) -> ActionResult:
        raise NotImplementedError


class MotionController(ABC):
    @abstractmethod
    def leave_danger_area(self, event: AbnormalEvent, retreat_distance_m: float) -> ActionResult:
        raise NotImplementedError
