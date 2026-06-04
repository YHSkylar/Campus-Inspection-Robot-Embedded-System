from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "Park Inspection Robot Backend"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./inspection_robot.db"
    max_task_speed: float = 2.0
    low_battery_threshold: int = 20
    detection_confidence_threshold: float = 0.9
    confirmation_frames: int = 3
    status_refresh_seconds: int = 1
    alarm_report_deadline_seconds: int = 2
    default_robot_id: str = "robot-001"
    current_version: str = "1.0.0"

    @property
    def database_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url.replace("sqlite:///", "", 1))
        return Path("inspection_robot.db")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", Settings().app_name),
        database_url=os.getenv("DATABASE_URL", Settings().database_url),
        max_task_speed=float(os.getenv("MAX_TASK_SPEED", Settings().max_task_speed)),
        low_battery_threshold=int(
            os.getenv("LOW_BATTERY_THRESHOLD", Settings().low_battery_threshold)
        ),
        detection_confidence_threshold=float(
            os.getenv(
                "DETECTION_CONFIDENCE_THRESHOLD",
                Settings().detection_confidence_threshold,
            )
        ),
        confirmation_frames=int(
            os.getenv("CONFIRMATION_FRAMES", Settings().confirmation_frames)
        ),
        current_version=os.getenv("CURRENT_VERSION", Settings().current_version),
    )


settings = get_settings()
