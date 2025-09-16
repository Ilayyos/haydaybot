"""Template matching utilities."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import cv2
import numpy as np


log = logging.getLogger(__name__)


class Scanner:
    """Perform template matching on screenshots."""

    def __init__(
        self,
        template_dir: str = "images",
        min_distance: int = 30,
        *,
        cache_templates: bool = True,
        preload: bool = False,
    ) -> None:
        self.template_dir = Path(template_dir)
        self.min_distance = min_distance
        self.cache_templates = cache_templates
        self._template_cache: Dict[str, Tuple[np.ndarray, Tuple[int, int]]] = {}

        self.categories = {
            "farm": ["empty.png", "grown.png", "planting_wheat.png", "hoe.png"],
            "shop": [
                "shop.png",
                "sold.png",
                "create_offer.png",
                "small_silo.png",
                "wheat.png",
                "10x.png",
                "lower_price.png",
                "sell.png",
                "wheat_shop.png",
                "create_advert.png",
                "advert.png",
                "shop_close.png",
            ],
            "ui": ["silo_full.png", "silo_close.png", "large_shop_close.png", "advert_close.png"],
        }

        self.image_category = {}
        for category, images in self.categories.items():
            for image in images:
                self.image_category[image] = category

        if preload:
            self.preload_templates()

    # ------------------------------------------------------------------
    # Template handling

    def _template_path(self, filename: str) -> Path:
        if filename in self.image_category:
            category = self.image_category[filename]
            return self.template_dir / category / filename
        return self.template_dir / filename

    def load_template(self, filename: str) -> Tuple[np.ndarray, Tuple[int, int]]:
        """Load a template image from disk, optionally using a cache."""

        if self.cache_templates and filename in self._template_cache:
            return self._template_cache[filename]

        path = self._template_path(filename)
        template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise FileNotFoundError(f"Template not found: {path}")

        result = template, template.shape[::-1]
        if self.cache_templates:
            self._template_cache[filename] = result
        return result

    def preload_templates(self) -> None:
        """Preload all known templates to warm the cache."""

        for filename in self.image_category:
            try:
                self.load_template(filename)
            except FileNotFoundError as exc:
                log.warning("Unable to preload template %s: %s", filename, exc)

    def clear_cache(self) -> None:
        """Clear the template cache."""

        self._template_cache.clear()

    # ------------------------------------------------------------------
    # Matching utilities

    @staticmethod
    def _filter_points(positions: Iterable[Tuple[int, int]], min_distance: int) -> List[Tuple[int, int]]:
        filtered: List[Tuple[int, int]] = []
        for pos in positions:
            if all(math.hypot(pos[0] - p[0], pos[1] - p[1]) >= min_distance for p in filtered):
                filtered.append(pos)
        return filtered

    def findPoints(
        self,
        screenshot: np.ndarray,
        template_filename: str,
        threshold: float,
        min_distance: int | None = None,
    ) -> List[Tuple[int, int]]:
        """Find all match points in the screenshot that meet the threshold."""

        min_distance = min_distance if min_distance is not None else self.min_distance
        template, (w, h) = self.load_template(template_filename)
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        positions = [(x + w // 2, y + h // 2) for x, y in zip(locations[1], locations[0])]
        return self._filter_points(positions, min_distance)

    def findPoint(
        self, screenshot: np.ndarray, template_filename: str, threshold: float
    ) -> Tuple[int, int] | None:
        """Find the best match point in the screenshot."""

        template, (w, h) = self.load_template(template_filename)
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return None
        return (max_loc[0] + w // 2, max_loc[1] + h // 2)

