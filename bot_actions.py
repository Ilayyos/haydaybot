import time
from scanner import Scanner
from controller import Controller
from visualiser import Visualiser
from constants import TARGET_COLOR, ACTION_COLOR, WARNING_COLOR, PATH_COLOR, CLICK_COLOR, UI_DELAY, FAST_CLICK_DURATION

def plant(scanner: Scanner, controller: Controller, visualiser: Visualiser) -> None:
    """Plant wheat in all empty farm slots."""
    visualiser.status_console.add_message("Starting planting sequence")
    visualiser.status_console.set_progress("Planting", 0.0, TARGET_COLOR)
    
    screenshot = visualiser.take_screenshot()
    empty_slots = scanner.findPoints(screenshot, "empty.png", 0.8)
    visualiser.status_console.add_message(f"Found {len(empty_slots)} empty slots")
    
    # Show empty slots as green squares
    empty_slot_visuals = visualiser.addVisuals(empty_slots, TARGET_COLOR, radius=15, point_type="target")
    
    if not empty_slots:
        visualiser.status_console.add_message("No empty slots found")
        visualiser.status_console.remove_progress("Planting")
        visualiser.removeVisuals(empty_slot_visuals)  # Clean up visuals
        print("Edge case: No empty slots found during planting phase")
        return
        
    if empty_slots[0]:
        visualiser.status_console.set_progress("Planting", 0.2, TARGET_COLOR)
        visualiser.status_console.add_message("Selecting first empty slot")
        click_visual = visualiser.addVisuals(empty_slots[0], CLICK_COLOR, radius=10, point_type="click")
        controller.click(empty_slots[0], duration=0)
        visualiser.removeVisuals(click_visual)
        time.sleep(1)
    
    controller.pressKey('escape')
    visualiser.status_console.set_progress("Planting", 0.4, TARGET_COLOR)
    
    screenshot = visualiser.take_screenshot()
    visualiser.removeVisuals(empty_slot_visuals)  # Now empty_slot_visuals is defined
    
    empty_slots = scanner.findPoints(screenshot, "empty.png", 0.8, 60)
    
    if not empty_slots:
        visualiser.status_console.add_message("Lost empty slots after click")
        visualiser.status_console.remove_progress("Planting")
        print("Edge case: Lost empty slots after initial click")
        return
        
    visualiser.status_console.set_progress("Planting", 0.6, TARGET_COLOR)
    visualiser.status_console.add_message("Preparing to plant wheat")
    
    empty_slot_dots = visualiser.addVisuals(empty_slots, TARGET_COLOR, radius=15, point_type="target")
    
    line_ids = []
    if len(empty_slots) > 1:
        line_ids = visualiser.addDragPath(empty_slots, PATH_COLOR, thickness=2)
            
    click_visual = visualiser.addVisuals(empty_slots[0], CLICK_COLOR, radius=10, point_type="click")
    controller.click(empty_slots[0], duration=0)
    visualiser.removeVisuals(click_visual)
    
    screenshot = visualiser.take_screenshot()
    
    planting_wheat_point = scanner.findPoint(screenshot, "planting_wheat.png", 0.8)
    if planting_wheat_point is None:
        visualiser.status_console.add_message("Failed to find wheat button")
        visualiser.status_console.remove_progress("Planting")
        print("Edge case: Failed to find wheat planting button")
        return
        
    visualiser.status_console.set_progress("Planting", 0.8, TARGET_COLOR)
    visualiser.status_console.add_message("Planting wheat")
    
    planting_wheat_visual = visualiser.addVisuals(planting_wheat_point, ACTION_COLOR, radius=10, point_type="action")
    controller.mouseDownAt(planting_wheat_point, duration=0)
    controller.moveMouseBetweenPoints(empty_slots, 60, 4, duration=0)
    controller.mouseUp()
    
    controller.pressKey('escape')
    
    visualiser.removeVisuals(planting_wheat_visual)
    visualiser.removeVisuals(empty_slot_dots)
    visualiser.removeVisuals(line_ids)
    visualiser.take_screenshot()
    
    time.sleep(0.5)
    
    screenshot = visualiser.take_screenshot()
    empty_slots = scanner.findPoints(screenshot, "empty.png", 0.8)
    if len(empty_slots) > 1:
        missed = len(empty_slots)
        visualiser.status_console.add_message(f"Missed {missed} slots, retrying")
        print(f"Edge case: {missed} slots were missed during planting!")
        plant(scanner=scanner, controller=controller, visualiser=visualiser)
    else:
        visualiser.status_console.set_progress("Planting", 1.0, TARGET_COLOR)
        visualiser.status_console.add_message("Planting completed successfully")
        
    visualiser.status_console.remove_progress("Planting")

