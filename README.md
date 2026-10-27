# Notepad Grounding Bot

A Windows desktop RPA bot that fetches posts from an API and saves each one as a `.txt` file using Notepad — fully automated via visual desktop detection.

## What it does

1. Fetches 10 posts from `https://jsonplaceholder.typicode.com/posts` (falls back to `assets/sample_posts.json` if the API is unreachable)
2. For each post, detects the Notepad icon on the desktop using BotCity's image matching
3. Double-clicks it to open Notepad, types the post content, saves it as `~/Desktop/notepad-posts/post_<id>.txt`, then closes Notepad
4. Repeats for all 10 posts

A stop button stays always-on-top in the top-right corner so you can halt the bot at any time.

---

## Requirements

- Windows 10/11 with a visible desktop (not headless)
- Python 3.14
- [uv](https://docs.astral.sh/uv/) package manager
- Tesseract OCR (see below)
- The Notepad icon visible on the desktop

---

## 1. Install Tesseract OCR

Tesseract is required for detecting on-screen dialogs (e.g. "Replace file?" popups).

1. Download the installer from the official releases:
   - Go to `https://github.com/UB-Mannheim/tesseract/wiki` and grab the latest Windows 64-bit `.exe`
2. Run the installer. When asked for the install path, use the default:
   ```
   C:\Program Files\Tesseract-OCR\
   ```
3. Verify it installed correctly by opening a terminal and running:
   ```bash
   "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
   ```

> If you install to a different path, update `TESSERACT_CMD` in `config.py` to match.

---

## 2. Install Python dependencies

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

Install uv if you don't have it:
```bash
pip install uv
```

Then install all project dependencies:
```bash
uv sync
```

---

## 3. Set up the Notepad icon template

The bot detects Notepad by matching a reference image (`assets/notepad_icon.png`) against the live desktop.

A pre-captured template is already included. If detection fails on your machine (different DPI, icon size, or theme), recapture it from your own screen:

```bash
# Step 1 — take a full desktop screenshot to find the icon coordinates
uv run python -c "
from PIL import ImageGrab
img = ImageGrab.grab()
img.save('output/desktop_fresh.png')
print('Saved to output/desktop_fresh.png')
"
```

Open `output/desktop_fresh.png`, find the Notepad icon pixel bounds, then crop and save:

```bash
# Step 2 — replace left/top/right/bottom with the actual coordinates
uv run python -c "
from PIL import ImageGrab
img = ImageGrab.grab()
icon = img.crop((left, top, right, bottom))
icon.save('assets/notepad_icon.png')
print('Template saved:', icon.size)
"
```

---

## 4. Run the bot

Make sure the Notepad icon is visible on your desktop, then run:

```bash
uv run python main.py
```

The bot will:
- Show a small **Stop** button in the top-right corner of the screen
- Process each post one by one
- Save output files to `~/Desktop/notepad-posts/`
- Write a timestamped log to `logs/`

Click **Stop** at any time to halt after the current post finishes.

---

## Configuration

All tunable settings are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `BOTCITY_MATCH_THRESHOLD` | `0.9` | Icon detection confidence (0.0–1.0). Lower if detection fails. |
| `MAX_RETRIES` | `3` | How many times to retry finding the icon before giving up |
| `RETRY_DELAY_SECONDS` | `1` | Seconds to wait between retries |
| `SAVE_DIR` | `~/Desktop/notepad-posts` | Where the output `.txt` files are saved |
| `TESSERACT_CMD` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | Path to Tesseract executable |

---

## Troubleshooting

**Bot can't find the Notepad icon**
- Make sure the icon is on the desktop and not hidden behind other windows
- The bot will automatically press Win+D to show the desktop and retry once
- If it still fails, lower `BOTCITY_MATCH_THRESHOLD` in `config.py` (try `0.7`) or recapture the template (step 3 above)

**Files are saved empty**
- Notepad may not have had focus before typing — check the logs for activation warnings

**Tesseract not found**
- Verify the install path matches `TESSERACT_CMD` in `config.py`
- Run `"C:\Program Files\Tesseract-OCR\tesseract.exe" --version` in your terminal to confirm
