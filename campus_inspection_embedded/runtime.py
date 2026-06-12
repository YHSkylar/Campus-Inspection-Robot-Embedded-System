from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from time import sleep

from .config import SystemConfig
from .detectors import ConfirmationEngine, FireDetector, IntrusionDetector, LeakageDetector
from .interfaces import CameraAdapter, ElectricalSensor, PoseProvider, SmokeThermalSensor, TelemetryProvider
from .models import DeviceStatus, SensorSnapshot
from .repository import SQLiteRepository
from .services import EventReporter, ResponseService


@dataclass(slots=True)
class EmbeddedDependencies:
    smoke_thermal_sensor: SmokeThermalSensor
    electrical_sensor: ElectricalSensor
    camera_adapter: CameraAdapter
    pose_provider: PoseProvider
    telemetry_provider: TelemetryProvider
    repository: SQLiteRepository
    reporter: EventReporter
    response_service: ResponseService


class EmbeddedInspectionSystem:
    def __init__(self, config: SystemConfig, deps: EmbeddedDependencies) -> None:
        self.config = config
        self.deps = deps
        self.detectors = [
            FireDetector(config.fire),
            IntrusionDetector(config.intrusion),
            LeakageDetector(config.leakage),
        ]
        self.confirmation_engine = ConfirmationEngine(self.detectors)

    def run_cycle(self) -> list[int]:
        snapshot = self._collect_snapshot()
        device_status = self._build_device_status(snapshot)
        self.deps.repository.save_sensor_snapshot(snapshot)
        self.deps.repository.save_device_status(device_status)
        events = self._detect_events(snapshot, device_status.mode)
        event_ids: list[int] = []
        for event in sorted(events, key=self._priority_of):
            event_id = self.deps.repository.save_event(event)
            event.event_id = event_id
            self.deps.reporter.report_or_cache(event)
            self.deps.response_service.execute_report_and_leave(event)
            event_ids.append(event_id)
        self.deps.reporter.flush_pending()
        return event_ids

    def run_forever(self, max_cycles: int | None = None) -> None:
        executed = 0
        while max_cycles is None or executed < max_cycles:
            self.run_cycle()
            executed += 1
            sleep(self.config.cycle_interval_sec)

    def _collect_snapshot(self) -> SensorSnapshot:
        sensor_status = {"smoke_thermal": True, "electrical": True, "camera": True}
        smoke_thermal = None
        electrical = None
        camera_frame = None
        try:
            smoke_thermal = self.deps.smoke_thermal_sensor.read()
        except Exception:
            sensor_status["smoke_thermal"] = False
        try:
            electrical = self.deps.electrical_sensor.read()
        except Exception:
            sensor_status["electrical"] = False
        try:
            camera_frame = self.deps.camera_adapter.capture()
        except Exception:
            sensor_status["camera"] = False
        pose = self.deps.pose_provider.get_pose()
        telemetry = self.deps.telemetry_provider.get_telemetry()
        return SensorSnapshot(
            robot_id=self.config.robot_id,
            task_id=self.config.task_id,
            timestamp=datetime.now(),
            pose=pose,
            smoke_thermal=smoke_thermal,
            electrical=electrical,
            camera_frame=camera_frame,
            sensor_status=sensor_status,
            telemetry=telemetry,
        )

    def _build_device_status(self, snapshot: SensorSnapshot) -> DeviceStatus:
        mode = "normal" if all(snapshot.sensor_status.values()) else "degraded"
        return DeviceStatus(
            robot_id=snapshot.robot_id,
            timestamp=snapshot.timestamp,
            battery_level=snapshot.telemetry.battery_level,
            cpu_usage=snapshot.telemetry.cpu_usage,
            memory_usage=snapshot.telemetry.memory_usage,
            temperature=snapshot.telemetry.board_temperature_c,
            sensor_status=snapshot.sensor_status,
            comm_signal=snapshot.telemetry.comm_signal_dbm,
            mode=mode,
        )

    def _detect_events(self, snapshot: SensorSnapshot, mode: str) -> list:
        disabled_detectors = self._disabled_detectors(mode, snapshot.sensor_status)
        events = []
        for detector in self.detectors:
            if detector.name in disabled_detectors:
                self.confirmation_engine.consume(detector.name, None, snapshot)
                continue
            candidate = detector.evaluate(snapshot)
            event = self.confirmation_engine.consume(detector.name, candidate, snapshot)
            if event is not None:
                events.append(event)
        return events

    def _disabled_detectors(self, mode: str, sensor_status: dict[str, bool]) -> set[str]:
        disabled: set[str] = set()
        if not sensor_status.get("camera", False):
            disabled.add("intrusion")
        if not sensor_status.get("smoke_thermal", False):
            disabled.add("fire")
        if not sensor_status.get("electrical", False):
            disabled.add("leakage")
        if mode == "degraded" and "camera" in {k for k, v in sensor_status.items() if not v}:
            disabled.add("intrusion")
        return disabled

    def _priority_of(self, event) -> int:
        priorities = {"fire": 0, "intrusion": 1, "leakage": 2}
        return priorities.get(event.event_type, 99)
