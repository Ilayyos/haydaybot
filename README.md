# HayDay Bot

An automated bot for HayDay farming that handles planting, harvesting, and selling wheat.

## Features

- **Automated Farming**: Automatically plants, grows, and harvests wheat
  ![Automated Farming](https://i.imgur.com/V6oK97k.png)

- **Selling Management**: Handles selling crops and creating advertisements
  ![Selling Management](https://i.imgur.com/Sa2IqDZ.png)

- **Visual Feedback**: Provides real-time visual overlay of bot actions
- **Status Console**: Displays current status and progress of operations
  ![Visual Feedback](https://i.imgur.com/hgwdCua.png)

- **Configurable**: Easy to modify timing and detection parameters
- **Dry Run Mode**: Validate detection logic without sending mouse or keyboard input
- **Flexible CLI**: Override most runtime options via flags or a JSON config file

## Requirements

- Python 3.8+
- OpenCV
- PyAutoGUI
- NumPy
- Pillow
- Pynput

See `requirements.txt` for specific version requirements.

## Installation

1. Clone this repository:

   ```
   git clone https://github.com/poperiedev/haydaybot.git
   cd haydaybot
   ```

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Ensure you have the `images` directory with all required template images organized in their respective subfolders.

## Usage

Run `python main.py --help` to see the available CLI options. A few useful examples:

```bash
# Start with default settings
python main.py

# Disable mouse/keyboard output and dry-run the detection logic
python main.py --dry-run

# Capture a different monitor and disable the overlay
python main.py --monitor 2 --no-visualiser
```

Press the **SPACE** key at any time to request a graceful shutdown.

### Configuration file

The bot can be configured via a JSON file passed with `--config`. Any CLI flag
overrides the values defined in the file. A minimal example:

```json
{
  "monitor_index": 1,
  "display_offset": [-1920, 0],
  "move_duration": 0.3,
  "plant_wait_seconds": 120,
  "max_retries": 4,
  "dry_run": false,
  "thresholds": {
    "empty_slots": 0.82,
    "grown_wheat": 0.78
  }
}
```

### Template preloading

Passing `--prewarm` loads and caches all templates on startup which helps
reduce disk I/O pauses during long sessions. Use `--no-prewarm` to explicitly
skip the warm-up step.

## Project Structure

- `main.py` - Entry point and main loop
- `controller.py` - Mouse and keyboard control
- `scanner.py` - Image recognition and template matching
- `visualiser.py` - Visual overlay system
- `status_console.py` - Status message display
- `bot_actions.py` - Core bot actions (plant, harvest, sell)
- `constants.py` - Shared constants and type definitions

### Image Organization

The template images are organized into categories based on their function:

- **Farm Images** (`images/farm/`): Templates related to farming activities
  - empty.png - Empty farm slots
  - grown.png - Grown wheat ready for harvest
  - planting_wheat.png - Wheat planting button
  - hoe.png - Harvesting tool
- **Shop Images** (`images/shop/`): Templates related to shop and selling
  - shop.png - Shop button
  - sold.png - Sold items indicator
  - create_offer.png - Create offer button
  - small_silo.png - Silo button in shop
  - wheat.png - Wheat item in silo
  - 10x.png - Quantity selector
  - lower_price.png - Lower price button
  - sell.png - Sell button
  - wheat_shop.png - Wheat in shop
  - create_advert.png - Create advertisement button
  - advert.png - Advertisement option
  - shop_close.png - Shop close button
- **UI Images** (`images/ui/`): Templates related to UI elements and notifications
  - silo_full.png - Silo full notification
  - silo_close.png - Silo close button
  - large_shop_close.png - Large shop close button
  - advert_close.png - Advertisement close button

## Configuration

You can modify the following settings in `constants.py`:

- `VISUALISER_ENABLED` - Enable/disable visual feedback
- Color constants for visual elements
- Timing constants for UI interactions

## Troubleshooting

- **Bot not finding elements**: Check that your game resolution matches the expected resolution and that template images are correct.
- **Mouse movements not working**: Ensure PyAutoGUI has proper permissions to control your mouse.
- **Visual overlay issues**: Check that OpenCV windows are properly configured for your system.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the LICENSE file for details.

## Disclaimer

This bot is for educational purposes only. Use at your own risk. The developers are not responsible for any consequences of using this bot, including but not limited to account bans or violations of terms of service.
