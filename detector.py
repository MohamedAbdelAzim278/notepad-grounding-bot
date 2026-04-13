import logging
import cv2
import numpy as np
import pytesseract
from pathlib import Path
from PIL import ImageGrab
from config import SCREENSHOT_PATH, ANNOTATED_PATH, NOTEPAD_TEMPLATE, MATCH_THRESHOLD, TESSERACT_CMD, OUTPUT_DIR

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

log = logging.getLogger(__name__)

# Edge-based matching threshold — lower than color since edge scores are naturally smaller.
EDGE_MATCH_THRESHOLD = 0.35

# Scales to try during multi-scale matching (covers icon size variation across DPI/positions).
MATCH_SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]


def capture_desktop_screenshot() -> Path:
    log.debug("Capturing desktop screenshot -> %s", SCREENSHOT_PATH)
    image = ImageGrab.grab()
    image.save(SCREENSHOT_PATH)
    log.debug("Screenshot saved.")
    return SCREENSHOT_PATH


def _edges(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray, 50, 150)


def _best_multiscale_match(screenshot_map, template_map):
    """Try matching template_map against screenshot_map at multiple scales.
    Returns (best_score, best_loc, best_scale).
    """
    best_score, best_loc, best_scale = 0.0, (0, 0), 1.0
    th, tw = template_map.shape[:2]
    sh, sw = screenshot_map.shape[:2]

    for scale in MATCH_SCALES:
        new_w, new_h = int(tw * scale), int(th * scale)
        if new_w < 8 or new_h < 8 or new_w > sw or new_h > sh:
            continue
        resized = cv2.resize(template_map, (new_w, new_h))
        result = cv2.matchTemplate(screenshot_map, resized, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(result)
        if score > best_score:
            best_score, best_loc, best_scale = score, loc, scale

    return best_score, best_loc, best_scale


def find_notepad_icon():
    screenshot_path = capture_desktop_screenshot()

    screenshot = cv2.imread(str(screenshot_path))
    template = cv2.imread(str(NOTEPAD_TEMPLATE))

    if screenshot is None:
        log.error("Failed to read desktop screenshot from %s", screenshot_path)
        raise RuntimeError("Failed to read desktop screenshot.")
    if template is None:
        log.error("Failed to read template image from %s", NOTEPAD_TEMPLATE)
        raise RuntimeError(
            f"Failed to read template image at {NOTEPAD_TEMPLATE}. "
            "Make sure assets/notepad_icon.png exists."
        )

    # Pad the screenshot so matchTemplate can align the template even when
    # the icon sits flush against a screen edge (e.g. top row). Without this
    # padding, a few pixels of clipping destroys the edge-match score.
    th, tw = template.shape[:2]
    max_scale = max(MATCH_SCALES)
    pad_y = int(th * max_scale)
    pad_x = int(tw * max_scale)

    # Replicate-border for color keeps local stats realistic (no artificial
    # black borders that the color matcher would light up on).
    screenshot_padded = cv2.copyMakeBorder(
        screenshot, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_REPLICATE
    )

    # For edges, compute Canny on the original first, then zero-pad the
    # edge map. Padding before Canny would produce false edges at the
    # pad boundary.
    screenshot_edges_raw = _edges(screenshot)
    screenshot_edges = cv2.copyMakeBorder(
        screenshot_edges_raw, pad_y, pad_y, pad_x, pad_x,
        cv2.BORDER_CONSTANT, value=0,
    )
    template_edges = _edges(template)

    edge_score, edge_loc, edge_scale = _best_multiscale_match(screenshot_edges, template_edges)
    log.debug("Edge multi-scale best score=%.4f scale=%.1f (threshold=%.2f)",
              edge_score, edge_scale, EDGE_MATCH_THRESHOLD)

    # Color-based multi-scale match — fallback for when edges alone are weak.
    color_score, color_loc, color_scale = _best_multiscale_match(screenshot_padded, template)
    log.debug("Color multi-scale best score=%.4f scale=%.1f (threshold=%.2f)",
              color_score, color_scale, MATCH_THRESHOLD)

    # Convert padded-image coords back to real screen coords.
    edge_loc = (edge_loc[0] - pad_x, edge_loc[1] - pad_y)
    color_loc = (color_loc[0] - pad_x, color_loc[1] - pad_y)

    # Pick the better method.
    if edge_score >= EDGE_MATCH_THRESHOLD and edge_score >= color_score * 0.5:
        max_val, max_loc, best_scale, method = edge_score, edge_loc, edge_scale, "edge"
    elif color_score >= MATCH_THRESHOLD:
        max_val, max_loc, best_scale, method = color_score, color_loc, color_scale, "color"
    else:
        log.warning(
            "Notepad icon not found (edge=%.4f at %s, color=%.4f at %s, thresholds=%.2f/%.2f).",
            edge_score, edge_loc, color_score, color_loc, EDGE_MATCH_THRESHOLD, MATCH_THRESHOLD,
        )
        # Save debug images so you can inspect what went wrong.
        debug_annotated = screenshot.copy()
        cv2.rectangle(debug_annotated, edge_loc,
                      (edge_loc[0] + int(template.shape[1] * edge_scale),
                       edge_loc[1] + int(template.shape[0] * edge_scale)),
                      (0, 0, 255), 2)
        cv2.putText(debug_annotated, f"best edge={edge_score:.2f}",
                    (edge_loc[0], max(20, edge_loc[1] - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imwrite(str(ANNOTATED_PATH), debug_annotated)
        cv2.imwrite(str(OUTPUT_DIR / "desktop_edges.png"), screenshot_edges_raw)
        cv2.imwrite(str(OUTPUT_DIR / "template_edges.png"), template_edges)
        log.warning("Debug images saved to %s (best-match location) and desktop_edges.png / template_edges.png",
                    ANNOTATED_PATH)
        return None

    th, tw = template.shape[:2]
    matched_w, matched_h = int(tw * best_scale), int(th * best_scale)
    center_x = max_loc[0] + matched_w // 2
    center_y = max_loc[1] + matched_h // 2

    annotated = screenshot.copy()
    top_left = max_loc
    bottom_right = (max_loc[0] + matched_w, max_loc[1] + matched_h)

    cv2.rectangle(annotated, top_left, bottom_right, (0, 255, 0), 2)
    cv2.circle(annotated, (center_x, center_y), 6, (0, 0, 255), -1)
    cv2.putText(
        annotated,
        f"{method} score={max_val:.2f}",
        (top_left[0], max(20, top_left[1] - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    cv2.imwrite(str(ANNOTATED_PATH), annotated)
    log.debug("Annotated detection image saved to %s", ANNOTATED_PATH)

    log.info("Notepad icon detected at (%d, %d) via %s matching, score=%.4f",
             center_x, center_y, method, max_val)
    return {
        "x": center_x,
        "y": center_y,
        "score": float(max_val),
        "screenshot_path": str(screenshot_path),
        "annotated_path": str(ANNOTATED_PATH),
    }


def find_word_on_screen(word: str):
    """Take a fresh screenshot and use OCR to find a word on screen.
    Returns (center_x, center_y) of the first match, or None.

    Upscales 3x and applies Otsu threshold before OCR so Tesseract
    can read Windows 11 ClearType-rendered UI text reliably.
    Coordinates are scaled back to original screen space.
    """
    img = ImageGrab.grab()
    scale = 3

    # Preprocess: upscale + grayscale + Otsu threshold
    img_np = np.array(img)
    img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    img_up = cv2.resize(img_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, img_thresh = cv2.threshold(img_up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # PSM 11 = sparse text, good for scattered UI labels
    config = "--psm 11 --oem 3"
    data = pytesseract.image_to_data(
        img_thresh, output_type=pytesseract.Output.DICT, config=config
    )

    # Normalize search: strip/replace curly apostrophes so "Don't" matches "Don\u2019t"
    needle = word.lower().replace("\u2019", "'").replace("\u2018", "'")

    for i, text in enumerate(data["text"]):
        if not text:
            continue
        normalized = text.lower().replace("\u2019", "'").replace("\u2018", "'")
        conf = int(data["conf"][i])
        if needle in normalized and conf > 20:
            # Scale coordinates back to original screen space
            x = (data["left"][i] + data["width"][i] // 2) // scale
            y = (data["top"][i] + data["height"][i] // 2) // scale
            log.info("Found '%s' on screen at (%d, %d) conf=%d", text, x, y, conf)
            return x, y

    log.debug("Word '%s' not found on screen.", word)
    return None
