"""Find a business on Google Maps by name, without an account and for free (decision D-022).

Opens Google Maps in a headless browser, rejects the cookies and reads the listing: name, address, rating
and URL. If the search returns several places, it returns each one's name, category, address, rating and
URL instead. The reviews themselves are downloaded with Apify (D-017): without an account Maps only shows
5 of them. In a headless browser Maps does not even show the total number of reviews; the browser is not
disguised to get it (D-013), so that figure arrives later with the download.

Run as a separate process (the app does), because Playwright and Streamlit do not share an event loop:
    python -m impacto.sources.google_maps "El Corte Inglés Princesa Madrid"
"""

import json
import re
import sys
import time
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

RESULTS = 'div[role="feed"] div[role="article"]'
ICONS = re.compile(r"[-]")  # Maps draws its icons with private-use characters
RATING = re.compile(r"^\s*(\d,\d)", re.MULTILINE)


def number(value: str | None) -> float | None:
    """'4,2' -> 4.2 (Spanish decimal comma)."""
    return float(value.replace(",", ".")) if value else None


def read_listing(page) -> dict:
    rating = RATING.search(page.locator('div[role="main"]').first.inner_text())
    address = page.locator('button[data-item-id="address"]')
    return {
        "name": page.locator("h1").first.inner_text(),
        "address": (address.first.get_attribute("aria-label") or "").removeprefix("Dirección: ").strip()
        if address.count() else None,
        "rating": number(rating.group(1)) if rating else None,
        "url": page.url.split("?")[0],
    }


def read_result(article) -> dict:
    """One card of a list of results: 'Name / 4,1 / Category · Address / ...'."""
    lines = [ICONS.sub("", line).strip() for line in article.inner_text().split("\n")]
    details = next((line for line in lines if "·" in line), "")
    parts = [part.strip() for part in details.split("·") if part.strip()]
    rating = RATING.search("\n".join(lines))
    link = article.locator('a[href*="/maps/place/"]').first
    return {
        "name": link.get_attribute("aria-label"),
        "category": parts[0] if parts else None,
        "address": parts[-1] if len(parts) > 1 else None,
        "rating": number(rating.group(1)) if rating else None,
        "url": link.get_attribute("href").split("?")[0],
    }


def find_place(query: str, timeout_s: int = 30) -> dict:
    """{"place": {...}} for a single match, {"candidates": [...]} for several (at most 6), or {} for none."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(locale="es-ES", viewport={"width": 1400, "height": 900})
        target = query if query.startswith("https://") else \
            f"https://www.google.com/maps/search/{quote_plus(query)}?hl=es"
        page.goto(target)
        reject = page.get_by_role("button", name="Rechazar todo")
        if reject.count():
            reject.first.click()

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if "/maps/place/" in page.url and page.locator("h1").count():
                time.sleep(1.5)  # let the listing finish loading
                result = {"place": read_listing(page)}
                break
            results = page.locator(RESULTS)
            if results.count() > 1:
                time.sleep(1)  # let the cards fill in
                result = {"candidates": [read_result(results.nth(i)) for i in range(min(results.count(), 6))]}
                break
            time.sleep(0.5)
        else:
            result = {}
        browser.close()
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(find_place(sys.argv[1]), ensure_ascii=False))
    except PlaywrightTimeout as error:
        print(json.dumps({"error": str(error)}))
