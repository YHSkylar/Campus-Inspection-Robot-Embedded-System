from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    app_name: str = "Park Inspection Robot Backend"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./inspection_robot.db"
    snapshot_dir: str = "./snapshots"
    max_task_speed: float = 2.0
    low_battery_threshold: int = 20
    detection_confidence_threshold: float = 0.9
    face_match_threshold: float = 0.75
    confirmation_frames: int = 3
    status_refresh_seconds: int = 1
    alarm_report_deadline_seconds: int = 2
    default_robot_id: str = "robot-001"
    current_version: str = "1.0.0"

    @property
    def database_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            raw_path = Path(self.database_url.replace("sqlite:///", "", 1))
            return raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        return PROJECT_ROOT / "inspection_robot.db"

    @property
    def snapshot_path(self) -> Path:
        raw_path = Path(self.snapshot_dir)
        return raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path


@lru_cache
def get_settings() -> Settings:
    base = Settings()
    return Settings(
        app_name=os.getenv("APP_NAME", base.app_name),
        database_url=os.getenv("DATABASE_URL", base.database_url),
        snapshot_dir=os.getenv("SNAPSHOT_DIR", base.snapshot_dir),
        max_task_speed=float(os.getenv("MAX_TASK_SPEED", base.max_task_speed)),
        low_battery_threshold=int(
            os.getenv("LOW_BATTERY_THRESHOLD", base.low_battery_threshold)
        ),
        detection_confidence_threshold=float(
            os.getenv(
                "DETECTION_CONFIDENCE_THRESHOLD",
                base.detection_confidence_threshold,
            )
        ),
        face_match_threshold=float(
            os.getenv("FACE_MATCH_THRESHOLD", base.face_match_threshold)
        ),
        confirmation_frames=int(
            os.getenv("CONFIRMATION_FRAMES", base.confirmation_frames)
        ),
        current_version=os.getenv("CURRENT_VERSION", base.current_version),
    )


settings = get_settings()
