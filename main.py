"""Entry point for the HayDay automation bot."""

from __future__ import annotations

import argparse
import logging
import threading
import time
from typing import Optional

import cv2
from pynput import keyboard

from bot_actions import HayDayBot
from config import BotConfig
from controller import Controller
from scanner import Scanner
from visualiser import Visualiser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automate HayDay farming tasks")
    parser.add_argument("--config", help="Path to JSON configuration file")
    parser.add_argument("--monitor", type=int, help="Monitor index to capture (1 = primary)")
    parser.add_argument("--offset", help="Display offset as 'x,y'")
    parser.add_argument("--move-duration", type=float, help="Mouse move duration in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Do not send mouse/keyboard events")
    parser.add_argument("--no-visualiser", action="store_true", help="Disable the overlay window")
    parser.add_argument("--prefer-pil", action="store_true", help="Prefer Pillow over MSS for screenshots")
    parser.add_argument("--plant-wait", type=int, help="Seconds to wait for crops to grow")
    parser.add_argument("--loop-delay", type=float, help="Delay between cycles in seconds")
    parser.add_argument("--max-retries", type=int, help="Maximum retries for planting/harvesting")
    parser.add_argument("--template-dir", help="Directory containing template images")
    parser.add_argument("--ui-delay", type=float, help="Delay for UI transitions")
    parser.add_argument("--fast-click", type=float, help="Duration for fast click actions")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--prewarm", dest="prewarm", action="store_true", help="Preload template images")
    parser.add_argument("--no-prewarm", dest="prewarm", action="store_false", help="Disable template preloading")
    parser.set_defaults(prewarm=None)
    return parser


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(args.verbose)
    config = BotConfig.from_args(args)
    config.describe()

    stop_event = threading.Event()

    def on_press(key: keyboard.Key) -> Optional[bool]:
        try:
            if key == keyboard.Key.space:
                logging.info("Stop signal received via keyboard")
                stop_event.set()
                return False
        except AttributeError:
            return None
        return None

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    scanner = Scanner(
        template_dir=config.template_dir,
        cache_templates=True,
        preload=config.prewarm_templates,
    )
    controller = Controller(move_duration=config.move_duration, dry_run=config.dry_run)
    visualiser = Visualiser(
        display_offset=config.display_offset,
        enabled=config.visualiser_enabled,
        monitor_index=config.monitor_index,
        prefer_mss=config.prefer_mss,
    )

    bot = HayDayBot(scanner, controller, visualiser, config)

    logging.info("Bot started. Press SPACE to stop.")

    try:
        while not stop_event.is_set():
            result = bot.execute_cycle(stop_event)
            logging.info("Cycle result: %s", result.message)

            if config.idle_delay > 0:
                end_time = time.time() + config.idle_delay
                while time.time() < end_time and not stop_event.is_set():
                    time.sleep(0.1)

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        stop_event.set()
    except Exception:
        logging.exception("Unexpected error during execution")
        stop_event.set()
    finally:
        logging.info("Shutting down bot")
        stop_event.set()
        listener.stop()
        visualiser.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

