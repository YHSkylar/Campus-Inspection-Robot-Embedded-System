"""Campus inspection robot embedded sensor subsystem."""

from .config import SystemConfig, load_config
from .runtime import EmbeddedInspectionSystem

__all__ = ["EmbeddedInspectionSystem", "SystemConfig", "load_config"]
