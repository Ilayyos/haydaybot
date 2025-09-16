"""High level automation logic for HayDay."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from config import BotConfig
from constants import ACTION_COLOR, CLICK_COLOR, PATH_COLOR, TARGET_COLOR, WARNING_COLOR
from controller import Controller
from scanner import Scanner
from visualiser import Visualiser


Point = Tuple[int, int]

@dataclass
class ActionResult:
    """Represents the outcome of a bot action."""

    success: bool
    message: str
    needs_sell: bool = False
    retries: int = 0


class HayDayBot:
    """Stateful orchestration of planting, harvesting and selling."""

    def __init__(
        self,
        scanner: Scanner,
        controller: Controller,
        visualiser: Visualiser,
        config: BotConfig,
    ) -> None:
        self.scanner = scanner
        self.controller = controller
        self.visualiser = visualiser
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public orchestration API

    def execute_cycle(self, stop_event=None) -> ActionResult:
        """Execute a full plant-wait-harvest cycle."""

        if self._should_stop(stop_event):
            return ActionResult(False, "Stopped before cycle start")

        screenshot = self.visualiser.take_screenshot()
        empty_slots = self._filter_slots(
            self.scanner.findPoints(
                screenshot,
                "empty.png",
                self.config.thresholds.empty_slots,
                min_distance=60,
            )
        )

        if not empty_slots:
            self._record("No empty slots available, waiting")
            self.visualiser.createTimer(self.config.no_slots_delay, color=WARNING_COLOR)
            while self.visualiser.updateTimer() and not self._should_stop(stop_event):
                time.sleep(0.1)
            return ActionResult(False, "Waiting for empty slots")

        plant_result = self.plant(stop_event, initial_slots=empty_slots)
        if self._should_stop(stop_event):
            return ActionResult(False, "Stopped during planting")
        if not plant_result.success:
            return plant_result

        self._record(f"Waiting {self.config.plant_wait_seconds}s for crops to grow")
        self.visualiser.createTimer(self.config.plant_wait_seconds)
        while self.visualiser.updateTimer() and not self._should_stop(stop_event):
            time.sleep(0.1)

        if self._should_stop(stop_event):
            return ActionResult(False, "Stopped before harvesting")

        harvest_result = self.harvest(stop_event)
        if self._should_stop(stop_event):
            return ActionResult(False, "Stopped during harvesting")

        if harvest_result.needs_sell:
            sell_result = self.sell(stop_event)
            if not sell_result.success or self._should_stop(stop_event):
                return sell_result
            harvest_result = self.harvest(stop_event)

        return harvest_result

    # ------------------------------------------------------------------
    # Planting logic

    def plant(self, stop_event=None, initial_slots: Optional[Sequence[Point]] = None) -> ActionResult:
        self._record("Starting planting sequence")
        self._set_progress("Planting", 0.0, TARGET_COLOR)

        visuals: List[int] = []
        line_ids: List[int] = []
        slots = list(initial_slots) if initial_slots else None

        try:
            for attempt in range(1, self.config.max_retries + 1):
                if self._should_stop(stop_event):
                    return ActionResult(False, "Stopped while planting", retries=attempt)

                screenshot = self.visualiser.take_screenshot()
                if slots is None:
                    slots = self._filter_slots(
                        self.scanner.findPoints(
                            screenshot,
                            "empty.png",
                            self.config.thresholds.empty_slots,
                            min_distance=60,
                        )
                    )

                self._record(f"Planting attempt {attempt}: {len(slots)} empty slots detected")

                if not slots:
                    return ActionResult(False, "No empty slots to plant", retries=attempt)

                visuals = self.visualiser.addVisuals(slots, TARGET_COLOR, radius=15, point_type="target")
                self._set_progress("Planting", 0.2, TARGET_COLOR)

                first_slot = slots[0]
                click_visual = self.visualiser.addVisuals(first_slot, CLICK_COLOR, radius=10, point_type="click")
                self.controller.click(first_slot, duration=0)
                self.visualiser.removeVisuals(click_visual)
                self._sleep(1, stop_event)

                self.controller.pressKey("escape")
                self._set_progress("Planting", 0.4, TARGET_COLOR)

                screenshot = self.visualiser.take_screenshot()
                self.visualiser.removeVisuals(visuals)
                visuals = []
                slots = self._filter_slots(
                    self.scanner.findPoints(
                        screenshot,
                        "empty.png",
                        self.config.thresholds.empty_slots,
                        min_distance=60,
                    )
                )

                if not slots:
                    self._record("Lost empty slots after selecting field, retrying", logging.WARNING)
                    continue

                self._set_progress("Planting", 0.6, TARGET_COLOR)
                visuals = self.visualiser.addVisuals(slots, TARGET_COLOR, radius=15, point_type="target")
                line_ids = (
                    self.visualiser.addDragPath(slots, PATH_COLOR, thickness=2)
                    if len(slots) > 1
                    else []
                )

                click_visual = self.visualiser.addVisuals(slots[0], CLICK_COLOR, radius=10, point_type="click")
                self.controller.click(slots[0], duration=0)
                self.visualiser.removeVisuals(click_visual)

                screenshot = self.visualiser.take_screenshot()
                wheat_point = self.scanner.findPoint(
                    screenshot,
                    "planting_wheat.png",
                    self.config.thresholds.planting_button,
                )

                if wheat_point is None:
                    self._record("Failed to locate wheat planting button", logging.WARNING)
                    self.visualiser.removeVisuals(line_ids)
                    self.visualiser.removeVisuals(visuals)
                    line_ids = []
                    visuals = []
                    continue

                plant_visual = self.visualiser.addVisuals(
                    wheat_point, ACTION_COLOR, radius=10, point_type="action"
                )
                self._set_progress("Planting", 0.8, TARGET_COLOR)

                self.controller.mouseDownAt(wheat_point, duration=0)
                self.controller.moveMouseBetweenPoints(slots, 60, 4, duration=0)
                self.controller.mouseUp()
                self.controller.pressKey("escape")

                self.visualiser.removeVisuals(plant_visual)
                self.visualiser.removeVisuals(line_ids)
                self.visualiser.removeVisuals(visuals)
                line_ids = []
                visuals = []

                self.visualiser.take_screenshot()
                self._sleep(0.5, stop_event)

                screenshot = self.visualiser.take_screenshot()
                remaining = self._filter_slots(
                    self.scanner.findPoints(
                        screenshot, "empty.png", self.config.thresholds.empty_slots
                    )
                )

                if remaining and attempt < self.config.max_retries:
                    self._record(f"{len(remaining)} slots missed, retrying planting")
                    slots = remaining
                    continue

                if remaining:
                    return ActionResult(False, "Planting incomplete", retries=attempt)

                self._set_progress("Planting", 1.0, TARGET_COLOR)
                self._record("Planting completed successfully")
                return ActionResult(True, "Planting complete", retries=attempt)

            return ActionResult(False, "Exceeded planting retries", retries=self.config.max_retries)
        finally:
            if visuals:
                self.visualiser.removeVisuals(visuals)
            if line_ids:
                self.visualiser.removeVisuals(line_ids)
            self._clear_progress("Planting")

    # ------------------------------------------------------------------
    # Harvesting logic

    def harvest(self, stop_event=None) -> ActionResult:
        self._record("Starting harvest sequence")
        self._set_progress("Harvesting", 0.0, ACTION_COLOR)

        visuals: List[int] = []
        line_ids: List[int] = []
        offset_visual: List[int] = []

        try:
            for attempt in range(1, self.config.max_retries + 1):
                if self._should_stop(stop_event):
                    return ActionResult(False, "Stopped while harvesting", retries=attempt)

                screenshot = self.visualiser.take_screenshot()
                grown_points = self.scanner.findPoints(
                    screenshot,
                    "grown.png",
                    self.config.thresholds.grown_wheat,
                )

                if not grown_points:
                    self._record("No grown wheat detected")
                    return ActionResult(False, "No grown wheat", retries=attempt)

                self._record(
                    f"Harvest attempt {attempt}: {len(grown_points)} wheat clusters located"
                )

                visuals = self.visualiser.addVisuals(
                    grown_points, TARGET_COLOR, radius=15, point_type="target"
                )
                self._set_progress("Harvesting", 0.2, ACTION_COLOR)

                first_point = grown_points[0]
                click_visual = self.visualiser.addVisuals(
                    first_point, CLICK_COLOR, radius=10, point_type="click"
                )
                self.controller.click(first_point, duration=0)
                self.visualiser.removeVisuals(click_visual)
                self._sleep(1, stop_event)

                self.controller.pressKey("escape")
                self._set_progress("Harvesting", 0.4, ACTION_COLOR)

                screenshot = self.visualiser.take_screenshot()
                self.visualiser.removeVisuals(visuals)
                visuals = []
                grown_points = self.scanner.findPoints(
                    screenshot,
                    "grown.png",
                    self.config.thresholds.grown_wheat,
                )

                if not grown_points:
                    self._record("Lost grown wheat positions after cancelling selection", logging.WARNING)
                    continue

                self._set_progress("Harvesting", 0.6, ACTION_COLOR)
                visuals = self.visualiser.addVisuals(
                    grown_points, TARGET_COLOR, radius=15, point_type="target"
                )
                line_ids = (
                    self.visualiser.addDragPath(grown_points, PATH_COLOR, thickness=2)
                    if len(grown_points) > 1
                    else []
                )

                offset_point = self.controller.offsetPoint(grown_points[0], 10, 10)
                offset_visual = self.visualiser.addVisuals(
                    offset_point, CLICK_COLOR, radius=10, point_type="click"
                )
                self.controller.click(offset_point, duration=0)

                if not self._get_hoe_in_hand(stop_event):
                    self._record("Unable to equip hoe tool", logging.WARNING)
                    self.visualiser.removeVisuals(line_ids)
                    self.visualiser.removeVisuals(visuals)
                    self.visualiser.removeVisuals(offset_visual)
                    line_ids = []
                    visuals = []
                    offset_visual = []
                    continue

                self._set_progress("Harvesting", 0.8, ACTION_COLOR)
                self.controller.moveMouseBetweenPoints(grown_points, 70, 4, duration=0)
                self.controller.mouseUp()

                self.visualiser.removeVisuals(line_ids)
                self.visualiser.removeVisuals(visuals)
                self.visualiser.removeVisuals(offset_visual)
                line_ids = []
                visuals = []
                offset_visual = []

                if self._check_silo_full(stop_event):
                    self._set_progress("Harvesting", 1.0, ACTION_COLOR)
                    self._record("Silo full – selling required")
                    return ActionResult(True, "Silo full", needs_sell=True, retries=attempt)

                self._sleep(0.5, stop_event)
                screenshot = self.visualiser.take_screenshot()
                remaining = self.scanner.findPoints(
                    screenshot,
                    "grown.png",
                    self.config.thresholds.grown_wheat,
                )

                if remaining and attempt < self.config.max_retries:
                    self._record(f"{len(remaining)} wheat clusters remain, retrying harvest")
                    continue

                if remaining:
                    return ActionResult(False, "Harvest incomplete", retries=attempt)

                self._set_progress("Harvesting", 1.0, ACTION_COLOR)
                self._record("Harvesting completed successfully")
                return ActionResult(True, "Harvest complete", retries=attempt)

            return ActionResult(False, "Exceeded harvest retries", retries=self.config.max_retries)
        finally:
            if visuals:
                self.visualiser.removeVisuals(visuals)
            if line_ids:
                self.visualiser.removeVisuals(line_ids)
            if offset_visual:
                self.visualiser.removeVisuals(offset_visual)
            self._clear_progress("Harvesting")

    # ------------------------------------------------------------------
    # Selling logic

    def sell(self, stop_event=None) -> ActionResult:
        self._record("Starting sell sequence")
        self._set_progress("Selling", 0.0, WARNING_COLOR)

        def _wait_ui(label: str) -> None:
            self._record(label)
            self._sleep(self.config.ui_delay, stop_event)

        try:
            screenshot = self.visualiser.take_screenshot()
            shop_point = self.scanner.findPoint(
                screenshot,
                "shop.png",
                self.config.thresholds.generic,
            )
            if shop_point is None:
                return ActionResult(False, "Failed to locate shop button")

            self._set_progress("Selling", 0.2, WARNING_COLOR)
            shop_visual = self.visualiser.addVisuals(
                shop_point, ACTION_COLOR, radius=15, point_type="action"
            )
            self.controller.click(shop_point, self.config.fast_click_duration)
            self.visualiser.removeVisuals(shop_visual)
            _wait_ui("Opening shop")

            screenshot = self.visualiser.take_screenshot()
            sold_points = self.scanner.findPoints(
                screenshot,
                "sold.png",
                self.config.thresholds.generic,
            )
            if sold_points:
                self._record(f"Clearing {len(sold_points)} sold items")
                sold_visuals: List[int] = []
                for point in sold_points:
                    sold_visuals.extend(
                        self.visualiser.addVisuals(point, WARNING_COLOR, radius=15, point_type="target")
                    )
                    sold_visuals.extend(
                        self.visualiser.addVisuals(point, CLICK_COLOR, radius=10, point_type="click")
                    )
                self.controller.clickPoints(sold_points, self.config.fast_click_duration)
                self.visualiser.removeVisuals(sold_visuals)
                _wait_ui("Clearing sold slots")

            screenshot = self.visualiser.take_screenshot()
            empty_store_points = self.scanner.findPoints(screenshot, "create_offer.png", 0.7)
            self._record(f"Preparing {len(empty_store_points)} market offers")
            self._set_progress("Selling", 0.4, WARNING_COLOR)

            empty_store_visuals = self.visualiser.addVisuals(
                empty_store_points, TARGET_COLOR, radius=15, point_type="target"
            )

            for idx, slot_point in enumerate(empty_store_points):
                if self._should_stop(stop_event):
                    return ActionResult(False, "Stopped while creating offers")

                progress = 0.4 + (0.3 * (idx / max(1, len(empty_store_points))))
                self._set_progress("Selling", progress, WARNING_COLOR)

                click_visual = self.visualiser.addVisuals(
                    slot_point, CLICK_COLOR, radius=10, point_type="click"
                )
                self.controller.click(slot_point, self.config.fast_click_duration)
                self.visualiser.removeVisuals(click_visual)
                _wait_ui("Creating offer")

                screenshot = self.visualiser.take_screenshot()
                silo_point = self.scanner.findPoint(
                    screenshot, "small_silo.png", self.config.thresholds.generic
                )
                if silo_point is None:
                    self._record("Unable to find silo button", logging.WARNING)
                    continue

                silo_visual = self.visualiser.addVisuals(
                    silo_point, ACTION_COLOR, radius=15, point_type="action"
                )
                self.controller.click(silo_point, self.config.fast_click_duration)
                self.visualiser.removeVisuals(silo_visual)
                _wait_ui("Opening silo")

                screenshot = self.visualiser.take_screenshot()
                wheat_point = self.scanner.findPoint(
                    screenshot, "wheat.png", self.config.thresholds.generic
                )
                if wheat_point is None:
                    self._record("Wheat not available in silo", logging.WARNING)
                    continue

                wheat_visual = self.visualiser.addVisuals(
                    wheat_point, ACTION_COLOR, radius=15, point_type="action"
                )
                self.controller.click(wheat_point, self.config.fast_click_duration)
                self.visualiser.removeVisuals(wheat_visual)
                self._sleep(self.config.ui_delay * 2, stop_event)

                screenshot = self.visualiser.take_screenshot()
                amount_point = self.scanner.findPoint(screenshot, "10x.png", self.config.thresholds.generic)
                if amount_point is None:
                    self._record("Not enough wheat for 10x offer", logging.WARNING)
                    close_point = self.scanner.findPoint(
                        screenshot, "large_shop_close.png", self.config.thresholds.generic
                    )
                    if close_point:
                        close_visual = self.visualiser.addVisuals(
                            close_point, CLICK_COLOR, radius=10, point_type="click"
                        )
                        self.controller.click(close_point, self.config.fast_click_duration)
                        self.visualiser.removeVisuals(close_visual)
                    continue

                lower_price_point = self.scanner.findPoint(
                    screenshot, "lower_price.png", self.config.thresholds.generic
                )
                sell_point = self.scanner.findPoint(
                    screenshot, "sell.png", self.config.thresholds.generic
                )

                sell_targets = [p for p in (lower_price_point, sell_point) if p]
                if not sell_targets:
                    self._record("Sell buttons not found", logging.WARNING)
                    continue

                targets_visuals = self.visualiser.addVisuals(
                    sell_targets, ACTION_COLOR, radius=15, point_type="action"
                )
                line_ids = self.visualiser.addDragPath(sell_targets, PATH_COLOR, thickness=2)

                self.controller.clickPoints(sell_targets, self.config.fast_click_duration)
                self.visualiser.removeVisuals(line_ids)
                self.visualiser.removeVisuals(targets_visuals)
                _wait_ui("Confirming sale")

            self.visualiser.removeVisuals(empty_store_visuals)
            self._set_progress("Selling", 0.8, WARNING_COLOR)

            screenshot = self.visualiser.take_screenshot()
            wheat_shop_point = self.scanner.findPoint(
                screenshot, "wheat_shop.png", self.config.thresholds.generic
            )

            if wheat_shop_point is not None:
                wheat_visual = self.visualiser.addVisuals(
                    wheat_shop_point, TARGET_COLOR, radius=15, point_type="target"
                )
                self.controller.click(wheat_shop_point, self.config.fast_click_duration)
                self.visualiser.removeVisuals(wheat_visual)
                _wait_ui("Opening advertisement dialog")

                screenshot = self.visualiser.take_screenshot()
                advert_point = self.scanner.findPoint(
                    screenshot, "advert.png", self.config.thresholds.generic
                )
                if advert_point is not None:
                    self._record("Creating advertisement")
                    offset_point = self.controller.offsetPoint(advert_point, 300, 0)
                    advert_visual = self.visualiser.addVisuals(
                        offset_point, ACTION_COLOR, radius=15, point_type="action"
                    )
                    self.controller.click(offset_point, self.config.fast_click_duration)
                    self.visualiser.removeVisuals(advert_visual)
                    _wait_ui("Confirming advertisement")

                    screenshot = self.visualiser.take_screenshot()
                    create_point = self.scanner.findPoint(
                        screenshot, "create_advert.png", self.config.thresholds.generic
                    )
                    if create_point:
                        create_visual = self.visualiser.addVisuals(
                            create_point, ACTION_COLOR, radius=15, point_type="action"
                        )
                        self.controller.click(create_point, self.config.fast_click_duration)
                        self.visualiser.removeVisuals(create_visual)
                else:
                    close_point = self.scanner.findPoint(
                        screenshot, "advert_close.png", self.config.thresholds.generic
                    )
                    if close_point:
                        close_visual = self.visualiser.addVisuals(
                            close_point, CLICK_COLOR, radius=10, point_type="click"
                        )
                        self.controller.click(close_point, self.config.fast_click_duration)
                        self.visualiser.removeVisuals(close_visual)

            self._set_progress("Selling", 0.9, WARNING_COLOR)
            screenshot = self.visualiser.take_screenshot()
            shop_close_point = self.scanner.findPoint(
                screenshot, "shop_close.png", self.config.thresholds.generic
            )
            if shop_close_point:
                close_visual = self.visualiser.addVisuals(
                    shop_close_point, CLICK_COLOR, radius=10, point_type="click"
                )
                self.controller.click(shop_close_point, self.config.fast_click_duration)
                self.visualiser.removeVisuals(close_visual)
                _wait_ui("Closing shop")

            self._set_progress("Selling", 1.0, WARNING_COLOR)
            self._record("Sell sequence completed")
            return ActionResult(True, "Sell complete")
        finally:
            self._clear_progress("Selling")

    # ------------------------------------------------------------------
    # Helpers

    def _record(self, message: str, level: int = logging.INFO) -> None:
        self.logger.log(level, message)
        self.visualiser.status_console.add_message(message)

    def _set_progress(self, task: str, value: float, color: Tuple[int, int, int]) -> None:
        self.visualiser.status_console.set_progress(task, value, color)

    def _clear_progress(self, task: str) -> None:
        self.visualiser.status_console.remove_progress(task)

    @staticmethod
    def _filter_slots(points: Sequence[Point]) -> List[Point]:
        return [point for idx, point in enumerate(points) if (idx + 1) % 3 != 0]

    @staticmethod
    def _should_stop(stop_event) -> bool:
        return stop_event is not None and stop_event.is_set()

    def _sleep(self, seconds: float, stop_event=None) -> None:
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self._should_stop(stop_event):
                break
            time.sleep(0.1)

    def _check_silo_full(self, stop_event=None) -> bool:
        screenshot = self.visualiser.take_screenshot()
        silo_point = self.scanner.findPoint(
            screenshot,
            "silo_full.png",
            self.config.thresholds.silo_full,
        )
        if silo_point is None:
            return False

        self._record("Silo is full, clearing dialog", logging.WARNING)
        silo_visual = self.visualiser.addVisuals(
            silo_point, WARNING_COLOR, radius=20, point_type="target"
        )
        close_point = self.scanner.findPoint(
            screenshot,
            "silo_close.png",
            self.config.thresholds.generic,
        )
        if close_point:
            close_visual = self.visualiser.addVisuals(
                close_point, CLICK_COLOR, radius=10, point_type="click"
            )
            self.controller.click(close_point, self.config.fast_click_duration)
            self.visualiser.removeVisuals(close_visual)
        self.visualiser.removeVisuals(silo_visual)
        self._sleep(0.25, stop_event)
        return True

    def _get_hoe_in_hand(self, stop_event=None) -> bool:
        for attempt in range(self.config.max_retries):
            if self._should_stop(stop_event):
                return False

            screenshot = self.visualiser.take_screenshot()
            hoe_point = self.scanner.findPoint(screenshot, "hoe.png", 0.9)
            if hoe_point is not None:
                hoe_visual = self.visualiser.addVisuals(
                    hoe_point, ACTION_COLOR, radius=15, point_type="action"
                )
                self.controller.mouseDownAt(hoe_point, duration=0)
                self.visualiser.removeVisuals(hoe_visual)
                return True

            self._record("Failed to find hoe tool, retrying", logging.WARNING)
            self._sleep(0.5, stop_event)

        return False


__all__ = ["HayDayBot", "ActionResult"]

