"""Configuration utilities for the HayDay automation bot."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Tuple

from constants import FAST_CLICK_DURATION, UI_DELAY, VISUALISER_ENABLED


log = logging.getLogger(__name__)


@dataclass
class ThresholdConfig:
    """Template-matching thresholds used throughout the bot."""

    empty_slots: float = 0.8
    grown_wheat: float = 0.8
    planting_button: float = 0.8
    silo_full: float = 0.8
    generic: float = 0.8

    def update(self, values: Dict[str, Any]) -> None:
        """Update threshold values from a dictionary."""

        for field_name in ("empty_slots", "grown_wheat", "planting_button", "silo_full", "generic"):
            if field_name in values:
                setattr(self, field_name, float(values[field_name]))


@dataclass
class BotConfig:
    """Runtime configuration for the automation bot."""

    monitor_index: int = 1
    display_offset: Tuple[int, int] = (0, 0)
    move_duration: float = 0.35
    dry_run: bool = False
    visualiser_enabled: bool = VISUALISER_ENABLED
    prefer_mss: bool = True
    plant_wait_seconds: int = 120
    idle_delay: float = 1.0
    no_slots_delay: int = 5
    max_retries: int = 3
    prewarm_templates: bool = True
    template_dir: str = "images"
    ui_delay: float = UI_DELAY
    fast_click_duration: float = FAST_CLICK_DURATION
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)

    def merge(self, values: Dict[str, Any]) -> None:
        """Merge values from a dictionary into the configuration."""

        for field_name in (
            "monitor_index",
            "display_offset",
            "move_duration",
            "dry_run",
            "visualiser_enabled",
            "prefer_mss",
            "plant_wait_seconds",
            "idle_delay",
            "no_slots_delay",
            "max_retries",
            "prewarm_templates",
            "template_dir",
            "ui_delay",
            "fast_click_duration",
        ):
            if field_name in values:
                value = values[field_name]
                if field_name == "display_offset" and isinstance(value, (list, tuple)):
                    value = (int(value[0]), int(value[1]))
                setattr(self, field_name, value)

        thresholds = values.get("thresholds")
        if isinstance(thresholds, dict):
            self.thresholds.update(thresholds)

    @classmethod
    def from_json(cls, path: Path) -> "BotConfig":
        """Load configuration from a JSON file."""

        data = json.loads(path.read_text())
        config = cls()
        config.merge(data)
        return config

    @classmethod
    def from_args(cls, args: Any) -> "BotConfig":
        """Create a configuration instance from CLI arguments."""

        config = cls()

        if getattr(args, "config", None):
            config = cls.from_json(Path(args.config))

        if getattr(args, "monitor", None) is not None:
            config.monitor_index = int(args.monitor)

        if getattr(args, "offset", None):
            config.display_offset = _parse_offset(args.offset)

        if getattr(args, "move_duration", None) is not None:
            config.move_duration = float(args.move_duration)

        if getattr(args, "dry_run", False):
            config.dry_run = True

        if getattr(args, "no_visualiser", False):
            config.visualiser_enabled = False

        if getattr(args, "prefer_pil", False):
            config.prefer_mss = False

        if getattr(args, "plant_wait", None) is not None:
            config.plant_wait_seconds = int(args.plant_wait)

        if getattr(args, "loop_delay", None) is not None:
            config.idle_delay = float(args.loop_delay)

        if getattr(args, "max_retries", None) is not None:
            config.max_retries = max(1, int(args.max_retries))

        if getattr(args, "template_dir", None):
            config.template_dir = str(args.template_dir)

        if getattr(args, "prewarm", None) is not None:
            config.prewarm_templates = bool(args.prewarm)

        if getattr(args, "ui_delay", None) is not None:
            config.ui_delay = float(args.ui_delay)

        if getattr(args, "fast_click", None) is not None:
            config.fast_click_duration = float(args.fast_click)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Export the configuration as a serialisable dictionary."""

        return {
            "monitor_index": self.monitor_index,
            "display_offset": list(self.display_offset),
            "move_duration": self.move_duration,
            "dry_run": self.dry_run,
            "visualiser_enabled": self.visualiser_enabled,
            "prefer_mss": self.prefer_mss,
            "plant_wait_seconds": self.plant_wait_seconds,
            "idle_delay": self.idle_delay,
            "no_slots_delay": self.no_slots_delay,
            "max_retries": self.max_retries,
            "prewarm_templates": self.prewarm_templates,
            "template_dir": self.template_dir,
            "ui_delay": self.ui_delay,
            "fast_click_duration": self.fast_click_duration,
            "thresholds": {
                "empty_slots": self.thresholds.empty_slots,
                "grown_wheat": self.thresholds.grown_wheat,
                "planting_button": self.thresholds.planting_button,
                "silo_full": self.thresholds.silo_full,
                "generic": self.thresholds.generic,
            },
        }

    def describe(self) -> None:
        """Log a human readable summary of the configuration."""

        log.info(
            "Running with monitor=%s, offset=%s, dry_run=%s, visualiser=%s",
            self.monitor_index,
            self.display_offset,
            self.dry_run,
            self.visualiser_enabled,
        )
        log.info(
            "Runtime: backend=%s, move_duration=%.2fs, plant_wait=%ss, retries=%s, prewarm=%s",
            "mss" if self.prefer_mss else "pil",
            self.move_duration,
            self.plant_wait_seconds,
            self.max_retries,
            self.prewarm_templates,
        )


def _parse_offset(value: str) -> Tuple[int, int]:
    """Parse an offset string in the form "x,y"."""

    if isinstance(value, (list, tuple)) and len(value) == 2:
        return int(value[0]), int(value[1])

    if isinstance(value, str):
        parts = value.replace(" ", "").split(",")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])

    raise ValueError(f"Invalid display offset: {value!r}")

