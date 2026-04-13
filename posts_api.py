import json
import logging
import httpx
from config import API_URL, ASSETS_DIR

log = logging.getLogger(__name__)


def fetch_first_10_posts():
    try:
        log.info("Fetching posts from API: %s", API_URL)
        response = httpx.get(API_URL, timeout=10, follow_redirects=True)
        response.raise_for_status()
        posts = response.json()[:10]
        log.info("Successfully fetched %d posts from API.", len(posts))
        return posts

    except Exception as exc:
        log.warning("API request failed: %s", exc)
        log.info("Falling back to local sample_posts.json")

        fallback_path = ASSETS_DIR / "sample_posts.json"

        if not fallback_path.exists():
            log.error("Fallback file not found: %s", fallback_path)
            raise RuntimeError(
                f"API failed and fallback file was not found: {fallback_path}"
            ) from exc

        with open(fallback_path, "r", encoding="utf-8") as f:
            posts = json.load(f)

        log.info("Loaded %d posts from fallback file.", len(posts[:10]))
        return posts[:10]
