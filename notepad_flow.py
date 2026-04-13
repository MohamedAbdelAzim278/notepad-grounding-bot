import logging
import time
from pathlib import Path
import pygetwindow as gw

from config import SAVE_DIR
from desktop_bot import double_click_at, type_text, save_file_with_dialog, close_notepad, clear_text, show_desktop, find_notepad_icon
from detector import find_word_on_screen

log = logging.getLogger(__name__)


def _is_notepad_window(title: str) -> bool:
    """Match real Notepad windows: 'Untitled - Notepad' or 'file.txt - Notepad'."""
    t = title.strip().lower()
    return t == "notepad" or t.endswith("- notepad")


def ensure_save_dir():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)


def wait_for_notepad(timeout_seconds: int = 8) -> bool:
    log.debug("Waiting up to %ds for Notepad window...", timeout_seconds)
    end_time = time.time() + timeout_seconds
    while time.time() < end_time:
        windows = [w for w in gw.getAllWindows() if _is_notepad_window(w.title)]
        if windows:
            win = windows[0]
            log.info("Notepad window detected: '%s'", win.title)
            try:
                win.activate()
                time.sleep(0.5)
                log.debug("Notepad window activated and focused.")
            except Exception as e:
                log.warning("Could not activate Notepad window: %s", e)
            return True
        time.sleep(0.5)
    log.warning("Notepad window did not appear within %ds.", timeout_seconds)
    return False


def close_and_verify_notepad(timeout_seconds: int = 5):
    """Close Notepad and wait until no Notepad windows remain.
    Visually handles any 'save changes?' dialog that appears after Alt+F4.
    """
    close_notepad()
    end_time = time.time() + timeout_seconds
    while time.time() < end_time:
        windows = [w for w in gw.getAllWindows() if _is_notepad_window(w.title)]
        if not windows:
            log.info("Notepad closed successfully.")
            return

        # Visually check for a 'save changes?' dialog and click Don't Save
        coords = find_word_on_screen("Don't")
        if coords:
            log.info("'Save changes?' dialog detected — clicking Don't Save at (%d, %d).", *coords)
            double_click_at(*coords)
            time.sleep(0.5)
            continue

        time.sleep(0.3)

    log.warning("Notepad window still visible after %ds — forcing close.", timeout_seconds)
    for w in gw.getAllWindows():
        if _is_notepad_window(w.title):
            try:
                w.close()
            except Exception as e:
                log.warning("Force-close failed: %s", e)
    time.sleep(0.5)


def launch_notepad_from_desktop():
    match = find_notepad_icon()
    if not match:
        # Other windows might be covering the icon — minimize everything
        # via Win+D and try once more against a clean desktop.
        log.info("Notepad icon not found — showing desktop (Win+D) and retrying.")
        show_desktop()
        match = find_notepad_icon()
        if not match:
            log.error("Notepad icon still not found after Win+D.")
            return None

    log.info("Double-clicking Notepad icon at (%d, %d)...", match["x"], match["y"])
    double_click_at(match["x"], match["y"])

    if not wait_for_notepad():
        log.error("Notepad did not open after double-click.")
        return None

    return match


def write_and_save_post(post: dict):
    ensure_save_dir()

    content = f"Title: {post['title']}\n\n{post['body']}"
    file_path = SAVE_DIR / f"post_{post['id']}.txt"

    log.info("Clearing text area before typing post %d...", post["id"])
    clear_text()

    log.info("Typing content for post %d...", post["id"])
    type_text(content)

    log.info("Saving file: %s", file_path)
    save_file_with_dialog(str(file_path))

    # Wait briefly for replace dialog to render, then check visually
    time.sleep(0.8)
    coords = find_word_on_screen("Yes")
    if coords:
        log.info("Replace dialog found — clicking Yes at (%d, %d).", *coords)
        double_click_at(*coords)
        time.sleep(0.5)
    else:
        log.debug("No replace dialog detected, continuing.")

    log.info("Closing Notepad.")
    close_and_verify_notepad()

    log.info("Post %d written and saved successfully.", post["id"])
    return file_path
