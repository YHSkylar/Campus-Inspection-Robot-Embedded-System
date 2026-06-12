from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime

from .config import FireDetectorConfig, IntrusionDetectorConfig, LeakageDetectorConfig
from .models import AbnormalEvent, DetectionCandidate, SensorSnapshot


class BaseDetector(ABC):
    def __init__(self, name: str, priority: int) -> None:
        self.name = name
        self.priority = priority

    @abstractmethod
    def evaluate(self, snapshot: SensorSnapshot) -> DetectionCandidate | None:
        raise NotImplementedError

    @property
    @abstractmethod
    def alert_threshold(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def suspicion_threshold(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def confirmation_frames(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def cooldown_sec(self) -> int:
        raise NotImplementedError


class FireDetector(BaseDetector):
    def __init__(self, config: FireDetectorConfig) -> None:
        super().__init__(name="fire", priority=0)
        self.config = config

    @property
    def alert_threshold(self) -> float:
        return self.config.alert_confidence_threshold

    @property
    def suspicion_threshold(self) -> float:
        return self.config.suspicion_confidence_threshold

    @property
    def confirmation_frames(self) -> int:
        return self.config.confirmation_frames

    @property
    def cooldown_sec(self) -> int:
        return self.config.cooldown_sec

    def evaluate(self, snapshot: SensorSnapshot) -> DetectionCandidate | None:
        reading = snapshot.smoke_thermal
        if reading is None:
            return None
        smoke_ratio = reading.smoke_ppm / self.config.smoke_ppm_threshold
        temp_ratio = reading.temperature_c / self.config.temperature_c_threshold
        if smoke_ratio < 0.7 and temp_ratio < 0.7:
            return None
        confidence = min((smoke_ratio * 0.55) + (temp_ratio * 0.45), 1.0)
        severity = "warning"
        if (
            reading.smoke_ppm >= self.config.critical_smoke_ppm
            or reading.temperature_c >= self.config.critical_temperature_c
        ):
            severity = "critical"
        return DetectionCandidate(
            detector_name=self.name,
            event_type="fire",
            severity=severity,
            confidence=confidence,
            source="smoke_thermal_sensor",
            details={
                "smoke_ppm": reading.smoke_ppm,
                "temperature_c": reading.temperature_c,
            },
        )


class IntrusionDetector(BaseDetector):
    def __init__(self, config: IntrusionDetectorConfig) -> None:
        super().__init__(name="intrusion", priority=1)
        self.config = config

    @property
    def alert_threshold(self) -> float:
        return self.config.alert_confidence_threshold

    @property
    def suspicion_threshold(self) -> float:
        return self.config.suspicion_confidence_threshold

    @property
    def confirmation_frames(self) -> int:
        return self.config.confirmation_frames

    @property
    def cooldown_sec(self) -> int:
        return self.config.cooldown_sec

    def evaluate(self, snapshot: SensorSnapshot) -> DetectionCandidate | None:
        frame = snapshot.camera_frame
        if frame is None:
            return None
        if self.config.restricted_areas and snapshot.pose.area_id not in self.config.restricted_areas:
            return None
        intruders = [match for match in frame.matches if not match.authorized]
        if not intruders:
            return None
        confidence = max(match.confidence for match in intruders)
        return DetectionCandidate(
            detector_name=self.name,
            event_type="intrusion",
            severity="critical",
            confidence=confidence,
            source="camera_face_recognition",
            image_path=frame.capture_ref,
            details={
                "restricted_area": snapshot.pose.area_id,
                "intruders": [
                    {
                        "person_id": match.person_id,
                        "display_name": match.display_name,
                        "confidence": match.confidence,
                    }
                    for match in intruders
                ],
            },
        )


class LeakageDetector(BaseDetector):
    def __init__(self, config: LeakageDetectorConfig) -> None:
        super().__init__(name="leakage", priority=2)
        self.config = config

    @property
    def alert_threshold(self) -> float:
        return self.config.alert_confidence_threshold

    @property
    def suspicion_threshold(self) -> float:
        return self.config.suspicion_confidence_threshold

    @property
    def confirmation_frames(self) -> int:
        return self.config.confirmation_frames

    @property
    def cooldown_sec(self) -> int:
        return self.config.cooldown_sec

    def evaluate(self, snapshot: SensorSnapshot) -> DetectionCandidate | None:
        reading = snapshot.electrical
        if reading is None:
            return None
        voltage_score = 0.0
        if reading.voltage_v < self.config.min_voltage_v:
            voltage_score = (self.config.min_voltage_v - reading.voltage_v) / self.config.min_voltage_v
        elif reading.voltage_v > self.config.max_voltage_v:
            voltage_score = (reading.voltage_v - self.config.max_voltage_v) / self.config.max_voltage_v
        current_score = max(reading.current_a / self.config.max_current_a, 0.0)
        leakage_score = 0.0
        if reading.leakage_current_a is not None:
            leakage_score = reading.leakage_current_a / self.config.leakage_current_threshold_a
        else:
            leakage_score = current_score * 0.8 + voltage_score * 0.2
        if voltage_score < 0.03 and leakage_score < 0.7 and current_score < 0.7:
            return None
        confidence = min(max(leakage_score, current_score * 0.85 + voltage_score * 0.15), 1.0)
        severity = "critical" if confidence >= 0.9 else "warning"
        return DetectionCandidate(
            detector_name=self.name,
            event_type="leakage",
            severity=severity,
            confidence=confidence,
            source="electrical_sensor",
            details={
                "voltage_v": reading.voltage_v,
                "current_a": reading.current_a,
                "leakage_current_a": reading.leakage_current_a,
            },
        )


class ConfirmationEngine:
    def __init__(self, detectors: list[BaseDetector]) -> None:
        self.detectors = {detector.name: detector for detector in detectors}
        self.hit_counts: dict[str, int] = defaultdict(int)
        self.last_triggered_at: dict[str, datetime] = {}

    def consume(
        self,
        detector_name: str,
        candidate: DetectionCandidate | None,
        snapshot: SensorSnapshot,
    ) -> AbnormalEvent | None:
        detector = self.detectors[detector_name]
        if candidate is None:
            self.hit_counts[detector_name] = 0
            return None
        if candidate.confidence < detector.suspicion_threshold:
            self.hit_counts[detector_name] = 0
            return None
        if candidate.confidence < detector.alert_threshold:
            self.hit_counts[detector_name] = 0
            return None
        self.hit_counts[detector_name] += 1
        if self.hit_counts[detector_name] < detector.confirmation_frames:
            return None
        last = self.last_triggered_at.get(detector_name)
        if last is not None and (snapshot.timestamp - last).total_seconds() < detector.cooldown_sec:
            return None
        self.hit_counts[detector_name] = 0
        self.last_triggered_at[detector_name] = snapshot.timestamp
        return AbnormalEvent(
            robot_id=snapshot.robot_id,
            task_id=snapshot.task_id,
            event_type=candidate.event_type,
            severity=candidate.severity,
            confidence=candidate.confidence,
            occurred_at=snapshot.timestamp,
            location=snapshot.pose.to_location_text(),
            image_path=candidate.image_path,
            status="unhandled",
            reported=False,
            source=candidate.source,
            bearing_deg=snapshot.pose.theta,
            details=candidate.details,
        )
