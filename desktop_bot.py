from botcity.core import DesktopBot
import logging
import time

import cv2
import numpy as np
from PIL import ImageGrab

from config import NOTEPAD_TEMPLATE, BOTCITY_MATCH_THRESHOLD, ANNOTATED_PATH, OUTPUT_DIR

log = logging.getLogger(__name__)


class MyBot(DesktopBot):
    pass


bot = MyBot()

# Register the Notepad icon template once at import time.
bot.add_image("notepad", str(NOTEPAD_TEMPLATE))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def double_click_at(x: int, y: int):
    bot.click_at(x=x, y=y)
    bot.wait(200)
    bot.click_at(x=x, y=y)


def type_text(text: str):
    # Select all first so any existing content is replaced by the paste
    bot.control_a(wait=200)
    bot.paste(text, wait=500)


def clear_text():
    # No-op: type_text already selects-all before pasting, so this is handled there
    pass


def press_enter():
    bot.enter()


def save_file_with_dialog(full_path: str):
    # Alt+F, A always opens Save As regardless of whether file is already named.
    # This prevents Ctrl+S silently saving to a previous filename.
    bot.alt_f(wait=800)
    bot.kb_type("a")
    bot.wait(1000)

    # Select all existing text in the filename field, then paste the full path
    bot.control_a(wait=200)
    bot.paste(full_path, wait=500)
    bot.enter(wait=1500)


def close_notepad():
    # Alt+F4 using generic multi-key press
    bot.type_keys_with_interval(100, ["alt", "f4"])
    bot.wait(1000)


def show_desktop():
    # Win+D — minimizes all windows to reveal the desktop.
    bot.type_keys_with_interval(100, ["win", "d"])
    bot.wait(800)


def find_notepad_icon() -> dict | None:
    """Locate the Notepad icon on the desktop using BotCity's built-in
    template matching. Returns {'x', 'y', 'score'} or None if not found.
    """
    found = bot.find("notepad", matching=BOTCITY_MATCH_THRESHOLD, waiting_time=3000)
    if not found:
        log.warning("BotCity find: Notepad icon not found (threshold=%.2f).", BOTCITY_MATCH_THRESHOLD)
        return None

    # get_last_x/y return the top-left corner of the matched region.
    # BotCity also stores element width/height — use them to get the center.
    el = bot.get_last_element()
    center_x = el.left + el.width // 2
    center_y = el.top + el.height // 2

    # Annotate and save a debug screenshot showing the detected region.
    screenshot = cv2.cvtColor(np.array(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
    cv2.rectangle(screenshot, (el.left, el.top), (el.left + el.width, el.top + el.height), (0, 255, 0), 2)
    cv2.circle(screenshot, (center_x, center_y), 6, (0, 0, 255), -1)
    cv2.putText(screenshot, f"score={BOTCITY_MATCH_THRESHOLD:.2f}",
                (el.left, max(20, el.top - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imwrite(str(ANNOTATED_PATH), screenshot)
    log.debug("Annotated screenshot saved to %s", ANNOTATED_PATH)

    log.info("Notepad icon detected at (%d, %d) via BotCity find.", center_x, center_y)
    return {"x": center_x, "y": center_y, "score": float(BOTCITY_MATCH_THRESHOLD),
            "annotated_path": str(ANNOTATED_PATH)}


def sleep_seconds(seconds: float):
    time.sleep(seconds)