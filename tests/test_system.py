from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from campus_inspection_embedded.config import load_config
from campus_inspection_embedded.demo import (
    FixedPoseProvider,
    ScriptedCameraAdapter,
    ScriptedElectricalSensor,
    ScriptedSmokeThermalSensor,
    StaticTelemetryProvider,
)
from campus_inspection_embedded.models import CameraFrame, ElectricalReading, FaceMatch, Pose, SmokeThermalReading
from campus_inspection_embedded.repository import SQLiteRepository
from campus_inspection_embedded.runtime import EmbeddedDependencies, EmbeddedInspectionSystem
from campus_inspection_embedded.services import EventReporter, JsonlControlCenterClient, ResponseService, SimpleMotionController


def load_test_config(tmp: Path):
    config = load_config(Path("config/default_config.json"))
    config.cache_db_path = str(tmp / "embedded_runtime.db")
    config.report_output_path = str(tmp / "reported_events.jsonl")
    return config


class EmbeddedSystemTestCase(unittest.TestCase):
    def build_system(
        self,
        smoke_values,
        electrical_values,
        camera_values,
        *,
        mutate_client=None,
    ):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config = load_test_config(Path(temp_dir.name))
        repository = SQLiteRepository(config.cache_db_path)
        client = JsonlControlCenterClient(config.report_output_path)
        if mutate_client is not None:
            mutate_client(client)
        motion_controller = SimpleMotionController()
        system = EmbeddedInspectionSystem(
            config=config,
            deps=EmbeddedDependencies(
                smoke_thermal_sensor=ScriptedSmokeThermalSensor(smoke_values),
                electrical_sensor=ScriptedElectricalSensor(electrical_values),
                camera_adapter=ScriptedCameraAdapter(camera_values),
                pose_provider=FixedPoseProvider(Pose(x=1.0, y=2.0, theta=0.3, area_id="A-3")),
                telemetry_provider=StaticTelemetryProvider(),
                repository=repository,
                reporter=EventReporter(repository, client),
                response_service=ResponseService(
                    repository=repository,
                    motion_controller=motion_controller,
                    retreat_distance_m=config.retreat_distance_m,
                    handler_id=config.handler_id,
                ),
            ),
        )
        return system, repository, client, motion_controller

    def test_fire_detection_requires_consecutive_confirmation(self):
        system, repository, _, motion_controller = self.build_system(
            smoke_values=[
                SmokeThermalReading(130.0, 70.0),
                SmokeThermalReading(135.0, 72.0),
                SmokeThermalReading(150.0, 79.0),
            ],
            electrical_values=[ElectricalReading(220.0, 0.6, 0.01)] * 3,
            camera_values=[CameraFrame(frame_id="c1")] * 3,
        )
        for _ in range(3):
            system.run_cycle()
        events = repository.list_events()
        self.assertEqual(1, len(events))
        self.assertEqual("fire", events[0].event_type)
        self.assertTrue(events[0].reported)
        self.assertEqual(1, len(motion_controller.executed_actions))

    def test_intrusion_event_is_cached_and_flushed_after_network_recovery(self):
        def mutate_client(client):
            client.available = False

        system, repository, client, _ = self.build_system(
            smoke_values=[SmokeThermalReading(50.0, 30.0)] * 4,
            electrical_values=[ElectricalReading(220.0, 0.5, 0.01)] * 4,
            camera_values=[
                CameraFrame(
                    frame_id="i1",
                    capture_ref="i1.jpg",
                    matches=[FaceMatch("u1", "UNKNOWN", 0.91, False)],
                ),
                CameraFrame(
                    frame_id="i2",
                    capture_ref="i2.jpg",
                    matches=[FaceMatch("u1", "UNKNOWN", 0.92, False)],
                ),
                CameraFrame(
                    frame_id="i3",
                    capture_ref="i3.jpg",
                    matches=[FaceMatch("u1", "UNKNOWN", 0.93, False)],
                ),
                CameraFrame(frame_id="i4", capture_ref="i4.jpg", matches=[]),
            ],
            mutate_client=mutate_client,
        )
        for _ in range(3):
            system.run_cycle()
        events = repository.list_unreported_events()
        self.assertEqual(1, len(events))
        self.assertFalse(events[0].reported)
        client.available = True
        system.run_cycle()
        self.assertEqual([], repository.list_unreported_events())

    def test_camera_failure_enters_degraded_mode_and_disables_intrusion(self):
        class FailingCameraAdapter:
            def capture(self):
                raise RuntimeError("camera disconnected")

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config = load_test_config(Path(temp_dir.name))
        repository = SQLiteRepository(config.cache_db_path)
        client = JsonlControlCenterClient(config.report_output_path)
        system = EmbeddedInspectionSystem(
            config=config,
            deps=EmbeddedDependencies(
                smoke_thermal_sensor=ScriptedSmokeThermalSensor([SmokeThermalReading(50.0, 30.0)]),
                electrical_sensor=ScriptedElectricalSensor([ElectricalReading(220.0, 0.5, 0.01)]),
                camera_adapter=FailingCameraAdapter(),
                pose_provider=FixedPoseProvider(Pose(x=1.0, y=2.0, theta=0.3, area_id="A-3")),
                telemetry_provider=StaticTelemetryProvider(),
                repository=repository,
                reporter=EventReporter(repository, client),
                response_service=ResponseService(
                    repository=repository,
                    motion_controller=SimpleMotionController(),
                    retreat_distance_m=config.retreat_distance_m,
                    handler_id=config.handler_id,
                ),
            ),
        )
        system.run_cycle()
        conn = repository._connect()
        try:
            mode = conn.execute("SELECT mode FROM device_status ORDER BY status_id DESC LIMIT 1").fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM abnormal_event").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual("degraded", mode)
        self.assertEqual(0, count)

    def test_leakage_detection_uses_electrical_thresholds(self):
        system, repository, _, _ = self.build_system(
            smoke_values=[SmokeThermalReading(50.0, 30.0)] * 2,
            electrical_values=[
                ElectricalReading(182.0, 2.6, 0.21),
                ElectricalReading(180.0, 2.8, 0.24),
            ],
            camera_values=[CameraFrame(frame_id="ok")] * 2,
        )
        for _ in range(2):
            system.run_cycle()
        events = repository.list_events()
        self.assertEqual(1, len(events))
        self.assertEqual("leakage", events[0].event_type)
        self.assertTrue(events[0].reported)


if __name__ == "__main__":
    unittest.main()
