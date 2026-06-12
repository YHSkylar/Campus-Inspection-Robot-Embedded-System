from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import SystemConfig, load_config
from .interfaces import CameraAdapter, ElectricalSensor, PoseProvider, SmokeThermalSensor, TelemetryProvider
from .models import CameraFrame, DeviceTelemetry, ElectricalReading, FaceMatch, Pose, SmokeThermalReading
from .repository import SQLiteRepository
from .runtime import EmbeddedDependencies, EmbeddedInspectionSystem
from .services import EventReporter, JsonlControlCenterClient, ResponseService, SimpleMotionController


@dataclass
class ScriptedSmokeThermalSensor(SmokeThermalSensor):
    values: list[SmokeThermalReading]
    index: int = 0

    def read(self) -> SmokeThermalReading:
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


@dataclass
class ScriptedElectricalSensor(ElectricalSensor):
    values: list[ElectricalReading]
    index: int = 0

    def read(self) -> ElectricalReading:
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


@dataclass
class ScriptedCameraAdapter(CameraAdapter):
    values: list[CameraFrame]
    index: int = 0

    def capture(self) -> CameraFrame:
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


class FixedPoseProvider(PoseProvider):
    def __init__(self, pose: Pose) -> None:
        self.pose = pose

    def get_pose(self) -> Pose:
        return self.pose


class StaticTelemetryProvider(TelemetryProvider):
    def __init__(self, telemetry: DeviceTelemetry | None = None) -> None:
        self.telemetry = telemetry or DeviceTelemetry(
            battery_level=88.0,
            cpu_usage=26.0,
            memory_usage=34.0,
            board_temperature_c=45.0,
            comm_signal_dbm=-48,
        )

    def get_telemetry(self) -> DeviceTelemetry:
        return self.telemetry


def build_demo_system(config: SystemConfig) -> EmbeddedInspectionSystem:
    repository = SQLiteRepository(config.cache_db_path)
    client = JsonlControlCenterClient(config.report_output_path)
    motion_controller = SimpleMotionController()
    deps = EmbeddedDependencies(
        smoke_thermal_sensor=ScriptedSmokeThermalSensor(
            [
                SmokeThermalReading(smoke_ppm=60.0, temperature_c=34.0),
                SmokeThermalReading(smoke_ppm=135.0, temperature_c=72.0),
                SmokeThermalReading(smoke_ppm=145.0, temperature_c=76.0),
                SmokeThermalReading(smoke_ppm=152.0, temperature_c=79.0),
                SmokeThermalReading(smoke_ppm=70.0, temperature_c=32.0),
            ]
        ),
        electrical_sensor=ScriptedElectricalSensor(
            [
                ElectricalReading(voltage_v=220.0, current_a=0.8, leakage_current_a=0.01),
                ElectricalReading(voltage_v=219.0, current_a=0.9, leakage_current_a=0.01),
                ElectricalReading(voltage_v=219.0, current_a=0.9, leakage_current_a=0.01),
                ElectricalReading(voltage_v=182.0, current_a=2.8, leakage_current_a=0.22),
                ElectricalReading(voltage_v=180.0, current_a=2.9, leakage_current_a=0.25),
            ]
        ),
        camera_adapter=ScriptedCameraAdapter(
            [
                CameraFrame(frame_id="f1", capture_ref="captures/f1.jpg", matches=[]),
                CameraFrame(frame_id="f2", capture_ref="captures/f2.jpg", matches=[]),
                CameraFrame(
                    frame_id="f3",
                    capture_ref="captures/f3.jpg",
                    matches=[
                        FaceMatch(
                            person_id="unknown-1",
                            display_name="UNKNOWN",
                            confidence=0.92,
                            authorized=False,
                        )
                    ],
                ),
                CameraFrame(
                    frame_id="f4",
                    capture_ref="captures/f4.jpg",
                    matches=[
                        FaceMatch(
                            person_id="unknown-1",
                            display_name="UNKNOWN",
                            confidence=0.94,
                            authorized=False,
                        )
                    ],
                ),
                CameraFrame(
                    frame_id="f5",
                    capture_ref="captures/f5.jpg",
                    matches=[
                        FaceMatch(
                            person_id="unknown-1",
                            display_name="UNKNOWN",
                            confidence=0.95,
                            authorized=False,
                        )
                    ],
                ),
            ]
        ),
        pose_provider=FixedPoseProvider(Pose(x=10.5, y=8.2, theta=1.57, area_id="A-3")),
        telemetry_provider=StaticTelemetryProvider(),
        repository=repository,
        reporter=EventReporter(repository, client),
        response_service=ResponseService(
            repository=repository,
            motion_controller=motion_controller,
            retreat_distance_m=config.retreat_distance_m,
            handler_id=config.handler_id,
        ),
    )
    return EmbeddedInspectionSystem(config=config, deps=deps)


def default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "default_config.json"


def main() -> int:
    config = load_config(default_config_path())
    system = build_demo_system(config)
    system.run_forever(max_cycles=5)
    print(f"demo completed, sqlite={config.cache_db_path}, reports={config.report_output_path}")
    return 0
