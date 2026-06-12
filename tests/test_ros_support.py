from __future__ import annotations

import math
import unittest

from campus_inspection_embedded.models import CameraFrame, ElectricalReading, FaceMatch, SmokeThermalReading
from campus_inspection_embedded.ros_support import (
    LaserScanSnapshot,
    choose_retreat_command,
    parse_electrical_payload,
    parse_face_result_payload,
    parse_smoke_thermal_payload,
    quaternion_to_yaw,
)


class RosSupportTestCase(unittest.TestCase):
    def test_parse_smoke_thermal_payload(self):
        reading = parse_smoke_thermal_payload('{"smoke_ppm": 136.5, "temperature_c": 72.0}')
        self.assertEqual(SmokeThermalReading(136.5, 72.0), reading)

    def test_parse_electrical_payload(self):
        reading = parse_electrical_payload('{"voltage_v": 218.0, "current_a": 1.8, "leakage_current_a": 0.12}')
        self.assertEqual(ElectricalReading(218.0, 1.8, 0.12), reading)

    def test_parse_face_result_payload(self):
        frame = parse_face_result_payload(
            '{"frame_id":"f10","capture_ref":"topic://usb_cam/image_raw#10","matches":[{"person_id":"u-1","display_name":"UNKNOWN","confidence":0.93,"authorized":false}]}'
        )
        self.assertIsInstance(frame, CameraFrame)
        self.assertEqual("f10", frame.frame_id)
        self.assertEqual(1, len(frame.matches))
        self.assertEqual(FaceMatch("u-1", "UNKNOWN", 0.93, False, "ros_face_result"), frame.matches[0])

    def test_quaternion_to_yaw(self):
        yaw = quaternion_to_yaw(0.0, 0.0, math.sin(math.pi / 4.0), math.cos(math.pi / 4.0))
        self.assertAlmostEqual(math.pi / 2.0, yaw, places=5)

    def test_choose_retreat_command_reverse_when_rear_is_clear(self):
        scan = LaserScanSnapshot(
            angle_min=-math.pi,
            angle_increment=math.pi / 180.0,
            ranges=[2.0] * 360,
        )
        command = choose_retreat_command(
            scan,
            retreat_distance_m=2.0,
            reverse_speed_mps=-0.2,
            rotate_speed_radps=0.5,
            step_sec=0.2,
            safe_back_distance_m=0.6,
            rear_arc_half_width_deg=25.0,
        )
        self.assertLess(command.linear_x, 0.0)
        self.assertEqual(0.0, command.angular_z)
        self.assertEqual("rear_clear_reverse", command.reason)

    def test_choose_retreat_command_rotate_when_rear_is_blocked(self):
        ranges = [2.0] * 360
        for index in list(range(0, 26)) + list(range(335, 360)):
            ranges[index] = 0.3
        scan = LaserScanSnapshot(
            angle_min=-math.pi,
            angle_increment=math.pi / 180.0,
            ranges=ranges,
        )
        command = choose_retreat_command(
            scan,
            retreat_distance_m=2.0,
            reverse_speed_mps=-0.2,
            rotate_speed_radps=0.5,
            step_sec=0.2,
            safe_back_distance_m=0.6,
            rear_arc_half_width_deg=25.0,
        )
        self.assertEqual(0.0, command.linear_x)
        self.assertGreater(command.angular_z, 0.0)
        self.assertEqual("rear_blocked_rotate", command.reason)


if __name__ == "__main__":
    unittest.main()