def harvest(scanner: Scanner, controller: Controller, visualiser: Visualiser) -> None:
    """Harvest all grown wheat from the farm."""
    visualiser.status_console.add_message("Starting harvest sequence")
    visualiser.status_console.set_progress("Harvesting", 0.0, ACTION_COLOR)
    
    def checkIfSiloFull() -> bool:
        screenshot = visualiser.take_screenshot()
        silo_full_point = scanner.findPoint(screenshot, "silo_full.png", 0.8)
        if (silo_full_point is not None):
            visualiser.status_console.add_message("Silo is full, need to sell")
            print("Edge case: Silo is full, initiating sell sequence")
            silo_visual = visualiser.addVisuals(silo_full_point, WARNING_COLOR, radius=20, point_type="target")
            silo_close_point = scanner.findPoint(screenshot, "silo_close.png", 0.8)
            if silo_close_point is None:
                visualiser.status_console.add_message("Failed to find close button")
                print("Edge case: Failed to find silo close button")
                return False
            click_visual = visualiser.addVisuals(silo_close_point, CLICK_COLOR, radius=10, point_type="click")
            controller.click(silo_close_point, duration=0)
            visualiser.removeVisuals(click_visual)
            visualiser.removeVisuals(silo_visual)
            
            time.sleep(0.25)
            return True
        return False
            
    def getHoeInHand() -> None:
        visualiser.status_console.add_message("Getting hoe tool")
        screenshot = visualiser.take_screenshot()
    
        hoe_point = scanner.findPoint(screenshot, "hoe.png", 0.9)
        if (hoe_point is None):
            visualiser.status_console.add_message("Failed to find hoe, retrying")
            print("Edge case: Failed to find hoe tool, retrying harvest")
            harvest(scanner, controller, visualiser)
            return
        
        hoe_visual = visualiser.addVisuals(hoe_point, ACTION_COLOR, radius=15, point_type="action")
        controller.mouseDownAt(hoe_point, duration=0)
        visualiser.removeVisuals(hoe_visual)
        
    screenshot = visualiser.take_screenshot()
    grown_points = scanner.findPoints(screenshot, "grown.png", threshold=0.8)
    
    if not grown_points:
        visualiser.status_console.add_message("No grown wheat found")
        visualiser.status_console.remove_progress("Harvesting")
        print("Edge case: No grown wheat found to harvest")
        return
        
    visualiser.status_console.add_message(f"Found {len(grown_points)} grown wheat")
    visualiser.status_console.set_progress("Harvesting", 0.2, ACTION_COLOR)
    
    grown_visuals = visualiser.addVisuals(grown_points, TARGET_COLOR, radius=15, point_type="target")
    
    if len(grown_points) > 0:
        if grown_points[0]:
            visualiser.status_console.set_progress("Harvesting", 0.4, ACTION_COLOR)
            click_visual = visualiser.addVisuals(grown_points[0], CLICK_COLOR, radius=10, point_type="click")
            controller.click(grown_points[0], duration=0)
            visualiser.removeVisuals(click_visual)
            time.sleep(1)
    else:
        visualiser.status_console.add_message("Lost grown points")
        print("Edge case: Lost grown points after detection")
        return
    
    controller.pressKey('escape')
    visualiser.status_console.set_progress("Harvesting", 0.6, ACTION_COLOR)
    
    screenshot = visualiser.take_screenshot()
    visualiser.removeVisuals(grown_visuals)
    
    grown_points = scanner.findPoints(screenshot, "grown.png", 0.8)
    if not grown_points:
        visualiser.status_console.add_message("Lost grown points after escape")
        print("Edge case: Lost grown points after escape key")
        return
        
    visualiser.status_console.set_progress("Harvesting", 0.8, ACTION_COLOR)
    visualiser.status_console.add_message("Harvesting wheat")
    
    grown_visuals = visualiser.addVisuals(grown_points, TARGET_COLOR, radius=15, point_type="target")
    
    line_ids = []
    if len(grown_points) > 1:
        line_ids = visualiser.addDragPath(grown_points, PATH_COLOR, thickness=2)
    
    offset_point = controller.offsetPoint(grown_points[0], 10, 10)
    offset_visual = visualiser.addVisuals(offset_point, CLICK_COLOR, radius=10, point_type="click")
    
    controller.click(offset_point, duration=0)
    
    getHoeInHand()

    controller.moveMouseBetweenPoints(grown_points, 70, 4, duration=0)
    controller.mouseUp()
    
    visualiser.removeVisuals(line_ids)
    visualiser.removeVisuals(grown_visuals)
    visualiser.removeVisuals(offset_visual)
    
    if (checkIfSiloFull() is True):
        visualiser.status_console.set_progress("Harvesting", 1.0, ACTION_COLOR)
        visualiser.status_console.remove_progress("Harvesting")
        sell(scanner, controller, visualiser)
        return
    
    time.sleep(0.5)
    
    screenshot = visualiser.take_screenshot()
    grown_points = scanner.findPoints(screenshot, "grown.png", 0.8)
    if len(grown_points) > 0:
        missed = len(grown_points)
        visualiser.status_console.add_message(f"Missed {missed} spots, retrying")
        print(f"Edge case: {missed} grown spots were missed during harvesting!")
        harvest(scanner=scanner, controller=controller, visualiser=visualiser)
    else:
        visualiser.status_console.set_progress("Harvesting", 1.0, ACTION_COLOR)
        visualiser.status_console.add_message("Harvesting completed successfully")
        
    visualiser.status_console.remove_progress("Harvesting")

