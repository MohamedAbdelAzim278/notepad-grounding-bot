import logging
import threading
import time
from config import MAX_RETRIES, RETRY_DELAY_SECONDS
from logger import setup_run_logger
from posts_api import fetch_first_10_posts
from notepad_flow import launch_notepad_from_desktop, write_and_save_post
from stop_button import run_stop_button, is_stopped

log = logging.getLogger(__name__)


def launch_with_retry():
    for attempt in range(1, MAX_RETRIES + 1):
        if is_stopped():
            return False
        log.info("Attempt %d/%d: searching for Notepad icon...", attempt, MAX_RETRIES)
        match = launch_notepad_from_desktop()
        if match:
            log.info("Notepad icon found at (%d, %d) score=%.2f", match["x"], match["y"], match["score"])
            log.debug("Annotated screenshot: %s", match["annotated_path"])
            return True

        log.warning("Attempt %d/%d failed to find or launch Notepad.", attempt, MAX_RETRIES)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS)

    return False


def run_bot():
    setup_run_logger()
    log.info("=== Run started ===")

    log.info("Fetching posts...")
    posts = fetch_first_10_posts()
    log.info("Retrieved %d posts.", len(posts))

    for post in posts:
        if is_stopped():
            log.info("Stop requested — exiting after post %d.", post["id"])
            break

        log.info("Processing post %d...", post["id"])

        if not launch_with_retry():
            if is_stopped():
                log.info("Stop requested during icon search.")
                break
            log.error("Could not detect or launch Notepad after %d retries.", MAX_RETRIES)
            raise RuntimeError("Could not detect or launch Notepad after retries.")

        file_path = write_and_save_post(post)
        log.info("Saved post %d -> %s", post["id"], file_path)

        time.sleep(1)

    log.info("=== Bot finished ===")


def main():
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Stop button runs on the main thread (required by tkinter)
    run_stop_button()

    # If window closed before bot finished, wait briefly for clean shutdown
    bot_thread.join(timeout=3)


if __name__ == "__main__":
    main()
