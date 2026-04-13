from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"

DESKTOP_DIR = Path.home() / "Desktop"
SAVE_DIR = DESKTOP_DIR / "tjm-project"

NOTEPAD_TEMPLATE = ASSETS_DIR / "notepad_icon.png"
API_URL = "https://jsonplaceholder.typicode.com/posts"

SCREENSHOT_PATH = OUTPUT_DIR / "desktop.png"
ANNOTATED_PATH = OUTPUT_DIR / "annotated_detection.png"

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1
MATCH_THRESHOLD = 0.75
BOTCITY_MATCH_THRESHOLD = 0.9

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"