import time
import cv2
import numpy as np
from constants import OUTLINE_COLOR

class StatusConsole:
    def __init__(self):
        self.messages = []
        self.progress_bars = {}
        self.max_messages = 5  # Maximum number of messages to show
        self.console_width = 300  # Width of console in pixels
        self.line_height = 20   # Height of each line
        self.margin = 20        # Margin from screen edge
        
    def add_message(self, message: str) -> None:
        """Add a message to the console with timestamp."""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.messages.append(f"[{timestamp}] {message}")
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
            
    def set_progress(self, task: str, progress: float, color: tuple) -> None:
        """Set progress for a task (0.0 to 1.0)."""
        self.progress_bars[task] = {
            "progress": min(1.0, max(0.0, progress)),
            "color": color
        }
        
    def remove_progress(self, task: str) -> None:
        """Remove a progress bar."""
        if task in self.progress_bars:
            del self.progress_bars[task]
            
    def render(self, base_img: np.ndarray) -> None:
        """Render the console overlay."""
        height, width = base_img.shape[:2]
        
        # Calculate console dimensions
        total_height = (len(self.messages) + len(self.progress_bars) * 2) * self.line_height + self.margin
        
        # Create semi-transparent background
        console_bg = np.zeros((total_height, self.console_width, 3), dtype=np.uint8)
        console_bg.fill(32)  # Dark gray background
        
        # Add border
        cv2.rectangle(console_bg, (0, 0), (self.console_width-1, total_height-1), OUTLINE_COLOR, 1)
        
        # Add messages
        y_offset = self.margin
        for msg in self.messages:
            cv2.putText(
                console_bg,
                msg,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (200, 200, 200),  # Light gray text
                1,
                cv2.LINE_AA
            )
            y_offset += self.line_height
            
        # Add progress bars
        for task, data in self.progress_bars.items():
            # Task name
            cv2.putText(
                console_bg,
                task,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (200, 200, 200),
                1,
                cv2.LINE_AA
            )
            y_offset += self.line_height
            
            # Progress bar background
            bar_width = self.console_width - 20
            bar_height = 6
            cv2.rectangle(
                console_bg,
                (10, y_offset - bar_height),
                (10 + bar_width, y_offset),
                (64, 64, 64),
                -1
            )
            
            # Progress bar fill
            fill_width = int(bar_width * data["progress"])
            if fill_width > 0:
                cv2.rectangle(
                    console_bg,
                    (10, y_offset - bar_height),
                    (10 + fill_width, y_offset),
                    data["color"],
                    -1
                )
                
            # Progress bar border
            cv2.rectangle(
                console_bg,
                (10, y_offset - bar_height),
                (10 + bar_width, y_offset),
                OUTLINE_COLOR,
                1
            )
            
            # Percentage text
            percentage = f"{int(data['progress'] * 100)}%"
            text_size = cv2.getTextSize(percentage, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            cv2.putText(
                console_bg,
                percentage,
                (10 + bar_width - text_size[0] - 5, y_offset - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (200, 200, 200),
                1,
                cv2.LINE_AA
            )
            
            y_offset += self.line_height
            
        # Blend console onto base image
        x_pos = width - self.console_width - self.margin
        y_pos = self.margin
        
        # Create mask for proper alpha blending
        mask = np.zeros((total_height, self.console_width, 3), dtype=np.uint8)
        cv2.rectangle(mask, (0, 0), (self.console_width-1, total_height-1), (255, 255, 255), -1)
        
        # Blend console background
        alpha = 0.8
        roi = base_img[y_pos:y_pos+total_height, x_pos:x_pos+self.console_width]
        cv2.addWeighted(console_bg, alpha, roi, 1 - alpha, 0, roi) 