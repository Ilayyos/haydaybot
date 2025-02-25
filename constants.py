from typing import Tuple, List, Optional, Union

# Type aliases for clarity
Point = Tuple[int, int]
Duration = Optional[float]

# Global visibility flag
VISUALISER_ENABLED = True  # Set to False to disable all visualiser functionality

# Color constants
TARGET_COLOR = (0, 255, 128)  # Mint green - for target locations
ACTION_COLOR = (255, 128, 0)  # Light blue - for interactive elements
WARNING_COLOR = (0, 0, 255)   # Pure red - for warnings
PATH_COLOR = (255, 255, 0)    # Cyan - for movement paths
CLICK_COLOR = (255, 0, 255)   # Magenta - for click points
OUTLINE_COLOR = (128, 128, 128)  # Gray - for outlines and secondary elements

RED = (0, 0, 255)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)

# UI timing constants
FAST_CLICK_DURATION = 0.17
UI_DELAY = 0.25  # Default delay for UI updates 