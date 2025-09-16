import logging
import os
import time
import math
from typing import Dict, Iterable, List

import cv2
import numpy as np
try:
    from PIL import ImageGrab
except Exception:  # pragma: no cover - optional dependency
    ImageGrab = None
try:
    import mss
except Exception:  # pragma: no cover - optional dependency
    mss = None
from status_console import StatusConsole
from constants import (
    VISUALISER_ENABLED,
    GREEN,
    OUTLINE_COLOR,
    TARGET_COLOR,
    ACTION_COLOR,
    WARNING_COLOR,
    PATH_COLOR,
    CLICK_COLOR,
)


log = logging.getLogger(__name__)

class Visualiser:
    def __init__(
        self,
        display_offset=(0, 0),
        *,
        enabled: bool | None = None,
        monitor_index: int = 1,
        prefer_mss: bool = True,
    ) -> None:
        """Initialise the visual overlay and screenshot backend."""

        self.window_name = "Visualiser"
        self.display_offset = display_offset
        self.enabled = VISUALISER_ENABLED if enabled is None else enabled
        self.monitor_index = monitor_index
        self.prefer_mss = prefer_mss
        self.screenshot = None
        self.visuals: Dict[int, Dict[str, object]] = {}
        self.next_id = 1
        self.timer_end_time = None
        self.timer_color = None
        self.status_console = StatusConsole()
        self.screen_width = 1920
        self.screen_height = 1080
        self._mss_monitor_index = max(1, monitor_index)

        self.backend = self._select_backend()
        self._configure_screen_dimensions()

        if not self.enabled:
            return

        self._initialise_window()

    # ------------------------------------------------------------------
    # Internal helpers

    def _select_backend(self) -> str:
        if self.prefer_mss and mss is not None:
            log.debug("Using MSS for screenshots")
            return "mss"
        if ImageGrab is not None:
            log.debug("Using Pillow ImageGrab for screenshots")
            return "pil"
        if mss is not None:
            log.debug("Falling back to MSS for screenshots")
            return "mss"
        raise RuntimeError("No screenshot backend available")

    def _configure_screen_dimensions(self) -> None:
        if self.backend == "pil" and ImageGrab is not None:
            screen = ImageGrab.grab()
            self.screen_width, self.screen_height = screen.size
        elif self.backend == "mss" and mss is not None:
            with mss.mss() as sct:
                monitors = sct.monitors
                index = self._resolve_monitor_index(monitors)
                monitor = monitors[index]
                self.screen_width = monitor["width"]
                self.screen_height = monitor["height"]
                self._mss_monitor_index = index
        else:
            self.screen_width, self.screen_height = 1920, 1080

    def _resolve_monitor_index(self, monitors: List[Dict[str, int]]) -> int:
        if not monitors:
            return 1

        desired = max(1, self.monitor_index)
        max_index = max(1, len(monitors) - 1)
        if desired > max_index:
            log.warning(
                "Requested monitor %s is unavailable, using monitor %s instead",
                desired,
                max_index,
            )
            return max_index
        return desired

    def _initialise_window(self) -> None:
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        if os.name == "nt":
            import win32api
            import win32con
            import win32gui

            hwnd = win32gui.FindWindow(None, self.window_name)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
                ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT,
            )
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(0, 0, 0),
                255,
                win32con.LWA_COLORKEY,
            )

        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
        cv2.moveWindow(self.window_name, self.display_offset[0], self.display_offset[1])
        cv2.setWindowProperty(
            self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )

    def take_screenshot(self):
        """Capture a screenshot using the configured backend."""

        if self.enabled:
            current_visuals = self.visuals.copy()
            current_messages = self.status_console.messages.copy()
            current_progress_bars = self.status_console.progress_bars.copy()
            self.visuals = {}
            self.status_console.messages = []
            self.status_console.progress_bars = {}
            self.render()
            cv2.waitKey(1)

        if self.backend == "mss" and mss is not None:
            with mss.mss() as sct:
                monitors = sct.monitors
                index = self._resolve_monitor_index(monitors)
                monitor = monitors[index]
                screenshot = np.array(sct.grab(monitor))
                self.screen_width = monitor["width"]
                self.screen_height = monitor["height"]
            self.screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        elif self.backend == "pil" and ImageGrab is not None:
            screenshot = ImageGrab.grab()
            self.screen_width, self.screen_height = screenshot.size
            self.screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        else:  # pragma: no cover - no screenshot backend available
            raise RuntimeError("No screenshot backend available")

        if self.enabled:
            self.visuals = current_visuals
            self.status_console.messages = current_messages
            self.status_console.progress_bars = current_progress_bars
            self.render()

        return self.screenshot

    def addVisuals(self, points, color, radius=5, point_type="target"):
        """
        Overlays visual elements on the screenshot.
        points: either a single (x, y) tuple or a list of (x, y) tuples.
        color: color tuple in BGR format.
        radius: radius of the dot/size of the square.
        point_type: "target" (square), "action" (circle), "click" (cross)
        Returns a list of visual IDs.
        """
        if not self.enabled:
            return []

        if isinstance(points, tuple):
            points = [points]
        elif points is None:
            return []

        visual_ids = []
        for pt in points:
            vid = self.next_id
            self.visuals[vid] = {
                "type": point_type,
                "data": {
                    "point": pt,
                    "radius": radius,
                    "template_size": (30, 30),  # Default template size
                    "timestamp": time.time()  # Add timestamp for animations
                },
                "color": color
            }
            visual_ids.append(vid)
            self.next_id += 1
        self.render()
        return visual_ids

    def addLine(self, start_point, end_point, color, thickness=2, line_type="solid"):
        """
        Adds a line between two points.
        start_point: (x, y) tuple for line start
        end_point: (x, y) tuple for line end
        color: color tuple in BGR format
        thickness: line thickness in pixels
        line_type: "solid" or "dashed" for different line styles
        Returns the visual ID for the line
        """
        if not self.enabled:
            return -1
            
        vid = self.next_id
        self.visuals[vid] = {
            "type": "line",
            "data": {
                "start": start_point,
                "end": end_point,
                "thickness": thickness,
                "line_type": line_type
            },
            "color": color
        }
        self.next_id += 1
        self.render()
        return vid

    def addDragPath(self, points, color=PATH_COLOR, thickness=2):
        """
        Adds a drag path visualization with arrows.
        points: List of points forming the path
        """
        if not self.enabled:
            return []
            
        if len(points) < 2:
            return []

        visual_ids = []
        # Add main path
        for i in range(len(points) - 1):
            vid = self.addLine(points[i], points[i + 1], color, thickness)
            visual_ids.append(vid)
            
            # Add arrow at midpoint
            mid_x = (points[i][0] + points[i + 1][0]) // 2
            mid_y = (points[i][1] + points[i + 1][1]) // 2
            arrow_vid = self.next_id
            self.visuals[arrow_vid] = {
                "type": "arrow",
                "data": {
                    "point": (mid_x, mid_y),
                    "direction": (points[i + 1][0] - points[i][0], 
                                points[i + 1][1] - points[i][1])
                },
                "color": color
            }
            visual_ids.append(arrow_vid)
            self.next_id += 1

        self.render()
        return visual_ids

    def removeVisuals(self, visual_ids):
        """Removes overlays with the given visual IDs."""
        if not self.enabled:
            return

        for vid in visual_ids:
            if vid in self.visuals:
                del self.visuals[vid]
        self.render()

    def render(self):
        """
        Redraws only the visuals on a transparent background with modern styling.
        """
        if not self.enabled:
            return

        # Create base image using screen dimensions if screenshot is None
        if self.screenshot is None:
            base_img = np.zeros((self.screen_height, self.screen_width, 3), dtype=np.uint8)
        else:
            base_img = np.zeros_like(self.screenshot)
        
        # Draw all visuals
        for visual in self.visuals.values():
            if "data" not in visual or "point" not in visual["data"]:
                continue
                
            pt = visual["data"]["point"]
            r = visual["data"].get("radius", 5)  # Default radius if not specified
            color = visual["color"]
            
            if visual["type"] == "target":
                # Draw modern square with thin border and coordinates
                cv2.rectangle(
                    base_img,
                    (pt[0] - r, pt[1] - r),
                    (pt[0] + r, pt[1] + r),
                    OUTLINE_COLOR,
                    1  # Thinner border
                )
                # Add small corner accents
                accent_len = 3
                for corner in [(1,1), (1,-1), (-1,1), (-1,-1)]:
                    cv2.line(
                        base_img,
                        (pt[0] + corner[0]*r, pt[1] + corner[1]*r),
                        (pt[0] + corner[0]*(r-accent_len), pt[1] + corner[1]*r),
                        color,
                        1
                    )
                    cv2.line(
                        base_img,
                        (pt[0] + corner[0]*r, pt[1] + corner[1]*r),
                        (pt[0] + corner[0]*r, pt[1] + corner[1]*(r-accent_len)),
                        color,
                        1
                    )
                # Add coordinates
                cv2.putText(
                    base_img,
                    f"({pt[0]}, {pt[1]})",
                    (pt[0] - r, pt[1] - r - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,
                    color,
                    1
                )
                
            elif visual["type"] == "action":
                # Draw precise circle with pulse effect
                pulse = np.sin(time.time() * 4) * 2  # Subtle pulse
                cv2.circle(
                    base_img,
                    pt,
                    int(r + pulse),
                    color,
                    1  # Thinner border
                )
                # Add crosshair
                cv2.line(base_img, (pt[0]-4, pt[1]), (pt[0]+4, pt[1]), color, 1)
                cv2.line(base_img, (pt[0], pt[1]-4), (pt[0], pt[1]+4), color, 1)
                
            elif visual["type"] == "click":
                # Draw modern cross with diamond
                size = r // 2
                cv2.line(base_img, 
                        (pt[0] - size, pt[1] - size),
                        (pt[0] + size, pt[1] + size),
                        color, 1)
                cv2.line(base_img,
                        (pt[0] - size, pt[1] + size),
                        (pt[0] + size, pt[1] - size),
                        color, 1)
                # Add diamond
                diamond_points = np.array([
                    [pt[0], pt[1]-r],
                    [pt[0]+r//2, pt[1]],
                    [pt[0], pt[1]+r],
                    [pt[0]-r//2, pt[1]]
                ])
                cv2.polylines(base_img, [diamond_points], True, OUTLINE_COLOR, 1)
                
            elif visual["type"] == "line":
                if "start" not in visual["data"] or "end" not in visual["data"]:
                    continue
                    
                pt1 = visual["data"]["start"]
                pt2 = visual["data"]["end"]
                thickness = visual["data"].get("thickness", 1)
                
                if visual["data"].get("line_type") == "dashed":
                    # Draw modern dashed line
                    dash_length = 5  # Shorter dashes
                    gap_length = 3   # Smaller gaps
                    total_length = np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)
                    num_dashes = int(total_length / (dash_length + gap_length))
                    
                    for i in range(num_dashes):
                        start_ratio = i * (dash_length + gap_length) / total_length
                        end_ratio = min((i * (dash_length + gap_length) + dash_length) / total_length, 1.0)
                        
                        dash_start = (
                            int(pt1[0] + (pt2[0] - pt1[0]) * start_ratio),
                            int(pt1[1] + (pt2[1] - pt1[1]) * start_ratio)
                        )
                        dash_end = (
                            int(pt1[0] + (pt2[0] - pt1[0]) * end_ratio),
                            int(pt1[1] + (pt2[1] - pt1[1]) * end_ratio)
                        )
                        
                        cv2.line(
                            base_img,
                            dash_start,
                            dash_end,
                            color,
                            thickness
                        )
                else:
                    # Draw solid line with gradient
                    num_segments = 10
                    for i in range(num_segments):
                        alpha = i / num_segments
                        start_x = int(pt1[0] + (pt2[0] - pt1[0]) * (i/num_segments))
                        start_y = int(pt1[1] + (pt2[1] - pt1[1]) * (i/num_segments))
                        end_x = int(pt1[0] + (pt2[0] - pt1[0]) * ((i+1)/num_segments))
                        end_y = int(pt1[1] + (pt2[1] - pt1[1]) * ((i+1)/num_segments))
                        segment_color = tuple(int(c2 * alpha + c1 * (1-alpha)) for c1, c2 in zip(color, OUTLINE_COLOR))
                        cv2.line(base_img, (start_x, start_y), (end_x, end_y), segment_color, thickness)
                    
            elif visual["type"] == "arrow":
                if "direction" not in visual["data"]:
                    continue
                    
                dx, dy = visual["data"]["direction"]
                angle = np.arctan2(dy, dx)
                arrow_length = 15  # Shorter arrow
                arrow_angle = np.pi / 4  # 45 degrees
                
                # Calculate arrow head points
                p1 = (
                    int(pt[0] - arrow_length * np.cos(angle + arrow_angle)),
                    int(pt[1] - arrow_length * np.sin(angle + arrow_angle))
                )
                p2 = (
                    int(pt[0] - arrow_length * np.cos(angle - arrow_angle)),
                    int(pt[1] - arrow_length * np.sin(angle - arrow_angle))
                )
                
                # Draw arrow head with gradient
                cv2.line(base_img, pt, p1, color, 1)
                cv2.line(base_img, pt, p2, color, 1)
                cv2.line(base_img, p1, p2, OUTLINE_COLOR, 1)
        
        # Render status console
        self.status_console.render(base_img)
        
        cv2.imshow("Visualiser", base_img)
        cv2.waitKey(1)


    def createTimer(self, seconds: int, color=GREEN) -> None:
        """
        Start a countdown timer.
        
        Args:
            seconds (int): Number of seconds to count down from
            color (tuple): BGR color tuple for the timer text
        """
        if not self.enabled:
            return

        self.timer_end_time = time.time() + seconds
        self.timer_color = color
        
    def updateTimer(self) -> bool:
        """
        Update the timer display if a timer is active.
        
        Returns:
            bool: True if timer is still running, False if finished or no timer active
        """
        if not self.enabled:
            return False

        if self.timer_end_time is None:
            return False
            
        if time.time() >= self.timer_end_time:
            self.timer_end_time = None
            self.timer_color = None
            return False
            
        remaining = int(self.timer_end_time - time.time())
        self._renderTimer(remaining)
        return True
        
    def _renderTimer(self, seconds_remaining: int) -> None:
        """
        Internal method to render the timer on screen with modern styling.
        """
        if not self.enabled:
            return

        # Create transparent base image
        base_img = np.zeros_like(self.screenshot)
        
        # Calculate minutes and seconds
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        timer_text = f"{minutes:02d}:{seconds:02d}"
        
        # Get image dimensions
        height, width = base_img.shape[:2]
        
        # Modern styling for timer
        font_scale = 3.0
        thickness = 3  # Increased thickness for bolder text
        font = cv2.FONT_HERSHEY_DUPLEX  # Changed font for better anti-aliasing
        text_size = cv2.getTextSize(timer_text, font, font_scale, thickness)[0]
        
        # Calculate center position
        text_x = (width - text_size[0]) // 2
        text_y = (height + text_size[1]) // 2
        
        # Draw modern timer background with semi-transparent fill
        padding = 30  # Increased padding
        bg_pts = np.array([
            [text_x - padding, text_y - text_size[1] - padding],
            [text_x + text_size[0] + padding, text_y - text_size[1] - padding],
            [text_x + text_size[0] + padding, text_y + padding],
            [text_x - padding, text_y + padding]
        ], np.int32)
        
        # Create a separate image for the semi-transparent background
        overlay = base_img.copy()
        cv2.fillPoly(overlay, [bg_pts], (64, 64, 64))  # Dark gray fill
        cv2.polylines(overlay, [bg_pts], True, OUTLINE_COLOR, 1)
        
        # Blend the overlay with the base image
        alpha = 0.7  # 70% opacity
        cv2.addWeighted(overlay, alpha, base_img, 1 - alpha, 0, base_img)
        
        # Add progress bar
        progress = seconds_remaining / 120  # Assuming max time is 120 seconds
        bar_width = text_size[0] + 2*padding
        bar_height = 4  # Slightly taller progress bar
        bar_x = text_x - padding
        bar_y = text_y + padding + 10
        
        # Progress bar background (darker)
        cv2.rectangle(base_img,
                     (bar_x, bar_y),
                     (bar_x + bar_width, bar_y + bar_height),
                     (32, 32, 32),  # Darker gray
                     -1)
        
        # Progress bar fill
        cv2.rectangle(base_img, 
                     (bar_x, bar_y),
                     (bar_x + int(bar_width * progress), bar_y + bar_height),
                     self.timer_color,
                     -1)
        
        # Progress bar outline
        cv2.rectangle(base_img,
                     (bar_x, bar_y),
                     (bar_x + bar_width, bar_y + bar_height),
                     OUTLINE_COLOR,
                     1)
        
        # Add timer text with multiple passes for better anti-aliasing
        # Outer glow/shadow effect
        glow_color = (32, 32, 32)  # Dark gray glow
        for offset in range(2, 5, 2):
            cv2.putText(
                base_img,
                timer_text,
                (text_x - offset, text_y),
                font,
                font_scale,
                glow_color,
                thickness + 2,
                cv2.LINE_AA
            )
            cv2.putText(
                base_img,
                timer_text,
                (text_x + offset, text_y),
                font,
                font_scale,
                glow_color,
                thickness + 2,
                cv2.LINE_AA
            )
            cv2.putText(
                base_img,
                timer_text,
                (text_x, text_y - offset),
                font,
                font_scale,
                glow_color,
                thickness + 2,
                cv2.LINE_AA
            )
            cv2.putText(
                base_img,
                timer_text,
                (text_x, text_y + offset),
                font,
                font_scale,
                glow_color,
                thickness + 2,
                cv2.LINE_AA
            )
        
        # Main text with anti-aliasing
        cv2.putText(
            base_img,
            timer_text,
            (text_x, text_y),
            font,
            font_scale,
            self.timer_color,
            thickness,
            cv2.LINE_AA
        )

        cv2.imshow("Visualiser", base_img)
        cv2.waitKey(1)

    def close(self) -> None:
        """Close the overlay window."""

        if self.enabled:
            cv2.destroyWindow(self.window_name)
