import os
import cv2
import math
import numpy as np

class Scanner:
    def __init__(self, template_dir="images", min_distance=30):
        """
        Initialize the Scanner with template directory and minimum distance between matches.
        
        Args:
            template_dir (str): Base directory where template images are stored.
            min_distance (int): Minimum distance between accepted matches.
        """
        self.template_dir = template_dir
        self.min_distance = min_distance
        
        # Define image categories for organized structure
        self.categories = {
            "farm": ["empty.png", "grown.png", "planting_wheat.png", "hoe.png"],
            "shop": ["shop.png", "sold.png", "create_offer.png", "small_silo.png", 
                    "wheat.png", "10x.png", "lower_price.png", "sell.png", 
                    "wheat_shop.png", "create_advert.png", "advert.png", "shop_close.png"],
            "ui": ["silo_full.png", "silo_close.png", "large_shop_close.png", "advert_close.png"]
        }
        
        # Create a lookup dictionary for faster category lookup
        self.image_category = {}
        for category, images in self.categories.items():
            for image in images:
                self.image_category[image] = category

    def load_template(self, filename):
        """
        Load a template image from the appropriate category directory.
        
        Args:
            filename (str): Name of the template image file.
            
        Returns:
            tuple: (template, (width, height)) - The template image and its dimensions.
            
        Raises:
            FileNotFoundError: If the template image cannot be found.
        """
        if filename in self.image_category:
            category = self.image_category[filename]
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                self.template_dir, 
                category, 
                filename
            )
        else:
            # If the image is not categorized, look in the base directory
            # This should not happen with the current setup but provides flexibility
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                self.template_dir, 
                filename
            )
        
        template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise FileNotFoundError(f"Template not found: {path}")
        
        return template, template.shape[::-1]

    def findPoints(self, screenshot, template_filename, threshold, min_distance=None):
        """
        Finds all match points (center positions) in the screenshot that meet the threshold.
        
        Args:
            screenshot: The screenshot image to search in.
            template_filename: Name of the template image file.
            threshold: Minimum matching threshold (0.0 to 1.0).
            min_distance: Minimum distance between matches (overrides instance default if provided).
            
        Returns:
            list: List of (x, y) tuples representing center positions of matches.
        """
        if min_distance is None:
            min_distance = self.min_distance
            
        template, (w, h) = self.load_template(template_filename)
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        positions = [(x + w // 2, y + h // 2) for x, y in zip(locations[1], locations[0])]

        filtered = []
        for pos in positions:
            if all(math.hypot(pos[0] - p[0], pos[1] - p[1]) >= min_distance for p in filtered):
                filtered.append(pos)
        return filtered

    def findPoint(self, screenshot, template_filename, threshold):
        """
        Finds the best match point (center position) in the screenshot.
        
        Args:
            screenshot: The screenshot image to search in.
            template_filename: Name of the template image file.
            threshold: Minimum matching threshold (0.0 to 1.0).
            
        Returns:
            tuple: (x, y) tuple representing the center position of the best match,
                  or None if no match meets the threshold.
        """
        template, (w, h) = self.load_template(template_filename)
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return None
        return (max_loc[0] + w // 2, max_loc[1] + h // 2) 