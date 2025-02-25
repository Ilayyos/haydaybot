import time
import cv2
from pynput import keyboard

from controller import Controller
from scanner import Scanner
from visualiser import Visualiser
from bot_actions import plant, harvest, sell
from constants import RED

# Global exit flag
exit_flag = False

def on_press(key):
    """Handle keyboard press events."""
    global exit_flag
    try:
        if key == keyboard.Key.space:
            print("\nExiting program...")
            exit_flag = True
            return False  # Stop listener
    except AttributeError:
        pass

def main():
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # Initialize components
    scanner = Scanner()
    visualiser = Visualiser(display_offset=(-1920, 0))
    controller = Controller(move_duration=0.5)
    
    print("Bot started! Press SPACE to exit at any time.")
    
    try:
        while not exit_flag:
            screenshot = visualiser.take_screenshot()
            empty_slots = scanner.findPoints(screenshot, "empty.png", 0.8, 60)
            # Remove every third slot like in plant function
            filtered_slots = [slot for i, slot in enumerate(empty_slots) if (i + 1) % 3 != 0]
            empty_slots = filtered_slots
            
            if not empty_slots:  # No empty slots found
                print("No empty slots available, waiting 5 seconds...")
                visualiser.createTimer(5, color=RED)  # Create a red 5-second timer
                while visualiser.updateTimer() and not exit_flag:
                    time.sleep(0.1)
            else:
                plant(scanner=scanner, controller=controller, visualiser=visualiser)
                
                screenshot = visualiser.take_screenshot()
                visualiser.createTimer(120)
                
                while visualiser.updateTimer() and not exit_flag:
                    time.sleep(0.1)
                
            if not exit_flag:
                harvest(scanner=scanner, controller=controller, visualiser=visualiser)
            
            time.sleep(1)  # Small delay between cycles
            
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        # Cleanup
        print("\nBot stopped successfully!")
        cv2.destroyAllWindows()
        listener.stop()

if __name__ == "__main__":
    main() 