def sell(scanner: Scanner, controller: Controller, visualiser: Visualiser) -> None:
    """Sell harvested wheat at the shop."""
    visualiser.status_console.add_message("Starting sell sequence")
    visualiser.status_console.set_progress("Selling", 0.0, WARNING_COLOR)
    
    screenshot = visualiser.take_screenshot()
    shop_point = scanner.findPoint(screenshot, "shop.png", 0.8)
    if shop_point is None:
        visualiser.status_console.add_message("Failed to find shop button")
        visualiser.status_console.remove_progress("Selling")
        print("Edge case: Failed to find shop button")
        return
        
    visualiser.status_console.set_progress("Selling", 0.2, WARNING_COLOR)
    visualiser.status_console.add_message("Opening shop")
    
    shop_visual = visualiser.addVisuals(shop_point, ACTION_COLOR, radius=15, point_type="action")
    controller.click(shop_point, FAST_CLICK_DURATION)
    visualiser.removeVisuals(shop_visual)
    time.sleep(UI_DELAY)  # Wait for shop to open
    
    screenshot = visualiser.take_screenshot()
    sold_points = scanner.findPoints(screenshot, "sold.png", 0.8)
    if sold_points:
        visualiser.status_console.add_message(f"Clearing {len(sold_points)} sold items")
        print(f"Edge case: Found {len(sold_points)} sold items to clear")
        
    visualiser.status_console.set_progress("Selling", 0.4, WARNING_COLOR)
    
    sold_visuals = []
    for point in sold_points:
        sold_visuals.extend(visualiser.addVisuals(point, WARNING_COLOR, radius=15, point_type="target"))
        click_visual = visualiser.addVisuals(point, CLICK_COLOR, radius=10, point_type="click")
        sold_visuals.extend(click_visual)
        
    controller.clickPoints(sold_points, FAST_CLICK_DURATION)
    visualiser.removeVisuals(sold_visuals)
    time.sleep(UI_DELAY)  # Wait for sold items to clear
    time.sleep(1)
    
    screenshot = visualiser.take_screenshot()
    empty_store_points = scanner.findPoints(screenshot, "create_offer.png", 0.7)
    if not empty_store_points:
        visualiser.status_console.add_message("No empty store slots")
        print("Edge case: No empty store slots available")
        
    visualiser.status_console.set_progress("Selling", 0.6, WARNING_COLOR)
    visualiser.status_console.add_message(f"Creating {len(empty_store_points)} offers")
    
    empty_store_visuals = visualiser.addVisuals(empty_store_points, TARGET_COLOR, radius=15, point_type="target")

    if len(empty_store_points) > 0:
        for i, filling_point in enumerate(empty_store_points):
            progress = 0.6 + (0.3 * (i / len(empty_store_points)))
            visualiser.status_console.set_progress("Selling", progress, WARNING_COLOR)
            
            click_visual = visualiser.addVisuals(filling_point, CLICK_COLOR, radius=10, point_type="click")
            controller.click(filling_point, FAST_CLICK_DURATION)
            visualiser.removeVisuals(click_visual)
            time.sleep(UI_DELAY)  # Wait for create offer dialog
            
            screenshot = visualiser.take_screenshot()
            small_silo_button_point = scanner.findPoint(screenshot, "small_silo.png", 0.8)
            if small_silo_button_point is None:
                visualiser.status_console.add_message("Failed to find silo button")
                print("Edge case: Failed to find silo button in shop")
                continue
                
            silo_visual = visualiser.addVisuals(small_silo_button_point, ACTION_COLOR, radius=15, point_type="action")
            controller.click(small_silo_button_point, FAST_CLICK_DURATION)
            visualiser.removeVisuals(silo_visual)
            time.sleep(UI_DELAY)  # Wait for silo to open
            
            screenshot = visualiser.take_screenshot()
            wheat_point = scanner.findPoint(screenshot, "wheat.png", 0.8)
            if wheat_point is None:
                visualiser.status_console.add_message("Failed to find wheat in silo")
                print("Edge case: Failed to find wheat in silo")
                continue
                
            wheat_visual = visualiser.addVisuals(wheat_point, ACTION_COLOR, radius=15, point_type="action")
            controller.click(wheat_point, FAST_CLICK_DURATION)
            visualiser.removeVisuals(wheat_visual)
            time.sleep(UI_DELAY * 2)  # Extra wait for wheat selection UI
            
            screenshot = visualiser.take_screenshot()
            amount_point = scanner.findPoint(screenshot, "10x.png", 0.8)
            if (amount_point is None):
                visualiser.status_console.add_message("Not enough wheat for 10x")
                print("Edge case: Not enough wheat for 10x sale")
                large_shop_close_point = scanner.findPoint(screenshot, "large_shop_close.png", 0.8)
                close_visual = visualiser.addVisuals(large_shop_close_point, CLICK_COLOR, radius=10, point_type="click")
                controller.click(large_shop_close_point, FAST_CLICK_DURATION)
                visualiser.removeVisuals(close_visual)
                break
            
            lower_price_point = scanner.findPoint(screenshot, "lower_price.png", 0.8)
            put_on_sale_pont = scanner.findPoint(screenshot, "sell.png", 0.8)
            
            sell_targets_list = [lower_price_point, put_on_sale_pont]
            sell_targets_visuals = visualiser.addVisuals(sell_targets_list, ACTION_COLOR, radius=15, point_type="action")
            line_ids = visualiser.addDragPath(sell_targets_list, PATH_COLOR, thickness=2)
            
            controller.clickPoints(sell_targets_list, FAST_CLICK_DURATION)
            visualiser.removeVisuals(line_ids)
            visualiser.removeVisuals(sell_targets_visuals)
            time.sleep(UI_DELAY)  # Wait for sale to complete
            
    visualiser.removeVisuals(empty_store_points)
    screenshot = visualiser.take_screenshot()
    
    visualiser.removeVisuals(empty_store_visuals)
    
    visualiser.status_console.set_progress("Selling", 0.9, WARNING_COLOR)
    visualiser.status_console.add_message("Checking for advertisement")
    
    wheat_in_shop_without_ad_point = scanner.findPoint(screenshot, "wheat_shop.png", 0.8)
    if (wheat_in_shop_without_ad_point is not None):
        wheat_visual = visualiser.addVisuals(wheat_in_shop_without_ad_point, TARGET_COLOR, radius=15, point_type="target")
        controller.click(wheat_in_shop_without_ad_point, FAST_CLICK_DURATION)
        visualiser.removeVisuals(wheat_visual)
        time.sleep(UI_DELAY)  # Wait for wheat details to open
        
        screenshot = visualiser.take_screenshot()
        advert_available_point = scanner.findPoint(screenshot, "advert.png", 0.8)
        if (advert_available_point is None):
            visualiser.status_console.add_message("No advertisement available")
            large_shop_close_point = scanner.findPoint(screenshot, "advert_close.png", 0.8)
            close_visual = visualiser.addVisuals(large_shop_close_point, CLICK_COLOR, radius=10, point_type="click")
            controller.click(large_shop_close_point, FAST_CLICK_DURATION)
            visualiser.removeVisuals(close_visual)
        else:
            visualiser.status_console.add_message("Creating advertisement")
            offsetPoint = controller.offsetPoint(advert_available_point, 300, 0)
            advert_visual = visualiser.addVisuals(offsetPoint, ACTION_COLOR, radius=15, point_type="action")
            controller.click(offsetPoint, FAST_CLICK_DURATION)
            visualiser.removeVisuals(advert_visual)
            time.sleep(UI_DELAY)  # Wait for advert dialog
            
            screenshot = visualiser.take_screenshot()
            create_advert_button_point = scanner.findPoint(screenshot, "create_advert.png", 0.8)
            create_visual = visualiser.addVisuals(create_advert_button_point, ACTION_COLOR, radius=15, point_type="action")
            controller.click(create_advert_button_point, FAST_CLICK_DURATION)
            visualiser.removeVisuals(create_visual)
    
    visualiser.status_console.set_progress("Selling", 1.0, WARNING_COLOR)
    visualiser.status_console.add_message("Closing shop")
    
    visualiser.take_screenshot()
    shop_close_point = scanner.findPoint(screenshot, "shop_close.png", 0.8)
    close_visual = visualiser.addVisuals(shop_close_point, CLICK_COLOR, radius=10, point_type="click")
    controller.click(shop_close_point, FAST_CLICK_DURATION)
    visualiser.removeVisuals(close_visual)
    
    time.sleep(UI_DELAY)  # Wait for shop to close
    screenshot = visualiser.take_screenshot()
    
    visualiser.status_console.remove_progress("Selling")
    visualiser.status_console.add_message("Sell sequence completed")
    
    harvest(scanner=scanner, controller=controller, visualiser=visualiser) 