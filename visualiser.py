import os
import cv2
import numpy as np
import time
import math
from PIL import ImageGrab
from status_console import StatusConsole
from constants import (
    VISUALISER_ENABLED, GREEN, OUTLINE_COLOR,
    TARGET_COLOR, ACTION_COLOR, WARNING_COLOR, 
    PATH_COLOR, CLICK_COLOR
)

class Visualiser:
    def __init__(self, display_offset=(0, 0)):
        """
        Initialize the visualiser with overlay window.
        """
        self.display_offset = display_offset
        self.screenshot = None
        self.visuals = {}
        self.next_id = 1
        self.timer_end_time = None
        self.timer_color = None
        self.status_console = StatusConsole()  # Add status console
        self.screen_width = 1920  # Default values
        self.screen_height = 1080

        if not VISUALISER_ENABLED:
            return

        # Create overlay window
        cv2.namedWindow("Visualiser", cv2.WINDOW_NORMAL)
        
        # Set window to be transparent and click-through
        if os.name == 'nt':  # Windows
            import win32gui
            import win32con
            import win32api
            
            # Get window handle
            hwnd = win32gui.FindWindow(None, "Visualiser")
            
            # Set window to be layered and transparent (click-through)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd, 
                win32con.GWL_EXSTYLE, 
                ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            )
            
            # Set the window to be fully transparent
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(0, 0, 0),  # Color key (black will be transparent)
                255,  # Alpha (fully opaque)
                win32con.LWA_COLORKEY  # Use color key for transparency
            )
        
        # Keep window on top
        cv2.setWindowProperty("Visualiser", cv2.WND_PROP_TOPMOST, 1)
        
        # Get screen dimensions for the main monitor
        screen = ImageGrab.grab()
        self.screen_width, self.screen_height = screen.size
        
        # Position window on main monitor and make it fullscreen
        cv2.moveWindow("Visualiser", 0, 0)
        cv2.setWindowProperty("Visualiser", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def take_screenshot(self):
        """
        Captures a screenshot of the primary monitor.
        Temporarily hides visuals and status console to avoid capturing them.
        """
        if VISUALISER_ENABLED:
            # Store current states and clear display
            current_visuals = self.visuals.copy()
            current_messages = self.status_console.messages.copy()
            current_progress_bars = self.status_console.progress_bars.copy()
            
            # Clear all visual elements
            self.visuals = {}
            self.status_console.messages = []
            self.status_console.progress_bars = {}
            self.render()
            cv2.waitKey(1)  # Allow display to update

        # Take the screenshot
        screenshot = ImageGrab.grab()
        self.screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        if VISUALISER_ENABLED:
            # Restore states
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
        if not VISUALISER_ENABLED:
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
        if not VISUALISER_ENABLED:
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
        if not VISUALISER_ENABLED:
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
        if not VISUALISER_ENABLED:
            return

        for vid in visual_ids:
            if vid in self.visuals:
                del self.visuals[vid]
        self.render()

    def render(self):
        """
        Redraws only the visuals on a transparent background with modern styling.
        """
        if not VISUALISER_ENABLED:
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
        if not VISUALISER_ENABLED:
            return

        self.timer_end_time = time.time() + seconds
        self.timer_color = color
        
    def updateTimer(self) -> bool:
        """
        Update the timer display if a timer is active.
        
        Returns:
            bool: True if timer is still running, False if finished or no timer active
        """
        if not VISUALISER_ENABLED:
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
        if not VISUALISER_ENABLED:
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