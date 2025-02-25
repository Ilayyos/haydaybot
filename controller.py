import pyautogui
from constants import Point, Duration
import math

class Controller:
    def __init__(self, move_duration: float = 0.5) -> None:
        """
        Initialize the mouse controller.
        
        Args:
            move_duration (float): Default duration for mouse movements
        """
        self.move_duration = move_duration
        pyautogui.FAILSAFE = True
        
    def offsetPoint(self, point: Point, offset_x: int = 0, offset_y: int = 0) -> Point:
        """
        Returns a new point with the specified offsets applied.
        
        Args:
            point (tuple): Base (x, y) coordinates
            offset_x (int): Horizontal offset in pixels
            offset_y (int): Vertical offset in pixels
            
        Returns:
            tuple: New (x, y) coordinates with offsets applied, or None if input was None
        """
        if point is None:
            return None
        return (point[0] + offset_x, point[1] + offset_y)
        
    def click(self, point: Point, duration: Duration = None) -> bool:
        """
        Move to a point and click.
        
        Args:
            point (tuple): (x, y) coordinates to click
            duration (float, optional): Override default move duration
        """
        if point is None:
            return False
            
        move_time = duration if duration is not None else self.move_duration
        pyautogui.moveTo(point[0], point[1], duration=move_time)
        pyautogui.click()
        return True
        
    def drag(self, start_point: Point, end_point: Point, duration: Duration = None) -> bool:
        """
        Perform a drag operation from start to end point.
        
        Args:
            start_point (tuple): (x, y) coordinates to start drag
            end_point (tuple): (x, y) coordinates to end drag
            duration (float, optional): Override default move duration
        """
        if start_point is None or end_point is None:
            return False
            
        move_time = duration if duration is not None else self.move_duration
        pyautogui.moveTo(start_point[0], start_point[1], duration=move_time)
        pyautogui.mouseDown()
        pyautogui.moveTo(end_point[0], end_point[1], duration=move_time)
        pyautogui.mouseUp()
        return True
        
    def pressKey(self, key: str) -> bool:
        """
        Press a keyboard key.
        
        Args:
            key (str): Key to press (e.g., 'escape', 'enter', 'space')
        """
        pyautogui.press(key)
        return True

    def mouseDownAt(self, point: Point, duration: Duration = None) -> bool:
        """
        Move to a point and press the mouse button down.
        
        Args:
            point (tuple): (x, y) coordinates to move to
            duration (float, optional): Override default move duration
        """
        if point is None:
            return False
            
        move_time = duration if duration is not None else self.move_duration
        pyautogui.moveTo(point[0], point[1], duration=move_time)
        pyautogui.mouseDown()
        return True
        
    def moveMouseBetweenPoints(self, points: list[Point], circle_radius: int = 0, circle_points: int = 0, duration: Duration = None) -> bool:
        """
        Move the mouse through a series of points with a small circular motion around each point.
        
        Args:
            points (list): List of (x, y) coordinate tuples to move through
            circle_radius (int): Radius of circular motion around each point
            circle_points (int): Number of points in the circular motion
            duration (float, optional): Override default move duration per movement
        """
        if not points:
            return False
            
        # Use instant movement (duration=0) for maximum speed
        for point in points:
            if point is None:
                continue
                
            # Move to the actual point instantly
            center_x = point[0] + 20  # Base offset
            center_y = point[1] + 20
            pyautogui.moveTo(center_x, center_y, duration=0)
            
            # Make a small circular motion around the point instantly
            if circle_points > 0:
                for i in range(circle_points):
                    angle = 2 * math.pi * i / circle_points
                    x = center_x + circle_radius * math.cos(angle)
                    y = center_y + circle_radius * math.sin(angle)
                    pyautogui.moveTo(x, y, duration=0)  # Instant circular motion
                
        return True
        
    def mouseUp(self) -> bool:
        """Release the mouse button."""
        pyautogui.mouseUp()
        return True

    def clickPoints(self, points: list[Point], duration: Duration = None) -> bool:
        """
        Click all points in the list sequentially.
        
        Args:
            points (List[Point]): List of (x, y) coordinates to click
            duration (float, optional): Override default move duration per click
            
        Returns:
            bool: True if any points were clicked, False if list was empty or None
        """
        if not points:
            return False
            
        for point in points:
            if point is None:
                continue
            self.click(point, duration)
            
        return True 