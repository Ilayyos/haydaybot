"""Mouse and keyboard control helpers for the HayDay bot."""

from __future__ import annotations

import logging
import math
from typing import Iterable, Optional

import pyautogui

from constants import Duration, Point


log = logging.getLogger(__name__)


class Controller:
    """Wrap PyAutoGUI to offer higher-level operations."""

    def __init__(self, move_duration: float = 0.5, *, dry_run: bool = False, pause: float = 0.0) -> None:
        """Initialise the mouse controller."""

        self.move_duration = move_duration
        self.dry_run = dry_run
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = pause

    # ------------------------------------------------------------------
    # Internal helpers

    def _log_action(self, action: str, point: Optional[Point] = None) -> None:
        if self.dry_run:
            log.debug("[DRY RUN] %s at %s", action, point)

    @staticmethod
    def _ensure_point(point: Optional[Point]) -> bool:
        if point is None:
            log.debug("No point provided for controller action")
            return False
        return True

    # ------------------------------------------------------------------
    # Public API

    def offsetPoint(self, point: Point, offset_x: int = 0, offset_y: int = 0) -> Point:
        """Returns a new point with the specified offsets applied."""

        if point is None:
            return None
        return (point[0] + offset_x, point[1] + offset_y)

    def click(self, point: Point, duration: Duration = None) -> bool:
        """Move to a point and click."""

        if not self._ensure_point(point):
            return False

        move_time = duration if duration is not None else self.move_duration
        self._log_action("click", point)
        if not self.dry_run:
            pyautogui.moveTo(point[0], point[1], duration=move_time)
            pyautogui.click()
        return True

    def drag(self, start_point: Point, end_point: Point, duration: Duration = None) -> bool:
        """Perform a drag operation from start to end point."""

        if not self._ensure_point(start_point) or not self._ensure_point(end_point):
            return False

        move_time = duration if duration is not None else self.move_duration
        self._log_action("drag", start_point)
        if not self.dry_run:
            pyautogui.moveTo(start_point[0], start_point[1], duration=move_time)
            pyautogui.mouseDown()
            pyautogui.moveTo(end_point[0], end_point[1], duration=move_time)
            pyautogui.mouseUp()
        return True

    def pressKey(self, key: str) -> bool:
        """Press a keyboard key."""

        self._log_action(f"press {key}")
        if not self.dry_run:
            pyautogui.press(key)
        return True

    def mouseDownAt(self, point: Point, duration: Duration = None) -> bool:
        """Move to a point and press the mouse button down."""

        if not self._ensure_point(point):
            return False

        move_time = duration if duration is not None else self.move_duration
        self._log_action("mouse down", point)
        if not self.dry_run:
            pyautogui.moveTo(point[0], point[1], duration=move_time)
            pyautogui.mouseDown()
        return True

    def moveMouseBetweenPoints(
        self,
        points: Iterable[Point],
        circle_radius: int = 0,
        circle_points: int = 0,
        duration: Duration = None,
    ) -> bool:
        """Move the mouse through a series of points."""

        points = list(points)
        if not points:
            return False

        for point in points:
            if not self._ensure_point(point):
                continue

            center_x = point[0] + 20
            center_y = point[1] + 20
            self._log_action("move", (center_x, center_y))
            if not self.dry_run:
                pyautogui.moveTo(center_x, center_y, duration=0)

            if circle_points > 0:
                for i in range(circle_points):
                    angle = 2 * math.pi * i / circle_points
                    x = center_x + circle_radius * math.cos(angle)
                    y = center_y + circle_radius * math.sin(angle)
                    self._log_action("move", (x, y))
                    if not self.dry_run:
                        pyautogui.moveTo(x, y, duration=0)

        return True

    def mouseUp(self) -> bool:
        """Release the mouse button."""

        self._log_action("mouse up")
        if not self.dry_run:
            pyautogui.mouseUp()
        return True

    def clickPoints(self, points: Iterable[Point], duration: Duration = None) -> bool:
        """Click all points in the list sequentially."""

        acted = False
        for point in points:
            if not self._ensure_point(point):
                continue
            acted = True
            self.click(point, duration)

        return acted

